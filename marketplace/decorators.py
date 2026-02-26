from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def login_required_custom(view_func):
    """Redirect unauthenticated users to login."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return wrapper


def producer_required(view_func):
    """Allow only users with the 'producer' role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        if request.user.role != 'producer':
            messages.error(request, 'Access denied. A producer account is required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


def customer_required(view_func):
    """Allow only users with a buyer role (customer, community_group, restaurant)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        if request.user.role not in ('customer', 'community_group', 'restaurant'):
            messages.error(request, 'Access denied. This page is for customers only.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper
