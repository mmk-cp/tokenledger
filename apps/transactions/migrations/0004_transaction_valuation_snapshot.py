import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0002_currency_catalog"),
        ("transactions", "0003_currency_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="converted_amount",
            field=models.DecimalField(
                blank=True,
                decimal_places=12,
                max_digits=24,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("1E-12"))],
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="converted_currency",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="converted_transactions",
                to="currencies.currency",
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="conversion_rate",
            field=models.DecimalField(
                blank=True,
                decimal_places=12,
                max_digits=24,
                null=True,
                validators=[django.core.validators.MinValueValidator(Decimal("1E-12"))],
            ),
        ),
        migrations.AddField(
            model_name="transaction",
            name="conversion_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
