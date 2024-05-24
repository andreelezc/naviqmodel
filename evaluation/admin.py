from nested_admin import nested
from django.contrib import admin
from .models import *
from .forms import *
from django.db import transaction
from datetime import datetime


# Custom action to duplicate records
def duplicate_model(modeladmin, request, queryset):
    with transaction.atomic():
        for quality_profile in queryset:
            original_quality_profile_id = quality_profile.id
            new_name = f"{quality_profile.name} (Copy {datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"
            quality_profile.id = None  # Clear the primary key to create a new instance
            quality_profile.name = new_name  # Assign the new unique name
            quality_profile.save()

            # Duplicate all related QualityProfileCriterion objects
            for criterion in QualityProfileCriterion.objects.filter(quality_profile_id=original_quality_profile_id):
                original_criterion_id = criterion.id
                criterion.id = None
                criterion.quality_profile = quality_profile
                criterion.save()

                # Duplicate all related ProfileCriterionProperty objects
                for property in ProfileCriterionProperty.objects.filter(quality_profile_criterion_id=original_criterion_id):
                    original_property_id = property.id
                    property.id = None
                    property.quality_profile_criterion = criterion
                    property.save()

                    # Duplicate all related ProfileCriterionPropertyApplication objects
                    for application in ProfileCriterionPropertyApplication.objects.filter(profile_criterion_property_id=original_property_id):
                        application.id = None
                        application.profile_criterion_property = property
                        application.save()


duplicate_model.short_description = "Duplicate selected records"


class AnswerOptionInline(nested.NestedTabularInline):
    model = AnswerOption
    extra = 2


class ApplicationInline(nested.NestedTabularInline):
    model = ProfileCriterionPropertyApplication
    # form = ProfileCriterionPropertyApplicationForm
    # formset = BaseProfileCriterionPropertyApplicationFormset
    extra = 1


class ProfileCriterionPropertyInline(nested.NestedTabularInline):
    model = ProfileCriterionProperty
    # form = ProfileCriterionPropertyForm
    # formset = BaseProfileCriterionPropertyFormset
    extra = 1
    inlines = [ApplicationInline]


class QualityProfileCriterionInline(nested.NestedTabularInline):
    model = QualityProfileCriterion
    # form = QualityProfileCriterionForm
    # formset = BaseQualityProfileCriterionFormset
    extra = 1
    inlines = [ProfileCriterionPropertyInline]


@admin.register(Application)
class ApplicationAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description', 'response_type', 'help_text', 'help_image']
    list_editable = ['name', 'description', 'response_type', 'help_text', 'help_image']
    inlines = [AnswerOptionInline]


@admin.register(Property)
class PropertyAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description']
    list_editable = ['name', 'description']


@admin.register(Criterion)
class CriterionAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description']
    list_editable = ['name', 'description']


@admin.register(QualityProfile)
class QualityProfileAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description', 'custom', 'user']
    inlines = [QualityProfileCriterionInline]
    actions = [duplicate_model]


@admin.register(UserResponse)
class UserResponseAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'user', 'evaluation', '__str__']
    filter_horizontal = ['selected_options']


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'result', 'score', 'quality_profile', 'status', 'title',
                    'minimum_viable_score']
    readonly_fields = ['date', 'result', 'score', 'detailed_scores']
    search_fields = ['user__username', 'title', 'status']
    list_filter = ['status', 'date', 'quality_profile']
    fieldsets = (
        (None, {
            'fields': ('user', 'file', 'quality_profile', 'status', 'title', 'minimum_viable_score')
        }),
        ('Results', {
            'fields': ('score', 'result', 'detailed_scores')
        }),
    )
