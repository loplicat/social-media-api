# Generated by Django 5.0.6 on 2024-08-16 15:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("content", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="profile",
            name="first_name",
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name="profile",
            name="last_name",
            field=models.CharField(max_length=100),
        ),
    ]
