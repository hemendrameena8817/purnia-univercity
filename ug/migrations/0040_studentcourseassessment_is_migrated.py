from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ug', '0039_ugstudentprofile_medium_of_student_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentcourseassessment',
            name='is_migrated',
            field=models.BooleanField(default=False),
        ),
    ]
