import django.contrib.gis.db.models.fields
from django.db import migrations


def alter_boundary_column(apps, schema_editor):
    if schema_editor.connection.vendor == 'postgresql':
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE geography_policestationboundary ALTER COLUMN boundary TYPE geometry(Geometry, 4326);")


class Migration(migrations.Migration):

    dependencies = [
        ('geography', '0003_geocodingcache'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AlterField(
                    model_name='policestationboundary',
                    name='boundary',
                    field=django.contrib.gis.db.models.fields.GeometryField(blank=True, null=True, srid=4326),
                ),
            ],
            database_operations=[
                migrations.RunPython(alter_boundary_column, reverse_code=migrations.RunPython.noop),
            ]
        ),
    ]
