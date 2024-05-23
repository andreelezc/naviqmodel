from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from ckeditor.fields import RichTextField


# Abstract base class for evaluative entities
class EvaluativeEntity(models.Model):
    name = models.CharField(max_length=255)
    description = RichTextField(blank=True, null=True)

    class Meta:
        abstract = True


# Quality Profile Model
class QualityProfile(models.Model):
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True, null=True)
    custom = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Quality Profile"
        verbose_name_plural = "Quality Profiles"


# Criterion Model (inherits from EvaluativeEntity)
class Criterion(EvaluativeEntity):
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Criterion"
        verbose_name_plural = "Criteria"

    def calculate_score(self, quality_profile, user, evaluation):
        total_score = Decimal('0.0')
        detailed_properties = {}  # Dictionary to store detailed scores by property

        quality_profile_criterion = QualityProfileCriterion.objects.get(quality_profile=quality_profile, criterion=self)
        profile_criterion_properties = ProfileCriterionProperty.objects.filter(
            quality_profile_criterion=quality_profile_criterion)

        for profile_criterion_property in profile_criterion_properties:
            # The property's calculate_score_for_user returns a tuple: (score, detailed_applications)
            property_score, property_details = profile_criterion_property.property.calculate_score_for_user(
                user, evaluation, quality_profile_criterion)

            # Aggregate the property scores and weights
            total_score += property_score * profile_criterion_property.property_weight

            # Store the detailed scores for each property along with its weight
            detailed_properties[profile_criterion_property.property.name] = {
                'score': str(property_score),
                'weight': str(profile_criterion_property.property_weight),
                'description': profile_criterion_property.property.description,
                'details': property_details  # Nested details from applications
            }

        return total_score, detailed_properties


# Property Model (inherits from EvaluativeEntity)
class Property(EvaluativeEntity):
    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Property"
        verbose_name_plural = "Properties"

    def calculate_score_for_user(self, user, evaluation, quality_profile_criterion):
        # Fetch all ProfileCriterionProperty instances related to this property
        profile_criterion_properties = ProfileCriterionProperty.objects.filter(
            property=self,
            quality_profile_criterion=quality_profile_criterion
        )
        total_score = Decimal('0.0')
        detailed_applications = {}  # To store detailed scores by application

        # Iterate over each ProfileCriterionProperty to handle applications separately
        for profile_criterion_property in profile_criterion_properties:
            applications = Application.objects.filter(
                profilecriterionpropertyapplication__profile_criterion_property=profile_criterion_property
            ).distinct()

            # Check which applications have "N/A" selected by the user
            na_responses = UserResponse.objects.filter(
                user=user,
                selected_options__description="N/A",
                application__in=applications,
                evaluation=evaluation
            )
            applications_with_na = [response.application for response in na_responses]

            # Calculate weights: Only redistribute weights if applications are excluded because of "N/A"
            if applications.count() != applications.exclude(id__in=[app.id for app in applications_with_na]).count():
                weight_per_app = Decimal(1) / Decimal(
                    applications.exclude(id__in=[app.id for app in applications_with_na]).count())
                weights = {app.id: weight_per_app for app in
                           applications.exclude(id__in=[app.id for app in applications_with_na])}
            else:
                # Assign original weights from the ProfileCriterionPropertyApplication if no exclusions
                weights = {app.id: app.profilecriterionpropertyapplication_set.get(
                    profile_criterion_property=profile_criterion_property).app_weight for app in applications}

            # Calculate scores for applications being considered
            for app in applications:
                try:
                    user_response = UserResponse.objects.get(user=user, application=app, evaluation=evaluation)
                    selected_options = user_response.selected_options.all()
                    app_score = app.calculate_score(selected_options)

                    if app_score is not None:
                        weighted_app_score = app_score * weights[app.id]
                        if app not in applications_with_na:
                            total_score += app_score * weights[app.id]

                        detailed_applications[app.name] = {
                            'score': str(weighted_app_score),
                            'weight': str(weights[app.id]),
                            'description': app.description,
                            'user_response': ', '.join([option.description for option in selected_options])
                        }
                    else:
                        detailed_applications[app.name] = {
                            'score': 'N/A',
                            'weight': 'N/A',
                            'description': app.description,
                            'user_response': ', '.join([option.description for option in selected_options])
                        }
                except UserResponse.DoesNotExist:
                    detailed_applications[app.name] = {
                        'score': '0',
                        'weight': str(weights[app.id] if app.id in weights else 'N/A'),
                        'description': app.description,
                        'note': 'No response found'
                    }
                    continue

        return total_score, detailed_applications


# Application Model (inherits from EvaluativeEntity)
class Application(EvaluativeEntity):
    response_type = models.CharField(max_length=10,
                                     choices=[('single', 'Single Choice'), ('multiple', 'Multiple Choice')],
                                     default='single')
    help_text = RichTextField(blank=True, null=True)
    help_image = models.ImageField(blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Application"
        verbose_name_plural = "Applications"

    def calculate_score(self, selected_options):
        # For single-choice applications
        if self.response_type == "single":
            if len(selected_options) != 1:
                raise ValueError("A single choice application must have exactly one selected option.")
            selected_option = selected_options.first()
            return selected_option.get_value()

        # For multiple-choice applications
        elif self.response_type == "multiple":
            total_score = Decimal(0)
            for option in selected_options:
                if option.description != "N/A":
                    value = option.get_value()
                    if value is not None:
                        total_score += value
            return total_score

        else:
            raise ValueError("Unrecognized response type.")


# Intermediate Model to connect QualityProfile and Criterion, and manage criterion weight
class QualityProfileCriterion(models.Model):
    quality_profile = models.ForeignKey(QualityProfile, on_delete=models.CASCADE)
    criterion = models.ForeignKey(Criterion, on_delete=models.CASCADE)
    criterion_weight = models.DecimalField(max_digits=5, decimal_places=2)

    def __str__(self):
        return f"{self.quality_profile} - {self.criterion}"

    class Meta:
        unique_together = ('quality_profile', 'criterion')
        verbose_name = "Quality Profile Criterion"
        verbose_name_plural = "Quality Profile Criteria"


# Intermediate Model to connect QualityProfile, Criterion, and Property for property weight
class ProfileCriterionProperty(models.Model):
    quality_profile_criterion = models.ForeignKey(QualityProfileCriterion, on_delete=models.CASCADE)
    property = models.ForeignKey(Property, on_delete=models.CASCADE)
    property_weight = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        unique_together = ('quality_profile_criterion', 'property')
        verbose_name = "Quality Profile Criterion Property"
        verbose_name_plural = "Quality Profile Criterion Properties"


# Intermediate Model to connect an Application within a QualityProfile
class ProfileCriterionPropertyApplication(models.Model):
    profile_criterion_property = models.ForeignKey(ProfileCriterionProperty, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    app_weight = models.DecimalField(max_digits=5, decimal_places=2)

    class Meta:
        verbose_name = "Profile Criterion Property Application"
        verbose_name_plural = "Profile Criterion Property Applications"


# Model for AnswerOption
class AnswerOption(models.Model):
    application = models.ForeignKey(Application, related_name='answer_options', on_delete=models.CASCADE)
    description = models.TextField()
    value = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)

    def get_value(self):
        return self.value

    def __str__(self):
        return self.description

    class Meta:
        verbose_name = "Answer Option"
        verbose_name_plural = "Answer Options"


# Model for Evaluation
class Evaluation(models.Model):
    user = models.ForeignKey(User, related_name='evaluations', on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    result = models.TextField(blank=True, null=True)
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    file = models.URLField(verbose_name="File URL")
    quality_profile = models.ForeignKey(QualityProfile, related_name='evaluations', on_delete=models.PROTECT)
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('archived', 'Archived')
    ]
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    title = models.CharField(max_length=200, verbose_name="Title", blank=True, null=True, default="New Evaluation")
    minimum_viable_score = models.DecimalField(max_digits=4, decimal_places=2, default=0.5)
    detailed_scores = models.JSONField(default=dict)

    def create_evaluation(self, file, user, quality_profile):
        self.file = file
        self.user = user
        self.quality_profile = quality_profile
        self.save()

    def mark_as_draft(self):
        self.status = 'draft'
        self.save()

    def mark_as_completed(self):
        self.status = 'completed'
        self.save()

    def mark_as_archived(self):
        self.status = 'archived'
        self.save()

    def calculate_final_score(self):
        total_score = Decimal('0.0')
        detailed_criteria = {}  # This will only store criterion-level details now

        # Calculating scores for criteria
        for profile_criterion in self.quality_profile.qualityprofilecriterion_set.all():
            criterion = profile_criterion.criterion
            criterion_score, criterion_details = criterion.calculate_score(self.quality_profile, self.user, self)
            detailed_criteria[criterion.name] = {
                'score': str(criterion_score),
                'weight': str(profile_criterion.criterion_weight),
                'description': criterion.description,
                'details': criterion_details  # This includes property details from Criterion model
            }
            total_score += criterion_score * profile_criterion.criterion_weight

        self.score = total_score
        self.detailed_scores = {'criteria': detailed_criteria}  # Updated to reflect the new structure
        self.result = self.assign_result()
        self.save()

        return total_score

    def assign_result(self):
        if 0 <= self.score < 0.33:
            return "Low Quality"
        elif 0.33 <= self.score < 0.66:
            return "Medium Quality"
        else:
            return "High Quality"

    class Meta:
        verbose_name = "Evaluation"
        verbose_name_plural = "Evaluations"


# Model for UserResponse
class UserResponse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    application = models.ForeignKey(Application, related_name='responses', on_delete=models.CASCADE)
    evaluation = models.ForeignKey(Evaluation, related_name='responses', on_delete=models.CASCADE)
    selected_options = models.ManyToManyField(AnswerOption, related_name="responses")

    def __str__(self):
        selected_descriptions = [f"{option.description} (Value: {option.value})" for option in self.selected_options.all()]
        descriptions_str = ", ".join(selected_descriptions)
        return f"{self.application.name}: {descriptions_str}"

    class Meta:
        unique_together = ('user', 'application', 'evaluation')
        verbose_name = "User Response"
        verbose_name_plural = "User Responses"
