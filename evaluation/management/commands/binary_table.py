from django.core.management.base import BaseCommand
from evaluation.models import Evaluation, Application, UserResponse, AnswerOption
import pandas as pd

class Command(BaseCommand):
    help = 'Generate a binary table from the response options for an evaluation'

    def handle(self, *args, **options):
        # Retrieve the evaluation you're interested in
        evaluation = Evaluation.objects.get(id=6)  # Replace with the actual evaluation ID

        # Prepare the table structure
        table_data = []

        # Loop through each application associated with the evaluation's quality profile
        applications = Application.objects.filter(
            profilecriterionpropertyapplication__profile_criterion_property__quality_profile_criterion__quality_profile=evaluation.quality_profile
        ).distinct().order_by('id')

        for app in applications:
            # Get the user's response for this application
            try:
                user_response = UserResponse.objects.get(evaluation=evaluation, application=app)
                selected_options = user_response.selected_options.all()
            except UserResponse.DoesNotExist:
                selected_options = []

            # Add the application name to the table
            table_data.append({
                'Description and options': app.name,
                'Choice': ''
            })

            # Loop through each possible answer option
            answer_options = AnswerOption.objects.filter(application=app).order_by('id')
            for option in answer_options:
                if option.description != "N/A":
                    # Check if the current option was selected
                    choice_marker = '•' if option in selected_options else ''
                    table_data.append({
                        'Description and options': option.description,
                        'Choice': choice_marker
                    })

        # Convert the table data to a DataFrame and print it
        df = pd.DataFrame(table_data)
        print(df.head(53))
