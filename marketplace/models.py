from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator

# extending the default django user model so we can add a role field
# learned this from the django docs - you have to do this at the start
# otherwise changing it later breaks everything
class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('customer', 'Customer'),
        ('producer', 'Producer'),
        ('community_group', 'Community Group'),
        ('restaurant', 'Restaurant'),
        ('admin', 'Admin'),
    ]
    # role field to distinguish between different types of users
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')

    def __str__(self):
        return f"{self.username} ({self.role})"


# this stores extra info about producers (business name, address etc)
# linked 1-to-1 with the user account
class ProducerProfile(models.Model):
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='producer_profile'
    )
    business_name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    address = models.TextField()
    postcode = models.CharField(max_length=10)  # used for food miles calculation

    def __str__(self):
        return self.business_name


# simple category model for organising products (vegetables, dairy etc)
class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)  # slug is used in the URL filter
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = 'categories'  # fixes the admin showing "categorys"

    def __str__(self):
        return self.name


# main product model - has quite a lot of fields because of the sprint requirements
class Product(models.Model):
    # each product belongs to a producer, if producer deleted all their products go too
    producer = models.ForeignKey(
        ProducerProfile, on_delete=models.CASCADE, related_name='products'
    )
    # category is optional - SET_NULL means the product stays even if category is deleted
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name='products'
    )
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    allergens = models.TextField(blank=True, help_text='List any allergens, e.g. "Contains nuts"')
    is_organic = models.BooleanField(default=False)
    harvest_date = models.DateField(null=True, blank=True)
    best_before = models.DateField(null=True, blank=True)
    farm_origin = models.CharField(max_length=200, blank=True)  # postcode or farm name
    is_seasonal = models.BooleanField(default=False)
    seasonal_months = models.CharField(
        max_length=200, blank=True, help_text='e.g. June, July, August'
    )
    # choices for seasonal status shown on product cards
    season_status_choices = [
        ('in_season', 'In Season'),
        ('out_of_season', 'Out of Season'),
        ('coming_soon', 'Coming Soon'),
    ]
    season_status = models.CharField(max_length=20, choices=season_status_choices, default='in season',blank=True)
    season_start = models.DateField(null=True, blank=True, help_text= 'When this product comes into season')
    season_end = models.DateField(null=True, blank=True, help_text= 'When this product goes out of season')
    # minimum 48 hours lead time as per the project spec
    lead_time_hours = models.PositiveIntegerField(
        default=48, help_text='Minimum order lead time in hours'
    )
    # producer gets an email alert when stock drops below this number
    low_stock_threshold = models.PositiveIntegerField(
        default=5, help_text='Send alert when stock falls below this level'
    )
    is_discounted = models.BooleanField(default=False)
    sale_price = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)  # set automatically when created
    updated_at = models.DateTimeField(auto_now=True)      # updates every time the model is saved

    def __str__(self):
        return f"{self.name} — {self.producer.business_name}"


# order model - created when customer completes checkout
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),       # set after stripe payment succeeds
        ('confirmed', 'Confirmed'),
        ('delivered', 'Delivered'),
    ]
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    delivery_address = models.TextField()
    delivery_date = models.DateField()
    commission_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)  # 5% platform fee
    payment_intent_id = models.CharField(max_length=200, blank=True)  # stored from stripe

    def __str__(self):
        return f"Order #{self.id} by {self.customer.username}"


# each order can have multiple items (one per product)
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    # SET_NULL so the order history stays even if a product gets deleted
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=8, decimal_places=2)  # snapshot of price at time of order

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in Order #{self.order.id}"


# customers can leave a review after their order is delivered
class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reviews')
    rating = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'customer')  # one review per product per customer

    def __str__(self):
        return f"Review by {self.customer.username} for {self.product.name}"


# restaurant users can save a weekly order template so they dont have to re-add everything each time
class WeeklyOrderTemplate(models.Model):
    customer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='weekly_order_templates')
    name = models.CharField(max_length=200, default='My Weekly Order')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - {self.customer.username}"


# the individual product lines inside a weekly template
class WeeklyOrderItem(models.Model):
    template = models.ForeignKey(WeeklyOrderTemplate, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete =models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} x {self.product.name} in {self.template.name}"
