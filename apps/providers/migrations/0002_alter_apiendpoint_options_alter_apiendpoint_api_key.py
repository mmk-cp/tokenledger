from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("providers", "0001_initial")]
    operations = [
        migrations.AlterModelOptions(
            name="apiendpoint",
            options={
                "ordering": ("provider__name", "name"),
                "permissions": (("view_sensitive_api_key", "Can view sensitive API keys"),),
                "verbose_name": "API Endpoint",
                "verbose_name_plural": "API Endpoints",
            },
        ),
    ]
