from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0004_alter_idolevent_event_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='idolevent',
            name='event_type',
            field=models.CharField(
                choices=[
                    ('TRACKING_STARTED', 'Tracking Started'),
                    ('TRACKING_STOPPED', 'Tracking Stopped'),
                    ('ASSIGNMENT_CREATED', 'Assignment Created'),
                    ('ASSIGNMENT_HANDOVER', 'Assignment Handover'),
                    ('ASSIGNMENT_ENDED', 'Assignment Ended'),
                    ('ZONE_ENTERED', 'Zone Entered'),
                    ('HOLDING_POINT_ENTERED', 'Holding Point Entered'),
                    ('HOLDING_POINT_EXITED', 'Holding Point Exited'),
                    ('VISARJAN_REACHED', 'Visarjan Site Reached'),
                    ('IMMERSION_COMPLETED', 'Immersion Completed'),
                    ('REPORT_GENERATED', 'Report Generated'),
                ],
                db_index=True,
                max_length=50
            ),
        ),
    ]
