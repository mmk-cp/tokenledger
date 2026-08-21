from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("customer_credentials", "0003_alter_customercredential_options")]
    operations = [
        migrations.AlterModelOptions(
            name="customercredential",
            options={
                "ordering": ("-created_at",),
                "permissions": (("view_sensitive_api_key", "Can view sensitive API keys"),),
                "verbose_name": "Customer Credential",
                "verbose_name_plural": "Customer Credentials",
            },
        ),
    ]
