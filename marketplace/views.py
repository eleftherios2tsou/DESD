from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistrationForm, ProducerRegistrationForm, ProductForm,CheckoutForm
from .models import ProducerProfile, Product, Category, Order, OrderItem
from .decorators import producer_required, customer_required


def home(request):
    return render(request, 'marketplace/home.html')


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
        form = ProductForm(request.POST)
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
        form = ProductForm(request.POST, instance=product)
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
    return render(request, 'marketplace/product_detail.html', {'product': product})

@customer_required
def cart_add(request, pk):
    if request.method != 'POST':
        return redirect('product_list')
    product = get_object_or_404(Product, pk=pk)
    cart = request.session.get('cart', {})
    quantity = int(request.POST.get('quantity', 1))
    
    product_id = str(pk)
    if product_id in cart:
        cart[product_id]['quantity'] += quantity  # increase if already in cart
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
            
            # Clear cart
            del request.session['cart']
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