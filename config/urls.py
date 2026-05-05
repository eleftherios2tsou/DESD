from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

# main url config - everything routes through here first
urlpatterns = [
    path('admin/', admin.site.urls),                         # django admin panel
    path('api/', include('marketplace.api_urls')),           # REST API routes (S1-011)
    path('api-auth/', include('rest_framework.urls')),       # adds login/logout to the browsable api
    path('', include('marketplace.urls')),                   # all our main app urls
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# the static() call at the end serves uploaded images in development
# in production you'd use nginx or s3 for this but this is fine for now
