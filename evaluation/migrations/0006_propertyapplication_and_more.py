# Generated by Django 4.2.13 on 2024-05-13 09:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        (
            "evaluation",
            "0005_alter_profilecriterionpropertyapplication_unique_together_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="PropertyApplication",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("app_weight", models.DecimalField(decimal_places=2, max_digits=5)),
                (
                    "application",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="evaluation.application",
                    ),
                ),
                (
                    "property",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="evaluation.property",
                    ),
                ),
            ],
            options={
                "verbose_name": "Property Application",
                "verbose_name_plural": "Property Applications",
                "unique_together": {("property", "application")},
            },
        ),
        migrations.DeleteModel(name="ProfileCriterionPropertyApplication",),
    ]
