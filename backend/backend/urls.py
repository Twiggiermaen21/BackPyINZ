from django.contrib import admin
from django.urls import path,include
from api.views import CreateUserView, google_auth
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/user/register/",CreateUserView.as_view(),name="register"),
    path("api/token/",TokenObtainPairView.as_view(),name="get_token"),
    path("api/token/refresh/",TokenRefreshView.as_view(),name="refresh"),
    path("api-auth/",include("rest_framework.urls")),
    path('accounts/', include('allauth.urls')),
    path("api/auth/google/", google_auth),
    path("api/",include("api.urls")),
]

urlpatterns += static(settings.STATIC_IMAGES_URL, document_root=settings.STATIC_IMAGES_ROOT)

