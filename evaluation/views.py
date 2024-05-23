from .models import *
from django.template.loader import render_to_string
from evaluation.forms import CustomUserCreationForm, EvaluationForm, UserResponseForm, EvaluationScoreForm
from django.shortcuts import render, redirect, get_object_or_404, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.views.generic import CreateView, ListView, UpdateView, DeleteView
from django.views.decorators.http import require_POST
from django.urls import reverse_lazy, reverse
from django.http import JsonResponse, Http404, HttpResponseRedirect, HttpResponseNotFound
from itertools import chain
from django import forms
from .report_service import ReportService


def home_view(request):
    # Construct hierarchical tree -- data in JSON
    tree_data = {
        "name": "Quality",
        "description": "We define the quality of a narrative visualization as <i>'the degree to which the "
                       "visualization satisfies the declared and implicit needs of the various stakeholders and, "
                       "therefore, adds value'</i>, in accordance with ISO/IEC 25010. In order to get concrete "
                       "measures, we model the abstract concept of quality based on Criteria and Properties.",
        "children": []
    }

    # Retrieve the "standard" quality profile (case-insensitive)
    quality_profile_name = "standard"
    quality_profile = QualityProfile.objects.filter(name__iexact=quality_profile_name).first()

    if quality_profile:
        for profile_criterion in QualityProfileCriterion.objects.filter(quality_profile=quality_profile):
            criterion = profile_criterion.criterion
            criterion_dict = {
                "name": criterion.name,
                "description": criterion.description,
                "children": []
            }

            profile_criterion_properties = ProfileCriterionProperty.objects.filter(
                quality_profile_criterion=profile_criterion)
            for profile_criterion_property in profile_criterion_properties:
                property = profile_criterion_property.property
                property_dict = {
                    "name": property.name,
                    "description": property.description,
                    "children": []
                }

                profile_criterion_property_applications = ProfileCriterionPropertyApplication.objects.filter(
                    profile_criterion_property=profile_criterion_property)
                for profile_criterion_property_application in profile_criterion_property_applications:
                    app = profile_criterion_property_application.application
                    app_dict = {
                        "name": app.name,
                        "description": app.help_text if app.help_text else "No description available"
                    }
                    property_dict["children"].append(app_dict)

                criterion_dict["children"].append(property_dict)

            tree_data["children"].append(criterion_dict)

    return render(request, 'home.html', {'tree_data': tree_data})


def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Iniciamos sesión con el usuario recién registrado

            # Obtenemos la URL a la que redirigir después del inicio de sesión
            next_url = request.POST.get('next') or 'home'
            return redirect(next_url)
    else:
        form = CustomUserCreationForm()
    return render(request, 'register.html', {'form': form})


# Vistas para Quality Profile
class QualityProfileListView(ListView):
    model = QualityProfile
    template_name = 'quality_profile/quality_profile_list.html'
    context_object_name = 'qualityprofiles'

    def get_queryset(self):
        # Si el usuario está autenticado, mostrar perfiles personalizados y predeterminados.
        if self.request.user.is_authenticated:
            user_profiles = QualityProfile.objects.filter(user=self.request.user).order_by('name')
            default_profiles = QualityProfile.objects.filter(user__isnull=True).order_by('name')
            return list(chain(default_profiles, user_profiles))
        # Si el usuario no está autenticado, mostrar solo perfiles predeterminados.
        else:
            return QualityProfile.objects.filter(user__isnull=True).order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Puedes agregar más información al contexto si es necesario.
        return context


# Vistas para Evaluation
@login_required
def create_evaluation_view(request):
    if request.method == 'POST':
        form = EvaluationForm(request.POST, user=request.user)
        if form.is_valid():
            evaluation = Evaluation(
                user=request.user,
                file=form.cleaned_data['file_url'],
                quality_profile=form.cleaned_data['quality_profile'],
                minimum_viable_score=form.cleaned_data['minimum_viable_score'],
                status='draft',  # Initial status 'draft'
            )
            evaluation.save()
            return redirect('question_and_options', evaluation_id=evaluation.id, current_question_index=0)
    else:
        form = EvaluationForm(user=request.user)

    return render(request, 'evaluation/create_evaluation.html', {'form': form})


# For editing and retrieving purposes
def get_current_evaluation_with_responses(user, evaluation_id):
    try:
        evaluation = Evaluation.objects.get(id=evaluation_id, user=user)
        user_responses = UserResponse.objects.filter(user=user, evaluation=evaluation)
        return evaluation, user_responses
    except Evaluation.DoesNotExist:
        return None, None


@login_required
def pregunta_siguiente(request, evaluation_id, current_question_index=0):
    # Ensure index is non-negative
    if current_question_index < 0:
        current_question_index = 0

    # Retrieve the evaluation and ensure it exists
    evaluation = get_object_or_404(Evaluation, id=evaluation_id, user=request.user)

    # Retrieve applications based on the quality profile
    applications = Application.objects.filter(
        profilecriterionpropertyapplication__profile_criterion_property__quality_profile_criterion__quality_profile=evaluation.quality_profile
    ).distinct().order_by('id')

    # Redirect to the finalization view if all questions have been answered
    if current_question_index >= len(applications):
        return redirect('finalize_evaluation', evaluation_id=evaluation.id)

    # Get the current application and its associated answer options
    application = applications[current_question_index]
    answer_options = AnswerOption.objects.filter(application=application)

    # Check if the current question is the last one
    is_last_question = current_question_index == len(applications) - 1

    # Fetch existing responses if any (used for editing an evaluation)
    _, user_responses = get_current_evaluation_with_responses(request.user, evaluation_id)
    current_response = user_responses.filter(application=application).first()

    if request.method == 'POST':
        # Handle form submission
        form = UserResponseForm(request.POST, answer_options=answer_options, application=application)

        if form.is_valid():
            selected_options_data = form.cleaned_data['selected_options']

            # Handle both single and multiple choice types
            if application.response_type == 'multiple':
                selected_options_ids = [option.id for option in selected_options_data]
            else:
                selected_options_ids = [selected_options_data.id] if selected_options_data else []

            # Create or update the user response
            user_response, created = UserResponse.objects.get_or_create(
                user=request.user,
                application=application,
                evaluation=evaluation
            )

            user_response.selected_options.set(selected_options_ids)
            user_response.save()

            # Redirect to the next question or finalize the evaluation
            if is_last_question:
                return redirect('finalize_evaluation', evaluation_id=evaluation.id)
            else:
                return redirect('question_and_options', evaluation_id=evaluation.id,
                                current_question_index=current_question_index + 1)
    else:
        # Pre-fill the form with existing responses for editing
        if current_response:
            initial_selected_options = [option.id for option in current_response.selected_options.all()]
            form = UserResponseForm(answer_options=answer_options, application=application,
                                    initial={'selected_options': initial_selected_options})
        else:
            form = UserResponseForm(answer_options=answer_options, application=application)

    # Render the question and options template with the context
    return render(request, 'evaluation/question_and_options.html', {
        'form': form,
        'application': application,
        'is_last_question': is_last_question,
        'current_question_index': current_question_index,
        'total_questions': len(applications),
        'evaluation': evaluation,
        'answer_options': answer_options
    })


@login_required
def finalize_evaluation(request, evaluation_id):
    # Fetch the evaluation by ID
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)

    # Check if the logged-in user is the owner of the evaluation
    if evaluation.user != request.user:
        messages.warning(request, "The current user is not the owner of the evaluation.")
        return redirect('create_evaluation')

    # Handle the POST request when the last question is submitted
    if request.method == 'POST':
        # Fetch all applications linked with the evaluation's quality profile
        applications = Application.objects.filter(
            profilecriterionpropertyapplication__profile_criterion_property__quality_profile_criterion__quality_profile=evaluation.quality_profile
        ).distinct().order_by('id')

        # Process each application and user response
        for application in applications:
            answer_options = AnswerOption.objects.filter(application=application)
            form = UserResponseForm(request.POST, answer_options=answer_options, application=application)

            if form.is_valid():
                # Update or create user responses for each application
                user_response, created = UserResponse.objects.get_or_create(
                    user=request.user,
                    application=application,
                    evaluation=evaluation
                )

                user_response.selected_options.clear()
                selected_options_ids = request.POST.getlist('selected_options')
                for option_id in selected_options_ids:
                    option = AnswerOption.objects.get(id=option_id)
                    user_response.selected_options.add(option)

                user_response.save()

        # Check if the evaluation is being edited
        is_edit = request.POST.get("is_edit") == "true"

        if is_edit and evaluation.status == "completed":
            messages.success(request, "The evaluation has been successfully edited.")
        else:
            messages.success(request, "The evaluation has been completed.")

        # Mark the evaluation as completed and calculate the final score
        evaluation.mark_as_completed()
        evaluation.calculate_final_score()
        evaluation.save()

        # Generate report data
        report_service = ReportService(evaluation, request.user)
        report_data = report_service.generate_report()

        # Instantiate the form to show MVS on report
        mvs_form = EvaluationScoreForm(instance=evaluation)

        # Render the evaluation report template with report data
        return render(request, 'evaluation/evaluation_report.html', {
            'evaluation': evaluation,
            'report_data': report_data,
            'form': mvs_form
        })
    else:
        # Redirect to home if the request method is not POST
        messages.warning(request, "Invalid access.")
        return redirect('home')


# Actualizar el título o nombre de la evaluación
@login_required
@require_POST
def update_evaluation_title(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id, user=request.user)
    new_title = request.POST.get('title', '')

    if new_title:
        evaluation.title = new_title
        evaluation.save()
        return JsonResponse({"success": True, "new_title": new_title})

    return JsonResponse({"success": False})


@login_required
def update_mvs(request, evaluation_id):
    if request.method == 'POST':
        evaluation = get_object_or_404(Evaluation, id=evaluation_id)
        form = EvaluationScoreForm(request.POST, instance=evaluation)
        if form.is_valid():
            form.save()
            # Devolver una respuesta JSON con el mensaje de éxito
            return JsonResponse({'success': True, 'message': 'MVS updated successfully!'})
    # Manejar errores o request no POST aquí
    return JsonResponse({'success': False, 'message': 'An error occurred'})


@login_required
def update_recommendations(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    report_service = ReportService(evaluation, request.user)
    recommendations = report_service.generate_recommendations()
    # Renderizar el fragmento de HTML de las nuevas recomendaciones utilizando una plantilla
    html_content = render_to_string('evaluation/evaluation_recommendations.html', {'recommendations': recommendations},
                                    request=request)
    return HttpResponse(html_content)


class EvaluationListView(LoginRequiredMixin, ListView):
    model = Evaluation
    template_name = 'evaluation/evaluation_list.html'
    context_object_name = 'evaluations'

    def get_queryset(self):
        # Filtrar las evaluaciones para mostrar solo las del usuario actual
        return Evaluation.objects.filter(user=self.request.user).order_by('-date')


# Para ver los reportes desde la lista de evaluaciones
@login_required
def view_evaluation_report(request, evaluation_id):
    evaluation = get_object_or_404(Evaluation, id=evaluation_id)
    report_service = ReportService(evaluation, request.user)
    report_data = report_service.generate_report()
    mvs_form = EvaluationScoreForm(instance=evaluation)  # Crear la instancia del formulario

    # Add 'from_list' to the context with a value of True
    return render(request, 'evaluation/evaluation_report.html', {
        'evaluation': evaluation,
        'report_data': report_data,
        'form': mvs_form,
        'from_list': True  # Indicates the user came from the evaluations list
    })


class EvaluationDeleteView(DeleteView):
    model = Evaluation

    def get_object(self, queryset=None):
        obj = super().get_object()
        # Verifica que la evaluación pertenezca al usuario (ajusta según tus reglas de negocio)
        if obj.user != self.request.user:
            raise Http404("The requested evaluation was not found.")
        return obj

    def delete(self, request, *args, **kwargs):
        # Obtener el objeto
        self.object = self.get_object()

        # Eliminar el objeto
        self.object.delete()

        # Agregar mensaje de éxito
        messages.success(request, 'Evaluation successfully deleted!')

        # Si la solicitud es AJAX, devolver una respuesta JSON
        if request.is_ajax():
            return JsonResponse({"status": "success"})

        # Si no es AJAX, continuar con el flujo habitual
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        # URL a la que redirigir después de una eliminación exitosa
        return reverse_lazy('list_evaluations')


@login_required
def edit_evaluation(request, evaluation_id, current_question_index=0):
    # Fetch the current evaluation and its responses
    evaluation, _ = get_current_evaluation_with_responses(request.user, evaluation_id)
    if not evaluation:
        return HttpResponseNotFound('Evaluation not found.')

    # Retrieve all applications associated with the quality profile of the evaluation
    applications = Application.objects.filter(
        profilecriterionpropertyapplication__profile_criterion_property__quality_profile_criterion__quality_profile=evaluation.quality_profile
    ).distinct().order_by('id')

    # Handle case when the current index is beyond the number of applications
    if current_question_index >= len(applications):
        # Redirect to the report view when all questions have been answered
        return redirect('view_evaluation_report', evaluation_id=evaluation.id)

    # Get the current application based on the index
    application = applications[current_question_index]

    if request.method == 'POST':
        # Handle form submission
        answer_options = AnswerOption.objects.filter(application=application)
        form = UserResponseForm(request.POST, answer_options=answer_options, application=application)

        if form.is_valid():
            # Get or create a UserResponse object for the current user, application, and evaluation
            user_response, _ = UserResponse.objects.get_or_create(
                user=request.user,
                application=application,
                evaluation=evaluation
            )

            # Clear any previous selections and add new ones
            user_response.selected_options.clear()
            selected_options_data = form.cleaned_data['selected_options']
            selected_options_ids = [so.id for so in selected_options_data] if application.response_type == 'multiple' else [selected_options_data.id]
            for option_id in selected_options_ids:
                option = AnswerOption.objects.get(id=option_id)
                user_response.selected_options.add(option)

            user_response.save()

            # Redirect to the next question or finalize the evaluation
            next_question_index = current_question_index + 1
            return redirect('edit_evaluation', evaluation_id=evaluation.id, current_question_index=next_question_index)
    else:
        # Handle GET request - render the form with pre-filled data
        answer_options = AnswerOption.objects.filter(application=application)
        user_response, _ = UserResponse.objects.get_or_create(
            user=request.user,
            application=application,
            evaluation=evaluation
        )
        initial_selected_options = [option.id for option in user_response.selected_options.all()]
        form = UserResponseForm(answer_options=answer_options, application=application, initial={'selected_options': initial_selected_options})

    # Context for the template
    context = {
        'form': form,
        'application': application,
        'is_last_question': current_question_index == len(applications) - 1,
        'current_question_index': current_question_index,
        'total_questions': len(applications),
        'evaluation': evaluation,
        'is_edit': True  # Indicate that this is an edit session
    }

    return render(request, 'evaluation/question_and_options.html', context)
