import django.db.models.deletion
from django.db import migrations, models


SEEDED_CURRENCIES = {
    "USD": ("US Dollar", "$", "FIAT", 2),
    "IRR": ("Iranian Toman", "", "FIAT", 0),
    "EUR": ("Euro", "€", "FIAT", 2),
    "USDT": ("Tether", "₮", "CRYPTO", 6),
    "BTC": ("Bitcoin", "₿", "CRYPTO", 8),
    "ETH": ("Ethereum", "Ξ", "CRYPTO", 8),
}


def seed_and_map_currencies(apps, schema_editor):
    Currency = apps.get_model("currencies", "Currency")
    ExchangeRate = apps.get_model("currencies", "ExchangeRate")

    for code, (name, symbol, currency_type, decimal_places) in SEEDED_CURRENCIES.items():
        Currency.objects.get_or_create(
            code=code,
            defaults={
                "name": name,
                "symbol": symbol,
                "currency_type": currency_type,
                "decimal_places": decimal_places,
                "is_active": True,
            },
        )

    for exchange_rate in ExchangeRate.objects.all().iterator():
        base_code = exchange_rate.base_currency.strip().upper()
        target_code = exchange_rate.target_currency.strip().upper()
        base_currency, _ = Currency.objects.get_or_create(
            code=base_code,
            defaults={
                "name": base_code,
                "currency_type": "CRYPTO",
                "decimal_places": 8,
                "is_active": True,
            },
        )
        target_currency, _ = Currency.objects.get_or_create(
            code=target_code,
            defaults={
                "name": target_code,
                "currency_type": "FIAT",
                "decimal_places": 2,
                "is_active": True,
            },
        )
        exchange_rate.base_currency_ref_id = base_currency.pk
        exchange_rate.target_currency_ref_id = target_currency.pk
        exchange_rate.save(
            update_fields=("base_currency_ref", "target_currency_ref")
        )


class Migration(migrations.Migration):
    dependencies = [("currencies", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Currency",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("code", models.CharField(max_length=20, unique=True)),
                ("name", models.CharField(max_length=100)),
                ("symbol", models.CharField(blank=True, max_length=20)),
                ("currency_type", models.CharField(choices=[("FIAT", "Fiat"), ("CRYPTO", "Crypto")], db_index=True, max_length=10)),
                ("decimal_places", models.PositiveSmallIntegerField(default=2)),
                ("is_active", models.BooleanField(db_index=True, default=True)),
            ],
            options={"verbose_name": "Currency", "verbose_name_plural": "Currencies", "ordering": ("code",)},
        ),
        migrations.AddField(
            model_name="exchangerate",
            name="base_currency_ref",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="base_exchange_rates", to="currencies.currency"),
        ),
        migrations.AddField(
            model_name="exchangerate",
            name="target_currency_ref",
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.PROTECT, related_name="target_exchange_rates", to="currencies.currency"),
        ),
        migrations.RunPython(seed_and_map_currencies, migrations.RunPython.noop),
        migrations.RemoveIndex(
            model_name="exchangerate",
            name="currencies__base_cu_4607f0_idx",
        ),
        migrations.RemoveField(model_name="exchangerate", name="base_currency"),
        migrations.RemoveField(model_name="exchangerate", name="target_currency"),
        migrations.RenameField(model_name="exchangerate", old_name="base_currency_ref", new_name="base_currency"),
        migrations.RenameField(model_name="exchangerate", old_name="target_currency_ref", new_name="target_currency"),
        migrations.AlterField(
            model_name="exchangerate",
            name="base_currency",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="base_exchange_rates", to="currencies.currency"),
        ),
        migrations.AlterField(
            model_name="exchangerate",
            name="target_currency",
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="target_exchange_rates", to="currencies.currency"),
        ),
        migrations.AddIndex(
            model_name="exchangerate",
            index=models.Index(fields=["base_currency", "target_currency", "effective_date"], name="currencies__base_cu_4607f0_idx"),
        ),
    ]
