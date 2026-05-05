import os
from django.core.wsgi import get_wsgi_application

# wsgi is what the web server uses to talk to django
# docker uses this when running the app
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()
