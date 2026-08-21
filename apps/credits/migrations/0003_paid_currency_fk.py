import django.db.models.deletion
from django.db import migrations, models


def backfill_paid_currencies(apps, schema_editor):
    CreditPurchase = apps.get_model("credits", "CreditPurchase")
    Currency = apps.get_model("currencies", "Currency")
    unresolved = set()

    for purchase in CreditPurchase.objects.all().iterator():
        code = (purchase.paid_currency or "").strip().upper()
        currency = Currency.objects.filter(code=code).first()
        if currency is None:
            unresolved.add(code or "<blank>")
            continue
        purchase.paid_currency_ref_id = currency.pk
        purchase.save(update_fields=("paid_currency_ref",))

    if unresolved:
        values = ", ".join(sorted(unresolved))
        raise RuntimeError(
            "Credit purchase currency migration found unresolved currency codes: "
            f"{values}. Add matching Currency records and rerun the migration."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0002_currency_catalog"),
        ("credits", "0002_customercreditallocation"),
    ]

    operations = [
        migrations.AddField(
            model_name="creditpurchase",
            name="paid_currency_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="credit_purchases_migration",
                to="currencies.currency",
            ),
        ),
        migrations.RunPython(backfill_paid_currencies, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="creditpurchase",
            name="paid_currency",
        ),
        migrations.RenameField(
            model_name="creditpurchase",
            old_name="paid_currency_ref",
            new_name="paid_currency",
        ),
        migrations.AlterField(
            model_name="creditpurchase",
            name="paid_currency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="credit_purchases",
                to="currencies.currency",
            ),
        ),
    ]
