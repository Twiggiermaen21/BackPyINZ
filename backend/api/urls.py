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

    path('styl-artystyczny/', views.StylArtystycznyCreate.as_view()),
    path('kompozycja/', views.KompozycjaCreate.as_view()),
    path('kolorystyka/', views.KolorystykaCreate.as_view()),
    path('atmosfera/', views.AtmosferaCreate.as_view()),
    path('inspiracja/', views.InspiracjaCreate.as_view()),
    path('tlo/', views.TloCreate.as_view()),
    path('perspektywa/', views.PerspektywaCreate.as_view()),
    path('detale/', views.DetaleCreate.as_view()),
    path('realizm/', views.RealizmCreate.as_view()),
    path('styl-narracyjny/', views.StylNarracyjnyCreate.as_view()),
    path("calendars/", views.CalendarCreateView.as_view(), name="calendar-create"),

]