from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout, update_session_auth_hash
from django.contrib.auth.forms import AuthenticationForm
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Avg
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
    products = Product.objects.filter(is_active=True)
    
    # Get query parameters from URL
    search = request.GET.get('search', '')
    category = request.GET.get('category', '')
    organic = request.GET.get('organic', '')
    
    # Apply filters if they exist
    if search:
        products = products.filter(name__icontains=search)
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
            # Validate stock before creating anything
            for product_id, item in cart.items():
                product = get_object_or_404(Product, pk=int(product_id))
                if product.stock < item['quantity']:
                    messages.error(request, f'"{product.name}" only has {product.stock} units in stock. Please update your cart.')
                    return redirect('cart_view')

            # Calculate total
            for item in cart.values():
                item['subtotal'] = float(item['price']) * item['quantity']

            total = sum(item['subtotal'] for item in cart.values())
            commission = total * 0.05

            # Create order
            order = Order.objects.create(
                customer=request.user,
                delivery_address=form.cleaned_data['delivery_address'],
                delivery_date=form.cleaned_data['delivery_date'],
                total_price=total,
                commission_amount=commission
            )
            
            # Create order items
            for product_id, item in cart.items():
                product = get_object_or_404(Product, pk=int(product_id))
                OrderItem.objects.create(
                    order=order,
                    product=product,
                    quantity=item['quantity'],
                    unit_price=item['price']
                )
            #Update product stock
                product.stock -= item['quantity']
                product.save()
            
            # Clear cart
            del request.session['cart']

            # Build item summary for emails
            item_lines = '\n'.join(
                f"  - {item['name']} x{item['quantity']}  £{item['subtotal']:.2f}"
                for item in cart.values()
            )

            # Email to customer
            if request.user.email:
                send_mail(
                    subject=f'Order #{order.id} Confirmed — Bristol Food Network',
                    message=(
                        f"Hi {request.user.username},\n\n"
                        f"Your order has been placed successfully!\n\n"
                        f"Order #{order.id}\n"
                        f"Delivery date: {order.delivery_date}\n"
                        f"Delivery address: {order.delivery_address}\n\n"
                        f"Items:\n{item_lines}\n\n"
                        f"Subtotal: £{total:.2f}\n"
                        f"Commission (5%): £{commission:.2f}\n"
                        f"Total: £{total + commission:.2f}\n\n"
                        f"Thank you for supporting local producers!\n\n"
                        f"Bristol Food Network"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[request.user.email],
                    fail_silently=True,
                )

            # Email to each unique producer — only their own items
            producer_items = {}
            for product_id, item in cart.items():
                product = Product.objects.filter(pk=int(product_id)).first()
                if product:
                    pid = product.producer.pk
                    if pid not in producer_items:
                        producer_items[pid] = {'producer': product.producer, 'lines': []}
                    producer_items[pid]['lines'].append(
                        f"  - {item['name']} x{item['quantity']}  £{item['subtotal']:.2f}"
                    )

            for pid, data in producer_items.items():
                producer = data['producer']
                if producer.user.email:
                    producer_item_lines = '\n'.join(data['lines'])
                    send_mail(
                        subject=f'New Order #{order.id} for your products',
                        message=(
                            f"Hi {producer.business_name},\n\n"
                            f"You have a new order from {request.user.username}.\n\n"
                            f"Order #{order.id}\n"
                            f"Delivery date: {order.delivery_date}\n\n"
                            f"Items ordered from you:\n{producer_item_lines}\n\n"
                            f"Please confirm the order from your dashboard.\n\n"
                            f"Bristol Food Network"
                        ),
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[producer.user.email],
                        fail_silently=True,
                    )

            messages.success(request, f'Order #{order.id} placed successfully!')
            return redirect('home')
    else:
        form = CheckoutForm()
    
    # Calculate subtotals for template display
    for item in cart.values():
        item['subtotal'] = float(item['price']) * item['quantity']
    
    total = sum(item['subtotal'] for item in cart.values())
    commission = total * 0.05

    return render(request, 'marketplace/checkout.html', {
        'form': form, 
        'cart': cart, 
        'total': total,
        'commission': commission
    })

@customer_required
def order_history(request):
    orders = Order.objects.filter(customer=request.user).order_by('-created_at')
    return render(request, 'marketplace/order_history.html', {'orders': orders})
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
