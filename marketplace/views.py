import csv
import stripe
from collections import defaultdict
from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Avg, Q
from django.http import HttpResponse

from .forms import RegistrationForm, ProducerRegistrationForm, ProductForm, CheckoutForm, AccountSettingsForm, ProducerProfileForm, ReviewForm
from .models import ProducerProfile, Product, Category, Order, OrderItem, Review
from .decorators import producer_required, customer_required


def home(request):
    featured_products = Product.objects.filter(is_active=True).order_by('-created_at')[:6]
    return render(request, 'marketplace/home.html',{'featured_products': featured_products})


def register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please log in.')
            return redirect('login')
    else:
        form = RegistrationForm()
    return render(request, 'marketplace/register.html', {'form': form})


def register_producer(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = ProducerRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'producer'
            user.save()
            ProducerProfile.objects.create(
                user=user,
                business_name=form.cleaned_data['business_name'],
                address=form.cleaned_data['address'],
                postcode=form.cleaned_data['postcode'],
                description=form.cleaned_data.get('description', ''),
            )
            messages.success(request, 'Producer account created! Please log in.')
            return redirect('login')
    else:
        form = ProducerRegistrationForm()
    return render(request, 'marketplace/producer_register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            if user.role == 'producer':
                return redirect('dashboard')
            return redirect('home')
        # form is invalid — errors will be shown in template
    else:
        form = AuthenticationForm()
    return render(request, 'marketplace/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('home')



@producer_required
def producer_dashboard(request):
    profile, created = ProducerProfile.objects.get_or_create(user=request.user)
    products = Product.objects.filter(producer=profile).order_by('-created_at')
    return render(request, 'marketplace/dashboard.html', {'products': products, 'profile': profile})


@producer_required
def product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = request.user.producer_profile
            product.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/product_form.html', {'form': form, 'action': 'Create'})


@producer_required
def product_edit(request, pk):
    product = get_object_or_404(Product, pk=pk, producer=request.user.producer_profile)
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, f'Product "{product.name}" updated successfully.')
            return redirect('dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'marketplace/product_form.html', {'form': form, 'action': 'Edit', 'product': product})


@producer_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk, producer=request.user.producer_profile)
    if request.method == 'POST':
        name = product.name
        product.delete()
        messages.success(request, f'Product "{name}" deleted.')
        return redirect('dashboard')
    return render(request, 'marketplace/product_confirm_delete.html', {'product': product})

def producer_profile(request, pk):
    profile = get_object_or_404(ProducerProfile, pk=pk)
    products = Product.objects.filter(producer=profile, is_active=True).order_by('-created_at')
    return render(request, 'marketplace/producer_profile.html', {'profile': profile, 'products': products})


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related('producer', 'category')

    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    organic = request.GET.get('organic', '')

    if search:
        products = products.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search) |
            Q(producer__business_name__icontains=search)
        )
    if category:
        products = products.filter(category__slug=category)
    if organic:
        products = products.filter(is_organic=True)

    return render(request, 'marketplace/product_list.html', {
        'products': products,
        'categories': Category.objects.all(),
        'search': search,
        'category': category,
        'organic': organic,
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    reviews = product.reviews.all().order_by('-created_at')
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']    
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,})


@producer_required
def producer_orders_management(request):
    orders = Order.objects.filter(items__product__producer=request.user.producer_profile).distinct().order_by('-created_at')
    return render(request, 'marketplace/producer_orders.html', {'orders': orders})
@producer_required
def update_order_status(request, pk):
    order = get_object_or_404(Order, pk=pk, items__product__producer=request.user.producer_profile)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status
            order.save()
            messages.success(request, f'Order #{order.id} status updated to {new_status}.')
        else:
            messages.error(request, 'Invalid status selected.')
    return redirect('producer_orders')


def account_settings(request):
    if not request.user.is_authenticated:
        return redirect('login')

    producer_form = None

    if request.method == 'POST':
        account_form = AccountSettingsForm(request.POST, instance=request.user)
        if request.user.role == 'producer':
            producer_form = ProducerProfileForm(request.POST, instance=request.user.producer_profile)

        account_valid = account_form.is_valid()
        producer_valid = producer_form.is_valid() if producer_form else True

        if account_valid and producer_valid:
            user = account_form.save()
            if producer_form:
                producer_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Account settings updated successfully.')
            return redirect('account_settings')
    else:
        account_form = AccountSettingsForm(instance=request.user)
        if request.user.role == 'producer':
            producer_form = ProducerProfileForm(instance=request.user.producer_profile)

    return render(request, 'marketplace/account_settings.html', {
        'account_form': account_form,
        'producer_form': producer_form,
    })


@customer_required
def cart_add(request, pk):
    if request.method != 'POST':
        return redirect('product_list')
    product = get_object_or_404(Product, pk=pk, is_active=True)
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))

    product_id = str(pk)
    current_in_cart = cart[product_id]['quantity'] if product_id in cart else 0
    if product.stock < current_in_cart + quantity:
        messages.error(request, f'Not enough stock for "{product.name}". Only {product.stock} available.')
        return redirect('product_detail', pk=pk)

    if product_id in cart:
        cart[product_id]['quantity'] += quantity
    else:
        cart[product_id] = {
            'name': product.name,
            'price': str(product.price),
            'quantity': quantity,
            'producer': product.producer.business_name
        }

    request.session['cart'] = cart
    return redirect('cart_view')
@customer_required
def cart_remove(request, pk):
    if request.method != 'POST':
        return redirect('cart_view')
    cart = request.session.get('cart', {})
    product_id = str(pk)
    if product_id in cart:
        del cart[product_id]
        request.session['cart'] = cart
    return redirect('cart_view')
@customer_required
def cart_view(request):
    cart = request.session.get('cart', {})
    total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'marketplace/cart.html', {'cart': cart, 'total': total})
@customer_required
def cart_update(request, pk):
    if request.method != 'POST':
        return redirect('cart_view')
    cart = request.session.get('cart', {})
    product_id = str(pk)
    quantity = int(request.POST.get('quantity', 1))
    if product_id in cart:
        if quantity > 0:
            cart[product_id]['quantity'] = quantity
        else:
            del cart[product_id]
    request.session['cart'] = cart
    return redirect('cart_view')
@customer_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart_view')

    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            # Stock validation before touching Stripe
            for product_id, item in cart.items():
                product = get_object_or_404(Product, pk=int(product_id))
                if product.stock < item['quantity']:
                    messages.error(request, f'"{product.name}" only has {product.stock} units in stock. Please update your cart.')
                    return redirect('cart_view')

            for item in cart.values():
                item['subtotal'] = float(item['price']) * item['quantity']
            total = sum(item['subtotal'] for item in cart.values())

            # Persist delivery details in session so payment view can use them
            request.session['pending_checkout'] = {
                'delivery_address': form.cleaned_data['delivery_address'],
                'delivery_date': str(form.cleaned_data['delivery_date']),
                'full_name': form.cleaned_data['full_name'],
                'email': form.cleaned_data['email'],
                'postcode': form.cleaned_data['postcode'],
            }
            request.session['cart'] = cart  # ensure subtotals are persisted

            # Create Stripe PaymentIntent
            stripe.api_key = settings.STRIPE_SECRET_KEY
            try:
                intent = stripe.PaymentIntent.create(
                    amount=round(total * 100),  # pence
                    currency='gbp',
                    metadata={'user_id': request.user.id},
                )
                request.session['stripe_client_secret'] = intent.client_secret
            except stripe.error.StripeError as e:
                messages.error(request, f'Payment setup failed: {e.user_message}')
                return redirect('checkout')

            return redirect('payment')
    else:
        form = CheckoutForm()

    for item in cart.values():
        item['subtotal'] = float(item['price']) * item['quantity']
    total = sum(item['subtotal'] for item in cart.values())
    commission = total * 0.05

    # Group items by producer for S3-002 breakdown
    cart_by_producer = {}
    for item in cart.values():
        p = item['producer']
        if p not in cart_by_producer:
            cart_by_producer[p] = {'items': [], 'subtotal': 0.0}
        cart_by_producer[p]['items'].append(item)
        cart_by_producer[p]['subtotal'] += item['subtotal']

    return render(request, 'marketplace/checkout.html', {
        'form': form,
        'cart': cart,
        'cart_by_producer': cart_by_producer,
        'total': total,
        'commission': commission,
    })


@customer_required
def payment(request):
    client_secret = request.session.get('stripe_client_secret')
    if not client_secret or not request.session.get('pending_checkout'):
        return redirect('checkout')

    return render(request, 'marketplace/payment.html', {
        'client_secret': client_secret,
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


@customer_required
def checkout_complete(request):
    payment_intent_id = request.GET.get('payment_intent')
    redirect_status = request.GET.get('redirect_status')

    if redirect_status != 'succeeded' or not payment_intent_id:
        messages.error(request, 'Payment was not successful. Please try again.')
        return redirect('cart_view')

    # Idempotency: if this PaymentIntent already created an order, show it
    existing = Order.objects.filter(payment_intent_id=payment_intent_id).first()
    if existing:
        return redirect('order_confirmation', pk=existing.pk)

    # Verify with Stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    try:
        intent = stripe.PaymentIntent.retrieve(payment_intent_id)
    except stripe.error.StripeError:
        messages.error(request, 'Could not verify payment. Please contact support.')
        return redirect('cart_view')

    if intent.status != 'succeeded':
        messages.error(request, 'Payment was not completed. Please try again.')
        return redirect('cart_view')

    pending = request.session.get('pending_checkout')
    cart = request.session.get('cart', {})
    if not pending or not cart:
        messages.error(request, 'Session expired. Please try again.')
        return redirect('cart_view')

    for item in cart.values():
        item['subtotal'] = float(item['price']) * item['quantity']
    total = sum(item['subtotal'] for item in cart.values())
    commission = total * 0.05

    order = Order.objects.create(
        customer=request.user,
        delivery_address=pending['delivery_address'],
        delivery_date=date.fromisoformat(pending['delivery_date']),
        total_price=total,
        commission_amount=commission,
        status='paid',
        payment_intent_id=payment_intent_id,
    )

    for product_id, item in cart.items():
        product = get_object_or_404(Product, pk=int(product_id))
        OrderItem.objects.create(
            order=order,
            product=product,
            quantity=item['quantity'],
            unit_price=item['price'],
        )
        product.stock -= item['quantity']
        product.save()

    # Clear session
    request.session.pop('cart', None)
    request.session.pop('pending_checkout', None)
    request.session.pop('stripe_client_secret', None)

    # Customer confirmation email
    item_lines = '\n'.join(
        f"  - {item['name']} x{item['quantity']}  £{item['subtotal']:.2f}"
        for item in cart.values()
    )
    if request.user.email:
        send_mail(
            subject=f'Order #{order.id} Confirmed — Bristol Food Network',
            message=(
                f"Hi {request.user.username},\n\n"
                f"Payment confirmed! Your order is on its way.\n\n"
                f"Order #{order.id}\n"
                f"Delivery date: {order.delivery_date}\n"
                f"Delivery address: {order.delivery_address}\n\n"
                f"Items:\n{item_lines}\n\n"
                f"Total paid: £{total:.2f}\n\n"
                f"Thank you for supporting local producers!\n\nBristol Food Network"
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[request.user.email],
            fail_silently=True,
        )

    # Per-producer notification emails
    producer_items = defaultdict(lambda: {'producer': None, 'lines': []})
    for product_id, item in cart.items():
        product = Product.objects.filter(pk=int(product_id)).select_related('producer').first()
        if product:
            pid = product.producer.pk
            producer_items[pid]['producer'] = product.producer
            producer_items[pid]['lines'].append(
                f"  - {item['name']} x{item['quantity']}  £{item['subtotal']:.2f}"
            )
    for data in producer_items.values():
        producer = data['producer']
        if producer and producer.user.email:
            send_mail(
                subject=f'New Order #{order.id} for your products',
                message=(
                    f"Hi {producer.business_name},\n\n"
                    f"You have a new paid order from {request.user.username}.\n\n"
                    f"Order #{order.id}\n"
                    f"Delivery date: {order.delivery_date}\n\n"
                    f"Items ordered from you:\n{chr(10).join(data['lines'])}\n\n"
                    f"Please confirm the order from your dashboard.\n\nBristol Food Network"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[producer.user.email],
                fail_silently=True,
            )

    return redirect('order_confirmation', pk=order.pk)


def order_confirmation(request, pk):
    if not request.user.is_authenticated:
        return redirect('login')
    order = get_object_or_404(Order, pk=pk, customer=request.user)

    # Per-producer breakdown for S3-002
    producer_breakdown = {}
    for item in order.items.select_related('product__producer').all():
        if item.product:
            pname = item.product.producer.business_name
            if pname not in producer_breakdown:
                producer_breakdown[pname] = {'items': [], 'subtotal': Decimal('0')}
            producer_breakdown[pname]['items'].append(item)
            producer_breakdown[pname]['subtotal'] += item.unit_price * item.quantity

    return render(request, 'marketplace/order_confirmation.html', {
        'order': order,
        'producer_breakdown': producer_breakdown,
    })

@customer_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'marketplace/order_history.html', {'orders': orders})


@producer_required
def producer_payments(request):
    profile = request.user.producer_profile

    order_items = OrderItem.objects.filter(
        product__producer=profile,
        order__status='delivered',
    ).select_related('order', 'product').order_by('-order__delivery_date')

    # Group by ISO week
    weeks = defaultdict(list)
    for item in order_items:
        iso = item.order.delivery_date.isocalendar()
        weeks[(iso[0], iso[1])].append(item)

    week_summaries = []
    for (year, week_num), items in sorted(weeks.items(), reverse=True):
        gross = sum(item.unit_price * item.quantity for item in items)
        commission = gross * Decimal('0.05')
        net = gross * Decimal('0.95')
        week_summaries.append({
            'year': year,
            'week': week_num,
            'start_date': date.fromisocalendar(year, week_num, 1),
            'end_date': date.fromisocalendar(year, week_num, 7),
            'items': items,
            'gross': gross,
            'commission': commission,
            'net': net,
        })

    # UK tax year: 6 April – 5 April
    today = date.today()
    if today.month < 4 or (today.month == 4 and today.day < 6):
        tax_year_start = date(today.year - 1, 4, 6)
    else:
        tax_year_start = date(today.year, 4, 6)

    ty_items = [i for i in order_items if i.order.delivery_date >= tax_year_start]
    tax_year_gross = sum(i.unit_price * i.quantity for i in ty_items)

    return render(request, 'marketplace/producer_payments.html', {
        'week_summaries': week_summaries,
        'tax_year_gross': tax_year_gross,
        'tax_year_net': tax_year_gross * Decimal('0.95'),
        'tax_year_start': tax_year_start,
    })


@producer_required
def producer_payments_export(request):
    profile = request.user.producer_profile

    order_items = OrderItem.objects.filter(
        product__producer=profile,
        order__status='delivered',
    ).select_related('order', 'product').order_by('-order__delivery_date')

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = (
        f'attachment; filename="payments_{profile.business_name.replace(" ", "_")}.csv"'
    )

    writer = csv.writer(response)
    writer.writerow(['Order #', 'Delivery Date', 'Product', 'Qty', 'Unit Price (£)', 'Gross (£)', 'Commission 5% (£)', 'Net 95% (£)'])

    for item in order_items:
        gross = item.unit_price * item.quantity
        writer.writerow([
            item.order.id,
            item.order.delivery_date,
            item.product.name if item.product else 'Deleted product',
            item.quantity,
            item.unit_price,
            gross,
            (gross * Decimal('0.05')).quantize(Decimal('0.01')),
            (gross * Decimal('0.95')).quantize(Decimal('0.01')),
        ])

    return response
@customer_required
def submit_review(request,product_pk):
    product = get_object_or_404(Product, pk=product_pk)

    # Check customer has a delivered order containing this product
    has_delivered_order = Order.objects.filter(
        customer=request.user,
        status='delivered',
        items__product=product
    ).exists()

    if not has_delivered_order:
        messages.error(request, 'You can only review products from delivered orders.')
        return redirect('product_detail', pk=product_pk)

    # Check they haven't already reviewed this product
    if Review.objects.filter(product=product, customer=request.user).exists():
        messages.error(request, 'You have already reviewed this product.')
        return redirect('product_detail', pk=product_pk)

    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.product = product
            review.customer = request.user
            review.save()
            messages.success(request, 'Your review has been submitted.')
            return redirect('product_detail', pk=product_pk)
    else:
        form = ReviewForm()

    return render(request, 'marketplace/submit_review.html', {
        'form': form,
        'product': product,
    })
