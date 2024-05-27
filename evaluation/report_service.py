import json

import plotly.graph_objs as go
import plotly.utils

from .models import Application, ProfileCriterionPropertyApplication, ProfileCriterionProperty, \
    QualityProfileCriterion

from decimal import Decimal, InvalidOperation


class ReportService:
    def __init__(self, evaluation, user):
        """Initialize the ReportService with an evaluation instance and the user requesting the report."""
        self.evaluation = evaluation
        self.user = user

    def generate_report(self):
        # Ensure that only the user who owns the evaluation can access the report.
        if self.evaluation.user != self.user:
            raise PermissionError("User does not have permission to access this report.")

        # Use precomputed total score and detailed data for criteria and properties
        total_score = self.evaluation.score
        detailed_criteria_data = self.evaluation.detailed_scores.get('criteria', {})

        # Extract properties and applications from nested criteria details
        detailed_property_data = {}
        detailed_applications = {}

        for criterion_name, criterion_info in detailed_criteria_data.items():
            for property_name, property_info in criterion_info['details'].items():
                detailed_property_data[property_name] = property_info

                for application_name, application_info in property_info['details'].items():
                    detailed_applications[application_name] = application_info

        # Sort criteria by score in descending order
        sorted_criteria_data = {k: v for k, v in
                                sorted(detailed_criteria_data.items(), key=lambda item: Decimal(item[1]['score']),
                                       reverse=True)}

        # Generate visualizations for criteria and properties
        criteria_chart_json = self._create_criteria_scores_chart(sorted_criteria_data)
        properties_chart_json = self._create_top_properties_chart(detailed_property_data)

        # Compute dynamic parts of the report: recommendations and deltas:
        # 1- Calculate the maximum contribution (potential contribution) for each application
        applications_max_contribution = self.calculate_contribution_for_all_applications()

        # 2- Calculate the sum of total potential contributions for verification
        max_contribution_total = sum(applications_max_contribution.values())

        # 3- Calculate the delta for each application
        applications_deltas = self.calculate_deltas_for_all_applications()

        # Generate recommendations
        recommendations = self.generate_recommendations()

        # Compile all report data into a dictionary
        report_data = {
            'total_score': total_score,
            'evaluation_id': self.evaluation.id,
            'quality_profile': self.evaluation.quality_profile.name,
            'minimum_viable_score': self.evaluation.minimum_viable_score,
            'criteria_scores': detailed_criteria_data,
            'criteria_chart': criteria_chart_json,
            'property_scores': detailed_property_data,
            'properties_chart': properties_chart_json,
            'detailed_applications': detailed_applications,
            'max_contribution_total': max_contribution_total,
            'recommendations': recommendations,
            'applications_deltas': applications_deltas,
        }

        return report_data

    def _create_criteria_scores_chart(self, criteria_scores):
        """Generate a bar chart for criteria scores using Plotly."""
        # Extract criteria names and values after sorting
        criteria_names = list(criteria_scores.keys())
        criteria_values = [round(float(info['score']), 2) for info in criteria_scores.values()]

        text_labels = [f'{value}' for value in criteria_values]

        # Calculate maximum value and adjust for label space
        max_value = max(criteria_values) if criteria_values else 0
        adjusted_max = max(max_value * 1.2, 1)

        # Create a horizontal bar chart with fixed bar width
        chart = go.Figure([go.Bar(
            x=criteria_values,
            y=criteria_names,
            orientation='h',
            marker=dict(color='#14213D'),
            text=text_labels,
            textposition='outside',
            width=0.5  # Fixed bar width to control the visual height of each bar
        )])
        chart.update_layout(
            xaxis_title='Score',
            plot_bgcolor='white',
            yaxis=dict(
                # categoryorder='total ascending',
                title='',
                tickfont=dict(size=14),
                # Setting the y-axis to 'tickmode' can further aid in spacing control
                tickmode='array',
                tickvals=list(range(len(criteria_names))),
                ticktext=criteria_names
            ),
            xaxis=dict(
                range=[0, adjusted_max],
                tickfont=dict(size=14),
            ),
            title_font=dict(size=16),
            width=580,
            height=400,  # Static height, adjust as needed or keep dynamic calculation
            margin=dict(l=10, r=10, t=10, b=10, pad=10)
        )
        return json.dumps(chart, cls=plotly.utils.PlotlyJSONEncoder)

    def _create_top_properties_chart(self, property_scores, top_n=5):
        """
        Generate a bar chart for the top N properties based on their scores using Plotly.

        """
        # Sort properties by score and select the top N entries.
        top_properties = sorted(property_scores.items(), key=lambda x: float(x[1]['score']), reverse=True)[:top_n]
        property_names = [prop[0] for prop in top_properties]
        property_values = [round(float(prop[1]['score']), 2) for prop in top_properties]

        # Prepare text labels for display on the bars.
        text_labels = [f'{value}' for value in property_values]

        # Calculate maximum score to adjust the x-axis range, ensuring all labels fit.
        max_value = max(property_values) if property_values else 0
        adjusted_max = max(max_value * 1.2, 1)

        # Create a horizontal bar chart with custom settings for aesthetics.
        chart = go.Figure([go.Bar(
            x=property_values,
            y=property_names,
            orientation='h',
            marker=dict(color='#14213D'),
            text=text_labels,
            textposition='outside',
            width=0.5  # Fixed bar width to control the visual height of each bar
        )])
        # Configure the layout of the chart with a dynamic x-axis range, custom margins, and a set plot size.
        chart.update_layout(
            xaxis_title='Score',
            plot_bgcolor='white',
            yaxis=dict(
                # categoryorder='total ascending',
                title='',
                tickfont=dict(size=14),
            ),
            xaxis=dict(
                range=[0, adjusted_max],
                tickfont=dict(size=14),
            ),
            title_font=dict(size=16),
            width=580,
            height=400,
            margin=dict(l=10, r=10, t=10, b=10, pad=10)
        )
        return json.dumps(chart, cls=plotly.utils.PlotlyJSONEncoder)

    def generate_recommendations(self):
        """
            Generate a list of recommended applications to improve based on their delta values,
            prioritizing those with the largest delta. The recommendations are made to help the
            evaluation score reach or exceed the minimum viable score set by the user.

            Returns:
                recommendations (list): A list of application names that are recommended for improvement.
        """

        # Check if the current score already meets or exceeds the minimum viable score.
        # If it does, no recommendations are needed.
        if self.evaluation.score >= self.evaluation.minimum_viable_score:
            return []

        recommendations = []

        # Calculate the score gap that needs to be covered to meet the minimum viable score.
        remaining_delta = self.evaluation.minimum_viable_score - self.evaluation.score
        application_deltas = self.calculate_deltas_for_all_applications()

        # Calculate the deltas for all applications and sort them in descending order of their delta values (largest
        # delta first).
        sorted_applications = sorted(application_deltas.items(), key=lambda x: x[1], reverse=True)

        # Iterate over the applications, adding them to the recommendations list until the remaining delta is covered
        # or all applications are considered.
        for app_name, delta in sorted_applications:
            # If the remaining delta is already covered, stop adding more recommendations.
            if remaining_delta <= 0 or delta <= 0:  # Skip applications that don't contribute to the remaining delta
                # (delta is zero or less)
                continue

            # Get the application instance
            application = Application.objects.get(name=app_name)
            recommendations.append({
                'name': app_name,
                'help_text': application.help_text,
                'help_img': application.help_image.url if application.help_image else None
            })

            # Reduce the remaining delta by the delta of the current application.
            remaining_delta -= delta

        return recommendations

    def calculate_contribution_for_all_applications(self):
        max_contributions = {}
        for profile_criterion in QualityProfileCriterion.objects.filter(
                quality_profile=self.evaluation.quality_profile):
            for profile_criterion_property in ProfileCriterionProperty.objects.filter(
                    quality_profile_criterion=profile_criterion):
                for profile_criterion_property_application in ProfileCriterionPropertyApplication.objects.filter(
                        profile_criterion_property=profile_criterion_property):
                    application = profile_criterion_property_application.application
                    max_contributions[application.name] = self.calculate_contribution_for_application(application,
                                                                                                      profile_criterion,
                                                                                                      profile_criterion_property,
                                                                                                      profile_criterion_property_application)
        return max_contributions

    def calculate_contribution_for_application(self, application, profile_criterion, profile_criterion_property,
                                               profile_criterion_property_application):
        app_weight_in_property = profile_criterion_property_application.app_weight
        property_weight_in_criterion = profile_criterion_property.property_weight
        criterion_weight_in_profile = profile_criterion.criterion_weight

        contribution = app_weight_in_property * property_weight_in_criterion * criterion_weight_in_profile
        return contribution

    def calculate_deltas_for_all_applications(self):
        deltas = {}
        for profile_criterion in QualityProfileCriterion.objects.filter(
                quality_profile=self.evaluation.quality_profile):
            for profile_criterion_property in ProfileCriterionProperty.objects.filter(
                    quality_profile_criterion=profile_criterion):
                for profile_criterion_property_application in ProfileCriterionPropertyApplication.objects.filter(
                        profile_criterion_property=profile_criterion_property):
                    application = profile_criterion_property_application.application
                    current_score = self.get_application_score(application)

                    if current_score is None:
                        continue  # Skip N/A scores

                    max_contribution = self.calculate_contribution_for_application(application, profile_criterion,
                                                                                   profile_criterion_property,
                                                                                   profile_criterion_property_application)
                    deltas[application.name] = max_contribution * (1 - current_score)
        return deltas

    def get_application_score(self, application):
        """
        Retrieve the current score for an application from precomputed detailed_scores.
        """
        detailed_criteria = self.evaluation.detailed_scores.get('criteria', {})
        for criterion_name, criterion_details in detailed_criteria.items():
            for property_name, property_details in criterion_details['details'].items():
                if application.name in property_details['details']:
                    app_details = property_details['details'][application.name]
                    score_str = app_details['score']
                    if score_str == "N/A":
                        return None  # Return None to indicate non-applicable
                    try:
                        return Decimal(score_str)
                    except (ValueError, InvalidOperation) as e:
                        print(f"Error converting score to Decimal for {application.name}: {score_str} - {e}")
                        raise

        return Decimal('0.0'    )
