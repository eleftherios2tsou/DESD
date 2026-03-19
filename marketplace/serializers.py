from rest_framework import serializers
from datetime import date, timedelta
from decimal import Decimal
from .models import Category, Product, ProducerProfile, Order, OrderItem


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


class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    customer_username = serializers.CharField(source='customer.username', read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'customer_username', 'status',
            'delivery_address', 'delivery_date',
            'total_price', 'commission_amount',
            'items', 'created_at', 'updated_at',
        ]
        read_only_fields = ['id', 'customer_username', 'total_price', 'commission_amount', 'created_at', 'updated_at']


class OrderStatusSerializer(serializers.ModelSerializer):
    """Used by producers to update order status only."""
    class Meta:
        model = Order
        fields = ['status']


class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1)


class OrderCreateSerializer(serializers.Serializer):
    """Used by customers to create an order via the API."""
    delivery_address = serializers.CharField()
    delivery_date = serializers.DateField()
    items = OrderItemCreateSerializer(many=True)

    def validate_delivery_date(self, value):
        if value < date.today() + timedelta(days=2):
            raise serializers.ValidationError('Delivery date must be at least 48 hours from now.')
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Order must contain at least one item.')
        return value

    def validate(self, attrs):
        for item in attrs.get('items', []):
            product = item['product']
            if product.stock < item['quantity']:
                raise serializers.ValidationError(
                    f'Insufficient stock for "{product.name}". Only {product.stock} available.'
                )
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        customer = self.context['request'].user
        total = sum(item['product'].price * item['quantity'] for item in items_data)
        commission = total * Decimal('0.05')

        order = Order.objects.create(
            customer=customer,
            delivery_address=validated_data['delivery_address'],
            delivery_date=validated_data['delivery_date'],
            total_price=total,
            commission_amount=commission,
        )

        for item in items_data:
            product = item['product']
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                unit_price=product.price,
            )
            product.stock -= item['quantity']
            product.save()

        return order
