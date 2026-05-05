from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import Sum, Count
from django.template.response import TemplateResponse
from django.urls import path
from django.http import HttpResponse
from datetime import date, timedelta
from decimal import Decimal
from collections import defaultdict
import csv

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


# ── Commission Report — admin financial report with date range, per-order breakdown, CSV export ──

def commission_report_view(request):
    today = date.today()
    default_from = today - timedelta(weeks=2)

    # read date range from query string, default to previous 2 weeks
    date_from_str = request.GET.get('date_from', default_from.isoformat())
    date_to_str = request.GET.get('date_to', today.isoformat())
    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError:
        date_from = default_from
        date_to = today

    orders = Order.objects.filter(
        status__in=['paid', 'confirmed', 'delivered'],
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).prefetch_related('items__product__producer').order_by('-created_at')

    # build per-order breakdown grouped by producer within each order
    order_reports = []
    for order in orders:
        producers = defaultdict(lambda: {'name': '', 'gross': Decimal('0'), 'items': []})
        for item in order.items.all():
            if item.product:
                pid = item.product.producer.pk
                producers[pid]['name'] = item.product.producer.business_name
                producers[pid]['gross'] += item.unit_price * item.quantity
                producers[pid]['items'].append(item)
        for pb in producers.values():
            pb['commission'] = (pb['gross'] * Decimal('0.05')).quantize(Decimal('0.01'))
            pb['net'] = (pb['gross'] * Decimal('0.95')).quantize(Decimal('0.01'))
        order_reports.append({
            'order': order,
            'producers': dict(producers),
        })

    # summary totals for the selected period
    total_gross = sum(r['order'].total_price for r in order_reports)
    total_commission = sum(r['order'].commission_amount for r in order_reports)
    total_net = total_gross - total_commission

    # group by month for the monthly summary section
    monthly = defaultdict(lambda: {'gross': Decimal('0'), 'commission': Decimal('0'), 'net': Decimal('0'), 'count': 0})
    for r in order_reports:
        key = r['order'].created_at.strftime('%B %Y')
        monthly[key]['gross'] += r['order'].total_price
        monthly[key]['commission'] += r['order'].commission_amount
        monthly[key]['net'] += r['order'].total_price - r['order'].commission_amount
        monthly[key]['count'] += 1

    # UK tax year for YTD totals
    if today.month < 4 or (today.month == 4 and today.day < 6):
        tax_year_start = date(today.year - 1, 4, 6)
    else:
        tax_year_start = date(today.year, 4, 6)

    ytd_qs = Order.objects.filter(status__in=['paid', 'confirmed', 'delivered'], created_at__date__gte=tax_year_start)
    ytd_gross = ytd_qs.aggregate(t=Sum('total_price'))['t'] or Decimal('0')
    ytd_commission = ytd_qs.aggregate(t=Sum('commission_amount'))['t'] or Decimal('0')

    context = {
        **admin.site.each_context(request),
        'title': 'Commission Report',
        'date_from': date_from,
        'date_to': date_to,
        'order_reports': order_reports,
        'total_orders': len(order_reports),
        'total_gross': total_gross,
        'total_commission': total_commission,
        'total_net': total_net,
        'monthly_summary': dict(monthly),
        'ytd_gross': ytd_gross,
        'ytd_commission': ytd_commission,
        'ytd_net': ytd_gross - ytd_commission,
        'tax_year_start': tax_year_start,
    }
    return TemplateResponse(request, 'admin/commission_report.html', context)


def commission_report_csv(request):
    today = date.today()
    date_from_str = request.GET.get('date_from', (today - timedelta(weeks=2)).isoformat())
    date_to_str = request.GET.get('date_to', today.isoformat())
    try:
        date_from = date.fromisoformat(date_from_str)
        date_to = date.fromisoformat(date_to_str)
    except ValueError:
        date_from = today - timedelta(weeks=2)
        date_to = today

    orders = Order.objects.filter(
        status__in=['paid', 'confirmed', 'delivered'],
        created_at__date__gte=date_from,
        created_at__date__lte=date_to,
    ).prefetch_related('items__product__producer').order_by('-created_at')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="commission_report_{date_from}_{date_to}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Order #', 'Order Date', 'Customer', 'Status', 'Producer', 'Producer Gross (£)', 'Commission 5% (£)', 'Producer Net 95% (£)', 'Order Total (£)', 'Order Commission (£)'])

    for order in orders:
        producers = defaultdict(lambda: {'name': '', 'gross': Decimal('0')})
        for item in order.items.all():
            if item.product:
                pid = item.product.producer.pk
                producers[pid]['name'] = item.product.producer.business_name
                producers[pid]['gross'] += item.unit_price * item.quantity

        for pb in producers.values():
            commission = (pb['gross'] * Decimal('0.05')).quantize(Decimal('0.01'))
            net = (pb['gross'] * Decimal('0.95')).quantize(Decimal('0.01'))
            writer.writerow([
                order.id,
                order.created_at.date(),
                order.customer.username,
                order.status,
                pb['name'],
                pb['gross'],
                commission,
                net,
                order.total_price,
                order.commission_amount,
            ])

    return response


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
        path(
            'marketplace/commission/',
            self.admin_view(commission_report_view),
            name='commission_report',
        ),
        path(
            'marketplace/commission/export/',
            self.admin_view(commission_report_csv),
            name='commission_report_csv',
        ),
    ]
    return custom + _original_get_urls(self)


admin.AdminSite.get_urls = _patched_get_urls
