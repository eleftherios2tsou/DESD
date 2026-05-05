# Bristol Regional Food Network – Digital Marketplace

A Django-based marketplace connecting local Bristol producers with customers, community groups, and restaurants.

## Tech Stack
- Django 4.2 + Django REST Framework 3.15
- PostgreSQL 15 (via Docker)
- Stripe (test mode) for payments
- Pillow for image uploads
- Docker + Docker Compose

---

## Quick Start

### With Docker (recommended)

```bash
# 1. Clone the repo
git clone https://github.com/eleftherios2tsou/bristol_marketplace.git
cd bristol_marketplace

# 2. Copy environment variables
cp .env.example .env   # then fill in your Stripe test keys

# 3. Build and start
docker-compose up --build

# 4. In a second terminal — run migrations
docker-compose exec web python manage.py migrate

# 5. Create a superuser (optional)
docker-compose exec web python manage.py createsuperuser

# App is available at http://localhost:8000
```

### Without Docker (local dev)

```bash
pip install -r requirements.txt

# Set environment variables (see below), then:
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

---

## Environment Variables

Create a `.env` file in the project root (or export these in your shell):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | insecure fallback (change in prod) |
| `DEBUG` | Debug mode (`1` = on) | `1` |
| `POSTGRES_DB` | Database name | `bristol_marketplace` |
| `POSTGRES_USER` | Database user | `postgres` |
| `POSTGRES_PASSWORD` | Database password | `postgres` |
| `POSTGRES_HOST` | Database host | `db` (Docker) / `localhost` (local) |
| `POSTGRES_PORT` | Database port | `5432` |
| `STRIPE_SECRET_KEY` | Stripe secret key (test mode) | *(required for payments)* |
| `STRIPE_PUBLISHABLE_KEY` | Stripe publishable key (test mode) | *(required for payments)* |

Get free Stripe test keys at https://dashboard.stripe.com/test/apikeys

---

## Test Accounts

Run these commands after `migrate` and `createsuperuser` to seed demo data, or create accounts manually via the registration pages:

| Role | Username | Password | Notes |
|------|----------|----------|-------|
| Superuser | `admin` | *(set during createsuperuser)* | Django admin access |
| Producer | Register at `/register/producer/` | — | Gets producer dashboard |
| Customer | Register at `/register/` | — | Gets shopping cart |

**Stripe test card:** `4242 4242 4242 4242` · expiry: 12/34 · CVC: 123

---

## URL Map

### Public
| URL | Description |
|-----|-------------|
| `/` | Homepage — featured products |
| `/products/` | Browse all products (search, filter) |
| `/products/<id>/` | Product detail + reviews |
| `/producers/<id>/` | Public producer profile |
| `/register/` | Customer registration |
| `/register/producer/` | Producer registration |
| `/login/` | Login |
| `/logout/` | Logout |

### Customer (login required)
| URL | Description |
|-----|-------------|
| `/cart/` | Shopping cart |
| `/cart/add/<id>/` | Add product to cart |
| `/cart/remove/<id>/` | Remove from cart |
| `/cart/update/<id>/` | Update quantity |
| `/checkout/` | Delivery details form |
| `/checkout/payment/` | Stripe Elements payment page |
| `/checkout/complete/` | Post-payment order creation |
| `/orders/<id>/confirmation/` | Order confirmation |
| `/orders/history/` | Order history |
| `/products/<id>/review/` | Submit product review |
| `/account/settings/` | Email / password / profile settings |
| `/account/delete/` | GDPR account deletion |

### Producer (login required, producer role)
| URL | Description |
|-----|-------------|
| `/dashboard/` | Producer dashboard |
| `/dashboard/products/add/` | Add new product |
| `/dashboard/products/<id>/edit/` | Edit product |
| `/dashboard/products/<id>/delete/` | Delete product |
| `/producer/orders/` | Order management |
| `/producer/orders/<id>/update/` | Update order status |
| `/producer/payments/` | Weekly payment settlements |
| `/producer/payments/export/` | Download CSV |

### REST API
| URL | Method | Description |
|-----|--------|-------------|
| `/api/products/` | GET | List active products |
| `/api/products/` | POST | Create product (producers) |
| `/api/products/<id>/` | GET/PUT/PATCH/DELETE | Product detail/edit |
| `/api/products/my/` | GET | Producer's own products |
| `/api/categories/` | GET | List categories |
| `/api/orders/` | GET | Customer's / producer's orders |
| `/api/orders/` | POST | Create order (customers) |
| `/api/orders/<id>/` | PATCH | Update status (producers) |

### Admin
| URL | Description |
|-----|-------------|
| `/admin/` | Django admin |
| `/admin/marketplace/metrics/` | Marketplace metrics dashboard (superuser) |

---

## Sprint Summary

### Sprint 1 (Eleftherios & Gia)
| ID | Feature | Assignee |
|----|---------|----------|
| S1-001 | Docker + Django setup | Eleftherios |
| S1-002 | Custom user model with roles | Eleftherios |
| S1-003 | Customer registration & login | Gia |
| S1-004 | Producer registration + ProducerProfile | Gia |
| S1-005 | RBAC decorators | Eleftherios |
| S1-006 | Product & Category models | Eleftherios |
| S1-007 | Producer dashboard + product CRUD | Eleftherios |
| S1-008 | Product browsing + search/filter | Gia |
| S1-009 | Shopping cart (session-based) | Gia |
| S1-010 | Order model + basic checkout | Gia |
| S1-011 | Django REST Framework API | Eleftherios |
| S1-012 | Migrations & admin | Eleftherios |
| S1-013 | Base HTML templates | Eleftherios |

### Sprint 2 (Eleftherios & Gia)
| ID | Feature | Assignee |
|----|---------|----------|
| S2-001 | Producer order management | Gia |
| S2-002 | Customer order history | Gia |
| S2-003 | Stock decrement on checkout | Gia |
| S2-004 | Product image upload | Eleftherios |
| S2-005 | Public producer profile | Eleftherios |
| S2-006 | Order confirmation emails | Eleftherios |
| S2-007 | User account settings | Gia |
| S2-008 | Order API enhancements | Gia |
| S2-009 | Delivery date validation | Gia |
| S2-010 | Featured products on homepage | Eleftherios |
| S2-011 | Product reviews & ratings | Eleftherios |
| S2-012 | Responsive / mobile layout | Eleftherios |

### Sprint 3 (Eleftherios & Gia Ngo)
| ID | Feature | Assignee | Status |
|----|---------|----------|--------|
| S3-001 | Stripe payment integration | Eleftherios | Done |
| S3-002 | Multi-vendor order split & payment distribution | Eleftherios | Done |
| S3-003 | Producer weekly payment settlement + CSV | Eleftherios | Done |
| S3-004 | Product search functionality | Gia Ngo | Done |
| S3-005 | Organic certification filter | Gia Ngo | Done |
| S3-006 | Seasonal availability management | Gia Ngo | Done |
| S3-007 | Producer stock / inventory update | Gia Ngo | Done |
| S3-008 | Order history with reorder | Gia Ngo | Done |
| S3-009 | Food miles display | Eleftherios | Done |
| S3-010 | Community group & restaurant account types | Gia Ngo | Done |
| S3-011 | Security hardening & GDPR | Eleftherios | Done |
| S3-012 | Admin metrics dashboard | Eleftherios | Done |
| S3-013 | End-to-end testing & bug fixes | Eleftherios | Done |
| S3-014 | README & submission prep | Eleftherios | Done |
| S3-015 | Surplus produce discounts | Gia Ngo | Done |
| S3-016 | Low stock notifications | Eleftherios | Done |

---

## Running Tests

```bash
# With Docker
docker-compose exec web python manage.py test marketplace

# Locally
python manage.py test marketplace
```

---



| ID      | Task Title                                   | Description / Acceptance Criteria | Test Cases | Priority | Assignee | Estimate | Status |
|---------|----------------------------------------------|-----------------------------------|------------|----------|----------|----------|--------|
| S1-001  | Project setup: Django + Docker Compose       | Initialise Django project with config app, set up docker-compose.yml with web and db (Postgres) containers, Dockerfile, requirements.txt | — | Critical | Eleftherios | 4h | Done |
| S1-002  | Custom User model with roles                 | Extend AbstractUser with role field (Customer, Producer, Community Group, Restaurant, Admin). Configure AUTH_USER_MODEL. | TC-022 | Critical | Eleftherios | 3h | Done |
| S1-003  | Customer registration & login                | Registration form, login/logout views, session management, password hashing. Redirect based on role. | TC-001, TC-002, TC-022 | Critical | Gia Ngo | 4h | Done |
| S1-004  | Producer registration + ProducerProfile model| Producer-specific registration with business name, address, postcode. Create ProducerProfile on save. | TC-001 | Critical | Gia Ngo | 3h | Done |
| S1-005  | Role-based access control (RBAC)             | Decorators/middleware to prevent customers accessing producer features and vice versa. Unauthorised access shows error. | TC-022 | Critical | Eleftherios | 3h | Done |
| S1-006  | Product & Category models                    | Product model with: name, description, price, stock, allergens, organic flag, harvest date, best before, farm origin, seasonal availability, 48h lead time. | TC-003, TC-015 | Critical | Eleftherios | 3h | Done |
| S1-007  | Producer: create/edit/list products          | Producer dashboard with product CRUD. ProductForm using Django ModelForm. | TC-003 | Critical | Eleftherios | 5h | Done |
| S1-008  | Product browsing + search/filter             | Product list page with category filter, search by name, organic filter. Product detail page showing allergens, farm origin, harvest date. | TC-004, TC-015 | Critical | Gia Ngo | 4h | Done |
| S1-009  | Shopping cart (session-based)                | Add/remove/update cart items. Cart persists during session. Shows producer info and subtotals. | TC-006 | High | Gia Ngo | 3h | Done |
| S1-010  | Order model + basic checkout                 | Order and OrderItem models. Basic checkout flow with delivery address, date (min 48h), 5% commission calculation. | TC-007 | High | Gia Ngo | 5h | Done |
| S1-011  | Django REST Framework API setup              | Install DRF, configure authentication. Product and Order viewsets with serializers. Basic API browsable interface. | — | High | Eleftherios | 3h | Done |
| S1-012  | Database migrations & admin setup            | Run and test migrations. Register all models in Django admin with useful list displays and filters. | — | High | Eleftherios | 2h | Done |
| S1-013  | Base HTML templates                          | Base template with navbar (login/logout, role-aware links), home page, and shared CSS. | — | High | Eleftherios | 3h | Done |

## Sprint 2 Target Features

| ID | Task Title | Description / Acceptance Criteria | Test Cases | Priority | Assignee | Estimate | Status |
|----|------------|-----------------------------------|------------|----------|----------|----------|--------|
| S2-001 | Producer order management | Producers see a dashboard view listing all orders containing their products. Can update order status: Pending → Confirmed → Delivered. Orders scoped to logged-in producer only. | TC-009, TC-010 | Critical | Gia Ngo | 4h | Done |
| S2-002 | Customer order history | Authenticated customers can view a list of their past orders with status, itemised products, subtotals, delivery date, and commission. | TC-008 | Critical | Gia Ngo | 3h | Done |
| S2-003 | Stock decrement on checkout | When an order is placed, each product's stock field is reduced by the ordered quantity. Products with zero stock show as out of stock and cannot be added to cart. | TC-011 | Critical | Gia Ngo | 2h | Done |
| S2-004 | Product image upload | Producers can upload an image when creating or editing a product. Image displayed on the product list card and product detail page. Use Pillow + Django's ImageField. Store in /media/. | — | High | Eleftherios | 4h | Done |
| S2-005 | Public producer profile page | Public page at /producers/<id>/ showing business name, description, postcode, and all active products from that producer. Product detail page links to the producer profile. | — | High | Eleftherios | 3h | Done |
| S2-006 | Order confirmation email | On successful checkout, send an email to the customer summarising the order. Send a separate notification email to each producer whose products were ordered. Use Django's built-in email backend. | — | High | Eleftherios | 3h | Done |
| S2-007 | User account settings | Authenticated users can update their email address and change their password. Producers can additionally edit their business name, address, postcode, and description from their dashboard. | — | Medium | Gia Ngo | 3h | Done |
| S2-008 | Order API enhancements | Customers can create orders via POST /api/orders/. Producers can update order status via PATCH /api/orders/<id>/. Serializer validates delivery date is at least 48 hours ahead. | — | Medium | Gia Ngo | 3h | Done |
| S2-009 | Delivery date validation | Enforce 48-hour minimum lead time on the checkout form with a clear validation error. Block past dates. | TC-007 | Medium | Gia Ngo | 2h | Done |
| S2-010 | Featured products on homepage | Homepage displays the 6 most recently added active products in a grid. Each card shows name, producer, price, and organic badge. Links to the full product list. | — | Medium | Eleftherios | 2h | Done |
| S2-011 | Product reviews & ratings | Customers with a Delivered order containing a product can leave a 1–5 star rating and a text comment. Average rating displayed on the product detail page. | TC-024 | Low | Eleftherios | 4h | Done |
| S2-012 | Responsive / mobile layout | Fix layouts that break below 768px — navbar collapses, product grid stacks, forms are full width. Tested on mobile viewport in browser dev tools. | — | Low | Eleftherios | 3h | Done |

## Sprint 3 Target Features

| ID | Task Title | Description / Acceptance Criteria | Test Cases | Priority | Assignee | Est. | Status |
|----|------------|-----------------------------------|------------|----------|----------|------|--------|
| S3-001 | Stripe payment integration | Integrate Stripe (test mode) for checkout. Customer enters card details via Stripe Elements. PaymentIntent recorded against Order. Order status set to Paid. Failed payments show clear error. | TC-007, TC-008 | Critical | Eleftherios | 6h | Done |
| S3-002 | Multi-vendor order split & payment distribution | Checkout groups items by producer with separate subtotals. 5% commission deducted. Order confirmation shows full per-producer breakdown. Each producer notified for their items only. | TC-008 | Critical | Eleftherios | 5h | Done |
| S3-003 | Producer weekly payment settlement view | Producers view a Payments page showing weekly settlements by ISO week: gross order value, 5% commission, net payout (95%), and individual order line breakdown. Reports downloadable as CSV. Running UK tax-year total shown. | TC-012 | Critical | Eleftherios | 5h | Done |
| S3-004 | Product search functionality | Search bar queries product name, description, and producer business name (case-insensitive, partial match). Empty results show friendly message. Search combines with category and organic filters. | TC-005 | High | Gia Ngo | 3h | Done |
| S3-005 | Organic certification filter | Filter toggle shows only certified organic products. Organic badge displayed on product cards and detail pages. Combines with category and search filters. | TC-014 | High | Gia Ngo | 2h | Done |
| S3-006 | Seasonal availability management | Producers set seasonal dates and availability status (In Season / Out of Season / Coming Soon). Out-of-season products hidden from customer catalogue. In-season badge shown on product cards. | TC-016 | High | Gia Ngo | 3h | Done |
| S3-007 | Producer stock / inventory update | Producers update stock quantity from the dashboard without a full product edit. Stock changes take immediate effect. Zero-stock products show Out of Stock to customers and cannot be added to cart. | TC-011 | High | Gia Ngo | 3h | Done |
| S3-008 | Order history with reorder | Customer order history sorted most-recent-first shows order number, date, delivery date, producer names, status, and total. Reorder button adds items to cart, flagging unavailable products. | TC-021 | High | Gia Ngo | 4h | Done |
| S3-009 | Food miles display | Calculate straight-line distance between customer postcode and producer farm postcode using Haversine formula. Display food miles on product detail page. Cart page shows cumulative food miles for all items. | TC-013 | Medium | Eleftherios | 4h | Done |
| S3-010 | Community group & restaurant account types | Registration supports Community Group and Restaurant roles. Restaurant accounts can set up a recurring weekly order template — add products, manage the template, and add all items to cart in one click. | TC-017, TC-018 | Medium | Gia Ngo | 5h | Done |
| S3-011 | Security hardening & GDPR | CSRF protection on all forms. Login rate-limiting: lockout after 5 failed attempts, 15-minute cooldown via Django cache. Password minimum 8 characters enforced by validator. Users can delete their account and all personal data (GDPR right to erasure) via a confirmation modal. | TC-022 | Critical | Eleftherios | 4h | Done |
| S3-012 | Admin dashboard — marketplace metrics | Custom view at /admin/marketplace/metrics/ showing: total registered producers, customers, active products, total orders, paid/confirmed/delivered order counts, commission revenue to date, gross revenue, and orders by status. Superuser-only access. | TC-025 | Medium | Eleftherios | 3h | Done |
| S3-013 | End-to-end testing & bug fixes | 40+ automated Django test cases written covering authentication, RBAC, products & search, cart & stock, delivery validation, orders, reviews, GDPR deletion, and admin access. Six production bugs identified and fixed across reorder view, food miles, ProductForm validation, and cart commission display. | All TCs | Critical | Eleftherios | 6h | Done |
| S3-014 | README & submission prep | README updated with complete Docker and local setup instructions, environment variable reference (including Stripe keys), test account guidance, Stripe test card details, full URL map, sprint summary tables, automated test instructions, and contributions matrix. | — | High | Eleftherios | 2h | Done |
| S3-015 | Surplus produce discounts | Producers mark a product as discounted and set a reduced sale price. Sale price validated to be lower than original. Discounted products show sale price on product cards and detail pages. Discount price applied at cart add time and carries through to Stripe payment amount. | TC-019 | Medium | Gia Ngo | 4h | Done |
| S3-016 | Low stock notifications | When a product's stock falls below a configurable threshold (default: 5 units, set per product), an email alert is sent to the producer. Alert banner also shown in the producer dashboard until stock is replenished. | TC-023 | Medium | Eleftherios | 3h | Done |
