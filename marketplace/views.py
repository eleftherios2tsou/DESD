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
from django.db.models import Avg, F, Q
from django.http import HttpResponse

from .forms import RegistrationForm, ProducerRegistrationForm, ProductForm, CheckoutForm, AccountSettingsForm, ProducerProfileForm,ReviewForm, CommunityGroupRegistrationForm, RestaurantRegistrationForm
from .models import ProducerProfile, Product, Category, Order, OrderItem, Review, WeeklyOrderItem,WeeklyOrderTemplate
from .decorators import producer_required, customer_required, restaurant_required
from.utils import calculate_food_distance

# helper function to email the producer when stock drops below their threshold (S3-016)
# called after every checkout so it triggers automatically
def _send_low_stock_alert(product):
    """Email the producer when a product's stock drops below its threshold."""
    if product.stock >= product.low_stock_threshold:
        return  # stock is fine, nothing to do
    producer = product.producer
    if not producer.user.email:
        return  # cant send email if producer hasnt set one
    send_mail(
        subject=f'Low Stock Alert: {product.name}',
        message=(
            f"Hi {producer.business_name},\n\n"
            f'Stock for "{product.name}" has fallen to {product.stock} unit(s), '
            f'below your alert threshold of {product.low_stock_threshold}.\n\n'
            f'Please update your stock from your producer dashboard.\n\n'
            f'Bristol Food Network'
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[producer.user.email],
        fail_silently=True,  # dont crash the checkout if email fails
    )


def home(request):
    # show the 6 most recently added active products on the homepage (S2-010)
    featured_products = Product.objects.filter(is_active=True).order_by('-created_at')[:6]
    return render(request, 'marketplace/home.html',{'featured_products': featured_products})


def register(request):
    if request.user.is_authenticated:
        return redirect('home')  # already logged in, dont show registration
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
            # create the producer profile at the same time as the user account
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

def community_register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = CommunityGroupRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please log in.')
            return redirect('login')
    else:
        form = CommunityGroupRegistrationForm()
    return render(request, 'marketplace/community_register.html', {'form': form})

def restaurant_register(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = RestaurantRegistrationForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Account created! Please log in.')
            return redirect('login')
    else:
        form = RestaurantRegistrationForm()
    return render(request, 'marketplace/restaurant_register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    lockout_msg = None

    if request.method == 'POST':
        from django.core.cache import cache
        username = request.POST.get('username', '').strip()
        # use the cache to track failed login attempts per username (S3-011)
        cache_key = f'login_attempts_{username}'
        attempts = cache.get(cache_key, 0)

        if attempts >= 5:
            # lock the account for 15 minutes after 5 failed attempts
            lockout_msg = 'Account temporarily locked after 5 failed attempts. Please try again in 15 minutes.'
            form = AuthenticationForm()
        else:
            # AuthenticationForm handles the actual password check
            form = AuthenticationForm(request, data=request.POST)
            if form.is_valid():
                cache.delete(cache_key)  # reset the counter on success
                user = form.get_user()
                auth_login(request, user)
                # if remember me is not ticked, expire the session when the browser closes
                if not request.POST.get('remember_me'):
                    request.session.set_expiry(0)
                else:
                    request.session.set_expiry(1209600)  # 2 weeks in seconds
                # producers go to their dashboard, everyone else goes home
                if user.role == 'producer':
                    return redirect('dashboard')
                return redirect('home')
            else:
                cache.set(cache_key, attempts + 1, 900)  # lock for 15 minutes
    else:
        form = AuthenticationForm()

    return render(request, 'marketplace/login.html', {'form': form, 'lockout_msg': lockout_msg})


def logout_view(request):
    auth_logout(request)
    return redirect('home')


@producer_required
def producer_dashboard(request):
    profile, created = ProducerProfile.objects.get_or_create(user=request.user)
    products = Product.objects.filter(producer=profile).order_by('-created_at')
    # F() lets us compare two fields on the same model in a query
    low_stock = products.filter(is_active=True, stock__lt=F('low_stock_threshold'))
    return render(request, 'marketplace/dashboard.html', {
        'products': products,
        'profile': profile,
        'low_stock_products': low_stock,  # shown as a warning banner in the dashboard
    })


@producer_required
def product_create(request):
    if request.method == 'POST':
        # request.FILES is needed for image uploads
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.producer = request.user.producer_profile  # tie product to logged in producer
            product.save()
            messages.success(request, f'Product "{product.name}" created successfully.')
            return redirect('dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/product_form.html', {'form': form, 'action': 'Create'})


@producer_required
def product_edit(request, pk):
    # get_object_or_404 also checks the producer matches so they cant edit someone elses product
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

@producer_required
def update_stock(request, pk):
    # quick stock update from dashboard without opening the full product edit form (S3-007)
    product = get_object_or_404(Product, pk=pk, producer=request.user.producer_profile)
    if request.method == 'POST':
        try:
            new_stock = int(request.POST.get('stock', product.stock))
            if new_stock < 0:
                raise ValueError
            product.stock = new_stock
            product.save()
            messages.success(request, f'Stock for "{product.name}" updated to {new_stock}.')
        except ValueError:
            messages.error(request, 'Please enter a valid non-negative integer for stock.')
    return redirect('dashboard')

def producer_profile(request, pk):
    # public profile page showing the producer's business info and all their active products
    profile = get_object_or_404(ProducerProfile, pk=pk)
    products = Product.objects.filter(producer=profile, is_active=True).order_by('-created_at')
    return render(request, 'marketplace/producer_profile.html', {'profile': profile, 'products': products})


def product_list(request):
    # exclude out of season products from the catalogue
    products = Product.objects.filter(is_active=True).exclude(season_status = 'out_of_season').select_related('producer', 'category')

    # read filter values from the query string (?search=apple&category=veg&organic=1)
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    organic = request.GET.get('organic', '')

    if search:
        # Q objects let us do OR queries - searches name, description, and producer name
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
    # aggregate calculates the average rating across all reviews
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg']

    # calculate food miles if we have the customer's postcode from a previous checkout
    food_miles = None
    customer_postcode = request.session.get('customer_postcode') if request.user.is_authenticated else None
    if customer_postcode:
        food_miles = calculate_food_distance(customer_postcode, product.producer.postcode)

    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'food_distance': food_miles,
    })


@producer_required
def producer_orders_management(request):
    # only show orders that contain this producer's products
    orders = Order.objects.filter(items__product__producer=request.user.producer_profile).distinct().order_by('-created_at')
    return render(request, 'marketplace/producer_orders.html', {'orders': orders})

@producer_required
def update_order_status(request, pk):
    # also check the order contains this producer's products before allowing the update
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

    producer_form = None  # only shown for producer accounts

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
            # update_session_auth_hash keeps the user logged in after a password change
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
    # cart is stored in the session as a dict keyed by product id
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    # use sale price if product is discounted, otherwise use the regular price
    effective_price = float(product.sale_price) if product.is_discounted and product.sale_price else float(product.price)

    product_id = str(pk)
    current_in_cart = cart[product_id]['quantity'] if product_id in cart else 0
    # check we have enough stock including what's already in the cart
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
    total_food_distance = 0
    # if we know the customer's postcode, calculate cumulative food miles for the whole cart
    customer_postcode = request.session.get('customer_postcode')
    if customer_postcode:
        for pid, item in cart.items():
            try:
                product = Product.objects.get(pk=int(pid))
                distance = calculate_food_distance(customer_postcode, product.producer.postcode)
                if distance :
                    total_food_distance += distance
            except Product.DoesNotExist:
                continue  # product might have been deleted since it was added to cart
    total = sum(float(item['price']) * item['quantity'] for item in cart.values())
    return render(request, 'marketplace/cart.html', {
        'cart': cart,
        'total': total,
        'total_food_miles': round(total_food_distance, 1) if total_food_distance else None,
    })

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
            del cart[product_id]  # remove the item if quantity set to 0
    request.session['cart'] = cart
    return redirect('cart_view')

@customer_required
def checkout(request):
    cart = request.session.get('cart', {})
    if not cart:
        return redirect('cart_view')  # nothing to checkout

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
                'special_delivery_instructions': form.cleaned_data.get('special_delivery_instructions', '')
            }
            # save postcode to session so food miles work on product pages after checkout
            request.session['customer_postcode'] = form.cleaned_data['postcode']
            request.session['cart'] = cart  # ensure subtotals are persisted

            # Create Stripe PaymentIntent - amount is in pence so multiply by 100
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
    commission = total * 0.05  # 5% platform fee shown at checkout

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
    # stripe sends the client_secret to the browser so it can confirm the payment
    client_secret = request.session.get('stripe_client_secret')
    if not client_secret or not request.session.get('pending_checkout'):
        return redirect('checkout')  # something went wrong, start over

    return render(request, 'marketplace/payment.html', {
        'client_secret': client_secret,
        'publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })


@customer_required
def checkout_complete(request):
    # stripe redirects here after payment with payment_intent and redirect_status in the url
    payment_intent_id = request.GET.get('payment_intent')
    redirect_status = request.GET.get('redirect_status')

    if redirect_status != 'succeeded' or not payment_intent_id:
        messages.error(request, 'Payment was not successful. Please try again.')
        return redirect('cart_view')

    # Idempotency: if this PaymentIntent already created an order, show it
    # prevents duplicate orders if the user refreshes the confirmation page
    existing = Order.objects.filter(payment_intent_id=payment_intent_id).first()
    if existing:
        return redirect('order_confirmation', pk=existing.pk)

    # Verify with Stripe that the payment actually went through
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

    # create the order in the database now that payment is confirmed
    order = Order.objects.create(
        customer=request.user,
        delivery_address=pending['delivery_address'],
        delivery_date=date.fromisoformat(pending['delivery_date']),
        total_price=total,
        commission_amount=commission,
        status='paid',
        payment_intent_id=payment_intent_id,  # store so we can do idempotency check above
    )

    # create order items and decrement stock
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
        _send_low_stock_alert(product)  # email producer if stock is now low

    # Clear session data now that the order is saved
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

    # Per-producer notification emails - each producer only gets notified about their own items
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

    # group items by producer so we can show a per-producer breakdown (S3-002)
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
    # show most recent orders first
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')

    return render(request, 'marketplace/order_history.html', {'orders': orders})

@customer_required
def reorder(request, pk):
    # adds all items from a previous order back into the cart (S3-008)
    order = get_object_or_404(Order, pk=pk, customer=request.user)
    cart = request.session.get('cart', {})
    unavailable = []

    for item in order.items.all():
        product = item.product
        # skip products that no longer exist or are out of stock
        if product is None or not product.is_active or product.stock == 0:
            unavailable.append(item.product.name if product else 'Deleted product')
            continue

        pid = str(product.id)
        # dont add more than what's in stock
        qty = min(item.quantity, product.stock)

        effective_price = (
            float(product.sale_price) if product.is_discounted and product.sale_price
            else float(product.price)
        )
        if pid in cart:
            cart[pid]['quantity'] += qty
            cart[pid]['subtotal'] = float(cart[pid]['price']) * cart[pid]['quantity']
        else:
            cart[pid] = {
                'name': product.name,
                'price': str(effective_price),
                'quantity': qty,
                'producer': product.producer.business_name,
                'subtotal': effective_price * qty,
            }
    request.session['cart'] = cart
    request.session.modified = True  # tell django the session has changed

    if unavailable:
        messages.warning(request, f'Some items were unavailable and not added to cart: {", ".join(unavailable)}')

    messages.success(request, 'Order items added to cart. Please review your cart before checkout.')
    return redirect('cart_view')

@producer_required
def producer_payments(request):
    # payment settlements page showing weekly earnings (S3-003)
    profile = request.user.producer_profile

    # only count delivered orders - pending/paid orders arent settled yet
    order_items = OrderItem.objects.filter(
        product__producer=profile,
        order__status='delivered',
    ).select_related('order', 'product').order_by('-order__delivery_date')

    # group order items by ISO week number so we can show weekly summaries
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

    # UK tax year runs 6 April to 5 April the following year
    today = date.today()
    if today.month < 4 or (today.month == 4 and today.day < 6):
        tax_year_start = date(today.year - 1, 4, 6)
    else:
        tax_year_start = date(today.year, 4, 6)

    # filter to only items in the current tax year for the running total
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
    # download the payments data as a CSV file
    profile = request.user.producer_profile

    order_items = OrderItem.objects.filter(
        product__producer=profile,
        order__status='delivered',
    ).select_related('order', 'product').order_by('-order__delivery_date')

    # set content-disposition to attachment so the browser downloads it instead of showing it
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
def submit_review(request, product_pk):
    product = get_object_or_404(Product, pk=product_pk)

    # Check customer has a delivered order containing this product
    # you shouldnt be able to review something you havent actually received
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


def delete_account(request):
    # GDPR right to erasure - deletes the user and all their data (S3-011)
    if not request.user.is_authenticated:
        return redirect('login')
    if request.method == 'POST':
        if request.POST.get('confirm') == 'DELETE':
            user = request.user
            auth_logout(request)  # log out before deleting so the session doesnt break
            user.delete()  # CASCADE removes orders, reviews, producer profile
            messages.success(request, 'Your account and all personal data have been permanently deleted.')
            return redirect('home')
        messages.error(request, 'Please type DELETE exactly to confirm.')
        return redirect('account_settings')
    return redirect('account_settings')


@restaurant_required
def weekly_order_template(request):
    # restaurant feature - lets them save a recurring order and add it all to cart at once (S3-010)
    # get_or_create means the template is created automatically on first visit
    template, created = WeeklyOrderTemplate.objects.get_or_create(customer = request.user)
    items = template.items.select_related('product').all()

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'add':
            product_id = request.POST.get('product_id')
            quantity = int(request.POST.get('quantity', 1))
            product = get_object_or_404(Product, pk=product_id, is_active=True)
            # get_or_create so we dont end up with duplicate items for the same product
            item, item_created = WeeklyOrderItem.objects.get_or_create(template=template, product=product, defaults={'quantity': quantity})
            if not item_created:
                item.quantity = quantity  # update quantity if item already exists
                item.save()
            messages.success(request, f'Added "{product.name}" to your weekly template.')

        elif action == 'remove':
            item_id = request.POST.get('item_id')
            WeeklyOrderItem.objects.filter(pk=item_id, template=template).delete()
            messages.success(request, 'Item removed from your weekly template.')

        elif action == 'to_cart':
            # add all template items to the session cart in one click
            cart = request.session.get('cart', {})
            for item in items:
                product = item.product
                if product.is_active and product.stock > 0:
                    pid = str(product.id)
                    qty = min(item.quantity, product.stock)
                    effective_price = float(product.sale_price) if product.is_discounted and product.sale_price else float(product.price)
                    if pid in cart:
                        cart[pid]['quantity'] += qty
                        cart[pid]['subtotal'] = float(cart[pid]['price']) * cart[pid]['quantity']
                    else:
                        cart[pid] = {
                            'name': product.name,
                            'price': str(effective_price),
                            'quantity': qty,
                            'producer': product.producer.business_name,
                            'subtotal': effective_price * qty,
                        }
            request.session['cart'] = cart
            request.session.modified = True
            messages.success(request, 'Weekly template items added to cart. Please review your cart before checkout.')
            return redirect('cart_view')
        return redirect('weekly_order_template')

    # only show active, in-season products in the template picker
    products = Product.objects.filter(is_active=True).exclude(season_status = 'out_of_season').select_related('producer', 'category')
    return render(request, 'marketplace/weekly_order_template.html', {
        'template': template,
        'items': items,
        'products': products,
    })
