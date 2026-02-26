from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, ProducerProfile, Category, Product


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    fieldsets = list(UserAdmin.fieldsets) + [('Role', {'fields': ('role',)})]
    list_display = ['username', 'email', 'role', 'is_active', 'date_joined']
    list_filter = ['role', 'is_active']
    search_fields = ['username', 'email']


@admin.register(ProducerProfile)
class ProducerProfileAdmin(admin.ModelAdmin):
    list_display = ['business_name', 'user', 'postcode']
    search_fields = ['business_name', 'user__username', 'postcode']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'producer', 'category', 'price', 'stock', 'is_active', 'is_organic']
    list_filter = ['is_active', 'is_organic', 'is_seasonal', 'category']
    search_fields = ['name', 'producer__business_name', 'farm_origin']
    date_hierarchy = 'created_at'
