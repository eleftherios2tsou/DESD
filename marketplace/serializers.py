from rest_framework import serializers
from .models import Category, Product, ProducerProfile


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']


class ProducerSummarySerializer(serializers.ModelSerializer):
    """Lightweight producer info embedded inside product responses."""
    class Meta:
        model = ProducerProfile
        fields = ['id', 'business_name', 'postcode']


class ProductSerializer(serializers.ModelSerializer):
    producer = ProducerSummarySerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True,
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Product
        fields = [
            'id', 'name', 'description', 'price', 'stock',
            'allergens', 'is_organic',
            'harvest_date', 'best_before',
            'farm_origin', 'is_seasonal', 'seasonal_months',
            'lead_time_hours', 'is_active',
            'producer', 'category', 'category_id',
            'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'producer', 'created_at', 'updated_at']
