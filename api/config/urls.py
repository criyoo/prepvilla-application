from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from core import views as core_views


urlpatterns = [
  path("", RedirectView.as_view(url="/admin/", permanent=False)),
  path("api", core_views.api_root),
  path("admin/", admin.site.urls),
  path("api/", include("core.urls")),
]

if settings.DEBUG:
  urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
