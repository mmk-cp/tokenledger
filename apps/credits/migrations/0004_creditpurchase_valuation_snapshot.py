import django.core.validators
import django.db.models.deletion
from decimal import Decimal
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("credits", "0003_paid_currency_fk"),
        ("currencies", "0002_currency_catalog"),
    ]

    operations = [
        migrations.AddField(
            model_name="creditpurchase",
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
            model_name="creditpurchase",
            name="converted_currency",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="converted_credit_purchases",
                to="currencies.currency",
            ),
        ),
        migrations.AddField(
            model_name="creditpurchase",
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
            model_name="creditpurchase",
            name="conversion_date",
            field=models.DateField(blank=True, null=True),
        ),
    ]
