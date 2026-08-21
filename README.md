# TokenLedger

TokenLedger is an open-source AI API credit cost management system for resellers. It is intended to manage providers, API endpoints, wallets, purchases, customer allocations, transactions, and profit/loss reporting as the project evolves.

This repository currently contains the project foundation only. Business models, APIs, and domain features have not been implemented.

## Technology

- Python 3.12
- Django 5.2 LTS
- Django Unfold for the complete administration interface
- MySQL with mysqlclient
- django-environ for environment-based configuration
- cryptography for encrypted upstream API keys
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

   Set `API_KEY_ENCRYPTION_KEY` to a stable Fernet key before creating API endpoints. Generate one with:

   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```

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

The web service runs migrations and collects static files before Gunicorn starts. The MySQL data is persisted in the `mysql_data` Docker volume.

## Project layout

Domain apps live under the `apps` Python package. Every future model administration class must inherit from `unfold.admin.ModelAdmin`; the project intentionally does not use Django's default `ModelAdmin` styling. MySQL is the only supported database backend.

## License

TokenLedger is released under the MIT License. See [LICENSE](LICENSE).
