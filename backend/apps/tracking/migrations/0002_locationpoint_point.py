import django.contrib.gis.db.models.fields
from django.db import migrations


def add_point_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE tracking_locationpoint ADD COLUMN IF NOT EXISTS point geometry(Point, 4326);")


def drop_point_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE tracking_locationpoint DROP COLUMN IF EXISTS point;")


class Migration(migrations.Migration):

    dependencies = [
        ('tracking', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='locationpoint',
                    name='point',
                    field=django.contrib.gis.db.models.fields.PointField(blank=True, null=True, srid=4326),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_point_column, drop_point_column),
            ]
        ),
    ]
