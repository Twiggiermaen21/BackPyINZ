from django.urls import path
from . import views

urlpatterns=[
path("notes/",views.NoteListCreate.as_view(),name="note-list"),
path("notes/delete/<int:pk>/",views.NoteDelete.as_view(),name="delete-note"),
path('generate/', views.GenerateImage.as_view(), name='generate-image'),
path('generate-image-to-image-sdxl/', views.GenerateImageToImageSDXLView.as_view(), name='generate-image-to-image-sdxl'),
path('upscale-image/', views.UpscalingView.as_view(), name='upscale-image'),

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