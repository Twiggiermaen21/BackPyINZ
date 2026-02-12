# calendar_export/services.py
import os
import requests
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ..models import Calendar, CalendarYearData, GeneratedImage,  ImageForField 
from .utils import hex_to_rgb, get_font_path
import math
import time
import shutil
from io import BytesIO


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
            "weight": getattr(field_obj, "weight", None),
            "size": getattr(field_obj, "size", None),
            "color": getattr(field_obj, "color", None),
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

def hex_to_rgb(hex_color):
    """Zamienia hex string na tuple RGB."""
    if not isinstance(hex_color, str): return (255, 255, 255)
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)

def create_gradient_vertical(size, start_rgb, end_rgb):
    """Szybki gradient pionowy (resize 1px)."""
    width, height = size
    # Generujemy pasek o wysokości 256px dla płynności
    gradient_h = 256
    base = Image.new('RGB', (1, gradient_h))
    pixels = base.load()
    
    for y in range(gradient_h):
        t = y / (gradient_h - 1)
        # Opcjonalnie: t = math.pow(t, 0.8) # można zmienić krzywą, żeby kolor startowy był "większy"
        pixels[0, y] = interpolate_color(start_rgb, end_rgb, t)
        
    # Skalujemy do docelowego rozmiaru
    return base.resize((width, height), Image.Resampling.BICUBIC)

def create_radial_gradient_css(size, start_rgb, end_rgb, center=(0.5, 0.5), offset_y=0):
    """
    Gradient radialny (Circle).
    offset_y: przesunięcie środka w pionie w pikselach (np. 100).
    """
    width, height = size
    
    # Optymalizacja: Generujemy na mniejszym obrazku i skalujemy
    small_w = 400
    # Zachowujemy proporcje, żeby koło nie zrobiło się jajowate
    small_h = int(400 * (height / width))
    
    base = Image.new('RGB', (small_w, small_h))
    pixels = base.load()
    
    # 1. Obliczamy przesunięcie relatywne (jaką częścią wysokości jest offset)
    # Jeśli offset_y = 100 px, a wysokość to 7000 px, to przesuwamy o ok. 0.014 wysokości
    relative_offset = offset_y / height
    
    # 2. Ustalamy środek uwzględniając offset
    target_cy_normalized = center[1] + relative_offset
    
    cx = int(small_w * center[0])
    cy = int(small_h * target_cy_normalized)
    
    # Promień krycia (do najdalszego rogu od NOWEGO środka)
    max_dist = math.sqrt(max(cx, small_w - cx)**2 + max(cy, small_h - cy)**2)
    
    # Zabezpieczenie przed dzieleniem przez zero (gdyby max_dist wyszło 0)
    if max_dist == 0: max_dist = 1
    
    for y in range(small_h):
        for x in range(small_w):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            t = min(dist / max_dist, 1.0)
            pixels[x, y] = interpolate_color(start_rgb, end_rgb, t)
            
    return base.resize((width, height), Image.Resampling.LANCZOS)

def interpolate_color(start_rgb, end_rgb, factor):
    return tuple(int(start + (end - start) * factor) for start, end in zip(start_rgb, end_rgb))

def create_waves_css(size, start_rgb, end_rgb):
    """
    Odwzorowanie CSS: repeating-linear-gradient(135deg, A, B 20%, A 40%)
    """
    w, h = size
    
    # 1. Obliczamy przekątną, która w CSS jest podstawą do wyliczania %
    diagonal = math.sqrt(w**2 + h**2)
    
    # 2. Tworzymy płótno robocze
    # Musi być na tyle duże, aby po obrocie o 45 stopni zakryć cały docelowy prostokąt.
    # Kwadrat o boku = przekątna + zapas jest bezpieczny.
    canvas_side = int(diagonal * 1.5) 
    
    # 3. Definiujemy wysokość jednego cyklu (odpowiada 40% w CSS)
    cycle_height = int(diagonal * 0.40)
    
    # Zabezpieczenie przed zbyt małym cyklem (np. przy małych obrazkach)
    if cycle_height < 10: cycle_height = 10

    # 4. Generujemy jeden pasek gradientu (cykl)
    # W CSS: 0% (A) -> 20% (B) -> 40% (A). 
    # To oznacza, że w połowie cyklu (20% z 40%) mamy kolor B.
    strip_h = 256 # Rozdzielczość generowania gradientu (dla gładkości)
    strip = Image.new('RGB', (1, strip_h))
    px = strip.load()
    
    for y in range(strip_h):
        t = y / (strip_h - 1)
        if t <= 0.5:
            # Pierwsza połowa (0 -> 20%): A -> B
            local_t = t * 2
            px[0, y] = interpolate_color(start_rgb, end_rgb, local_t)
        else:
            # Druga połowa (20% -> 40%): B -> A
            local_t = (t - 0.5) * 2
            px[0, y] = interpolate_color(end_rgb, start_rgb, local_t)
            
    # Skalujemy pasek do docelowej wysokości cyklu
    cycle_img = strip.resize((canvas_side, cycle_height), Image.Resampling.BICUBIC)
    
    # 5. Powielamy cykl w pionie, aby wypełnić całe płótno robocze
    repeats = (canvas_side // cycle_height) + 2
    full_pattern = Image.new('RGB', (canvas_side, cycle_height * repeats))
    
    for i in range(repeats):
        full_pattern.paste(cycle_img, (0, i * cycle_height))
        
    # 6. Obrót
    # CSS 135deg (flow top-left -> bottom-right) daje pasy "bottom-left -> top-right" (/).
    # Poziome pasy obrócone o 45 stopni (CCW) dadzą ten efekt.
    # Używamy expand=False, bo płótno jest już nadmiarowe, a chcemy zachować centrum.
    rotated = full_pattern.rotate(45, resample=Image.Resampling.BICUBIC, expand=False)
    
    # 7. Wycinamy środek o wymiarach docelowych (Center Crop)
    center_x, center_y = rotated.width // 2, rotated.height // 2
    left = center_x - w // 2
    top = center_y - h // 2
    
    return rotated.crop((left, top, left + w, top + h))


def create_liquid_css(size, start_rgb, end_rgb):
    """
    Symulacja CSS: linear-gradient(135deg, A 0%, B 100%)
    """
    w, h = size
    diagonal = int(math.sqrt(w**2 + h**2))
    
    # Tworzymy pionowy gradient (A -> B) o długości przekątnej
    grad = create_gradient_vertical((diagonal, diagonal), start_rgb, end_rgb)
    
    # Obracamy o -45 (dla 135deg)
    rotated = grad.rotate(-45, resample=Image.Resampling.BICUBIC)
    
    center_x, center_y = rotated.width // 2, rotated.height // 2
    left = center_x - w // 2
    top = center_y - h // 2
    return rotated.crop((left, top, left + w, top + h))

def generate_bottom_bg_image(width, height, bg_color, end_color, theme, variant):
    rgb_start = hex_to_rgb(bg_color)
    rgb_end = hex_to_rgb(end_color)

    # === 1. MOTYWY SPECJALNE (Aurora, Liquid, Waves) ===
    
    if theme == "aurora":
        # CSS: radial-gradient(circle at 30% 30%, start, end, start)
        # Uproszczenie: Radial Start->End. Aby "Start" był na zewnątrz też, trzebaby complex gradient.
        # W CSS: start (0%) -> end (do pewnego momentu) -> start (100%).
        # Zróbmy klasyczny radial z przesuniętym środkiem.
        return create_radial_gradient_css((width, height), rgb_start, rgb_end, center=(0.3, 0.3))
        
    elif theme == "liquid":
        # CSS: linear-gradient(135deg, start 0%, end 100%)
        return create_liquid_css((width, height), rgb_start, rgb_end)
        
    elif theme == "waves":
        # CSS: repeating-linear-gradient(135deg, start, end 20%, start 40%)
        return create_waves_css((width, height), rgb_start, rgb_end)
        
    # === 2. VARIANTY KLASYCZNE (Classic) ===
    # Obsługa: vertical, horizontal, radial, diagonal
    
    else:
        if variant == "horizontal":
            # Generujemy pionowy mały i obracamy o 90
            grad = create_gradient_vertical((height, width), rgb_start, rgb_end)
            return grad.rotate(90, expand=True)
            
        elif variant == "radial":
            return create_radial_gradient_css((width, height), rgb_start, rgb_end, center=(0.5, 0.5))
            
        elif variant == "diagonal":
            # To samo co Liquid (135deg) lub standardowy linear bottom-right
            return create_liquid_css((width, height), rgb_start, rgb_end)
            
        else: 
            # Domyślnie: Vertical (to bottom)
            # Tutaj user prosił: "kolor początkowy musi być większy".
            # create_gradient_vertical robi liniowe przejście.
            # Jeśli start ma dominować, w 'create_gradient_vertical' można zmienić funkcję t.
            return create_gradient_vertical((width, height), rgb_start, rgb_end)



def handle_bottom_data(bottom_obj, export_dir):
    """
    Generuje obraz tła dla sekcji bottom (tylko dolna część kalendarza).
    """
    if not bottom_obj:
        return None

    # Stałe wymiary "Plecków" (dolnej sekcji)
    width, height = 3732, 7559  # Zgodnie z Twoją prośbą (dół)
    
    # Jeśli export_dir nie istnieje, utwórz go
    os.makedirs(export_dir, exist_ok=True)
    filename = os.path.join(export_dir, "bottom.png")
    
    generated_img = None
    return_data = {}

    # --- A. OBRAZ (BottomImage) ---
    if hasattr(bottom_obj, 'image') and bottom_obj.image:
        image_url = bottom_obj.image.url if hasattr(bottom_obj.image, "url") else None
        if image_url:
            return {"type": "image", "url": image_url, "image_path": None} 

    # --- B. KOLOR JEDNOLITY (BottomColor) ---
    elif hasattr(bottom_obj, 'color') and not hasattr(bottom_obj, 'start_color'):
        rgb = hex_to_rgb(bottom_obj.color)
        generated_img = Image.new("RGB", (width, height), rgb)
        return_data = {"type": "color", "color": bottom_obj.color}

    # --- C. GRADIENT (BottomGradient) ---
    elif hasattr(bottom_obj, 'start_color'):
        theme = getattr(bottom_obj, 'theme', 'classic')
        direction = getattr(bottom_obj, 'direction', 'to bottom')
        
        # Mapowanie kierunków z bazy na warianty
        variant = "vertical"
        if direction == "to right": variant = "horizontal"
        elif direction == "to bottom right": variant = "diagonal"
        elif direction == "radial": variant = "radial"
        
        print(f"🎨 Generowanie tła: Theme={theme}, Variant={variant}, Size={width}x{height}")
        
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

    # Zapis
    if generated_img:
        generated_img.save(filename, quality=95)
        return_data["image_path"] = filename
        return return_data

    return None


def process_top_image_with_year(top_image_path, data):
    """
    Rysuje rok z obsługą 'fake bold' i poprawnym ładowaniem
    plików .ttf z folderu 'fonts/'.
    """
    year_data = data.get("year_data") or data.get("year")

    if not top_image_path or not os.path.exists(top_image_path):
        print("⚠️ Brak pliku obrazu.")
        return None, None

    output_path = top_image_path.replace(".jpg", "_header_processed.jpg")
    
    try:
        TARGET_WIDTH = 3661
        TARGET_HEIGHT = 2480
        
        with Image.open(top_image_path) as img:
            img = img.convert("RGBA")
            img_fitted = ImageOps.fit(img, (TARGET_WIDTH, TARGET_HEIGHT), method=Image.Resampling.LANCZOS)
            
            if year_data:
                draw = ImageDraw.Draw(img_fitted)
                # --- DANE ---
                text_content = str(year_data.get("text", "2026"))
                font_size = int(float(year_data.get("size", 400))) 
                pos_x = int(float(year_data.get("positionX", 50)))
                pos_y = int(float(year_data.get("positionY", 50)))
                text_color = year_data.get("color", "#FFFFFF")
                
                # Sprawdzamy czy ma być BOLD
                weight_raw = str(year_data.get("weight", "normal")).lower()
                is_bold = weight_raw in ["bold", "700", "800", "900", "bolder"]
                
                # --- 1. ŁADOWANIE CZCIONKI Z FOLDERU FONTS ---
                # Pobieramy nazwę, np. "Arial" -> "arial"
                font_name = str(year_data.get("font", "arial"))

                font_path = get_font_path(font_name)
                # Sprawdzamy, czy plik istnieje
                if not os.path.exists(font_path):
                    print(f"⚠️ Nie znaleziono pliku: {font_path}. Przełączam na fonts/arial.ttf")
                    # Fallback na pewniaka (upewnij się, że masz fonts/arial.ttf)
                  

                try:
                    font = ImageFont.truetype(font_path, font_size)
                except OSError:
                    print(f"❌ Krytyczny błąd ładowania fontu {font_path}. Używam systemowego default.")
                    font = ImageFont.load_default() 
                
                # --- 2. OBLICZANIE STROKE (Fake Bold) ---
                if is_bold:
                    # 3% wysokości fontu jako obrys
                    stroke_w = int(font_size * 0.03)
                    if stroke_w < 1: stroke_w = 1
                else:
                    stroke_w = 0

                print(f"🖌️ Rysowanie: '{text_content}' | Font: {font_path} | Bold: {is_bold} (Stroke: {stroke_w}px)")

                # --- 3. RYSOWANIE ---
                draw.text(
                    (pos_x, pos_y),
                    text_content,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_w,
                    stroke_fill=text_color
                )

            # Zapis
            img_fitted = img_fitted.convert("RGB")
            img_fitted.save(output_path, quality=95, dpi=(300, 300))
            return output_path, output_path

    except Exception as e:
        print(f"❌ Błąd: {e}")
        return None, top_image_path





def process_calendar_bottom(data, upscaled_top_path=None):
    
    bottom_data = data.get("bottom", {})
    template_image_path = bottom_data.get("image_path")

    # --- 1. KONFIGURACJA ŚCIEŻKI ZAPISU ---
    timestamp = int(time.time())
    output_filename = f"final_calendar_{timestamp}.jpg"
    base_export_dir = os.path.join(os.getcwd(), "media", "calendar_exports")
    
    if not os.path.exists(base_export_dir):
        try: os.makedirs(base_export_dir)
        except: base_export_dir = os.getcwd()

    output_path = os.path.join(base_export_dir, output_filename)

    # --- KONFIGURACJA WYMIARÓW ---
    CANVAS_WIDTH = 3661
    H_HEADER = 2480       
    H_MONTH_BOX = 1594    
    H_AD_STRIP = 768      
    MARGIN_Y = 25         
    
    BOX_WIDTH = 3425
    AD_PADDING_X = 112
    AD_CONTENT_WIDTH = CANVAS_WIDTH - (2 * AD_PADDING_X)
    BOX_X = (CANVAS_WIDTH - BOX_WIDTH) // 2 

    H_SEGMENT = MARGIN_Y + H_MONTH_BOX + MARGIN_Y + H_AD_STRIP
    TOTAL_HEIGHT = H_HEADER + (3 * H_SEGMENT)
    
    # 📌 NOWE: Obliczamy wysokość samego dołu (plecków), żeby tam wkleić tło
    BACKING_HEIGHT = TOTAL_HEIGHT - H_HEADER

    MONTH_NAMES = ["GRUDZIEŃ", "STYCZEŃ", "LUTY"]

    print(f"ℹ️ Start generowania. Output: {output_path}")

    try:
        # Tworzymy białe tło dla CAŁOŚCI (żeby pod główką było biało, jeśli tło nie sięga)
        base_img = Image.new("RGB", (CANVAS_WIDTH, TOTAL_HEIGHT), "white")
        
        # =========================================================
        # 1. TŁO (POPRAWIONE: TYLKO NA DÓŁ / PLECKI)
        # =========================================================
        if template_image_path and os.path.exists(template_image_path):
            with Image.open(template_image_path) as src_bg:
                bg_layer = src_bg.convert("RGBA")
                
                # 📌 ZMIANA: Skalujemy tło tylko do wymiaru 'BACKING_HEIGHT' (same plecki), a nie całości.
                # Dzięki temu zdjęcie nie jest rozciągnięte na główkę.
                bg_layer = ImageOps.fit(bg_layer, (CANVAS_WIDTH, BACKING_HEIGHT), method=Image.Resampling.LANCZOS)
                
                # 📌 ZMIANA: Wklejamy przesunięte o H_HEADER w dół (pod główkę)
                # (0, H_HEADER) oznacza: X=0, Y=2480px
                base_img.paste(bg_layer, (0, H_HEADER))
                print(f"🖼️ Tło wklejone od Y={H_HEADER} (Wysokość tła: {BACKING_HEIGHT}px)")
        else:
            print("⚠️ Brak pliku tła, zostawiam białe.")
        
        draw = ImageDraw.Draw(base_img)

        # =========================================================
        # 2. GŁÓWKA (Bez zmian)
        # =========================================================
        if upscaled_top_path and os.path.exists(upscaled_top_path):
            try:
                header_img = Image.open(upscaled_top_path).convert("RGBA")
                header_fitted = ImageOps.fit(header_img, (CANVAS_WIDTH, H_HEADER), method=Image.Resampling.LANCZOS)
                base_img.paste(header_fitted, (0, 0), header_fitted)
            except Exception as e:
                print(f"⚠️ Błąd główki: {e}")

        # =========================================================
        # 3. SEGMENTY (Bez zmian)
        # =========================================================
        raw_fields = data.get("fields", {})

        for i in range(1, 4):
            prev_h = (i - 1) * H_SEGMENT
            box_start_y = H_HEADER + prev_h + MARGIN_Y
            strip_start_y = box_start_y + H_MONTH_BOX + MARGIN_Y
            
            # A. KALENDARIUM
            box_coords = [(BOX_X, box_start_y), (BOX_X + BOX_WIDTH, box_start_y + H_MONTH_BOX)]
            draw.rectangle(box_coords, fill="white", outline="#e5e7eb", width=5)
            
            month_name = MONTH_NAMES[i-1]
            try: m_font = ImageFont.truetype("arial.ttf", 150)
            except: m_font = ImageFont.load_default()
            
            center_x_box = BOX_X + (BOX_WIDTH / 2)
            left, top, right, bottom = draw.textbbox((0, 0), month_name, font=m_font)
            draw.text((center_x_box - ((right-left)/2), box_start_y + 40), month_name, font=m_font, fill="#1d4ed8")
            
            g_text = "[Siatka dni]"
            try: g_font = ImageFont.truetype("arial.ttf", 100)
            except: g_font = ImageFont.load_default()
            gl, gt, gr, gb = draw.textbbox((0, 0), g_text, font=g_font)
            draw.text((center_x_box - ((gr-gl)/2), box_start_y + (H_MONTH_BOX - (gb-gt))/2 - gt), g_text, font=g_font, fill="#9ca3af")

            # B. PASEK REKLAMOWY
            strip_img = Image.new("RGBA", (AD_CONTENT_WIDTH, H_AD_STRIP), (255, 255, 255, 0))
            strip_draw = ImageDraw.Draw(strip_img)
            
            config = raw_fields.get(str(i)) or raw_fields.get(i)
            scale = 1.0; pos_x = 0; pos_y = 0

            if config:
                try: scale = float(config.get("size", 1.0))
                except: scale = 1.0
                try: pos_x = int(float(config.get("positionX", 0)))
                except: pos_x = 0
                try: pos_y = int(float(config.get("positionY", 0)))
                except: pos_y = 0

                if config.get("text"):
                    text = config["text"]
                    f_size = int(config.get("size", 200))
                    try: font_ad = ImageFont.truetype("arial.ttf", f_size)
                    except: font_ad = ImageFont.load_default()
                    
                    l, t, r, b = strip_draw.textbbox((0, 0), text, font=font_ad)
                    text_w = r - l; text_h = b - t
                    txt_x = (AD_CONTENT_WIDTH - text_w) / 2
                    txt_y = (H_AD_STRIP - text_h) / 2
                    strip_draw.text((txt_x, txt_y), text, font=font_ad, fill=config.get("color", "#333"))

            # C. OBRAZKI DODATKOWE
            for key, val in raw_fields.items():
                if not isinstance(val, dict): continue
                if str(val.get("field_number")) == str(i) and val.get("image_url"):
                    img_source = val.get("image_url")
                    overlay = None
                    try:
                        if img_source.lower().startswith(("http://", "https://")):
                            response = requests.get(img_source, timeout=10)
                            if response.status_code == 200:
                                overlay = Image.open(BytesIO(response.content)).convert("RGBA")
                        else:
                            local_path = os.path.normpath(img_source)
                            if os.path.exists(local_path):
                                overlay = Image.open(local_path).convert("RGBA")
                        
                        if overlay:
                            new_w = int(overlay.width * scale); new_h = int(overlay.height * scale)
                            if new_w < 1: new_w = 1; 
                            if new_h < 1: new_h = 1
                            overlay = overlay.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            strip_img.paste(overlay, (pos_x, pos_y), overlay)
                    except Exception as e:
                        print(f"⚠️ Błąd img: {e}")

            base_img.paste(strip_img, (AD_PADDING_X, strip_start_y), strip_img)

        # 4. ZAPIS
        # Konwersja na CMYK
        base_img = base_img.convert("CMYK")
        
        # Opcjonalnie: Zmiana nazwy pliku, aby wiedzieć, że to wersja do druku
        output_filename = f"final_calendar_{timestamp}_CMYK.jpg"
        output_path = os.path.join(base_export_dir, output_filename)

        # Zapis - JPG obsługuje CMYK, ale nie wszystkie przeglądarki obrazów wyświetlą to poprawnie na ekranie.
        # Drukarnia jednak sobie z tym poradzi.
        base_img.save(output_path, format="JPEG", dpi=(300, 300), quality=95, subsampling=0)
        
        # ALTERNATYWA: Często drukarnie wolą format TIFF lub PDF dla CMYK
        # output_path_tiff = output_path.replace(".jpg", ".tiff")
        # base_img.save(output_path_tiff, format="TIFF", dpi=(300, 300), compression="tiff_lzw")
        
        print(f"✅ Sukces: Plik CMYK zapisany w {output_path}")

        # 5. CLEANUP
        if template_image_path:
            temp_dir_to_delete = os.path.dirname(os.path.normpath(template_image_path))
            if os.path.abspath(temp_dir_to_delete) != os.path.abspath(base_export_dir):
                if os.path.exists(temp_dir_to_delete):
                    try: shutil.rmtree(temp_dir_to_delete)
                    except: pass

        return output_path

    except Exception as e:
        print(f"❌ Krytyczny błąd: {e}")
        import traceback
        traceback.print_exc()
        return None