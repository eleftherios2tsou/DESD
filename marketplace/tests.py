from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase, Client
from django.urls import reverse
from django.core.cache import cache

from .models import CustomUser, ProducerProfile, Category, Product, Order, OrderItem, Review
from .forms import CheckoutForm


# ── Helpers ────────────────────────────────────────────────────────────────

def make_customer(username='customer', password='testpass123'):
    return CustomUser.objects.create_user(
        username=username, email=f'{username}@test.com',
        password=password, role='customer'
    )


def make_producer(username='producer', password='testpass123'):
    user = CustomUser.objects.create_user(
        username=username, email=f'{username}@test.com',
        password=password, role='producer'
    )
    profile = ProducerProfile.objects.create(
        user=user, business_name='Test Farm',
        address='123 Farm Lane', postcode='BS1 1AA'
    )
    return user, profile


def make_product(profile, name='Organic Carrots', price='2.50', stock=100, organic=True):
    cat, _ = Category.objects.get_or_create(name='Vegetables', defaults={'slug': 'vegetables'})
    return Product.objects.create(
        producer=profile, name=name, description='Fresh produce',
        price=price, stock=stock, category=cat, is_organic=organic,
    )


def future_date(days=3):
    return (date.today() + timedelta(days=days)).isoformat()


# ── TC-001 / TC-002: Registration & Login ──────────────────────────────────

class AuthTests(TestCase):

    def setUp(self):
        self.client = Client()
        cache.clear()

    def test_customer_registration(self):
        """TC-001: New customer can register"""
        response = self.client.post(reverse('register'), {
            'username': 'newuser',
            'email': 'new@test.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(CustomUser.objects.filter(username='newuser').exists())
        self.assertEqual(CustomUser.objects.get(username='newuser').role, 'customer')

    def test_registration_duplicate_email_rejected(self):
        """TC-001: Duplicate email is rejected"""
        make_customer(username='existing')
        response = self.client.post(reverse('register'), {
            'username': 'another',
            'email': 'existing@test.com',
            'password1': 'securepass123',
            'password2': 'securepass123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertFalse(CustomUser.objects.filter(username='another').exists())

    def test_login_customer_redirects_home(self):
        """TC-002: Customer redirected to home after login"""
        make_customer()
        response = self.client.post(reverse('login'), {
            'username': 'customer', 'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('home'))

    def test_login_producer_redirects_dashboard(self):
        """TC-002: Producer redirected to dashboard after login"""
        make_producer()
        response = self.client.post(reverse('login'), {
            'username': 'producer', 'password': 'testpass123',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_logout(self):
        """TC-002: Logged-in user can log out"""
        customer = make_customer()
        self.client.force_login(customer)
        response = self.client.get(reverse('logout'))
        self.assertRedirects(response, reverse('home'))

    def test_login_wrong_password_rejected(self):
        """TC-002: Wrong password shows error"""
        make_customer()
        response = self.client.post(reverse('login'), {
            'username': 'customer', 'password': 'wrongpassword',
        })
        self.assertEqual(response.status_code, 200)

    def test_login_rate_limit_after_5_failures(self):
        """TC-022: Account locked after 5 failed login attempts"""
        make_customer()
        for _ in range(5):
            self.client.post(reverse('login'), {
                'username': 'customer', 'password': 'wrong',
            })
        response = self.client.post(reverse('login'), {
            'username': 'customer', 'password': 'testpass123',
        })
        self.assertContains(response, 'locked')


# ── TC-022: Role-based access control ─────────────────────────────────────

class RBACTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.customer = make_customer()
        self.producer_user, self.profile = make_producer()

    def test_unauthenticated_dashboard_redirects_login(self):
        """TC-022: Unauthenticated user cannot reach producer dashboard"""
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('login'))

    def test_customer_blocked_from_dashboard(self):
        """TC-022: Customer role cannot access producer dashboard"""
        self.client.force_login(self.customer)
        response = self.client.get(reverse('dashboard'))
        self.assertRedirects(response, reverse('home'))

    def test_producer_blocked_from_cart(self):
        """TC-022: Producer role cannot access cart"""
        self.client.force_login(self.producer_user)
        response = self.client.get(reverse('cart_view'))
        self.assertRedirects(response, reverse('home'))

    def test_producer_blocked_from_checkout(self):
        """TC-022: Producer role cannot access checkout"""
        self.client.force_login(self.producer_user)
        response = self.client.get(reverse('checkout'))
        self.assertRedirects(response, reverse('home'))

    def test_customer_blocked_from_producer_orders(self):
        """TC-022: Customer cannot manage producer orders"""
        self.client.force_login(self.customer)
        response = self.client.get(reverse('producer_orders'))
        self.assertRedirects(response, reverse('home'))


# ── TC-003 / TC-004 / TC-005: Products ────────────────────────────────────

class ProductTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.producer_user, self.profile = make_producer()
        self.product = make_product(self.profile)

    def test_product_list_accessible_to_anonymous(self):
        """TC-004: Product list is public"""
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Carrots')

    def test_product_detail_accessible(self):
        """TC-004: Product detail page loads"""
        response = self.client.get(reverse('product_detail', kwargs={'pk': self.product.pk}))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Organic Carrots')

    def test_search_by_product_name(self):
        """TC-005: Search matches product name"""
        response = self.client.get(reverse('product_list') + '?search=carrot')
        self.assertContains(response, 'Organic Carrots')

    def test_search_by_description(self):
        """TC-005: Search matches product description"""
        response = self.client.get(reverse('product_list') + '?search=Fresh produce')
        self.assertContains(response, 'Organic Carrots')

    def test_search_by_producer_name(self):
        """TC-005: Search matches producer business name"""
        response = self.client.get(reverse('product_list') + '?search=Test Farm')
        self.assertContains(response, 'Organic Carrots')

    def test_search_no_match_shows_empty(self):
        """TC-005: Search with no match shows empty state"""
        response = self.client.get(reverse('product_list') + '?search=xyznothing')
        self.assertContains(response, 'No products found')

    def test_organic_filter(self):
        """TC-014: Organic filter hides non-organic products"""
        make_product(self.profile, name='Regular Potatoes', organic=False)
        response = self.client.get(reverse('product_list') + '?organic=true')
        self.assertContains(response, 'Organic Carrots')
        self.assertNotContains(response, 'Regular Potatoes')

    def test_producer_can_create_product(self):
        """TC-003: Producer can create a new product"""
        self.client.force_login(self.producer_user)
        response = self.client.post(reverse('product_create'), {
            'name': 'Fresh Tomatoes',
            'description': 'Ripe tomatoes',
            'price': '3.00',
            'stock': 50,
            'lead_time_hours': 48,
            'is_active': True,
            'is_organic': False,
            'is_seasonal': False,
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(Product.objects.filter(name='Fresh Tomatoes').exists())

    def test_producer_can_edit_own_product(self):
        """TC-003: Producer can edit their own product"""
        self.client.force_login(self.producer_user)
        response = self.client.post(
            reverse('product_edit', kwargs={'pk': self.product.pk}),
            {
                'name': 'Updated Carrots',
                'description': 'Even fresher',
                'price': '3.00',
                'stock': 80,
                'lead_time_hours': 48,
                'is_active': True,
                'is_organic': True,
                'is_seasonal': False,
            }
        )
        self.assertRedirects(response, reverse('dashboard'))
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Carrots')

    def test_producer_can_delete_product(self):
        """TC-003: Producer can delete their product"""
        self.client.force_login(self.producer_user)
        pk = self.product.pk
        self.client.post(reverse('product_delete', kwargs={'pk': pk}))
        self.assertFalse(Product.objects.filter(pk=pk).exists())


# ── TC-006 / TC-011: Cart & stock ─────────────────────────────────────────

class CartTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.customer = make_customer()
        _, profile = make_producer()
        self.product = make_product(profile, stock=10)

    def test_add_to_cart(self):
        """TC-006: Customer can add item to cart"""
        self.client.force_login(self.customer)
        self.client.post(reverse('cart_add', kwargs={'pk': self.product.pk}), {'quantity': 2})
        self.assertIn(str(self.product.pk), self.client.session['cart'])

    def test_cannot_add_more_than_stock(self):
        """TC-011: Adding quantity exceeding stock is rejected"""
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('cart_add', kwargs={'pk': self.product.pk}),
            {'quantity': 99}
        )
        self.assertRedirects(response, reverse('product_detail', kwargs={'pk': self.product.pk}))
        self.assertNotIn('cart', self.client.session)

    def test_remove_from_cart(self):
        """TC-006: Customer can remove item from cart"""
        self.client.force_login(self.customer)
        self.client.post(reverse('cart_add', kwargs={'pk': self.product.pk}), {'quantity': 1})
        self.client.post(reverse('cart_remove', kwargs={'pk': self.product.pk}))
        cart = self.client.session.get('cart', {})
        self.assertNotIn(str(self.product.pk), cart)

    def test_cart_view_shows_items(self):
        """TC-006: Cart view lists added items"""
        self.client.force_login(self.customer)
        self.client.post(reverse('cart_add', kwargs={'pk': self.product.pk}), {'quantity': 1})
        response = self.client.get(reverse('cart_view'))
        self.assertContains(response, self.product.name)


# ── TC-007: Delivery date validation ──────────────────────────────────────

class DeliveryDateTests(TestCase):

    def test_delivery_date_today_rejected(self):
        """TC-007: Delivery date of today fails validation"""
        form = CheckoutForm(data={
            'full_name': 'Test User',
            'email': 'test@test.com',
            'postcode': 'BS1 1AA',
            'delivery_address': '123 Test St',
            'delivery_date': date.today().isoformat(),
        })
        self.assertFalse(form.is_valid())
        self.assertIn('delivery_date', form.errors)

    def test_delivery_date_48h_ahead_passes(self):
        """TC-007: Delivery date 3 days ahead is valid"""
        form = CheckoutForm(data={
            'full_name': 'Test User',
            'email': 'test@test.com',
            'postcode': 'BS1 1AA',
            'delivery_address': '123 Test St',
            'delivery_date': future_date(3),
        })
        self.assertTrue(form.is_valid())

    def test_delivery_date_in_past_rejected(self):
        """TC-007: Past delivery date fails validation"""
        form = CheckoutForm(data={
            'full_name': 'Test User',
            'email': 'test@test.com',
            'postcode': 'BS1 1AA',
            'delivery_address': '123 Test St',
            'delivery_date': (date.today() - timedelta(days=1)).isoformat(),
        })
        self.assertFalse(form.is_valid())


# ── TC-009 / TC-010: Producer order management ────────────────────────────

class ProducerOrderTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.customer = make_customer()
        self.producer_user, self.profile = make_producer()
        self.product = make_product(self.profile)
        self.order = Order.objects.create(
            customer=self.customer,
            delivery_address='123 Test St',
            delivery_date=date.today() + timedelta(days=3),
            total_price=Decimal('5.00'),
            commission_amount=Decimal('0.25'),
            status='paid',
        )
        OrderItem.objects.create(
            order=self.order, product=self.product,
            quantity=2, unit_price=Decimal('2.50'),
        )

    def test_producer_sees_orders_with_their_products(self):
        """TC-009: Producer order management shows their orders"""
        self.client.force_login(self.producer_user)
        response = self.client.get(reverse('producer_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Order #{self.order.id}')

    def test_producer_can_update_order_status(self):
        """TC-010: Producer can move order from paid to confirmed"""
        self.client.force_login(self.producer_user)
        self.client.post(
            reverse('update_order_status', kwargs={'pk': self.order.pk}),
            {'status': 'confirmed'}
        )
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'confirmed')


# ── TC-008: Order history ─────────────────────────────────────────────────

class OrderHistoryTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.customer = make_customer()
        _, profile = make_producer()
        product = make_product(profile)
        self.order = Order.objects.create(
            customer=self.customer,
            delivery_address='123 Test',
            delivery_date=date.today() + timedelta(days=3),
            total_price=Decimal('5.00'),
            commission_amount=Decimal('0.25'),
            status='paid',
        )
        OrderItem.objects.create(
            order=self.order, product=product,
            quantity=1, unit_price=Decimal('5.00'),
        )

    def test_customer_sees_own_orders(self):
        """TC-008: Customer can view their order history"""
        self.client.force_login(self.customer)
        response = self.client.get(reverse('order_history'))
        self.assertContains(response, f'Order #{self.order.id}')

    def test_customer_cannot_see_other_orders(self):
        """TC-008: Customer only sees their own orders"""
        other = make_customer(username='other')
        self.client.force_login(other)
        response = self.client.get(reverse('order_history'))
        self.assertNotContains(response, f'Order #{self.order.id}')


# ── TC-024: Reviews ────────────────────────────────────────────────────────

class ReviewTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.customer = make_customer()
        _, profile = make_producer()
        self.product = make_product(profile)

    def _make_delivered_order(self):
        order = Order.objects.create(
            customer=self.customer,
            delivery_address='123 Test',
            delivery_date=date.today() + timedelta(days=3),
            total_price=Decimal('5.00'),
            commission_amount=Decimal('0.25'),
            status='delivered',
        )
        OrderItem.objects.create(
            order=order, product=self.product,
            quantity=1, unit_price=Decimal('5.00'),
        )
        return order

    def test_cannot_review_without_delivered_order(self):
        """TC-024: Review blocked without a delivered order"""
        self.client.force_login(self.customer)
        response = self.client.get(
            reverse('submit_review', kwargs={'product_pk': self.product.pk})
        )
        self.assertRedirects(response, reverse('product_detail', kwargs={'pk': self.product.pk}))

    def test_can_review_after_delivered_order(self):
        """TC-024: Customer can submit review after delivery"""
        self._make_delivered_order()
        self.client.force_login(self.customer)
        response = self.client.post(
            reverse('submit_review', kwargs={'product_pk': self.product.pk}),
            {'rating': 5, 'comment': 'Excellent!'}
        )
        self.assertRedirects(response, reverse('product_detail', kwargs={'pk': self.product.pk}))
        self.assertTrue(Review.objects.filter(product=self.product, customer=self.customer).exists())

    def test_cannot_review_same_product_twice(self):
        """TC-024: Duplicate review is blocked"""
        self._make_delivered_order()
        Review.objects.create(product=self.product, customer=self.customer, rating=4)
        self.client.force_login(self.customer)
        response = self.client.get(
            reverse('submit_review', kwargs={'product_pk': self.product.pk})
        )
        self.assertRedirects(response, reverse('product_detail', kwargs={'pk': self.product.pk}))


# ── TC-011 (GDPR): Account deletion ───────────────────────────────────────

class GDPRTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.customer = make_customer(username='gdpruser')

    def test_deletion_requires_exact_confirm(self):
        """GDPR: Account NOT deleted when wrong confirm text"""
        self.client.force_login(self.customer)
        self.client.post(reverse('delete_account'), {'confirm': 'delete'})
        self.assertTrue(CustomUser.objects.filter(username='gdpruser').exists())

    def test_deletion_succeeds_with_delete_confirm(self):
        """GDPR: Account deleted when user types DELETE"""
        self.client.force_login(self.customer)
        uid = self.customer.id
        response = self.client.post(reverse('delete_account'), {'confirm': 'DELETE'})
        self.assertFalse(CustomUser.objects.filter(id=uid).exists())
        self.assertRedirects(response, reverse('home'))


# ── TC-025: Admin metrics ─────────────────────────────────────────────────

class AdminMetricsTests(TestCase):

    def setUp(self):
        self.client = Client()
        self.superuser = CustomUser.objects.create_superuser(
            username='admin', email='admin@test.com', password='adminpass123'
        )

    def test_metrics_accessible_to_superuser(self):
        """TC-025: Superuser can access metrics page"""
        self.client.force_login(self.superuser)
        response = self.client.get('/admin/marketplace/metrics/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Marketplace Metrics')

    def test_metrics_blocked_for_non_staff(self):
        """TC-025: Non-staff user cannot access metrics"""
        customer = make_customer()
        self.client.force_login(customer)
        response = self.client.get('/admin/marketplace/metrics/')
        self.assertNotEqual(response.status_code, 200)
