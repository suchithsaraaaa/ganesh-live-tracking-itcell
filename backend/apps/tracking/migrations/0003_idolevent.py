import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('idols', '0001_initial'),
        ('tracking', '0002_locationpoint_point'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='IdolEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('gpid', models.CharField(db_index=True, max_length=64)),
                ('event_type', models.CharField(choices=[('TRACKING_STARTED', 'Tracking Started'), ('TRACKING_STOPPED', 'Tracking Stopped'), ('ASSIGNMENT_CREATED', 'Assignment Created'), ('ASSIGNMENT_HANDOVER', 'Assignment Handover'), ('ZONE_ENTERED', 'Zone Entered'), ('HOLDING_POINT_ENTERED', 'Holding Point Entered'), ('VISARJAN_REACHED', 'Visarjan Site Reached'), ('IMMERSION_COMPLETED', 'Immersion Completed')], db_index=True, max_length=50)),
                ('timestamp', models.DateTimeField(db_index=True)),
                ('latitude', models.FloatField(blank=True, null=True)),
                ('longitude', models.FloatField(blank=True, null=True)),
                ('zone', models.CharField(blank=True, max_length=100)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('actor', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='idol_events_triggered', to=settings.AUTH_USER_MODEL)),
                ('idol', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='operational_events', to='idols.idol')),
                ('tracking_session', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='operational_events', to='tracking.trackingsession')),
            ],
            options={
                'ordering': ['timestamp'],
                'indexes': [
                    models.Index(fields=['idol', 'timestamp'], name='tracking_id_idol_id_e181f0_idx'),
                    models.Index(fields=['gpid', 'timestamp'], name='tracking_id_gpid_02382f_idx'),
                    models.Index(fields=['event_type', 'timestamp'], name='tracking_id_event_t_c00059_idx'),
                ],
            },
        ),
    ]
