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
]
