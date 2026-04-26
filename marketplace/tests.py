from django.test import TestCase
from django.urls import reverse
from marketplace.models import CustomUser, ProducerProfile, Category, Product


class ProductSearchTests(TestCase):
    """TC-005: Product search functionality"""

    def setUp(self):
        producer_user = CustomUser.objects.create_user(
            username='farm1', password='pass', role='producer'
        )
        self.producer = ProducerProfile.objects.create(
            user=producer_user,
            business_name='Green Valley Farm',
            address='1 Farm Lane',
            postcode='BS1 1AA',
        )

        producer_user2 = CustomUser.objects.create_user(
            username='farm2', password='pass', role='producer'
        )
        self.producer2 = ProducerProfile.objects.create(
            user=producer_user2,
            business_name='Sunny Acres',
            address='2 Field Road',
            postcode='BS2 2BB',
        )

        self.veg = Category.objects.create(name='Vegetables', slug='vegetables')
        self.dairy = Category.objects.create(name='Dairy & Eggs', slug='dairy-eggs')

        self.tomato = Product.objects.create(
            producer=self.producer,
            category=self.veg,
            name='Heritage Tomatoes',
            description='Freshly picked vine tomatoes.',
            price='2.50',
            stock=20,
            is_organic=False,
        )
        self.eggs = Product.objects.create(
            producer=self.producer2,
            category=self.dairy,
            name='Free Range Eggs',
            description='Six large eggs from happy hens.',
            price='1.80',
            stock=50,
            is_organic=True,
        )
        self.milk = Product.objects.create(
            producer=self.producer,
            category=self.dairy,
            name='Whole Milk',
            description='Organic certified whole milk.',
            price='1.20',
            stock=30,
            is_organic=True,
        )

        self.url = reverse('product_list')

    # -- search by name --

    def test_search_by_name_exact_word(self):
        response = self.client.get(self.url, {'search': 'Tomatoes'})
        self.assertContains(response, 'Heritage Tomatoes')
        self.assertNotContains(response, 'Free Range Eggs')
        self.assertNotContains(response, 'Whole Milk')

    def test_search_by_name_partial(self):
        response = self.client.get(self.url, {'search': 'omato'})
        self.assertContains(response, 'Heritage Tomatoes')
        self.assertNotContains(response, 'Free Range Eggs')

    def test_search_by_name_case_insensitive(self):
        response = self.client.get(self.url, {'search': 'heritage tomatoes'})
        self.assertContains(response, 'Heritage Tomatoes')

    # -- search by description --

    def test_search_by_description_partial(self):
        response = self.client.get(self.url, {'search': 'happy hens'})
        self.assertContains(response, 'Free Range Eggs')
        self.assertNotContains(response, 'Heritage Tomatoes')

    def test_search_by_description_case_insensitive(self):
        response = self.client.get(self.url, {'search': 'VINE TOMATOES'})
        self.assertContains(response, 'Heritage Tomatoes')

    # -- search by producer name --

    def test_search_by_producer_name(self):
        response = self.client.get(self.url, {'search': 'Green Valley'})
        self.assertContains(response, 'Heritage Tomatoes')
        self.assertContains(response, 'Whole Milk')
        self.assertNotContains(response, 'Free Range Eggs')

    def test_search_by_producer_name_case_insensitive(self):
        response = self.client.get(self.url, {'search': 'sunny acres'})
        self.assertContains(response, 'Free Range Eggs')
        self.assertNotContains(response, 'Heritage Tomatoes')

    # -- empty / no results --

    def test_empty_search_returns_all_products(self):
        response = self.client.get(self.url, {'search': ''})
        self.assertContains(response, 'Heritage Tomatoes')
        self.assertContains(response, 'Free Range Eggs')
        self.assertContains(response, 'Whole Milk')

    def test_no_results_shows_friendly_message(self):
        response = self.client.get(self.url, {'search': 'zzznomatch'})
        self.assertContains(response, 'No products found')

    # -- combined filters --

    def test_search_combined_with_category_filter(self):
        response = self.client.get(self.url, {'search': 'Green Valley', 'category': 'dairy-eggs'})
        self.assertContains(response, 'Whole Milk')
        self.assertNotContains(response, 'Heritage Tomatoes')

    def test_search_combined_with_organic_filter(self):
        response = self.client.get(self.url, {'search': 'Green Valley', 'organic': 'true'})
        self.assertContains(response, 'Whole Milk')
        self.assertNotContains(response, 'Heritage Tomatoes')

    def test_search_combined_with_category_and_organic(self):
        response = self.client.get(self.url, {
            'search': 'eggs',
            'category': 'dairy-eggs',
            'organic': 'true',
        })
        self.assertContains(response, 'Free Range Eggs')
        self.assertNotContains(response, 'Whole Milk')
        self.assertNotContains(response, 'Heritage Tomatoes')

    def test_inactive_products_excluded_from_search(self):
        self.tomato.is_active = False
        self.tomato.save()
        response = self.client.get(self.url, {'search': 'Tomatoes'})
        self.assertNotContains(response, 'Heritage Tomatoes')
