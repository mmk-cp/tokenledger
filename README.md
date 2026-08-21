# TokenLedger


### Financial Management


Track internal financial movements.


Features:


- Purchase transactions
- Customer payments
- Expenses
- Refunds
- Adjustments
- Cash flow visibility
- Profitability reporting




### Currency Management


Support multiple currencies for financial operations.


Features:


- Fiat currencies
- Cryptocurrency currencies
- Custom exchange rates
- Historical conversion support
- USD-based financial reporting




### Wallet Management


Track operational wallets used for purchasing services.


Features:


- Multiple wallets
- Currency and network tracking
- Transaction movement visibility




### Audit & Security


Track important administrative changes.


Features:


- Automatic audit logging
- Field-level change history
- User activity tracking
- Sensitive credential protection
- Permission-based API key access




## Dashboard & Reports


TokenLedger includes an Unfold-powered Django administration dashboard with:


- Revenue overview
- Cost overview
- Net cash flow
- Credit inventory
- Customer summaries
- Provider profitability
- Expiring credits
- Wallet movements




## What TokenLedger is NOT


TokenLedger intentionally does not provide:


- AI API proxying
- Token usage tracking
- Request forwarding
- Customer self-service portal
- Billing automation
- Payment gateway integration


These features can be integrated separately when needed.




## Technology


- Python 3.12
- Django 5.2 LTS
- Django Unfold administration interface
- MySQL
- mysqlclient
- django-environ
- WhiteNoise
- Gunicorn




## Architecture


TokenLedger follows a Django domain-based architecture:



apps/
├── core
├── providers
├── wallets
├── customers
├── credits
├── transactions
├── currencies
└── customer_credentials





## Local Development


### 1. Create virtual environment


```bash
python -m venv .venv


source .venv/bin/activate
```

### 2. Install dependencies
```
pip install -r requirements.txt
```
### 3. Configure environment
cp .env.example .env

Configure MySQL:

```
DB_NAME
DB_USER
DB_PASSWORD
DB_HOST
DB_PORT
```

API credentials are operational credentials stored in the database.

Access to full API keys is controlled through Django permissions:

view_sensitive_api_key

Only trusted administrators should receive this permission.

4. Run migrations
python manage.py migrate
5. Create administrator
python manage.py createsuperuser
6. Run development server
python manage.py runserver

Admin panel:

http://127.0.0.1:8000/admin/

Production Deployment

Production requires:

```
DEBUG=False
SECRET_KEY
ALLOWED_HOSTS
MySQL configuration
HTTPS
```

Production enables:

Secure cookies
CSRF protection
HSTS support
Clickjacking protection
MIME sniffing protection

Validate deployment:

```
DJANGO_SETTINGS_MODULE=config.settings.production python manage.py check --deploy


python manage.py makemigrations --check --dry-run


python manage.py migrate --plan


python manage.py collectstatic --noinput
Docker

Start services:

docker compose up --build

Create administrator:

docker compose exec web python manage.py createsuperuser
```

Persistent data:

MySQL data: mysql_data
Uploaded media: media_data
Project Status

TokenLedger is actively evolving as an internal management platform for AI API resellers.

Current focus areas:

provider management
customer management
credit inventory
financial tracking
profitability visibility
operational reporting
License

TokenLedger is released under the MIT License.