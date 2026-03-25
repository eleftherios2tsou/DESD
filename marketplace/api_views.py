from rest_framework import viewsets, permissions, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Category, Product, Order
from .serializers import CategorySerializer, ProductSerializer, OrderSerializer, OrderCreateSerializer, OrderStatusSerializer


class IsProducerOrReadOnly(permissions.BasePermission):
    """
    Read access: anyone (including anonymous).
    Write access: only authenticated producers, and only for their own products.
    """
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated and request.user.role == 'producer'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.producer == request.user.producer_profile


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """
    List and retrieve product categories.
    GET /api/categories/
    GET /api/categories/{id}/
    """
    queryset = Category.objects.all().order_by('name')
    serializer_class = CategorySerializer
    permission_classes = [permissions.AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    """
    Full CRUD for products.
    GET    /api/products/           — list active products (public)
    GET    /api/products/{id}/      — product detail (public)
    POST   /api/products/           — create product (producers only)
    PUT    /api/products/{id}/      — full update (own products only)
    PATCH  /api/products/{id}/      — partial update (own products only)
    DELETE /api/products/{id}/      — delete (own products only)
    GET    /api/products/my/        — list caller's own products (producers only)
    """
    queryset = Product.objects.select_related('producer', 'category').filter(is_active=True)
    serializer_class = ProductSerializer
    permission_classes = [IsProducerOrReadOnly]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description', 'farm_origin', 'producer__business_name']
    ordering_fields = ['price', 'created_at', 'name']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = Product.objects.select_related('producer', 'category').filter(is_active=True)

        # Optional filters via query params
        category = self.request.query_params.get('category')
        organic = self.request.query_params.get('organic')

        if category:
            qs = qs.filter(category__slug=category)
        if organic in ('true', '1'):
            qs = qs.filter(is_organic=True)

        return qs

    def perform_create(self, serializer):
        serializer.save(producer=self.request.user.producer_profile)

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my(self, request):
        """Return only the authenticated producer's products (including inactive)."""
        if request.user.role != 'producer':
            return Response({'detail': 'Producer account required.'}, status=403)
        products = Product.objects.filter(
            producer=request.user.producer_profile
        ).order_by('-created_at')
        serializer = self.get_serializer(products, many=True)
        return Response(serializer.data)


class IsCustomer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'customer'


class IsProducer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role == 'producer'


class OrderViewSet(viewsets.ModelViewSet):
    """
    GET    /api/orders/         — own orders (customers) or orders with their products (producers)
    GET    /api/orders/{id}/    — order detail
    POST   /api/orders/         — create order (customers only)
    PATCH  /api/orders/{id}/    — update status (producers only)
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'head', 'options']

    def get_queryset(self):
        user = self.request.user
        if user.role == 'producer':
            return Order.objects.filter(
                items__product__producer=user.producer_profile
            ).distinct().prefetch_related('items__product').order_by('-created_at')
        return Order.objects.filter(
            customer=user
        ).prefetch_related('items__product').order_by('-created_at')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        if self.action == 'partial_update':
            return OrderStatusSerializer
        return OrderSerializer

    def get_permissions(self):
        if self.action == 'create':
            return [permissions.IsAuthenticated(), IsCustomer()]
        if self.action == 'partial_update':
            return [permissions.IsAuthenticated(), IsProducer()]
        return [permissions.IsAuthenticated()]

    def create(self, request, *args, **kwargs):
        serializer = OrderCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        order = serializer.save()
        return Response(OrderSerializer(order).data, status=status.HTTP_201_CREATED)

    def partial_update(self, request, *args, **kwargs):
        order = self.get_object()
        if not order.items.filter(product__producer=request.user.producer_profile).exists():
            return Response(
                {'detail': 'You do not have permission to update this order.'},
                status=status.HTTP_403_FORBIDDEN
            )
        serializer = OrderStatusSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(OrderSerializer(order).data)
