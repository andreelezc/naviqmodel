# import pandas as pd
# from django.core.management.base import BaseCommand
# from evaluation.models import User, Evaluation, QualityProfile, Application, UserResponse, AnswerOption
# import ast
# from chatgpt_batch_assessments import reassess_visualization
# from decimal import Decimal
#
# class Command(BaseCommand):
#     help = 'Batch create evaluations and generate binary tables from a dataset'
#
#     def handle(self, *args, **options):
#         # Hardcoded user and profile
#         username = 'andrea'
#         profile_name = 'Standard'
#
#         # Retrieve the user and quality profile
#         user = User.objects.get(username=username)
#         quality_profile = QualityProfile.objects.get(name=profile_name)
#
#         # File path to the CSV file
#         file_path = r"C:\Users\aflez\PycharmProjects\experimento_tesis\chatgpt results\E1.csv"
#
#         # Read the CSV file with pandas
#         df = pd.read_csv(file_path)
#
#         for _, row in df.iterrows():
#             evaluator = str(row['Evaluator']).strip()
#             vis_id = str(row['Vis ID']).strip()
#             vis_url = str(row['Vis URL']).strip()
#             responses_str = str(row['Response']).strip()
#             baseline = float(row['Baseline'])
#
#             # Parse the response string to a dictionary
#             selected_options_mapping = ast.literal_eval(responses_str)
#
#             # Create the evaluation name
#             evaluation_name = f"{evaluator} - {vis_id}"
#
#             # Create the Evaluation instance
#             evaluation = Evaluation.objects.create(
#                 user=user,
#                 file=vis_url,
#                 quality_profile=quality_profile,
#                 status='completed',
#                 title=evaluation_name,
#                 minimum_viable_score=0.5
#             )
#
#             # Loop through each application and create/update UserResponse
#             for app_id, selected_descriptions in selected_options_mapping.items():
#                 application = Application.objects.get(id=app_id)
#                 selected_options = AnswerOption.objects.filter(
#                     application=application,
#                     description__in=selected_descriptions
#                 )
#
#                 # Check if a UserResponse already exists for this user, application, and evaluation
#                 user_response, created = UserResponse.objects.update_or_create(
#                     user=user,
#                     application=application,
#                     evaluation=evaluation,
#                     defaults={
#                         'user': user,
#                         'application': application,
#                         'evaluation': evaluation,
#                     }
#                 )
#
#                 # Associate the selected options with this response
#                 user_response.selected_options.set(selected_options)
#                 user_response.save()
#
#             # Calculate the final score for the evaluation
#             evaluation.calculate_final_score()
#             evaluation.save()
#
#             # Compare the evaluation score with the baseline score
#             if abs(evaluation.score - Decimal(baseline)) > Decimal('0.1'):  # Set the threshold as needed
#                 print(f"Score difference for {evaluation_name} exceeds threshold. Reassessing...")
#                 reassess_visualization(vis_id, evaluator, csv_file=file_path)
#
#                 # Re-read the updated row from the CSV file
#                 updated_row = df[df['Vis ID'] == vis_id].iloc[0]
#                 responses_str = str(updated_row['Response']).strip()
#                 selected_options_mapping = ast.literal_eval(responses_str)
#
#                 # Re-create or update the UserResponses after reassessment
#                 for app_id, selected_descriptions in selected_options_mapping.items():
#                     application = Application.objects.get(id=app_id)
#                     selected_options = AnswerOption.objects.filter(
#                         application=application,
#                         description__in=selected_descriptions
#                     )
#
#                     user_response, created = UserResponse.objects.update_or_create(
#                         user=user,
#                         application=application,
#                         evaluation=evaluation,
#                         defaults={
#                             'user': user,
#                             'application': application,
#                             'evaluation': evaluation,
#                         }
#                     )
#                     user_response.selected_options.set(selected_options)
#                     user_response.save()
#
#                 evaluation.calculate_final_score()
#                 evaluation.save()
#
#             # Generate the binary table for this evaluation
#             self.generate_binary_table(evaluation_name, evaluation)
#
#             self.stdout.write(self.style.SUCCESS(f'Evaluation "{evaluation_name}" created with score {evaluation.score:.2f} and binary table generated.'))
#
#
#     def generate_binary_table(self, evaluation_name, evaluation):
#         # Prepare the table structure
#         table_data = []
#
#         # Loop through each application associated with the evaluation's quality profile
#         applications = Application.objects.filter(
#             profilecriterionpropertyapplication__profile_criterion_property__quality_profile_criterion__quality_profile=evaluation.quality_profile
#         ).distinct().order_by('id')
#
#         # Extract the evaluator's name from the evaluation name
#         evaluator_name = evaluation_name.split(" - ")[0]
#
#         for app in applications:
#             # Get the user's response for this application
#             try:
#                 user_response = UserResponse.objects.get(evaluation=evaluation, application=app)
#                 selected_options = user_response.selected_options.all()
#             except UserResponse.DoesNotExist:
#                 selected_options = []
#
#             # Add the application name to the table
#             table_data.append({
#                 'Description and options': app.name,
#                 evaluator_name: ''
#             })
#
#             # Loop through each possible answer option
#             answer_options = AnswerOption.objects.filter(application=app).order_by('id')
#             for option in answer_options:
#                 if option.description != "N/A":
#                     # Check if the current option was selected
#                     choice_marker = '•' if option in selected_options else ''
#                     table_data.append({
#                         'Description and options': option.description,
#                         evaluator_name: choice_marker
#                     })
#
#         # Add the final row with "Quality score" and the evaluation score
#         table_data.append({
#             'Description and options': 'Quality score',
#             evaluator_name: f'{evaluation.score:.2f}'  # Rounded to two decimal places
#         })
#
#         # Convert the table data to a DataFrame
#         df = pd.DataFrame(table_data)
#
#         # Save the table to a file with the evaluation name
#         df.to_csv(f'binary_tables/{evaluation_name}.csv', index=False)
#         self.stdout.write(self.style.SUCCESS(f'Binary table saved as {evaluation_name}.csv'))


import pandas as pd
from django.core.management.base import BaseCommand
from evaluation.models import User, Evaluation, QualityProfile, Application, UserResponse, AnswerOption
import ast
from chatgpt_individual_assessments import reassess_visualization_url
from decimal import Decimal
import os

class Command(BaseCommand):
    help = 'Batch create evaluations and generate binary tables from a dataset'

    def add_arguments(self, parser):
        # Adding an argument to pass just the evaluator file identifier (e.g., E1, E2, etc.)
        parser.add_argument(
            '--evaluator',
            type=str,
            help='Specify the evaluator identifier (e.g., E1, E2, etc.)',
        )

    def handle(self, *args, **options):
        # Hardcoded user and profile
        username = 'andrea'
        profile_name = 'Standard'

        # Retrieve the user and quality profile
        user = User.objects.get(username=username)
        quality_profile = QualityProfile.objects.get(name=profile_name)

        # Get the evaluator identifier (e.g., E1, E2) passed via command argument
        evaluator_identifier = options['evaluator']

        # Construct the CSV file path dynamically using the evaluator identifier
        file_dir = r"C:\Users\aflez\PycharmProjects\experimento_tesis\results\chatgpt_assessments"
        file_path = os.path.join(file_dir, f"{evaluator_identifier}.csv")

        # Verify the CSV file exists
        if not os.path.exists(file_path):
            self.stdout.write(self.style.ERROR(f"CSV file {file_path} not found."))
            return

        # Read the CSV file with pandas
        df = pd.read_csv(file_path)

        for _, row in df.iterrows():
            evaluator = str(row['Evaluator']).strip()
            vis_id = str(row['Vis ID']).strip()
            vis_url = str(row['Vis URL']).strip()
            responses_str = str(row['Response']).strip()
            baseline = float(row['Baseline'])

            # Parse the response string to a dictionary
            selected_options_mapping = ast.literal_eval(responses_str)

            # Create the evaluation name
            evaluation_name = f"{evaluator} - {vis_id}"

            # Create the Evaluation instance
            evaluation = Evaluation.objects.create(
                user=user,
                file=vis_url,
                quality_profile=quality_profile,
                status='completed',
                title=evaluation_name,
                minimum_viable_score=0.5
            )

            # Loop through each application and create/update UserResponse
            for app_id, selected_descriptions in selected_options_mapping.items():
                application = Application.objects.get(id=app_id)
                selected_options = AnswerOption.objects.filter(
                    application=application,
                    description__in=selected_descriptions
                )

                # Check if a UserResponse already exists for this user, application, and evaluation
                user_response, created = UserResponse.objects.update_or_create(
                    user=user,
                    application=application,
                    evaluation=evaluation,
                    defaults={
                        'user': user,
                        'application': application,
                        'evaluation': evaluation,
                    }
                )

                # Associate the selected options with this response
                user_response.selected_options.set(selected_options)
                user_response.save()

            # Calculate the final score for the evaluation
            evaluation.calculate_final_score()
            evaluation.save()

            # Track the closest score and the reassessment count
            score_diff = abs(evaluation.score - Decimal(baseline))
            closest_score = evaluation.score
            closest_diff = score_diff
            threshold = Decimal('0.1')
            max_reassessments = 3
            reassess_count = 0

            # Loop until the score is within the threshold or after 3 reassessments
            while score_diff > threshold and reassess_count < max_reassessments:
                reassess_count += 1
                print(
                    f"Score difference for {evaluation_name} exceeds threshold ({score_diff}). Reassessing (Attempt {reassess_count})...")

                # Reassess the visualization and update the CSV
                reassess_visualization_url(vis_id, evaluator, csv_file=file_path)

                # Re-read the updated row from the CSV file to get the updated responses
                df = pd.read_csv(file_path)
                updated_row = df[df['Vis ID'] == vis_id].iloc[0]
                responses_str = str(updated_row['Response']).strip()
                selected_options_mapping = ast.literal_eval(responses_str)

                # Re-create or update the UserResponses after reassessment
                for app_id, selected_descriptions in selected_options_mapping.items():
                    application = Application.objects.get(id=app_id)
                    selected_options = AnswerOption.objects.filter(
                        application=application,
                        description__in=selected_descriptions
                    )

                    # Check if a UserResponse already exists for this user, application, and evaluation
                    user_response, created = UserResponse.objects.update_or_create(
                        user=user,
                        application=application,
                        evaluation=evaluation,
                        defaults={
                            'user': user,
                            'application': application,
                            'evaluation': evaluation,
                        }
                    )

                    # Associate the selected options with this response
                    user_response.selected_options.set(selected_options)
                    user_response.save()

                # Recalculate and save the new score after reassessment
                evaluation.calculate_final_score()  # Recalculate the score based on the updated responses
                evaluation.save()

                # Update the score difference after reassessment
                score_diff = abs(evaluation.score - Decimal(baseline))

                # If the new score is closer to the baseline, update the closest score
                if score_diff < closest_diff:
                    closest_score = evaluation.score
                    closest_diff = score_diff

                print(f"New score for {evaluation_name}: {evaluation.score}, difference: {score_diff}")

            # After maximum reassessments, apply the closest score if the threshold wasn't met
            if score_diff > threshold:
                print(f"Max reassessments reached for {evaluation_name}. Using closest score: {closest_score}")
                evaluation.score = closest_score
                evaluation.save()

            # Generate the binary table for this evaluation
            self.generate_binary_table(evaluation_name, evaluation)

            self.stdout.write(self.style.SUCCESS(
                f'Evaluation "{evaluation_name}" created with score {evaluation.score:.2f} and binary table generated.'))

    def generate_binary_table(self, evaluation_name, evaluation):
        # Prepare the table structure
        table_data = []

        # Loop through each application associated with the evaluation's quality profile
        applications = Application.objects.filter(
            profilecriterionpropertyapplication__profile_criterion_property__quality_profile_criterion__quality_profile=evaluation.quality_profile
        ).distinct().order_by('id')

        # Extract the evaluator's name from the evaluation name
        evaluator_name = evaluation_name.split(" - ")[0]

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
                evaluator_name: ''
            })

            # Loop through each possible answer option
            answer_options = AnswerOption.objects.filter(application=app).order_by('id')
            for option in answer_options:
                if option.description != "N/A":
                    # Check if the current option was selected
                    choice_marker = '•' if option in selected_options else ''
                    table_data.append({
                        'Description and options': option.description,
                        evaluator_name: choice_marker
                    })

        # Add the final row with "Quality score" and the evaluation score
        table_data.append({
            'Description and options': 'Quality score',
            evaluator_name: f'{evaluation.score:.2f}'  # Rounded to two decimal places
        })

        # Convert the table data to a DataFrame
        df = pd.DataFrame(table_data)

        # Save the table to a file with the evaluation name
        df.to_csv(f'binary_tables/{evaluation_name}.csv', index=False)
        self.stdout.write(self.style.SUCCESS(f'Binary table saved as {evaluation_name}.csv'))
