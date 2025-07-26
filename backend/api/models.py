from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Note(models.Model):
    title = models.CharField(max_length=100)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User,on_delete=models.CASCADE,related_name="notes")

    def __str__(self):
        return self.title 
class GeneratedImage(models.Model):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prompt = models.CharField(max_length=500)
    height = models.IntegerField(default=512)
    width = models.IntegerField(default=512)
    
    styl_artystyczny = models.ForeignKey('StylArtystyczny', on_delete=models.SET_NULL, null=True, blank=True)
    kompozycja = models.ForeignKey('Kompozycja', on_delete=models.SET_NULL, null=True, blank=True)
    kolorystyka = models.ForeignKey('Kolorystyka', on_delete=models.SET_NULL, null=True, blank=True)
    atmosfera = models.ForeignKey('Atmosfera', on_delete=models.SET_NULL, null=True, blank=True)
    inspiracja = models.ForeignKey('Inspiracja', on_delete=models.SET_NULL, null=True, blank=True)
    tlo = models.ForeignKey('Tlo', on_delete=models.SET_NULL, null=True, blank=True)
    perspektywa = models.ForeignKey('Perspektywa', on_delete=models.SET_NULL, null=True, blank=True)
    detale = models.ForeignKey('Detale', on_delete=models.SET_NULL, null=True, blank=True)
    realizm = models.ForeignKey('Realizm', on_delete=models.SET_NULL, null=True, blank=True)
    styl_narracyjny = models.ForeignKey('StylNarracyjny', on_delete=models.SET_NULL, null=True, blank=True)

    url = models.CharField(max_length=255, default="unknown")
    created_at = models.DateTimeField(auto_now_add=True)


class Calendar(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    top_image = models.ForeignKey('GeneratedImage', on_delete=models.SET_NULL, null=True, blank=True, related_name="calendar_top_image")

    # bottom type
    BOTTOM_TYPE_CHOICES = [
        ("image", "Image"),
        ("color", "Color"),
        ("gradient", "Gradient"),
        ("theme-gradient", "Theme Gradient"),
    ]
    bottom_type = models.CharField(max_length=20, choices=BOTTOM_TYPE_CHOICES)

    # if bottom is an image
    bottom_image = models.ForeignKey('GeneratedImage', on_delete=models.SET_NULL, null=True, blank=True, related_name="calendar_bottom_image")

    # if bottom is a solid color
    bottom_color = models.CharField(max_length=7, blank=True, null=True)  # e.g. "#ffffff"

    # if bottom is a gradient
    gradient_start_color = models.CharField(max_length=7, blank=True, null=True)
    gradient_end_color = models.CharField(max_length=7, blank=True, null=True)
    gradient_direction = models.CharField(max_length=20, blank=True, null=True)  # e.g. "to bottom right"

    # if gradient is a themed one
    gradient_theme = models.CharField(max_length=50, blank=True, null=True)  # e.g. "aurora", "mesh"


class OutpaintingSDXL(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    input_image = models.ForeignKey(GeneratedImage, on_delete=models.CASCADE, related_name="outpaintings")
    output_file = models.CharField(max_length=255, blank=True, null=True, default="", help_text="Ścieżka do wygenerowanego obrazu")

    left = models.IntegerField(default=0, help_text="Ile pikseli rozszerzyć w lewo")
    right = models.IntegerField(default=0, help_text="Ile pikseli rozszerzyć w prawo")
    up = models.IntegerField(default=0, help_text="Ile pikseli rozszerzyć w górę")
    down = models.IntegerField(default=0, help_text="Ile pikseli rozszerzyć w dół")

    output_format = models.CharField(max_length=10, default="png", help_text="Format wygenerowanego obrazu (np. webp, png)")

    def __str__(self):
        return f"OutpaintingSDXL {self.id} - {self.output_file or 'pending'}"
class Upscaling(models.Model):

    created_at = models.DateTimeField(auto_now_add=True)
    input_image = models.ForeignKey(GeneratedImage, on_delete=models.CASCADE, related_name="upscalings")
    output_file = models.CharField(max_length=255, blank=True, null=True, default="", help_text="Ścieżka do wygenerowanego obrazu")
    upscale_factor = models.IntegerField(default=2, help_text="Współczynnik skalowania obrazu (np. 2x, 4x)")

    def __str__(self):
        return f"Upscaling {self.id} - {self.output_file or 'pending'}"
class StylArtystyczny(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Kompozycja(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Kolorystyka(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Atmosfera(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Inspiracja(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Tlo(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Perspektywa(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Detale(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class Realizm(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)
class StylNarracyjny(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

class CalendarType(models.Model):
    nazwa = models.CharField(max_length=100)