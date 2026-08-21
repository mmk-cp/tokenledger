import django.db.models.deletion
from django.db import migrations, models


def backfill_transaction_currencies(apps, schema_editor):
    Transaction = apps.get_model("transactions", "Transaction")
    Currency = apps.get_model("currencies", "Currency")
    unresolved = set()

    for transaction in Transaction.objects.all().iterator():
        code = (transaction.currency or "").strip().upper()
        currency = Currency.objects.filter(code=code).first()
        if currency is None:
            unresolved.add(code or "<blank>")
            continue
        transaction.currency_ref_id = currency.pk
        transaction.save(update_fields=("currency_ref",))

    if unresolved:
        values = ", ".join(sorted(unresolved))
        raise RuntimeError(
            "Transaction currency migration found unresolved currency codes: "
            f"{values}. Add matching Currency records and rerun the migration."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0002_currency_catalog"),
        ("transactions", "0002_expensecategory_transaction_counterparty_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="transaction",
            name="currency_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions_migration",
                to="currencies.currency",
            ),
        ),
        migrations.RunPython(backfill_transaction_currencies, migrations.RunPython.noop),
        migrations.RemoveField(model_name="transaction", name="currency"),
        migrations.RenameField(
            model_name="transaction",
            old_name="currency_ref",
            new_name="currency",
        ),
        migrations.AlterField(
            model_name="transaction",
            name="currency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="transactions",
                to="currencies.currency",
            ),
        ),
    ]
