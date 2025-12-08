# calendar_export/services.py

import os
import uuid
import requests
import json
from django.conf import settings
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont

# Importy modeli (zakładam, że są zdefiniowane w innej części projektu, np. .models)
# Trzeba zaimportować rzeczywiste modele Calendar, CalendarYearData, GeneratedImage, 
# BottomImage, BottomColor, BottomGradient, ImageForField, etc.
# Poniżej placeholder:
from ..models import Calendar, CalendarYearData, GeneratedImage, BottomImage, BottomColor, BottomGradient, ImageForField 

# Zewnętrzna biblioteka Cloudinary
import cloudinary.uploader 

# Importowanie funkcji pomocniczych
from .utils import hex_to_rgb, get_gradient_css

def fetch_calendar_data(calendar_id):
    """
    Pobiera obiekt Calendar wraz z powiązanymi danymi i obrazami 
    do prefetched_images_for_fields.
    """
    qs = Calendar.objects.filter(id=calendar_id).prefetch_related(
        Prefetch(
            "imageforfield_set",
            queryset=ImageForField.objects.all(),
            to_attr="prefetched_images_for_fields"
        )
    )
    return qs.first()

def get_year_data(calendar):
    """Pobiera i zwraca dane dla sekcji 'year' kalendarza."""
    year_data = None
    if getattr(calendar, "year_data_id", None):
        year_data_obj = CalendarYearData.objects.filter(id=calendar.year_data_id).first()
        if year_data_obj:
            year_data = {
                "text": year_data_obj.text,
                "font": year_data_obj.font,
                "weight": year_data_obj.weight,
                "size": year_data_obj.size,
                "color": year_data_obj.color,
                "positionX": year_data_obj.positionX,
                "positionY": year_data_obj.positionY,
            }
    return year_data

def handle_field_data(field_obj, field_number, export_dir):
    """
    Zwraca dane pola obrazkowego lub tekstowego. Jeśli jest to obraz 
    z zewnętrznym URL, pobiera i zapisuje plik.
    """
    if not field_obj:
        return None

    # Pole tekstowe (lub z pozycją/rozmiarem bez URL)
    if hasattr(field_obj, "positionX") and hasattr(field_obj, "size") and not hasattr(field_obj, "url"):
        return {
            "field_number": field_number,
            "positionX": getattr(field_obj, "positionX", None),
            "positionY": getattr(field_obj, "positionY", None),
            "size": getattr(field_obj, "size", None),
        }
    
    # Pole obrazkowe z URL
    if hasattr(field_obj, "url"):
        image_url = getattr(field_obj, "path", None) or getattr(field_obj, "url", None)
        if image_url:
            # W oryginalnym kodzie, pobieranie jest tylko jeśli jest export_dir, co sugeruje, 
            # że ścieżki względne są używane tylko dla eksportu.
            # Jeśli eksport_dir jest dostarczony, próbujemy pobrać i zapisać:
            if export_dir:
                try:
                    response = requests.get(image_url, stream=True)
                    if response.status_code == 200:
                        filename = f"field{field_number}_{os.path.basename(image_url)}"
                        dest = os.path.join(export_dir, filename)
                        with open(dest, "wb") as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        return {
                            "field_number": field_number,
                            "image_url": dest
                        }
                    else:
                         print(f"Error downloading field{field_number}: HTTP {response.status_code}")
                         return {"field_number": field_number, "image_url": image_url} # Zwróć URL, jeśli pobieranie się nie powiodło
                except Exception as e:
                    print(f"Error downloading field{field_number}: {e}")
                    return {"field_number": field_number, "image_url": image_url} # Zwróć URL w razie błędu

    # Jeśli pole ma tekst (bez względu na to, czy to TextForField czy inny obiekt)
    if hasattr(field_obj, "text") and field_obj.text:
        return {
            "text": field_obj.text,
            "font": getattr(field_obj, "font", None),
            "weight": getattr(field_obj, "weight", None)
        }

    return None

def handle_bottom_data(bottom_obj, export_dir):
    """
    Obsługuje dane dla sekcji 'bottom' (obraz, kolor, gradient). 
    Tworzy obrazy dla kolorów/gradientów i wgrywa do Cloudinary.
    """
    if not bottom_obj:
        return None

    # ================= OBRAZ =================
    if isinstance(bottom_obj, BottomImage) and bottom_obj.image:
        image_url = bottom_obj.image.url if hasattr(bottom_obj.image, "url") else None
        if image_url:
            # W tym miejscu oryginalny kod pobierał obraz i zapisywał, 
            # ale dla BottomImages, które są już w systemie, 
            # możemy po prostu zwrócić URL, a renderowanie niech pobiera.
            # Jeśli musisz koniecznie pobrać, użyj logiki z handle_field_data
            return {"type": "image", "url": image_url}

    # ================= KOLOR/GRADIENT (GENEROWANIE OBRAZÓW) =================
    elif isinstance(bottom_obj, (BottomColor, BottomGradient)):
        
        width, height = 1200, 8000 # Stałe wymiary

        if isinstance(bottom_obj, BottomColor):
            filename = os.path.join(export_dir, "bottom_color.png")
            img = Image.new("RGB", (width, height), bottom_obj.color)
            return_data = {"type": "color", "color": bottom_obj.color}

        elif isinstance(bottom_obj, BottomGradient):
            filename = os.path.join(export_dir, "bottom_gradient.png")
            start_rgb = hex_to_rgb(bottom_obj.start_color)
            end_rgb = hex_to_rgb(bottom_obj.end_color)

            img = Image.new("RGB", (width, height))
            pixels = img.load()

            if bottom_obj.direction == "to right":
                for x in range(width):
                    ratio = x / width
                    r = int(start_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
                    g = int(start_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
                    b = int(start_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)
                    for y in range(height):
                        pixels[x, y] = (r, g, b)
            else:  # to bottom
                for y in range(height):
                    ratio = y / height
                    r = int(start_rgb[0] * (1 - ratio) + end_rgb[0] * ratio)
                    g = int(start_rgb[1] * (1 - ratio) + end_rgb[1] * ratio)
                    b = int(start_rgb[2] * (1 - ratio) + end_rgb[2] * ratio)
                    for x in range(width):
                        pixels[x, y] = (r, g, b)
            
            return_data = {
                "type": "gradient",
                "start_color": bottom_obj.start_color,
                "end_color": bottom_obj.end_color,
                "direction": bottom_obj.direction,
                "strength": bottom_obj.strength,
                "theme": bottom_obj.theme,
                "css": get_gradient_css(bottom_obj.start_color, bottom_obj.end_color, bottom_obj.direction),
            }
        
        # Zapis i wgranie do Cloudinary
        try:
            img.save(filename)
            return_data["path"] = filename # Lokalna ścieżka tymczasowa

            upload_result = cloudinary.uploader.upload(
                filename, 
                folder="calendar_exports" 
            )
            cloudinary_url = upload_result.get("secure_url")
            print(f"☁️ Obraz wgrany do Cloudinary: {cloudinary_url}")
            
            # Usuwanie lokalnego pliku
            os.remove(filename)
            print(f"🗑️ Usunięto lokalny plik: {filename}")
            
            return_data["cloudinary_url"] = cloudinary_url
            return return_data

        except Exception as e:
            print(f"❌ Błąd podczas generowania/wgrywania bottom (kolor/gradient): {e}")
            return return_data # Zwróć dane z lokalną ścieżką lub bez URL Cloudinary

    return None

def process_top_image_with_year(calendar, data, export_dir):
    """
    Pobiera obraz 'top_image', rysuje na nim tekst roku, 
    zapisuje i wgrywa do Cloudinary.
    """
    top_image_path = data.get("top_image")
    year_data = data.get("year")
    
    if not top_image_path or not year_data:
        return None, data.get("top_image") # Zwróć to co było

    output_path = top_image_path.replace(".jpg", "_with_text.jpg")
    cloudinary_url = None
    
    try:
        # 1. Rysowanie tekstu
        image = Image.open(top_image_path)
        draw = ImageDraw.Draw(image)
        
        # Ładowanie czcionki
        try:
            # Użyj nazwy czcionki z danych, a nie hardkodowanego "times.ttf"
            font_path = year_data.get("font") or "times.ttf" # Użyj `year_data`
            font = ImageFont.truetype(font_path, int(year_data["size"]))
        except IOError:
            font = ImageFont.load_default()
            print("⚠️ Nie znaleziono niestandardowej czcionki, użyto domyślnej.")
        
        # Dodaj tekst
        draw.text(
            (int(year_data["positionX"]), int(year_data["positionY"])),
            year_data["text"],
            font=font,
            fill=year_data["color"]
        )

        # Zapisz wynik
        image.save(output_path)
        print(f"✅ Zapisano nowy obraz: {output_path}")

        # 2. Wgrywanie do Cloudinary
        upload_result = cloudinary.uploader.upload(
            output_path, 
            folder="calendar_exports"
        )
        cloudinary_url = upload_result.get("secure_url")
        print(f"☁️ Obraz wgrany do Cloudinary: {cloudinary_url}")

        # 3. Czyszczenie lokalnych plików
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"🗑️ Usunięto lokalny plik: {output_path}")
        
        # Usuń oryginalny pobrany plik top_image, jeśli był pobrany lokalnie
        original_path_remove = top_image_path
        if os.path.exists(original_path_remove):
             os.remove(original_path_remove)
             print(f"🗑️ Usunięto oryginalny lokalny plik: {original_path_remove}")

        return cloudinary_url, output_path # Zwróć Cloudinary URL i lokalną ścieżkę do posprzątania (choć została usunięta)

    except Exception as e:
        print(f"⚠️ Błąd w process_top_image_with_year: {e}")
        return None, top_image_path # W razie błędu zwróć None dla URL Cloudinary i oryginalną ścieżkę

def handle_top_image(calendar, export_dir):
    """Pobiera dane obrazu i zapisuje go lokalnie, jeśli rok ma być dodany."""
    top_image_path = None
    top_image_url = None
    
    if calendar.top_image_id:
        try:
            gen_img = GeneratedImage.objects.get(id=calendar.top_image_id)
            top_image_url = gen_img.url
            if gen_img.url:
                # Pobierz plik lokalnie TYLKO jeśli rok ma być na niego naniesiony
                if getattr(calendar, "year_data_id", None): 
                    filename = f"top_image_{os.path.basename(gen_img.url)}"
                    dest = os.path.join(export_dir, filename)
                    
                    response = requests.get(gen_img.url, stream=True)
                    if response.status_code == 200:
                        with open(dest, "wb") as f:
                            for chunk in response.iter_content(1024):
                                f.write(chunk)
                        top_image_path = dest
                    else:
                        print(f"Error downloading top_image: HTTP {response.status_code}")
                        top_image_path = None # Nie udało się pobrać, nie można rysować
                
                else:
                    # Jeśli nie ma roku, wystarczy URL
                    top_image_path = gen_img.url 

        except GeneratedImage.DoesNotExist:
            print(f"GeneratedImage z id {calendar.top_image_id} nie istnieje.")
            
    return top_image_path