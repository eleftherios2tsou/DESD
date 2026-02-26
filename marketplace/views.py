from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import RegistrationForm, ProducerRegistrationForm, ProductForm
from .models import ProducerProfile, Product
from .decorators import producer_required


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
    products = Product.objects.filter(producer=request.user.producer_profile).order_by('-created_at')
    return render(request, 'marketplace/dashboard.html', {'products': products})


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
