from rest_framework.routers import DefaultRouter
from . import api_views

# DRF router automatically generates all the standard urls for each viewset
# e.g. /api/products/, /api/products/<id>/, etc.
router = DefaultRouter()
router.register(r'products', api_views.ProductViewSet, basename='api-product')
router.register(r'categories', api_views.CategoryViewSet, basename='api-category')
router.register(r'orders', api_views.OrderViewSet, basename='api-order')

# router.urls contains all the generated url patterns
urlpatterns = router.urls
