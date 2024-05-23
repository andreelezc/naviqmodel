from django import forms
from django.forms.models import BaseInlineFormSet
from django.core.exceptions import ValidationError
from .models import ProfileCriterionPropertyApplication, ProfileCriterionProperty, QualityProfileCriterion, \
    QualityProfile, Evaluation, UserResponse
from decimal import Decimal
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.db import models


# Custom form for ProfileCriterionPropertyApplication
class ProfileCriterionPropertyApplicationForm(forms.ModelForm):
    class Meta:
        model = ProfileCriterionPropertyApplication
        fields = '__all__'

    def clean(self):
        super().clean()
        # This form now assumes validation does not need to aggregate data across other forms in the formset.
        return self.cleaned_data


# para validaciones en el admin - no anda porque muestra error sin haber errores - ver
# class BaseProfileCriterionPropertyApplicationFormset(BaseInlineFormSet):
#     def clean(self):
#         super().clean()
#         total_weight = Decimal('0.0')
#         for form in self.forms:
#             if not form.cleaned_data.get('DELETE', False) and 'app_weight' in form.cleaned_data:
#                 app_weight = form.cleaned_data.get('app_weight', Decimal('0.0'))
#                 total_weight += Decimal(app_weight)
#
#         if total_weight != Decimal('1.0'):
#             raise ValidationError("The total weight of all applications within a property must be 1.")


# Custom form for ProfileCriterionProperty
class ProfileCriterionPropertyForm(forms.ModelForm):
    class Meta:
        model = ProfileCriterionProperty
        fields = '__all__'


# Base formset for ProfileCriterionProperty
class BaseProfileCriterionPropertyFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        total_weight = sum(form.cleaned_data.get('property_weight', 0) for form in self.forms if
                           not form.cleaned_data.get('DELETE', False))
        if total_weight != 1:
            raise ValidationError("The total weight of all properties within a criterion must be 1.")


# Custom form for QualityProfileCriterion
class QualityProfileCriterionForm(forms.ModelForm):
    class Meta:
        model = QualityProfileCriterion
        fields = '__all__'


# Base formset for QualityProfileCriterion
class BaseQualityProfileCriterionFormset(BaseInlineFormSet):
    def clean(self):
        super().clean()
        total_weight = sum(form.cleaned_data.get('criterion_weight', 0) for form in self.forms if
                           not form.cleaned_data.get('DELETE', False))
        if total_weight != 1:
            raise ValidationError("The total weight of all criteria within a profile must be 1.")


# For User Registration
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(required=True, widget=forms.TextInput(
        attrs={'class': 'form-control', 'placeholder': 'Email'}))

    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'User name'}),
            'password1': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
            'password2': forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        }


# For creating an evaluation
class EvaluationForm(forms.ModelForm):
    file_url = forms.URLField(label="File URL")
    quality_profile = forms.ModelChoiceField(
        queryset=QualityProfile.objects.none(),  # Initially empty queryset
        label="Quality Profile",
        required=True,
        empty_label="------"
    )
    minimum_viable_score = forms.DecimalField(
        label="Minimum Viable Score",
        max_digits=4,
        decimal_places=2,
        required=False,
        initial=0.5,
        max_value=1,
        help_text="Define the minimum acceptable quality threshold for the evaluation. If not specified, defaults to "
                  "0.5. You can edit this value later."
    )

    class Meta:
        model = Evaluation
        fields = ['file_url', 'quality_profile', 'minimum_viable_score']

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super(EvaluationForm, self).__init__(*args, **kwargs)
        if user is not None:
            self.fields['quality_profile'].queryset = QualityProfile.objects.filter(
                models.Q(user=user) | models.Q(custom=False)
            )


# Formulario para editar solo el MVS de una Evaluation
class EvaluationScoreForm(forms.ModelForm):
    minimum_viable_score = forms.DecimalField(
        label="Minimum Viable Score",
        max_digits=4,
        decimal_places=2,
        required=False,
        # initial=0.5,
        help_text="Minimum acceptable quality threshold for the evaluation.",
        max_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = Evaluation
        fields = ['minimum_viable_score']


# Formulario para guardar respuestas (widget de acuerdo al tipo de respuesta)
class UserResponseForm(forms.ModelForm):
    class Meta:
        model = UserResponse
        fields = ['selected_options']

    def __init__(self, *args, **kwargs):
        print("DEBUG kwargs in form:", kwargs)

        answer_options = kwargs.pop('answer_options')
        application = kwargs.pop('application')
        super(UserResponseForm, self).__init__(*args, **kwargs)

        if application.response_type == 'multiple':
            self.fields['selected_options'] = forms.ModelMultipleChoiceField(
                queryset=answer_options,
                widget=forms.CheckboxSelectMultiple,
                required=True
            )
        else:
            self.fields['selected_options'] = forms.ModelChoiceField(
                queryset=answer_options,
                widget=forms.RadioSelect,
                empty_label=None,
                required=True
            )
