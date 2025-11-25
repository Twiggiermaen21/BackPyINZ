from django.urls import path

from .views.metadata_views import *
from .views.profile_views import *
from .views.calendar_views import *
from .views.image_views import *
urlpatterns=[

path('generate/', GenerateImage.as_view(), name='generate-image'),
path('generate-image-to-image-sdxl/', GenerateImageToImageSDXLView.as_view(), name='generate-image-to-image-sdxl'),
path('upscale-image/', UpscalingView.as_view(), name='upscale-image'),
path("images-by-project/<str:project_name>/", ImagesByProjectView.as_view()),

    path("user/update-profile/", ProfileUpdateView.as_view(), name="update-profile"),
    path("user/change-email/", EmailUpdateView.as_view(), name="change-email"),
    path("user/change-password/",PasswordChangeView.as_view(), name="change-password"),
    path("user/update-profile-image/", UpdateProfileImageView.as_view(), name="update-profile-image"),
    path("calendars/", CalendarCreateView.as_view(), name="calendar-create"),
    path("calendar/<int:pk>/", CalendarUpdateView.as_view(), name="calendar-update"),
    path("calendar-destroy/<int:pk>/", CalendarDetailView.as_view(), name="calendar-detail"),
    path("calendar-print/", CalendarPrint.as_view(), name="calendar-print"),

    path("calendar-by-project/<str:project_name>/", CalendarByProjectView.as_view()),


    path("calendar-search/", CalendarSearchBarView.as_view(), name="calendar-search"),
    path("image-search/", ImageSearchBarView.as_view(), name="image-search"),


    path('styl_artystyczny/', StylArtystycznyCreate.as_view(), name='styl-artystyczny-list'),
    path('styl_artystyczny/<int:pk>/', StylArtystycznyDetail.as_view(), name='styl-artystyczny-detail'),

    path('kompozycja/', KompozycjaCreate.as_view(), name='kompozycja-list'),
    path('kompozycja/<int:pk>/', KompozycjaDetail.as_view(), name='kompozycja-detail'),

    path('kolorystyka/', KolorystykaCreate.as_view(), name='kolorystyka-list'),
    path('kolorystyka/<int:pk>/', KolorystykaDetail.as_view(), name='kolorystyka-detail'),

    path('atmosfera/', AtmosferaCreate.as_view(), name='atmosfera-list'),
    path('atmosfera/<int:pk>/', AtmosferaDetail.as_view(), name='atmosfera-detail'),

    path('inspiracja/', InspiracjaCreate.as_view(), name='inspiracja-list'),
    path('inspiracja/<int:pk>/', InspiracjaDetail.as_view(), name='inspiracja-detail'),

    path('tlo/', TloCreate.as_view(), name='tlo-list'),
    path('tlo/<int:pk>/', TloDetail.as_view(), name='tlo-detail'),

    path('perspektywa/', PerspektywaCreate.as_view(), name='perspektywa-list'),
    path('perspektywa/<int:pk>/', PerspektywaDetail.as_view(), name='perspektywa-detail'),

    path('detale/', DetaleCreate.as_view(), name='detale-list'),
    path('detale/<int:pk>/', DetaleDetail.as_view(), name='detale-detail'),

    path('realizm/', RealizmCreate.as_view(), name='realizm-list'),
    path('realizm/<int:pk>/', RealizmDetail.as_view(), name='realizm-detail'),

    path('styl_narracyjny/', StylNarracyjnyCreate.as_view(), name='styl-narracyjny-list'),
    path('styl_narracyjny/<int:pk>/', StylNarracyjnyDetail.as_view(), name='styl-narracyjny-detail'),



]