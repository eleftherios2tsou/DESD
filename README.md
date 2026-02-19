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


| ID      | Task Title                                   | Description / Acceptance Criteria | Test Cases | Priority | Assignee | Estimate | Status |
|---------|----------------------------------------------|-----------------------------------|------------|----------|----------|----------|--------|
| S1-001  | Project setup: Django + Docker Compose       | Initialise Django project with config app, set up docker-compose.yml with web and db (Postgres) containers, Dockerfile, requirements.txt | — | Critical | TBD | 4h | To Do |
| S1-002  | Custom User model with roles                 | Extend AbstractUser with role field (Customer, Producer, Community Group, Restaurant, Admin). Configure AUTH_USER_MODEL. | TC-022 | Critical | TBD | 3h | To Do |
| S1-003  | Customer registration & login                | Registration form, login/logout views, session management, password hashing. Redirect based on role. | TC-001, TC-002, TC-022 | Critical | TBD | 4h | To Do |
| S1-004  | Producer registration + ProducerProfile model| Producer-specific registration with business name, address, postcode. Create ProducerProfile on save. | TC-001 | Critical | TBD | 3h | To Do |
| S1-005  | Role-based access control (RBAC)             | Decorators/middleware to prevent customers accessing producer features and vice versa. Unauthorised access shows error. | TC-022 | Critical | TBD | 3h | To Do |
| S1-006  | Product & Category models                    | Product model with: name, description, price, stock, allergens, organic flag, harvest date, best before, farm origin, seasonal availability, 48h lead time. | TC-003, TC-015 | Critical | TBD | 3h | To Do |
| S1-007  | Producer: create/edit/list products          | Producer dashboard with product CRUD. ProductForm using Django ModelForm. | TC-003 | Critical | TBD | 5h | To Do |
| S1-008  | Product browsing + search/filter             | Product list page with category filter, search by name, organic filter. Product detail page showing allergens, farm origin, harvest date. | TC-004, TC-015 | Critical | TBD | 4h | To Do |
| S1-009  | Shopping cart (session-based)                | Add/remove/update cart items. Cart persists during session. Shows producer info and subtotals. | TC-006 | High | TBD | 3h | To Do |
| S1-010  | Order model + basic checkout                 | Order and OrderItem models. Basic checkout flow with delivery address, date (min 48h), 5% commission calculation. | TC-007 | High | TBD | 5h | To Do |
| S1-011  | Django REST Framework API setup              | Install DRF, configure authentication. Product and Order viewsets with serializers. Basic API browsable interface. | — | High | TBD | 3h | To Do |
| S1-012  | Database migrations & admin setup            | Run and test migrations. Register all models in Django admin with useful list displays and filters. | — | High | TBD | 2h | To Do |
| S1-013  | Base HTML templates                          | Base template with navbar (login/logout, role-aware links), home page, and shared CSS. | — | High | TBD | 3h | To Do |

