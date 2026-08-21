from django.db import migrations, models
import django.db.models.deletion


def backfill_wallet_currencies(apps, schema_editor):
    Wallet = apps.get_model("wallets", "Wallet")
    Currency = apps.get_model("currencies", "Currency")
    unresolved = set()

    for wallet in Wallet.objects.all().iterator():
        code = (wallet.currency or "").strip().upper()
        currency = Currency.objects.filter(code=code).first()
        if currency is None:
            unresolved.add(code or "<blank>")
            continue
        wallet.currency_ref_id = currency.pk
        wallet.save(update_fields=("currency_ref",))

    if unresolved:
        values = ", ".join(sorted(unresolved))
        raise RuntimeError(
            "Wallet currency migration found unresolved currency codes: "
            f"{values}. Add matching Currency records and rerun the migration."
        )


class Migration(migrations.Migration):
    dependencies = [
        ("currencies", "0002_currency_catalog"),
        ("wallets", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="wallet",
            name="currency_ref",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="wallets_migration",
                to="currencies.currency",
            ),
        ),
        migrations.RunPython(backfill_wallet_currencies, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="wallet",
            name="wallets_wal_currenc_8bcacf_idx",
        ),
        migrations.RemoveField(model_name="wallet", name="currency"),
        migrations.RenameField(
            model_name="wallet",
            old_name="currency_ref",
            new_name="currency",
        ),
        migrations.AlterField(
            model_name="wallet",
            name="currency",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="wallets",
                to="currencies.currency",
            ),
        ),
        migrations.AddIndex(
            model_name="wallet",
            index=models.Index(
                fields=["currency", "network", "is_active"],
                name="wallets_wal_currenc_8bcacf_idx",
            ),
        ),
    ]
