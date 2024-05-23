"""
URL configuration for naviq_review_final project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from evaluation.views import *
from django.contrib.auth.views import LoginView, LogoutView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),

    # Home
    path('', home_view, name='home'),

    # Login
    path('login/', LoginView.as_view(template_name='login.html', success_url=reverse_lazy('home')), name='login'),
    path('logout/', LogoutView.as_view(next_page='home'), name='logout'),
    path('register/', register_view, name='register'),

    # Quality Profile
    path("quality-profiles/", QualityProfileListView.as_view(), name="quality_profile_list"),

    # Evaluation
    path('create-evaluation/', create_evaluation_view, name='create_evaluation'),
    path('evaluation/<int:evaluation_id>/question/<int:current_question_index>/', pregunta_siguiente, name='question_and_options'),
    path('evaluation/<int:evaluation_id>/finish/', finalize_evaluation, name='finalize_evaluation'),
    path('evaluation/<int:evaluation_id>/report/', view_evaluation_report, name='view_evaluation_report'),
    path('evaluation/<int:evaluation_id>/update-title/', update_evaluation_title, name='update_evaluation_title'),
    path('update-recommendations/<int:evaluation_id>/', update_recommendations, name='update_recommendations'),
    path('evaluation/update_mvs/<int:evaluation_id>/', update_mvs, name='update_mvs'),
    path('evaluations/', EvaluationListView.as_view(), name='list_evaluations'),
    path('evaluation/<int:pk>/delete/', EvaluationDeleteView.as_view(), name='delete_evaluation'),
    path('evaluation/<int:evaluation_id>/edit/<int:current_question_index>/', edit_evaluation, name='edit_evaluation'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)