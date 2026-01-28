# calendar_export/services.py
import os
import requests
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ..models import Calendar, CalendarYearData, GeneratedImage,  ImageForField 
from .utils import hex_to_rgb, get_font_path, load_image_robust
import math



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
 
# =========================================================
# 🛠️ FUNKCJE POMOCNICZE (Odwzorowanie CSS w PIL)
# =========================================================

def hex_to_rgb(hex_color):
    """Zamienia hex string na tuple RGB."""
    if not isinstance(hex_color, str): return (255, 255, 255)
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    return (255, 255, 255)

def interpolate_color(start_rgb, end_rgb, t):
    """Miesza dwa kolory w proporcji t (0.0 - 1.0)."""
    return tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * t) for i in range(3))

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

def create_radial_gradient_css(size, start_rgb, end_rgb, center=(0.5, 0.5)):
    """Gradient radialny (Circle)."""
    width, height = size
    # Optymalizacja: Generujemy na mniejszym obrazku i skalujemy
    small_w, small_h = 400, int(400 * (height/width))
    base = Image.new('RGB', (small_w, small_h))
    pixels = base.load()
    
    cx, cy = int(small_w * center[0]), int(small_h * center[1])
    # Promień krycia (do najdalszego rogu)
    max_dist = math.sqrt(max(cx, small_w-cx)**2 + max(cy, small_h-cy)**2)
    
    for y in range(small_h):
        for x in range(small_w):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            t = min(dist / max_dist, 1.0)
            pixels[x, y] = interpolate_color(start_rgb, end_rgb, t)
            
    return base.resize((width, height), Image.Resampling.LANCZOS)

def create_waves_css(size, start_rgb, end_rgb):
    """
    Symulacja CSS: repeating-linear-gradient(135deg, A, B 20%, A 40%)
    """
    w, h = size
    # Aby obrócić obraz bez ucinania rogów, tworzymy większy kwadrat (przekątna)
    diagonal = int(math.sqrt(w**2 + h**2))
    canvas_size = diagonal + 100
    
    # Tworzymy jeden cykl gradientu (A -> B -> A)
    # W CSS cykl to 40%. Przyjmijmy, że 40% odnosi się do przekątnej.
    cycle_height = int(canvas_size * 0.40) 
    if cycle_height < 100: cycle_height = 100
    
    # Pasek gradientu: A (0%) -> B (50% paska czyli 20% całości) -> A (100% paska czyli 40% całości)
    strip_h = 256
    strip = Image.new('RGB', (1, strip_h))
    px = strip.load()
    for y in range(strip_h):
        t = y / (strip_h - 1)
        if t < 0.5:
            # Pierwsza połowa: A -> B
            local_t = t * 2 
            px[0, y] = interpolate_color(start_rgb, end_rgb, local_t)
        else:
            # Druga połowa: B -> A
            local_t = (t - 0.5) * 2
            px[0, y] = interpolate_color(end_rgb, start_rgb, local_t)
            
    cycle_img = strip.resize((canvas_size, cycle_height), Image.Resampling.BICUBIC)
    
    # Powielamy cykl w pionie, aby wypełnić całe duże płótno
    repeats = (canvas_size // cycle_height) + 2
    full_pattern = Image.new('RGB', (canvas_size, cycle_height * repeats))
    for i in range(repeats):
        full_pattern.paste(cycle_img, (45, i * cycle_height))
        
    # Obracamy o -45 stopni (co daje 135deg w układzie CSS Top-Left)
    # W PIL rotate jest counter-clockwise, więc 45 to przeciwnie do wskazówek zegara.
    # CSS 135deg to po skosie w dół w prawo.
    # Żeby uzyskać pasy idące z lewy-góra na prawy-dół, musimy mieć pasy poziome i obrócić.
    # Tutaj mamy pasy poziome.
    rotated = full_pattern.rotate(0, resample=Image.Resampling.BICUBIC, expand=False)
    
    # Wycinamy środek o wymiarach docelowych
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


# =========================================================
# 🏭 GENERATOR TŁA
# =========================================================

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


# =========================================================
# 🚀 GŁÓWNA FUNKCJA (handle_bottom_data)
# =========================================================

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

import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps

# --- 3. GŁÓWNA FUNKCJA GENERUJĄCA ---
def process_calendar_bottom(data, upscaled_top_path=None):
    
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
        
        # --- PADDING ---
        PADDING_X = 112
        W_CONTENT = CANVAS_WIDTH - (2 * PADDING_X) 
        
        H_SEGMENT = MARGIN_Y + H_MONTH_BOX + MARGIN_Y + H_AD_STRIP
        TOTAL_HEIGHT = H_HEADER + (3 * H_SEGMENT)
        
        MONTH_NAMES = ["GRUDZIEŃ", "STYCZEŃ", "LUTY"]

        print(f"ℹ️ Start generowania. Padding: {PADDING_X}px, Szerokość robocza: {W_CONTENT}px")

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

        # ROK NA GŁÓWCE
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
            except Exception:
                pass

        # =========================================================
        # KROK C: PRZETWARZANIE PÓL
        # =========================================================
        raw_fields = data.get("fields", {})
        
        for i in range(1, 4):
            prev_h = (i - 1) * H_SEGMENT
            box_start_y = H_HEADER + prev_h + MARGIN_Y
            strip_start_y = box_start_y + H_MONTH_BOX + MARGIN_Y
            
            # 1. KALENDARIUM
            try:
                box_coords = [(PADDING_X, box_start_y), (PADDING_X + W_CONTENT, box_start_y + H_MONTH_BOX)]
                draw.rectangle(box_coords, fill="white", outline="#e5e7eb", width=5)
                
                month_name = MONTH_NAMES[i-1]
                m_font_path = get_font_path("Arial") 
                m_font = ImageFont.truetype(m_font_path, 150)
                m_color = "#1d4ed8"
                
                left, top, right, bottom = draw.textbbox((0, 0), month_name, font=m_font)
                m_w = right - left
                center_x = PADDING_X + (W_CONTENT / 2)
                m_x = center_x - (m_w / 2)
                m_y = box_start_y + 40 
                
                draw.text((m_x, m_y), month_name, font=m_font, fill=m_color)
                
                g_text = "[Siatka dni]"
                g_font = ImageFont.truetype(m_font_path, 100)
                gl, gt, gr, gb = draw.textbbox((0, 0), g_text, font=g_font)
                gw = gr - gl
                gx = center_x - (gw / 2)
                gy = box_start_y + (H_MONTH_BOX - (gb - gt)) / 2 - gt
                draw.text((gx, gy), g_text, font=g_font, fill="#9ca3af")

            except Exception as e:
                print(f"⚠️ Błąd rysowania kalendarium {i}: {e}")

            # ---------------------------------------------------------
            # 2. PASEK REKLAMOWY
            # ---------------------------------------------------------
            strip_img = Image.new("RGBA", (W_CONTENT, H_AD_STRIP), (255, 255, 255, 0))
            strip_draw = ImageDraw.Draw(strip_img)
           
            config = raw_fields.get(str(i)) or raw_fields.get(i)
            
            scale = 1.0
            pos_x = 0
            pos_y = 0

            if config:
                raw_scale = config.get("size")
                if raw_scale is not None:
                    try: scale = float(raw_scale)
                    except: scale = 1.0

                raw_pos_x = config.get("positionX")
                if raw_pos_x is not None:
                    try: pos_x = int(float(raw_pos_x))
                    except: pos_x = 0

                raw_pos_y = config.get("positionY")
                if raw_pos_y is not None:
                    try: pos_y = int(float(raw_pos_y))
                    except: pos_y = 0
                
                print(f"   ⚙️ [Pasek {i}] Obrazki: Skala={scale}, X={pos_x}, Y={pos_y}")

                # =========================================================
                # A. PRZETWARZANIE TEKSTU (SYMULACJA BOLD - PROPORCJA 1/60)
                # =========================================================
                if config.get("text"):
                    text_content = config["text"]
                    
                    raw_size = config.get("size", 200)
                    try:
                        f_size = int(float(raw_size))
                        if f_size < 10: f_size = 200
                    except: f_size = 200

                    f_color = config.get("color", "#000000")
                    f_font_name = config.get("font", "Arial")
                    font_path = get_font_path(f_font_name)
                    
                    # --- KONFIGURACJA POGRUBIENIA (DELIKATNY BOLD) ---
                    raw_weight = config.get("weight", "normal")
                    if raw_weight == "bold":
                        # Dzielimy przez 60, żeby bold był subtelny, a nie "napuchnięty"
                        bold_stroke = int(f_size / 60)
                        if bold_stroke < 1: bold_stroke = 1
                    else:
                        bold_stroke = 0
                    
                    try:
                        font = ImageFont.truetype(font_path, f_size)
                        
                        INTERNAL_MARGIN = 10 
                        MAX_WIDTH_LIMIT = W_CONTENT - (INTERNAL_MARGIN * 2)
                        
                        print(f"   📝 [Pasek {i}] Tekst: '{text_content[:20]}...' (Waga: {raw_weight}, Stroke: {bold_stroke})")

                        # --- ALGORYTM ZAWIJANIA ---
                        words = text_content.split()
                        lines = []
                        current_line = ""

                        for word in words:
                            # WAŻNE: Tu też uwzględniamy bold_stroke
                            l, t, r, b = strip_draw.textbbox((0, 0), word, font=font, stroke_width=bold_stroke)
                            word_width = r - l

                            # 1. Słowo gigant (Hard Wrap)
                            if word_width > MAX_WIDTH_LIMIT:
                                if current_line:
                                    lines.append(current_line)
                                    current_line = ""
                                
                                part = ""
                                for char in word:
                                    test_part = part + char
                                    # POPRAWKA: Dodano stroke_width=bold_stroke w tej linii poniżej!
                                    l, t, r, b = strip_draw.textbbox((0, 0), test_part, font=font, stroke_width=bold_stroke)
                                    if (r - l) <= MAX_WIDTH_LIMIT:
                                        part = test_part
                                    else:
                                        lines.append(part)
                                        part = char
                                current_line = part
                            
                            # 2. Słowo normalne
                            else:
                                test_line = (current_line + " " + word).strip()
                                l, t, r, b = strip_draw.textbbox((0, 0), test_line, font=font, stroke_width=bold_stroke)
                                line_width = r - l
                                
                                if line_width <= MAX_WIDTH_LIMIT:
                                    current_line = test_line
                                else:
                                    lines.append(current_line)
                                    current_line = word

                        if current_line:
                            lines.append(current_line)

                        # --- RYSOWANIE ---
                        if lines:
                            _, t_box, _, b_box = strip_draw.textbbox((0, 0), "Ay", font=font, stroke_width=bold_stroke)
                            line_height = b_box - t_box
                            line_spacing = line_height * 1.15
                            total_block_height = (len(lines) * line_spacing) - (line_spacing - line_height) 
                            
                            start_y = (H_AD_STRIP - total_block_height) / 2
                            start_y -= t_box
                            current_y = start_y
                            max_text_width = 0

                            for line in lines:
                                l, t, r, b = strip_draw.textbbox((0, 0), line, font=font, stroke_width=bold_stroke)
                                current_line_width = r - l
                                
                                center_x = (W_CONTENT - current_line_width) / 2
                                
                                strip_draw.text(
                                    (center_x, current_y), 
                                    line, 
                                    font=font, 
                                    fill=f_color,
                                    stroke_width=bold_stroke,
                                    stroke_fill=f_color
                                )
                                
                                if current_line_width > max_text_width:
                                    max_text_width = current_line_width
                                
                                current_y += line_spacing

                            print(f"      ✅ Rysowanie: {len(lines)} linii. Max szer: {max_text_width}px.")

                    except OSError:
                        print(f"❌ Błąd: Nie znaleziono pliku czcionki: {font_path}.")
                    except Exception as e:
                        print(f"❌ Nieoczekiwany błąd tekstu: {e}")

            # =========================================================
            # C. OBRAZKI DODATKOWE
            # =========================================================
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
                            strip_img.paste(overlay, (pos_x, pos_y), overlay)
                            print(f"      🖼️ Wklejono obrazek: {img_url}")
                            
                        except Exception as e:
                            print(f"⚠️ Błąd wklejania obrazka: {e}")

            # FINALIZACJA
            base_img.paste(strip_img, (PADDING_X, strip_start_y), strip_img)


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