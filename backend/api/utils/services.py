# calendar_export/services.py

import os
import requests
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont, ImageOps
import traceback
from ..models import Calendar, CalendarYearData, GeneratedImage, BottomImage, BottomColor, BottomGradient, ImageForField 
from .utils import hex_to_rgb, get_gradient_css, get_font_path, load_image_robust

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


# Upewnij się, że masz zaimportowaną funkcję pomocniczą
# from utils import get_font_path (zależnie gdzie ją trzymasz)

def process_top_image_with_year(top_image_path, data):
    """
    Pobiera obraz 'top_image', skaluje go do wymiarów Główki (3661x2480),
    rysuje na nim rok zgodnie z danymi z Frontendu i zapisuje.
    """
    
    # Dane roku z JSON-a
    year_data = data.get("year_data") # Uwaga: we frontendzie nazwałeś to 'year_data', sprawdź czy backend dostaje 'year' czy 'year_data'
    if not year_data:
        # Fallback, jeśli klucz nazywa się inaczej
        year_data = data.get("year")

    print(f"ℹ️ Przetwarzanie Główki (Header)...")

    if not top_image_path or not os.path.exists(top_image_path):
        print("⚠️ Brak pliku top_image.")
        return None, None

    # Ścieżka wyjściowa
    output_path = top_image_path.replace(".jpg", "_header_processed.jpg")
    
    try:
        # --- 1. KONFIGURACJA WYMIARÓW DOCELOWYCH ---
        TARGET_WIDTH = 3661
        TARGET_HEIGHT = 2480
        
        # --- 2. PRZYGOTOWANIE OBRAZU ---
        with Image.open(top_image_path) as img:
            img = img.convert("RGBA")
            
            # SKALOWANIE I PRZYCINANIE (CROP)
            # ImageOps.fit automatycznie skaluje i centruje obraz, 
            # aby wypełnił dokładnie 3661x2480 bez deformacji.
            img_fitted = ImageOps.fit(
                img, 
                (TARGET_WIDTH, TARGET_HEIGHT), 
                method=Image.Resampling.LANCZOS
            )
            
            # --- 3. RYSOWANIE ROKU ---
            if year_data:
                draw = ImageDraw.Draw(img_fitted)
                
                # Pobieranie danych (Wartości są już w pikselach dla 3661x2480)
                text_content = str(year_data.get("text", "2025"))
                # Frontend wysyła np. 400.0, rzutujemy na int
                font_size = int(float(year_data.get("size", 400))) 
                
                # Pobieranie pozycji (X, Y)
                pos_x = int(float(year_data.get("positionX", 50)))
                pos_y = int(float(year_data.get("positionY", 50)))
                
                text_color = year_data.get("color", "#FFFFFF")
                font_name = year_data.get("font", "Arial")
                font_weight = year_data.get("weight", "normal") # Opcjonalnie do obsługi boldów w przyszłości

                # Ładowanie czcionki
                try:
                    # Używamy naszej funkcji pomocniczej
                    font_path = get_font_path(font_name)
                    font = ImageFont.truetype(font_path, font_size)
                    
                    print(f"🖌️ Rysowanie roku: '{text_content}' | Font: {font_size}px | Pos: ({pos_x}, {pos_y})")
                    
                    draw.text(
                        (pos_x, pos_y),
                        text_content,
                        font=font,
                        fill=text_color
                    )
                except Exception as e:
                    print(f"⚠️ Błąd rysowania tekstu: {e}")
                    # Fallback text w razie błędu fontu
                    draw.text((pos_x, pos_y), text_content, fill=text_color)

            # --- 4. ZAPIS ---
            img_fitted = img_fitted.convert("RGB") # Konwersja do RGB przed zapisem JPG
            img_fitted.save(output_path, quality=95, dpi=(300, 300))
            
            print(f"✅ Utworzono gotową główkę: {output_path}")
            return output_path, output_path

    except Exception as e:
        print(f"❌ Krytyczny błąd w process_top_image_with_year: {e}")
        return None, top_image_path



# --- 3. GŁÓWNA FUNKCJA GENERUJĄCA ---
def process_calendar_bottom(data, upscaled_top_path=None):
    """
    Generuje Plecki kalendarza.
    Zastosowano mechanizm 'overflow: hidden' dla pasków reklamowych poprzez
    rysowanie ich na osobnych warstwach przed nałożeniem na tło.
    """
    
    bottom_data = data.get("bottom", {})
    base_image_path = bottom_data.get("image_path")

    if not base_image_path:
        print("❌ Błąd: Brak ścieżki do tła w JSON.")
        return None
    
    try:
        base_image_path = os.path.normpath(base_image_path)
        if not os.path.exists(base_image_path):
             print(f"❌ Błąd: Plik tła nie istnieje: {base_image_path}")
             return None

        # --- KONFIGURACJA WYMIARÓW ---
        CANVAS_WIDTH = 3661
        H_HEADER = 2480       
        H_MONTH_BOX = 1594    
        H_AD_STRIP = 768      
        MARGIN_Y = 25 
        H_SEGMENT = MARGIN_Y + H_MONTH_BOX + MARGIN_Y + H_AD_STRIP
        TOTAL_HEIGHT = H_HEADER + (3 * H_SEGMENT)
        
        # Kalendarium
        W_MONTH_BOX = 3425
        MARGIN_X_BOX = (CANVAS_WIDTH - W_MONTH_BOX) // 2
        MONTH_NAMES = ["GRUDZIEŃ", "STYCZEŃ", "LUTY"]

        print(f"ℹ️ Start generowania. Wymiary: {CANVAS_WIDTH}x{TOTAL_HEIGHT}")

        # Otwarcie tła
        with Image.open(base_image_path) as src_img:
            base_img = src_img.convert("RGBA")
            
        if base_img.size != (CANVAS_WIDTH, TOTAL_HEIGHT):
            base_img = base_img.resize((CANVAS_WIDTH, TOTAL_HEIGHT), Image.Resampling.LANCZOS)

        draw = ImageDraw.Draw(base_img)

        # =========================================================
        # KROK A: GŁÓWKA
        # =========================================================
        if upscaled_top_path:
            header_img = load_image_robust(upscaled_top_path)
            if header_img:
                header_fitted = ImageOps.fit(header_img, (CANVAS_WIDTH, H_HEADER), method=Image.Resampling.LANCZOS)
                base_img.paste(header_fitted, (0, 0))
                print(f"🖼️ Wklejono główkę")

        # --- ROK NA GŁÓWCE ---
        year_data = data.get("year")
        if year_data:
            try:
                y_text = str(year_data.get("text", "2026"))
                y_size = int(float(year_data.get("size", 400)))
                y_posX = int(float(year_data.get("positionX", 50)))
                y_posY = int(float(year_data.get("positionY", 50)))
                y_color = year_data.get("color", "#d40808")
                y_font_name = year_data.get("font", "Arial")
                
                font_path = get_font_path(y_font_name)
                font = ImageFont.truetype(font_path, y_size)
                draw.text((y_posX, y_posY), y_text, font=font, fill=y_color)
            except Exception as e:
                print(f"⚠️ Błąd rysowania roku: {e}")

        # =========================================================
        # KROK C: PRZETWARZANIE PÓL (KALENDARIUM + REKLAMA)
        # =========================================================
        raw_fields = data.get("fields", {})
        
        for i in range(1, 4):
            prev_h = (i - 1) * H_SEGMENT
            
            # Y Starty na głównym płótnie
            box_start_y = H_HEADER + prev_h + MARGIN_Y
            strip_start_y = box_start_y + H_MONTH_BOX + MARGIN_Y
            
            print(f"🔹 Segment {i}: Box Y={box_start_y}, Pasek Y={strip_start_y}")

            # 1. RYSOWANIE KALENDARIUM (Bez zmian)
            try:
                box_coords = [(MARGIN_X_BOX, box_start_y), (MARGIN_X_BOX + W_MONTH_BOX, box_start_y + H_MONTH_BOX)]
                draw.rectangle(box_coords, fill="white", outline="#e5e7eb", width=5)
                
                month_name = MONTH_NAMES[i-1]
                m_font_path = get_font_path("Arial") 
                m_font = ImageFont.truetype(m_font_path, 150)
                m_color = "#1d4ed8"
                
                left, top, right, bottom = draw.textbbox((0, 0), month_name, font=m_font)
                m_w, m_h = right - left, bottom - top
                m_x = (CANVAS_WIDTH - m_w) / 2
                m_y = box_start_y + 40 
                draw.text((m_x, m_y), month_name, font=m_font, fill=m_color)
                
                g_text = "[Siatka dni]"
                g_font = ImageFont.truetype(m_font_path, 100)
                gl, gt, gr, gb = draw.textbbox((0, 0), g_text, font=g_font)
                gx = (CANVAS_WIDTH - (gr - gl)) / 2
                gy = box_start_y + (H_MONTH_BOX - (gb - gt)) / 2 - gt
                draw.text((gx, gy), g_text, font=g_font, fill="#9ca3af")

            except Exception as e:
                print(f"⚠️ Błąd rysowania kalendarium {i}: {e}")

            # ---------------------------------------------------------
            # 2. PASEK REKLAMOWY Z EFEKTEM OVERFLOW: HIDDEN
            # ---------------------------------------------------------
            
            # Tworzymy NOWY, tymczasowy obrazek tylko dla paska reklamowego.
            # Dzięki temu wszystko co wyjdzie poza wymiar (CANVAS_WIDTH, H_AD_STRIP) zniknie.
            # RGBA (255, 255, 255, 0) oznacza w pełni przezroczyste tło.
            strip_img = Image.new("RGBA", (CANVAS_WIDTH, H_AD_STRIP), (255, 255, 255, 0))
            strip_draw = ImageDraw.Draw(strip_img)

            config = raw_fields.get(str(i)) or raw_fields.get(i)
            
            scale = 1.0
            pos_x = 0
            pos_y = 0

            if config:
                # A. TEKST REKLAMOWY
                if config.get("text"):
                    try:
                        text = config["text"]
                        f_size = int(float(config.get("size", 200)))
                        if f_size < 10: f_size = 200
                        f_color = config.get("color", "#000000")
                        f_font_name = config.get("font", "Arial")
                        
                        font_path = get_font_path(f_font_name)
                        font = ImageFont.truetype(font_path, f_size)
                        
                        left, top, right, bottom = strip_draw.textbbox((0, 0), text, font=font)
                        text_w, text_h = right - left, bottom - top
                        
                        # Pozycjonowanie tekstu względem PASKA (strip_img), a nie całego kalendarza
                        # 0,0 to lewy górny róg paska reklamowego
                        text_x = (CANVAS_WIDTH - text_w) / 2
                        text_y = (H_AD_STRIP - text_h) / 2 - top 
                        
                        strip_draw.text((text_x, text_y), text, font=font, fill=f_color)
                    except Exception as e:
                        print(f"⚠️ Błąd tekstu w polu {i}: {e}")
                
                # Parametry do obrazka
                try:
                    scale = float(config.get("size", 1.0))
                    pos_x = int(float(config.get("positionX", 0)))
                    pos_y = int(float(config.get("positionY", 0)))
                except:
                    pass 

            # B. OBRAZKI REKLAMOWE
            for key, val in raw_fields.items():
                if not isinstance(val, dict): continue
                
                if val.get("field_number") == i and val.get("image_url"):
                    img_url = val.get("image_url")
                    
                    overlay = load_image_robust(img_url)
                    
                    if overlay:
                        try:
                            new_w = int(overlay.width * scale)
                            new_h = int(overlay.height * scale)
                            if new_w <= 0: new_w = 1
                            if new_h <= 0: new_h = 1
                            
                            overlay = overlay.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            
                            # Wklejamy na strip_img.
                            # Używamy pos_x i pos_y BEZ dodawania strip_start_y,
                            # ponieważ rysujemy na lokalnym systemie współrzędnych paska.
                            paste_x = pos_x
                            paste_y = pos_y
                            
                            print(f"   🖼️ Wklejanie {key} na pasek ({paste_x}, {paste_y})")
                            
                            # Wklejenie z obsługą przezroczystości
                            strip_img.paste(overlay, (paste_x, paste_y), overlay)
                            
                        except Exception as e:
                            print(f"⚠️ Błąd wklejania {key}: {e}")

            # ---------------------------------------------------------
            # FINALIZACJA PASKA: Nałożenie gotowego paska na główne tło
            # ---------------------------------------------------------
            # Wklejamy przygotowany pasek (strip_img) w odpowiednie miejsce (strip_start_y) na głównym tle.
            # strip_img działa jak maska - to co się na nim nie zmieściło, fizycznie nie istnieje.
            base_img.paste(strip_img, (0, strip_start_y), strip_img)


        # 4. ZAPIS
        base_img = base_img.convert("RGB")
        base_img.save(base_image_path, dpi=(300, 300), quality=95)
        print(f"✅ Sukces: {base_image_path}")
        return base_image_path

    except Exception as e:
        print(f"❌ Krytyczny błąd: {e}")
        import traceback
        traceback.print_exc()
        return None