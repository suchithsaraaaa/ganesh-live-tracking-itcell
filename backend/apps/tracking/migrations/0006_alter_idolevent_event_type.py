from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0005_alter_idolevent_event_type'),
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
                    ('REACHED_SITE', 'Reached Site'),
                    ('ZONE_ENTERED', 'Zone Entered'),
                    ('HOLDING_POINT_ENTERED', 'Holding Point Entered'),
                    ('HOLDING_POINT_EXITED', 'Holding Point Exited'),
                    ('VISARJAN_REACHED', 'Visarjan Site Reached'),
                    ('IMMERSION_COMPLETED', 'Immersion Completed'),
                    ('VISARJAN_NOT_DONE', 'Visarjan Not Done'),
                    ('SENT_TO_HOLDING', 'Sent To Holding'),
                    ('RETURNED_TO_ORIGIN', 'Returned To Origin'),
                    ('REPORT_GENERATED', 'Report Generated'),
                ],
                db_index=True,
                max_length=50,
            ),
        ),
    ]
