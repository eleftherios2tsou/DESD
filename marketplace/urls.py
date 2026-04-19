from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Auth
    path('register/', views.register, name='register'),
    path('register/producer/', views.register_producer, name='register_producer'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Producer dashboard & product CRUD
    path('dashboard/', views.producer_dashboard, name='dashboard'),
    path('dashboard/products/add/', views.product_create, name='product_create'),
    path('dashboard/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('dashboard/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('producer/orders/', views.producer_orders_management, name='producer_orders'),
    path('producer/orders/<int:pk>/update/', views.update_order_status, name='update_order_status'),

    # Producer public profile
    path('producers/<int:pk>/', views.producer_profile, name='producer_profile'),

    #Customer views
    path('products/', views.product_list, name='product_list'),
    path('products/<int:pk>/', views.product_detail, name='product_detail'),
    path('cart/', views.cart_view, name='cart_view'),
    path('cart/add/<int:pk>/', views.cart_add, name='cart_add'),
    path('cart/remove/<int:pk>/', views.cart_remove, name='cart_remove'),
    path('cart/update/<int:pk>/', views.cart_update, name='cart_update'),
    path('checkout/', views.checkout, name='checkout'),
    path('checkout/payment/', views.payment, name='payment'),
    path('checkout/complete/', views.checkout_complete, name='checkout_complete'),
    path('orders/history/', views.order_history, name='order_history'),
    path('orders/<int:pk>/confirmation/', views.order_confirmation, name='order_confirmation'),

    # Producer payments
    path('producer/payments/', views.producer_payments, name='producer_payments'),
    path('producer/payments/export/', views.producer_payments_export, name='producer_payments_export'),

    # Account settings
    path('account/settings/', views.account_settings, name='account_settings'),
    path('products/<int:product_pk>/review/', views.submit_review, name='submit_review'),
]
