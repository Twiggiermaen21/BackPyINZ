# calendar_export/services.py

import os
import uuid
import requests
import json
from django.conf import settings
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont, ImageOps

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
                            "field_number": field_obj.field_number,
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





def handle_top_image(calendar, export_dir):
    """Pobiera dane obrazu i zapisuje go lokalnie, jeśli rok ma być dodany."""
    if calendar.top_image_id:
        try:
            gen_img = GeneratedImage.objects.get(id=calendar.top_image_id)
        except GeneratedImage.DoesNotExist:
            print(f"GeneratedImage z id {calendar.top_image_id} nie istnieje.")
            
    return gen_img.url

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
        
        width, height = 3732, 10181 # Stałe wymiary

        if isinstance(bottom_obj, BottomColor):
            filename = os.path.join(export_dir, "bottom.png")
            img = Image.new("RGB", (width, height), bottom_obj.color)
            return_data = {"type": "color", "color": bottom_obj.color}

        elif isinstance(bottom_obj, BottomGradient):
            filename = os.path.join(export_dir, "bottom.png")
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
        
        # Zapisz obraz lokalnie
        img.save(filename)
        
        # POPRAWKA: Najpierw aktualizujemy, potem zwracamy słownik
        return_data["image_path"] = filename  # Lub: return_data.update({"image_path": filename})
        return return_data  # Zwracamy obiekt, a nie wynik metody update()
        
    return None
def process_top_image_with_year(top_image_path, data):
    """
    Pobiera obraz 'top_image', rysuje na nim tekst roku, 
    zapisuje i (teoretycznie) wgrywa do Cloudinary.
    """
    year_data = data.get("year")
    
    if not top_image_path or not year_data:
        print("⚠️ Brak ścieżki obrazu lub danych roku.")
        return None, data.get("top_image")

    output_path = top_image_path.replace(".jpg", "_with_text.jpg")
    
    try:
        # 1. Otwarcie obrazu i pobranie wymiarów
        image = Image.open(top_image_path)
        img_width, img_height = image.size
        print(f"ℹ️ Wymiary obrazu: {img_width}x{img_height}")

        draw = ImageDraw.Draw(image)

        # --- SEKJA SKALOWANIA (POPRAWKA GŁÓWNA) ---
        # Zakładamy, że "bazowe" wartości w year_data były projektowane dla
        # standardowej szerokości Full HD (1920px).
        # Obliczamy mnożnik na podstawie rzeczywistej szerokości obrazu (np. 7K).
        BASE_REFERENCE_WIDTH = 1920.0
        
        # Obliczamy scale_factor. Dla obrazu 7680px wyniesie on ok. 4.0.
        # Używamy max(1.0, ...), żeby nie zmniejszać czcionki na małych obrazkach.
        scale_factor = max(1.0, img_width / BASE_REFERENCE_WIDTH)

        # Pobieramy bazowy rozmiar i pozycję, zapewniając wartości domyślne
        base_font_size = int(year_data.get("size", 100))
        base_pos_x = int(year_data.get("positionX", img_width / 2)) # Domyślnie środek
        base_pos_y = int(year_data.get("positionY", img_height / 2)) # Domyślnie środek

        # Aplikujemy skalowanie
        final_font_size = int(base_font_size * scale_factor)
        final_pos_x = int(base_pos_x * scale_factor)
        final_pos_y = int(base_pos_y * scale_factor)

        print(f"ℹ️ Skalowanie: {scale_factor:.2f}x.")
        print(f"ℹ️ Rozmiar czcionki: {base_font_size} -> {final_font_size}px")
        print(f"ℹ️ Pozycja: ({base_pos_x},{base_pos_y}) -> ({final_pos_x},{final_pos_y})")
        # -------------------------------------------


        # Ładowanie czcionki
        try:
            font_path = year_data.get("font")
            # Jeśli ścieżka nie jest podana lub plik nie istnieje, użyj times.ttf
            if not font_path or not os.path.exists(font_path):
                 font_path = "times.ttf"

            # Używamy PRZESKALOWANEGO rozmiaru (final_font_size)
            font = ImageFont.truetype(font_path, final_font_size)
        except IOError:
            # Fallback dla bardzo starych systemów bez times.ttf, 
            # ale uwaga: load_default() jest ZAWSZE malutka i bitmapowa.
            font = ImageFont.load_default()
            print("⚠️ BŁĄD KRYTYCZNY: Nie znaleziono czcionki TTF. Użyto domyślnej (będzie niewidoczna na 7K!). Upewnij się, że masz plik .ttf")
        
        text_content = year_data.get("text", "YEAR")
        text_color = year_data.get("color", "#FFFFFF") # Domyślnie biały

       


        # Dodaj tekst używając PRZESKALOWANYCH pozycji
        print(f"Rysowanie tekstu '{text_content}' na pozycji ({final_pos_x}, {final_pos_y})")  
        try:
            draw.text(
                (final_pos_x, final_pos_y),
                text_content,
                font=font,
                fill=text_color
            )
        except Exception as e:  
            print(f"⚠️ Błąd podczas rysowania: {e}")

        # Zapisz wynik
        image.save(output_path)
        print(f"✅ Zapisano nowy obraz z tekstem: {output_path}")

        
        return output_path, output_path 

    except Exception as e:
        print(f"⚠️ Błąd w process_top_image_with_year: {e}")
        return None, top_image_path

import traceback

def process_calendar_bottom(data, upscaled_top_path=None):
    """
    UKŁAD PRO (300 DPI) - BEZ MALOWANIA TŁA
    Wymiary pionowe (Y) są obliczane na sztywno:
    - Główka: 2480 px
    - Pasek reklamowy: 591 px
    - Kalendarium: 1654 px
    """
    
    bottom_data = data.get("bottom", {})
    base_image_path = bottom_data.get("image_path")

    if not base_image_path or not os.path.exists(base_image_path):
        print(f"❌ Błąd: Nie znaleziono pliku tła: {base_image_path}")
        return None

    try:
        # 1. Otwarcie obrazu tła
        with Image.open(base_image_path) as src_img:
            base_img = src_img.convert("RGBA")

        img_width, img_height = base_img.size
        draw = ImageDraw.Draw(base_img)
        print(f"ℹ️ Przetwarzanie: {base_image_path} ({img_width}x{img_height})")

        # --- KONFIGURACJA WYMIARÓW (PRO 300 DPI) ---
        # Zamiast row_height = img_height / 7, definiujemy konkretne wysokości
        H_HEADER = 2480    # 21 cm
        H_AD = 591         # 5 cm
        H_CAL = 1654       # 14 cm
        
        # Obliczamy pozycje Y (początki sekcji)
        # Gdzie zaczynają się paski reklamowe:
        y_ad1 = H_HEADER
        y_ad2 = H_HEADER + H_AD + H_CAL
        y_ad3 = H_HEADER + (2 * H_AD) + (2 * H_CAL)
        y_footer = H_HEADER + (3 * H_AD) + (3 * H_CAL)

        # =========================================================
        # KROK A: GŁÓWKA (Index 0)
        # =========================================================
        if upscaled_top_path and os.path.exists(upscaled_top_path):
            try:
                with Image.open(upscaled_top_path) as header_src:
                    header_img = header_src.convert("RGBA")
                    # Dopasowanie główki do wymiaru 2480 px wysokości
                    header_fitted = ImageOps.fit(
                        header_img, 
                        (img_width, H_HEADER), 
                        method=Image.Resampling.LANCZOS
                    )
                    base_img.paste(header_fitted, (0, 0))
                    print(f"🖼️ Wklejono Top Image: {upscaled_top_path}")
            except Exception as e:
                print(f"⚠️ Błąd przy wklejaniu główki: {e}")
        
        # UWAGA: Usunięto KROK B (rysowanie białych prostokątów), tło zostaje oryginalne.

        # =========================================================
        # KROK C: OBLICZENIE ŚRODKÓW PÓL (Index 2, 4, 6 + Stopka)
        # =========================================================
        # Obliczamy środek każdego paska reklamowego, żeby tam wstawić tekst/logo
        field_centers_y = {
            1: int(y_ad1 + (H_AD / 2)),    # Środek paska 1
            2: int(y_ad2 + (H_AD / 2)),    # Środek paska 2
            3: int(y_ad3 + (H_AD / 2)),    # Środek paska 3
            4: int(y_footer + 300)         # Środek stopki (orientacyjnie, +300px od góry stopki)
        }

        raw_fields = data.get("fields", {})
        items_to_draw = {}

        # Przetwarzanie danych wejściowych
        for key, item in raw_fields.items():
            if not isinstance(item, dict): continue
            
            f_num = None
            str_key = str(key)
            # Obsługa kluczy "1", "2", "3", "4"
            if str_key.isdigit():
                f_num = int(str_key)
            if "field_number" in item:
                f_num = int(item["field_number"])

            if f_num and f_num in field_centers_y:
                if "text" in item:
                    items_to_draw[f_num] = item
                    items_to_draw[f_num]["type"] = "text"
                elif "image_url" in item:
                    items_to_draw[f_num] = item
                    items_to_draw[f_num]["type"] = "image"

        # =========================================================
        # KROK D: RYSOWANIE TREŚCI (BEZ TŁA)
        # =========================================================
        center_x_fixed = img_width / 2

        for f_num, center_y in field_centers_y.items():
            if f_num not in items_to_draw:
                continue

            item = items_to_draw[f_num]
            
            # --- TEKST ---
            if item["type"] == "text":
                text = item["text"]
                # Font size dostosowany do wysokości paska (ok. 50% wysokości paska)
                font_size = int(H_AD * 0.5)

                try:
                    font = ImageFont.truetype("arial.ttf", font_size)
                except:
                    font = ImageFont.load_default()

                # Nowa metoda obliczania rozmiaru tekstu (bezpieczniejsza)
                left, top, right, bottom = draw.textbbox((0, 0), text, font=font)
                text_w = right - left
                text_h = bottom - top

                # Rysowanie tekstu (centrowanie)
                draw.text(
                    (center_x_fixed - text_w/2, center_y - text_h/2 - top), 
                    text, font=font, fill="black"
                )

            # --- OBRAZ ---
            elif item["type"] == "image":
                img_url = item["image_url"]
                if os.path.exists(img_url):
                    try:
                        with Image.open(img_url) as overlay_src:
                            overlay = overlay_src.convert("RGBA")
                            
                            # Skalowanie obrazka, żeby nie wyszedł poza pasek (z marginesem)
                            max_w = int(img_width * 0.9)
                            max_h = int(H_AD * 0.9) # 90% wysokości paska
                            
                            # Zachowanie proporcji (thumbnail robi to automatycznie)
                            overlay.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
                            
                            paste_x = int(center_x_fixed - overlay.width/2)
                            paste_y = int(center_y - overlay.height/2)
                            
                            # Używamy alpha_composite dla lepszej jakości przezroczystości
                            base_img.alpha_composite(overlay, dest=(paste_x, paste_y))
                    except Exception as e:
                        print(f"⚠️ Błąd obrazka field {f_num}: {e}")

        # 4. ZAPIS
        base_img = base_img.convert("RGB") # Konwersja do RGB (bezpieczniejsza dla druku)
        base_img.save(base_image_path, dpi=(300, 300))
        print(f"✅ Nadpisano plik: {base_image_path}")
        return base_image_path

    except Exception as e:
        print(f"❌ Błąd: {e}")
        traceback.print_exc()
        return None 