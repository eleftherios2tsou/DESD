from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

# custom decorators for role-based access control (S1-005)
# used like @producer_required above a view function to restrict access

def login_required_custom(view_func):
    """Redirect unauthenticated users to login."""
    @wraps(view_func)  # @wraps preserves the original function name and docstring
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
        # check the role field we added to CustomUser
        if request.user.role != 'producer':
            messages.error(request, 'Access denied. A producer account is required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper


# community groups and restaurants are treated as buyers, same as customers
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

def community_group_required(view_func):
    """Allow only users with the 'community_group' role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        if request.user.role != 'community_group':
            messages.error(request, 'Access denied. A community group account is required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper

def restaurant_required(view_func):
    """Allow only users with the 'restaurant' role."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please log in to access this page.')
            return redirect('login')
        if request.user.role != 'restaurant':
            messages.error(request, 'Access denied. A restaurant account is required.')
            return redirect('home')
        return view_func(request, *args, **kwargs)
    return wrapper
