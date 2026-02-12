from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from cloudinary.models import CloudinaryField

class ProfileImage(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    profile_image = CloudinaryField("profile_image", folder="ProfileImages", blank=True, null=True)

    def __str__(self):
        return self.user.username
class GeneratedImage(models.Model):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    prompt = models.CharField(max_length=500)
    height = models.IntegerField(default=512)
    width = models.IntegerField(default=512)
    name = models.CharField(max_length=100, default="new_image")
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
    name = models.CharField(max_length=100, default="new calendar")
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    top_image = models.ForeignKey(
        'GeneratedImage', on_delete=models.SET_NULL, null=True, blank=True, related_name="calendar_top_image"
    )

    # Rok
    year_data = models.OneToOneField(
        "CalendarYearData", on_delete=models.SET_NULL, null=True,  blank=True, related_name="calendar_year_data"
    )

    # Pola ogólne (GenericForeignKey)
    field1_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    field1_object_id = models.PositiveIntegerField(null=True, blank=True)
    field1 = GenericForeignKey("field1_content_type", "field1_object_id")

    field2_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    field2_object_id = models.PositiveIntegerField(null=True, blank=True)
    field2 = GenericForeignKey("field2_content_type", "field2_object_id")

    field3_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    field3_object_id = models.PositiveIntegerField(null=True, blank=True)
    field3 = GenericForeignKey("field3_content_type", "field3_object_id")

    # Dolna część kalendarza (GenericForeignKey zamiast kilku pól)
    bottom_content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    bottom_object_id = models.PositiveIntegerField(null=True, blank=True)
    bottom = GenericForeignKey("bottom_content_type", "bottom_object_id")
class CalendarProduction(models.Model):
    STATUS_CHOICES = (
        ("draft", "Projekt"),
        ("rejected", "Odrzucony"),
        ("to_produce", "Do produkcji"),
        ("in_production", "W produkcji"),
        ("done", "Gotowy"),
        ("archived", "Zarchiwizowany"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    author = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE
        ,
        related_name="production"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="draft"
    )

    # produkcyjne dane
    quantity = models.PositiveIntegerField(default=1)  # ilość egzemplarzy
    deadline = models.DateField(null=True, blank=True)  # termin produkcji
    production_note = models.TextField(blank=True)

    # kiedy faktycznie zakończono
    finished_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.calendar.name} - {self.get_status_display()}"

class CalendarMonthFieldText(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.CharField(max_length=255)
    
    # Istniejące pola
    font = models.CharField(max_length=100, blank=True, null=True)   # fontFamily
    weight = models.CharField(max_length=50, blank=True, null=True)  # fontWeight
    
    # Nowe pola
    color = models.CharField(max_length=50, default="#000000", help_text="Np. #000000 lub rgba(...)") # fontColor
    size = models.CharField(max_length=20, blank=True, null=True)    # fontSize
class CalendarMonthFieldImage(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    path = models.CharField(max_length=500)  
    positionX = models.CharField(max_length=50, blank=True, null=True)
    positionY = models.CharField(max_length=50, blank=True, null=True)
    size = models.PositiveIntegerField(blank=True, null=True)  

class CalendarYearData(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    text = models.CharField(max_length=255)
    font = models.CharField(max_length=100, blank=True, null=True)
    weight = models.CharField(max_length=50, blank=True, null=True)
    size = models.CharField(max_length=20, blank=True, null=True)
    color = models.CharField(max_length=7, blank=True, null=True)
    positionX = models.CharField(max_length=50, blank=True, null=True)
    positionY = models.CharField(max_length=50, blank=True, null=True)

class ImageForField(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendar = models.ForeignKey(Calendar, on_delete=models.CASCADE)
    field_number = models.IntegerField()
    url = models.URLField()
    created_at = models.DateTimeField(auto_now_add=True)

class BottomImage(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    image = models.ForeignKey('GeneratedImage', on_delete=models.SET_NULL, null=True, blank=True)
class BottomColor(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    color = models.CharField(max_length=7)
class BottomGradient(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    start_color = models.CharField(max_length=7)
    end_color = models.CharField(max_length=7)
    direction = models.CharField(max_length=20, blank=True, null=True)
    theme = models.CharField(max_length=50, blank=True, null=True)

class StylArtystyczny(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Kompozycja(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Kolorystyka(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Atmosfera(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Inspiracja(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Tlo(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Perspektywa(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Detale(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class Realizm(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']

class StylNarracyjny(models.Model):
    nazwa = models.CharField(max_length=100)
    tlumaczenie = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['id']
