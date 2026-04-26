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

# Set up PostgreSQL locally, then run from the root(bristol_marketplace):
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

| ID | Task Title | Description / Acceptance Criteria | Test Cases | Priority | Assignee | Estimate | Status |
|----|------------|-----------------------------------|------------|----------|----------|----------|--------|
| S3-001 | Stripe payment integration | Integrate Stripe (test mode) for checkout. Customer enters card details via Stripe Elements. On success, PaymentIntent recorded against Order. Order status set to Paid. Failed payments surface a clear error message. | TC-007, TC-008 | Critical | Eleftherios | 6h | To Do |
| S3-002 | Multi-vendor order split & payment distribution | When a cart contains products from multiple producers, checkout creates one Order and separate per-producer sub-totals. 5% commission deducted; 95% allocated to each producer. Order confirmation shows full breakdown per producer. | TC-008 | Critical | Eleftherios | 5h | To Do |
| S3-003 | Producer weekly payment settlement view | Producers can view a Payments page listing completed weekly settlements: gross order value, 5% commission deducted, net payout, individual order breakdown. Reports downloadable as CSV. Running tax-year total shown. | TC-012 | Critical | Eleftherios | 5h | To Do |
| S3-004 | Product search functionality | Search bar on product list page queries product name, description, and producer name (case-insensitive, partial matches). Empty results show a friendly message. Search combines with existing category and organic filters. | TC-005 | High | Gia Ngo | 3h | Done |
| S3-005 | Organic certification filter | Filter toggle on product list to show only Certified Organic products. Organic badge displayed on product cards and detail pages. Filter combines with category filter. Producers set certification status in the product form. | TC-014 | High | Gia Ngo | 2h | To Do |
| S3-006 | Seasonal availability management | Producers can set seasonal date ranges and availability status (In Season / Out of Season / Coming Soon) on each product. Out-of-season products are hidden from the customer-facing catalogue. In-season badge shown on product cards. | TC-016 | High | Gia Ngo | 3h | To Do |
| S3-007 | Producer stock / inventory update | Producers can update stock quantity and availability status for existing products without a full product edit. Stock changes take effect immediately. Products at zero stock show 'Out of Stock' to customers and cannot be added to cart. | TC-011 | High | Gia Ngo | 3h | To Do |
| S3-008 | Order history with reorder | Customer order history page (sorted most-recent-first) shows order number, date, delivery date, producer names, status, and total. Clicking an order shows full itemised detail. 'Reorder' button adds items to cart, flagging any unavailable products. | TC-020 | High | Gia Ngo | 4h | To Do |
| S3-009 | Food miles display | Calculate distance (straight-line, postcode-to-postcode) between customer postcode and producer farm postcode. Display food miles on product detail page and product cards. Cart page shows cumulative food miles for all items in the order. | TC-013 | Medium | Eleftherios | 4h | To Do |
| S3-010 | Community group & restaurant account types | Registration supports Community Group and Restaurant roles (extending CustomUser). Community group accounts can submit bulk quantity orders with special delivery instructions. Restaurant accounts can set up a recurring weekly order template. | TC-017, TC-018 | Medium | Eleftherios | 5h | To Do |
| S3-011 | Security hardening & GDPR | CSRF protection on all forms. Rate-limiting on login (lockout after 5 failed attempts). Passwords min 8 chars, enforced by validator. Payment info masked in order history. Users can delete their account and personal data (GDPR right to erasure). | TC-022 | Critical | Gia Ngo | 4h | To Do |
| S3-012 | Admin dashboard — marketplace metrics | Django admin extended with summary view: total registered producers, customers, products, and orders. Commission revenue to date displayed. All models accessible with search/filter in admin. Superuser-only. | TC-025 | Medium | Eleftherios | 3h | To Do |
| S3-013 | End-to-end testing & bug fixes | Run through all 25 test cases in the Dockerised environment. Log any failures as GitHub Issues, fix before final review. Ensure docker-compose up produces a clean, error-free boot. Confirm all migrations are applied. | All TCs | Critical | Whole team | 6h | To Do |
| S3-014 | README & submission prep | Update README with complete setup instructions, environment variable reference, test account credentials, and URL map. Ensure GitHub repo is public. Tag final release commit. Complete and sign Contributions Matrix. | — | High | Whole team | 2h | To Do |
| S3-015 | Surplus produce discounts | Producers can mark a product as discounted and set a reduced sale price. Discounted products are visually flagged on product list cards and the detail page. Discount applies to products approaching their best-before date or with high stock. | TC-019 | Medium | Eleftherios | 4h | To Do |
| S3-016 | Low stock notifications | When a product's stock falls below a configurable threshold (default: 5 units), the system sends an email alert to the producer. Alert also shown as a banner in the producer dashboard until stock is updated. | TC-023 | Medium | Gia Ngo | 3h | To Do |

