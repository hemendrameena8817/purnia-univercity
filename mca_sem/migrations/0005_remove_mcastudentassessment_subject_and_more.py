import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mca_sem', '0004_mcacommoncoursestructure_mcacoursestructure_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='mcastudentassessment',
            name='subject',
        ),
        migrations.AlterUniqueTogether(
            name='mcaexamschedule',
            unique_together=set(),
        ),
        migrations.AddField(
            model_name='mcacoursestructure',
            name='description',
            field=models.TextField(blank=True, help_text='Course Description', null=True),
        ),
        migrations.AddField(
            model_name='mcacoursestructure',
            name='label',
            field=models.CharField(blank=True, help_text='Assessment label (e.g. CIA-Theory, ESE-Practical)', max_length=100, null=True),
        ),
        migrations.AddField(
            model_name='mcaexamschedule',
            name='course_structure',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='exam_schedules', to='mca_sem.mcacoursestructure'),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='course_code',
            field=models.CharField(blank=True, help_text='Course Code', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='course_name',
            field=models.CharField(blank=True, help_text='Course Name', max_length=500, null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='course_type',
            field=models.CharField(blank=True, help_text='Course Type', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='max_credit',
            field=models.IntegerField(blank=True, help_text='Course Credit', null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='max_marks',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Course Marks', max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='min_marks',
            field=models.DecimalField(blank=True, decimal_places=2, help_text='Pass Mark', max_digits=10, null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='paper_code',
            field=models.CharField(blank=True, help_text='Paper Code', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='mcacoursestructure',
            name='semester',
            field=models.CharField(blank=True, help_text='Semester', max_length=20, null=True),
        ),
        migrations.RemoveField(
            model_name='mcaexamschedule',
            name='subject',
        ),
        migrations.DeleteModel(
            name='MCASubject',
        ),
    ]
