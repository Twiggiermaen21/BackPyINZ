from django.urls import path
from . import views

urlpatterns=[

path('generate/', views.GenerateImage.as_view(), name='generate-image'),
path('generate-image-to-image-sdxl/', views.GenerateImageToImageSDXLView.as_view(), name='generate-image-to-image-sdxl'),
path('upscale-image/', views.UpscalingView.as_view(), name='upscale-image'),

    path("user/update-profile/", views.ProfileUpdateView.as_view(), name="update-profile"),
    path("user/change-email/", views.EmailUpdateView.as_view(), name="change-email"),
    path("user/change-password/",views.PasswordChangeView.as_view(), name="change-password"),
    path("user/update-profile-image/", views.UpdateProfileImageView.as_view(), name="update-profile-image"),

       path('styl_artystyczny/', views.StylArtystycznyCreate.as_view(), name='styl-artystyczny-list'),
    path('styl_artystyczny/<int:pk>/', views.StylArtystycznyDetail.as_view(), name='styl-artystyczny-detail'),

    path('kompozycja/', views.KompozycjaCreate.as_view(), name='kompozycja-list'),
    path('kompozycja/<int:pk>/', views.KompozycjaDetail.as_view(), name='kompozycja-detail'),

    path('kolorystyka/', views.KolorystykaCreate.as_view(), name='kolorystyka-list'),
    path('kolorystyka/<int:pk>/', views.KolorystykaDetail.as_view(), name='kolorystyka-detail'),

    path('atmosfera/', views.AtmosferaCreate.as_view(), name='atmosfera-list'),
    path('atmosfera/<int:pk>/', views.AtmosferaDetail.as_view(), name='atmosfera-detail'),

    path('inspiracja/', views.InspiracjaCreate.as_view(), name='inspiracja-list'),
    path('inspiracja/<int:pk>/', views.InspiracjaDetail.as_view(), name='inspiracja-detail'),

    path('tlo/', views.TloCreate.as_view(), name='tlo-list'),
    path('tlo/<int:pk>/', views.TloDetail.as_view(), name='tlo-detail'),

    path('perspektywa/', views.PerspektywaCreate.as_view(), name='perspektywa-list'),
    path('perspektywa/<int:pk>/', views.PerspektywaDetail.as_view(), name='perspektywa-detail'),

    path('detale/', views.DetaleCreate.as_view(), name='detale-list'),
    path('detale/<int:pk>/', views.DetaleDetail.as_view(), name='detale-detail'),

    path('realizm/', views.RealizmCreate.as_view(), name='realizm-list'),
    path('realizm/<int:pk>/', views.RealizmDetail.as_view(), name='realizm-detail'),

    path('styl_narracyjny/', views.StylNarracyjnyCreate.as_view(), name='styl-narracyjny-list'),
    path('styl_narracyjny/<int:pk>/', views.StylNarracyjnyDetail.as_view(), name='styl-narracyjny-detail'),


    path("calendars/", views.CalendarCreateView.as_view(), name="calendar-create"),
    path("calendar/<int:pk>/", views.CalendarUpdateView.as_view(), name="calendar-update"),

]