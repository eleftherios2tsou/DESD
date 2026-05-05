from rest_framework import serializers
from datetime import date, timedelta
from decimal import Decimal
from .models import Category, Product, ProducerProfile, Order, OrderItem


# simple serializer for categories - just exposes the basic fields
class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'description']


# lightweight producer info that gets embedded inside product responses
# we dont want to return the full user object here, just the business name and postcode
class ProducerSummarySerializer(serializers.ModelSerializer):
    """Lightweight producer info embedded inside product responses."""
    class Meta:
        model = ProducerProfile
        fields = ['id', 'business_name', 'postcode']


class ProductSerializer(serializers.ModelSerializer):
    # nested serializers for read - returns full objects instead of just IDs
    producer = ProducerSummarySerializer(read_only=True)
    category = CategorySerializer(read_only=True)
    # category_id is write-only so API clients can set the category by ID
    # but the response returns the full category object
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


# used to show order items inside an order response
class OrderItemSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source='product.name', read_only=True)  # convenience field

    class Meta:
        model = OrderItem
        fields = ['id', 'product', 'product_name', 'quantity', 'unit_price']


# main order serializer - includes nested items
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


# producers only get to change the status field, nothing else
class OrderStatusSerializer(serializers.ModelSerializer):
    """Used by producers to update order status only."""
    class Meta:
        model = Order
        fields = ['status']


# used inside OrderCreateSerializer to validate each item in the cart
class OrderItemCreateSerializer(serializers.Serializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True))
    quantity = serializers.IntegerField(min_value=1)


# this handles creating an order via the API (POST /api/orders/)
class OrderCreateSerializer(serializers.Serializer):
    """Used by customers to create an order via the API."""
    delivery_address = serializers.CharField()
    delivery_date = serializers.DateField()
    items = OrderItemCreateSerializer(many=True)

    def validate_delivery_date(self, value):
        # same 48h rule as the checkout form
        if value < date.today() + timedelta(days=2):
            raise serializers.ValidationError('Delivery date must be at least 48 hours from now.')
        return value

    def validate_items(self, value):
        if not value:
            raise serializers.ValidationError('Order must contain at least one item.')
        return value

    def validate(self, attrs):
        # check stock for every item before creating anything
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
        # calculate total and commission before creating the order
        total = sum(item['product'].price * item['quantity'] for item in items_data)
        commission = total * Decimal('0.05')  # 5% platform fee

        order = Order.objects.create(
            customer=customer,
            delivery_address=validated_data['delivery_address'],
            delivery_date=validated_data['delivery_date'],
            total_price=total,
            commission_amount=commission,
        )

        # create an OrderItem for each product and decrement stock
        for item in items_data:
            product = item['product']
            OrderItem.objects.create(
                order=order,
                product=product,
                quantity=item['quantity'],
                unit_price=product.price,  # snapshot the price at time of order
            )
            product.stock -= item['quantity']
            product.save()

        return order
