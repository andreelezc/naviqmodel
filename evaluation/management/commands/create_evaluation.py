from django.core.management.base import BaseCommand
from evaluation.models import User, Evaluation, QualityProfile, Application, AnswerOption, UserResponse


class Command(BaseCommand):
    help = 'Create a new evaluation with responses'

    def handle(self, *args, **kwargs):
        # Your script here
        user = User.objects.get(username='andrea')
        quality_profile = QualityProfile.objects.get(name='Standard')
        evaluation = Evaluation.objects.create(
            user=user,
            file='https://github.com/andreelezc/naviq-validation/blob/main/chartr_9.png?raw=true',
            quality_profile=quality_profile,
            status='completed',
            title='E4 - V21',
            minimum_viable_score=0.5
        )

        selected_options_mapping = {
            1: ['N/A'],
            3: ['Descriptive axes titles'],
            4: ['Changes in data are explicit'],
            6: ['More than 5 series'],
            9: ['Data lacks a discernible order'],
            10: ['Data is labeled directly'],
            15: ['Fulfilled'],
            16: ['Fulfilled'],
            17: ['N/A'],
            18: ['Yes, colors distinguish different categories (for categorical data)'],
            19: ['Between 3 and 5 colors'],
            20: ['Colors have a purpose'],
            21: ['Colors are intuitive and follow common associations'],
            22: ['Color choices are distinguishable for color blindness'],
            23: ['Clearly stated'],
            24: ['Titles are short and concise'],
            25: ['Titles and subtitles use active voice', 'Titles and subtitles form complete sentences',
                 'Each sentence conveys an unique idea'],
            27: ['Hierarchical font sizes'],
            28: ['Center-aligned text'],
            29: ['Horizontal orientation'],
            30: ['Appropriate'],
            31: ['There is enough text/background contrast'],
            32: ['Gridlines are appropriate'],
            33: ['There are no 3D effects'],
            34: ['Emphasis is effective'],
            35: ['Data markers are appropriate'],
            36: ['Tick marks are appropriate'],
            37: ['Background or borders are plain and do not detract from the visualization'],
            40: ['Data sources are cited'],
            41: ['Author ID included'],
            45: ['Chart complexity is adecuate'],
            46: ['Messages are clear and useful'],
            47: ['N/A'],
            48: ['N/A'],
            50: ['N/A'],
            53: ['N/A']
        }

        for app_id, selected_descriptions in selected_options_mapping.items():
            application = Application.objects.get(id=app_id)
            selected_options = AnswerOption.objects.filter(
                application=application,
                description__in=selected_descriptions
            )

            user_response = UserResponse.objects.create(
                user=user,
                application=application,
                evaluation=evaluation
            )

            user_response.selected_options.set(selected_options)
            user_response.save()

        evaluation.calculate_final_score()
        evaluation.save()

        self.stdout.write(self.style.SUCCESS(f'Evaluation and responses created with ID: {evaluation.id}'))
