import django.contrib.gis.db.models.fields
from django.db import migrations


def add_boundary_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE geography_policestationboundary ADD COLUMN IF NOT EXISTS boundary geometry(Polygon, 4326);")


def drop_boundary_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE geography_policestationboundary DROP COLUMN IF EXISTS boundary;")


class Migration(migrations.Migration):

    dependencies = [
        ('geography', '0001_initial'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='policestationboundary',
                    name='boundary',
                    field=django.contrib.gis.db.models.fields.PolygonField(blank=True, null=True, srid=4326),
                ),
            ],
            database_operations=[
                migrations.RunPython(add_boundary_column, drop_boundary_column),
            ]
        ),
    ]
