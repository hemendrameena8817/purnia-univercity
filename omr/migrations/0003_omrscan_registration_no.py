from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("omr", "0002_alter_omrscan_image_alter_omrscan_sem_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="omrscan",
            name="registration_no",
            field=models.CharField(blank=True, max_length=30),
        ),
    ]
