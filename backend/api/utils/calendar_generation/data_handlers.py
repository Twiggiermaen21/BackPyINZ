from PIL import Image
import os
import requests
from ...models import GeneratedImage
from .pdf_utils import hex_to_rgb
from .gradients import generate_bottom_bg_image

def handle_field_data(field_obj, field_number, export_dir):
    """
    Ekstrakcja i przygotowanie danych z Pola Reklamowego (tekst lub obrazek). 
    Pobiera bezprosrednio zasoby webowe do lokalnego folderu eksportu i zwraca ustandaryzowany slownik z wlasciwosciami elementu.
    """
    if not field_obj:
        return None

    image_source = getattr(field_obj, "path", None) or getattr(field_obj, "url", None)

    if image_source:
        result = {
            "field_number": field_number,
            "type": "image",
            "image_url": image_source,
            "positionX": getattr(field_obj, "positionX", 0),
            "positionY": getattr(field_obj, "positionY", 0),
            "size": getattr(field_obj, "size", 1.0),
        }

        if export_dir and image_source.startswith(("http://", "https://")):
            try:
                original_name = os.path.basename(image_source.split("?")[0])
                if not original_name: original_name = "image.png"
                
                filename = f"field{field_number}_{original_name}"
                dest_path = os.path.join(export_dir, filename)

                response = requests.get(image_source, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    
                    result["image_url"] = dest_path
                else:
                    print(f"Blad pobierania pola {field_number}: HTTP {response.status_code}")
            
            except Exception as e:
                print(f"Wyjatek przy pobieraniu pola {field_number}: {e}")

        return result

    if hasattr(field_obj, "text") and field_obj.text:
        return {
            "field_number": field_number,
            "type": "text",
            "text": field_obj.text,
            "font": getattr(field_obj, "font", "Arial"),
            "weight": getattr(field_obj, "weight", "normal"),
            "size": getattr(field_obj, "size", 200),
            "color": getattr(field_obj, "color", "#000000"),
        }

    return None

def handle_top_image(calendar, export_dir):
    """
    Wydobywa z bazy URL do wygenerowanego (przez asystenta Flux) obrazka przypisanego do glowki.
    """
    if calendar.top_image_id:
        try:
            gen_img = GeneratedImage.objects.get(id=calendar.top_image_id)
            return gen_img.url
        except GeneratedImage.DoesNotExist:
            print(f"GeneratedImage z id {calendar.top_image_id} nie istnieje.")
            
    return None

def handle_bottom_data(bottom_obj, export_dir):
    """
    Przetwarza dolny panel kalendarza. Analizuje encje polimorficzna Bottom (kolor, obrazek, lub gradient) 
    i renderuje te dane na plik zastępczy PNG uzywany dalej jako tekstura podkladowa plecow w PDF.
    """
    if not bottom_obj:
        return None

    width, height = 3732, 7559
    
    os.makedirs(export_dir, exist_ok=True)
    filename = os.path.join(export_dir, "bottom.png")
    
    generated_img = None
    return_data = {}

    if hasattr(bottom_obj, 'image') and bottom_obj.image:
        image_url = bottom_obj.image.url if hasattr(bottom_obj.image, "url") else None
        if image_url:
            return {"type": "image", "url": image_url, "image_path": None} 

    elif hasattr(bottom_obj, 'color') and not hasattr(bottom_obj, 'start_color'):
        rgb = hex_to_rgb(bottom_obj.color)
        generated_img = Image.new("RGB", (width, height), rgb)
        return_data = {"type": "color", "color": bottom_obj.color}

    elif hasattr(bottom_obj, 'start_color'):
        theme = getattr(bottom_obj, 'theme', 'classic')
        direction = getattr(bottom_obj, 'direction', 'to bottom')
        
        variant = "vertical"
        if direction == "to right": variant = "horizontal"
        elif direction == "to bottom right": variant = "diagonal"
        elif direction == "radial": variant = "radial"
        
        generated_img = generate_bottom_bg_image(
            width, height, 
            bottom_obj.start_color, 
            bottom_obj.end_color, 
            theme, 
            variant
        )
        
        return_data = {
            "type": "gradient",
            "start_color": bottom_obj.start_color,
            "end_color": bottom_obj.end_color,
            "theme": theme,
            "image_path": filename
        }

    if generated_img:
        generated_img.save(filename, quality=95)
        return_data["image_path"] = filename
        return return_data

    return None


from ...models import Calendar, CalendarYearData

def fetch_calendar_data(calendar_id):
    """
    Konstruuje bazowe zapytanie modelu Calendar wraz z powiazaniami GenericForeignKey (dane reklamowe, tla).
    Wykorzystuje mechanizmy ORM takie jak select_related i prefetch_related dla minimalizacji ilosci wymagan do bazy.
    """
    qs = Calendar.objects.filter(id=calendar_id)
    
    qs = qs.select_related(
        "top_image",
        "year_data",
        "field1_content_type",
        "field2_content_type",
        "field3_content_type",
        "bottom_content_type",
    )

    qs = qs.prefetch_related(
        "field1",
        "field2",
        "field3",
        "bottom"
    )

    return qs.first()

def get_year_data(calendar):
    """
    Pobiera i odkodowuje z bazy parametry tekstowe naglowka roku (font, rozmiar, pozycja).
    Zwraca je w postaci uproszczonego slownika lub jako None.
    """
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
