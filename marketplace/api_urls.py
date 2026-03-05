from rest_framework.routers import DefaultRouter
from . import api_views

router = DefaultRouter()
router.register(r'products', api_views.ProductViewSet, basename='api-product')
router.register(r'categories', api_views.CategoryViewSet, basename='api-category')
router.register(r'orders', api_views.OrderViewSet, basename='api-order')

urlpatterns = router.urls
