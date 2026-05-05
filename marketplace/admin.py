from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum, Count
from django.template.response import TemplateResponse
from django.urls import path

from .models import CustomUser, ProducerProfile, Category, Product, Order, OrderItem, Review


# extending the built-in UserAdmin so the role field shows up in the admin panel
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = list(UserAdmin.fieldsets) + [('Role', {'fields': ('role',)})]
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email']


@admin.register(ProducerProfile)
class ProducerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'postcode']
    search_fields = ['business_name', 'user__username', 'postcode']


# prepopulated_fields automatically fills in the slug from the name
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'producer', 'category', 'price', 'stock', 'is_active', 'is_organic']
    list_filter = ['is_active', 'is_organic', 'is_seasonal', 'category']
    search_fields = ['name', 'producer__business_name', 'farm_origin']
    date_hierarchy = 'created_at'


# inline shows order items directly inside the order page in admin
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0  # dont show empty extra rows
    readonly_fields = ['product', 'quantity', 'unit_price']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'customer', 'status', 'total_price', 'commission_amount', 'delivery_date', 'created_at']
    list_filter = ['status', 'delivery_date']
    search_fields = ['customer__username', 'delivery_address']
    date_hierarchy = 'created_at'
    readonly_fields = ['created_at', 'updated_at', 'commission_amount']
    inlines = [OrderItemInline]


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['order', 'product', 'quantity', 'unit_price']
    search_fields = ['order__id', 'product__name']


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['product', 'customer', 'rating', 'created_at']
    list_filter = ['rating']
    search_fields = ['product__name', 'customer__username']


# ── Marketplace Metrics — superuser-only custom admin view ──
# this is a custom page we added to the admin for S3-012
# it shows overall platform stats like total orders, commission earned etc

def marketplace_metrics_view(request):
    context = {
        **admin.site.each_context(request),  # gives us the admin nav and styling
        'title': 'Marketplace Metrics',
        'customer_count': CustomUser.objects.filter(role='customer').count(),
        'producer_count': CustomUser.objects.filter(role='producer').count(),
        'product_count': Product.objects.filter(is_active=True).count(),
        'order_count': Order.objects.count(),
        # only count orders that have actually been paid
        'paid_order_count': Order.objects.filter(status__in=['paid', 'confirmed', 'delivered']).count(),
        # aggregate sums up all the commission values into one total
        'commission_total': Order.objects.filter(
            status__in=['paid', 'confirmed', 'delivered']
        ).aggregate(total=Sum('commission_amount'))['total'] or 0,
        'revenue_total': Order.objects.filter(
            status__in=['paid', 'confirmed', 'delivered']
        ).aggregate(total=Sum('total_price'))['total'] or 0,
        'review_count': Review.objects.count(),
        # builds a dict like {'Pending': 3, 'Paid': 12, ...} for the status breakdown
        'orders_by_status': {
            label: Order.objects.filter(status=value).count()
            for value, label in Order.STATUS_CHOICES
        },
    }
    return TemplateResponse(request, 'admin/marketplace_metrics.html', context)


# we patch the admin site's get_urls to inject our custom metrics url
# found this approach in the django docs - cleaner than overriding AdminSite
_original_get_urls = admin.AdminSite.get_urls


def _patched_get_urls(self):
    custom = [
        path(
            'marketplace/metrics/',
            self.admin_view(marketplace_metrics_view, cacheable=True),
            name='marketplace_metrics',
        ),
    ]
    return custom + _original_get_urls(self)


admin.AdminSite.get_urls = _patched_get_urls
