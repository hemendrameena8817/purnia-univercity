# Generated migration for changing ind_marks_obtained from DecimalField to CharField

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('llb', '0010_remove_llbstudentcourseassessment_exam_result_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='llbstudentcourseassessment',
            name='ind_marks_obtained',
            field=models.CharField(blank=True, help_text='Individual MARKS OBTAINED (numeric or \'AB\' for absent)', max_length=10, null=True),
        ),
    ]
