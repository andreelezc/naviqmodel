# from nested_admin import nested
# from django.contrib import admin
# from .models import *
# from django import forms
# from django.forms.models import BaseInlineFormSet
#
#
#
# # Inline admin for AnswerOptions within an Application
# class AnswerOptionInline(nested.NestedTabularInline):
#     model = AnswerOption
#     extra = 2  # Default number of extra forms to display
#
#
# # Admin for Applications
# @admin.register(Application)
# class ApplicationAdmin(nested.NestedModelAdmin):
#     list_display = ['name', 'response_type', 'help_text', 'help_image']
#     inlines = [AnswerOptionInline]
#
#
# # Inline admin for Applications within a Property
# class ApplicationInline(nested.NestedTabularInline):
#     model = PropertyApplication
#     extra = 1  # Number of extra forms
#
#
# # Admin for Properties
# @admin.register(Property)
# class PropertyAdmin(nested.NestedModelAdmin):
#     list_display = ['name', 'description']
#     inlines = [ApplicationInline]
#
#
# # Inline admin for Properties within a Criterion in a Quality Profile
# class ProfileCriterionPropertyInline(nested.NestedTabularInline):
#     model = ProfileCriterionProperty
#     extra = 1
#     show_change_link = True  # Allows direct editing of the property details
#
#
# # Inline admin for Criteria within a Quality Profile
# class QualityProfileCriterionInline(nested.NestedTabularInline):
#     model = QualityProfileCriterion
#     extra = 1
#     show_change_link = True  # Allows direct editing of the criterion details
#     inlines = [ProfileCriterionPropertyInline]
#
#
# # Admin for Criteria
# @admin.register(Criterion)
# class CriterionAdmin(nested.NestedModelAdmin):
#     list_display = ['name', 'description']
#
#
# # Admin for Quality Profiles
# @admin.register(QualityProfile)
# class QualityProfileAdmin(nested.NestedModelAdmin):
#     list_display = ['name', 'description', 'custom', 'user']
#     inlines = [QualityProfileCriterionInline]
#
#
# # Optional: If you need to manage UserResponses
# @admin.register(UserResponse)
# class UserResponseAdmin(nested.NestedModelAdmin):
#     list_display = ['user', 'application', 'quality_profile']
#     filter_horizontal = ['selected_options']


from nested_admin import nested
from django.contrib import admin
from .models import *
from .forms import *


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
    list_display = ['id', 'name', 'response_type', 'help_text', 'help_image']
    inlines = [AnswerOptionInline]


@admin.register(Property)
class PropertyAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description']


@admin.register(Criterion)
class CriterionAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description']


@admin.register(QualityProfile)
class QualityProfileAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'name', 'description', 'custom', 'user']
    inlines = [QualityProfileCriterionInline]


@admin.register(UserResponse)
class UserResponseAdmin(nested.NestedModelAdmin):
    list_display = ['id', 'user', 'application', 'evaluation']
    filter_horizontal = ['selected_options']


@admin.register(Evaluation)
class EvaluationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'result', 'score', 'quality_profile', 'status', 'title', 'minimum_viable_score']
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



