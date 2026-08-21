# TokenLedger

TokenLedger is an open-source AI API credit cost management system for resellers. It is intended to manage providers, API endpoints, wallets, purchases, customer allocations, transactions, and profit/loss reporting as the project evolves.

The current foundation includes core identity and audit infrastructure, provider/API endpoint inventory, operator wallet inventory, owner credit-purchase inventory, customer records and allocations, and a manually recorded financial transaction ledger. Automated usage, payment matching, invoicing, and reporting remain intentionally out of scope until their respective implementation steps.

## Technology

- Python 3.12
- Django 5.2 LTS
- Django Unfold for the complete administration interface
- MySQL with mysqlclient
- django-environ for environment-based configuration
- Django permissions for controlled API-key visibility
- WhiteNoise for production static-file serving
- Gunicorn as the production WSGI server

## Local development

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the environment template:

   ```bash
   cp .env.example .env
   ```

4. Create a MySQL database and user matching the `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` values in `.env`.

   API keys are operational credentials stored in the database. Full values are restricted by the `view_sensitive_api_key` model permissions; grant them only to trusted administrators.

5. Apply Django's built-in migrations and create an administrator:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. Start the development server:

   ```bash
   python manage.py runserver
   ```

The Unfold administration interface is available at <http://127.0.0.1:8000/admin/>.

## Settings

- `config.settings.development` is the default for local commands.
- `config.settings.production` enables production security settings and requires `SECRET_KEY`, `ALLOWED_HOSTS`, and MySQL configuration.
- Common settings live in `config.settings.base`.

Set `DJANGO_SETTINGS_MODULE=config.settings.production` in a production environment. Static assets are collected into `staticfiles/`; uploaded files are stored under `media/` by default and should use durable external storage in production deployments.

## Production deployment

Production requires a long random `SECRET_KEY`, non-empty `ALLOWED_HOSTS`, MySQL credentials, HTTPS, and `DEBUG=False`. Configure `CSRF_TRUSTED_ORIGINS` with complete HTTPS origins for public admin hosts. Production enables secure cookies, HTTPS redirection, HSTS, MIME sniffing protection, same-origin referrer policy, and clickjacking protection.

Required variables are `SECRET_KEY`, `ALLOWED_HOSTS`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`. Optional settings include `TIME_ZONE`, `LOG_LEVEL`, `DB_CONN_MAX_AGE`, `SECURE_SSL_REDIRECT`, and HSTS controls.

Validate releases with:

```bash
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py collectstatic --noinput
```

Back up MySQL and persistent media independently using encrypted, access-controlled off-host copies. Test restoration regularly and take a verified backup before migrations. Never expose `.env`, backups, logs, or media through static hosting.

## Docker

1. Copy `.env.example` to `.env` and replace the placeholder secrets. Docker overrides `DB_HOST` with the MySQL service hostname.

2. Build and start the services:

   ```bash
   docker compose up --build
   ```

3. Create an administrator account:

   ```bash
   docker compose exec web python manage.py createsuperuser
   ```

The web service runs migrations and collects static files before Gunicorn starts. MySQL data is persisted in `mysql_data`; uploaded media is persisted in `media_data`. Back up both volumes, and run migrations as a controlled release step when operating multiple replicas.

## Project layout

Domain apps live under the `apps` Python package. Every future model administration class must inherit from `unfold.admin.ModelAdmin`; the project intentionally does not use Django's default `ModelAdmin` styling. MySQL is the only supported database backend.

## License

TokenLedger is released under the MIT License. See [LICENSE](LICENSE).
