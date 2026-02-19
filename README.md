# Bristol Regional Food Network – Digital Marketplace

## Tech Stack
- Django 4.2 + Django REST Framework
- PostgreSQL (via Docker)
- Docker + Docker Compose

## Project Structure
```
bristol_marketplace/
├── config/              # Django project settings & URLs
├── marketplace/         # Main app (models, views, forms, API)
├── templates/           # HTML templates
├── static/              # CSS, JS, images
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Quick Start

### With Docker (recommended)
```bash
# Build and start all containers
docker-compose up --build

# Run migrations (in a new terminal)
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# App is available at http://localhost:8000
```

### Without Docker (local dev)
```bash
pip install -r requirements.txt

# Set up PostgreSQL locally, then:
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Key URLs
| URL | Description |
|-----|-------------|
| `/` | Homepage / product browsing |
| `/products/` | Full product list with filters |
| `/register/` | Customer registration |
| `/register/producer/` | Producer registration |
| `/login/` | Login |
| `/dashboard/` | Producer dashboard |
| `/cart/` | Shopping cart |
| `/admin/` | Django admin |
| `/api/products/` | REST API - products |
| `/api/orders/` | REST API - orders |

## Sprint 1 Target Features
- [x] Custom user model with roles (Customer, Producer, Community Group, Restaurant, Admin)
- [x] Customer registration & login (TC-001, TC-002)
- [x] Producer registration & dashboard
- [x] Product listing with allergens, organic status, seasonal info (TC-003, TC-015)
- [x] Product browsing with category/search filters
- [x] Shopping cart (session-based)
- [x] Role-based access control (TC-022)
- [x] Django REST Framework API endpoints
- [x] Docker containerisation (web + database)
