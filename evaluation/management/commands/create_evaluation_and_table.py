from django.core.management.base import BaseCommand
from evaluation.models import User, Evaluation, QualityProfile, Application, UserResponse, AnswerOption
import pandas as pd

class Command(BaseCommand):
    help = 'Create an evaluation and generate a binary table from the response options'

    def handle(self, *args, **options):
        # Define your parameters directly
        username = 'andrea'  # Replace with the desired username
        profile_name = 'Standard'  # Replace with the desired profile name
        file_url = 'https://github.com/andreelezc/naviq-validation/blob/main/wtf2.png?raw=true'

        # Retrieve the user and quality profile
        user = User.objects.get(username=username)
        quality_profile = QualityProfile.objects.get(name=profile_name)

        # Create the Evaluation instance
        evaluation = Evaluation.objects.create(
            user=user,
            file=file_url,
            quality_profile=quality_profile,
            status='completed',  # Set status as needed ('draft', 'completed', 'archived')
            title='E1 - V04',
            minimum_viable_score=0.5  # Adjust as necessary
        )

        # Example of selected options mapping (you can modify this based on your needs)
        selected_options_mapping = {
            1: ['N/A'],
            3: ['N/A'],
            4: ['Changes in data are not explicit'],
            6: ['More than 5 series'],
            9: ['Data lacks a discernible order'],
            10: ['Data is labeled by legends'],
            15: ['Unfulfilled'],
            16: ['Partially fulfilled'],
            17: ['One chart type is used'],
            18: ['Yes, colors distinguish different categories (for categorical data)'],
            19: ['More than 5 colors'],
            20: ['Colors are used without clear purpose'],
            21: ['Colors are counterintuitive or confusing'],
            22: ['Color choices are not distinguishable for color blindness'],
            23: ['Not stated'],
            24: ['Titles are short and concise'],
            25: ['None of the above'],
            27: ['Font sizes are inconsistent or too small/large'],
            28: ['Left-aligned text'],
            29: ['Horizontal orientation'],
            30: ['Sparse'],
            31: ['There is enough text/background contrast'],
            32: ['N/A'],
            33: ['There are no 3D effects'],
            34: ['No particular emphasis is applied'],
            35: ['N/A'],
            36: ['N/A'],
            37: ['Background or borders are plain and do not detract from the visualization'],
            40: ['Data sources are not cited'],
            41: ['Author ID not included'],
            45: ['None of the above'],
            46: ['Messages are unclear or missing'],
            47: ['N/A'],
            48: ['N/A'],
            50: ['N/A'],
            53: ['N/A']
        }

        # Loop through each application and create UserResponse
        for app_id, selected_descriptions in selected_options_mapping.items():
            application = Application.objects.get(id=app_id)
            selected_options = AnswerOption.objects.filter(
                application=application,
                description__in=selected_descriptions
            )

            # Create the UserResponse for the current Application
            user_response = UserResponse.objects.create(
                user=user,
                application=application,
                evaluation=evaluation
            )

            # Associate the selected options with this response
            user_response.selected_options.set(selected_options)
            user_response.save()

        # Calculate the final score for the evaluation
        evaluation.calculate_final_score()
        evaluation.save()

        # Generate the binary table
        self.generate_binary_table(evaluation)

        self.stdout.write(self.style.SUCCESS(f'Evaluation created with ID: {evaluation.id} (Score {evaluation.score}) and binary table generated.'))

    def generate_binary_table(self, evaluation):
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
        # print(df.to_string(index=False, header=True))

        # Optionally, save the table to a file
        df.to_csv(f'evaluation_binary_table_{evaluation.id}.csv', index=False)
        self.stdout.write(self.style.SUCCESS(f'Binary table saved as evaluation_binary_table_{evaluation.id}.csv'))
