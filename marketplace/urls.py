from django.urls import path
from . import views

# all the url patterns for the marketplace app
# these get included in config/urls.py under the root path
urlpatterns = [
    path('', views.home, name='home'),

    # Auth
    path('register/', views.register, name='register'),
    path('register/producer/', views.register_producer, name='register_producer'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/community/', views.community_register, name='community_register'),
    path('register/restaurant/', views.restaurant_register, name='restaurant_register'),
    path('weekly-order/', views.weekly_order_template, name='weekly_order_template'),  # restaurant feature (S3-010)

    # Producer dashboard & product CRUD
    path('dashboard/', views.producer_dashboard, name='dashboard'),
    path('dashboard/products/add/', views.product_create, name='product_create'),
    path('dashboard/products/<int:pk>/edit/', views.product_edit, name='product_edit'),
    path('dashboard/products/<int:pk>/delete/', views.product_delete, name='product_delete'),
    path('producer/orders/', views.producer_orders_management, name='producer_orders'),
    path('producer/orders/<int:pk>/update/', views.update_order_status, name='update_order_status'),
    path('dashboard/products/<int:pk>/stock/', views.update_stock, name='update_stock'),  # quick stock update (S3-007)

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
    path('checkout/payment/', views.payment, name='payment'),           # stripe payment page
    path('checkout/complete/', views.checkout_complete, name='checkout_complete'),  # stripe redirects here
    path('orders/history/', views.order_history, name='order_history'),
    path('orders/<int:pk>/confirmation/', views.order_confirmation, name='order_confirmation'),
    path('orders/<int:pk>/reorder/', views.reorder, name='reorder'),    # reorder from history (S3-008)

    # Producer payments
    path('producer/payments/', views.producer_payments, name='producer_payments'),
    path('producer/payments/export/', views.producer_payments_export, name='producer_payments_export'),  # csv download

    # Account settings & GDPR
    path('account/settings/', views.account_settings, name='account_settings'),
    path('account/delete/', views.delete_account, name='delete_account'),  # GDPR right to erasure (S3-011)
    path('products/<int:product_pk>/review/', views.submit_review, name='submit_review'),
]
