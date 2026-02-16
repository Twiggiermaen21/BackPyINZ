# calendar_export/services.py
import os
import requests
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ..models import Calendar, CalendarYearData, GeneratedImage
from .utils import _save_as_psd, create_export_folder, hex_to_rgb, get_font_path, _load_font
import math
import time
import shutil
from io import BytesIO
from psd_tools import PSDImage
from psd_tools.api.layers import PixelLayer

try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    HAS_PSD = True
except ImportError:
    HAS_PSD = False

# ==========================================================
# STAŁE WYMIAROWE Z SZABLONU DRUKARNI (@ 300 DPI)
# ==========================================================

# --- GŁÓWKA ---
HEADER_WIDTH = 3957       # 13.19 cali = 335 mm
HEADER_HEIGHT = 2658      #  8.86 cali = 225 mm

# --- PLECY ---
BACKING_WIDTH = 3789      # 12.63 cali = 321 mm

H_GLUE = 120              #  0.40 cali =  10 mm  (klejenie główki na górze)
H_MONTH_BOX = 1650        #  5.50 cali = 140 mm  (kalendarium)
H_BIG = 264               #  0.88 cali =  22 mm  (linia bigowania)
H_AD_STRIP = 354          #  1.18 cali =  30 mm  (pasek reklamowy)
H_BLEED_BOTTOM = 120      #  0.40 cali =  10 mm  (spad dolny)

BOX_WIDTH = 3543           # 11.81 cali = 300 mm  (szer. kalendarium/reklamy)
BOX_X = (BACKING_WIDTH - BOX_WIDTH) // 2   # 123 px (centrowanie)

AD_PADDING_X = BOX_X
AD_CONTENT_WIDTH = BOX_WIDTH

# Łączna wysokość pleców
BACKING_HEIGHT = (
    H_GLUE
    + H_MONTH_BOX + H_BIG + H_AD_STRIP   # segment 1
    + H_BIG
    + H_MONTH_BOX + H_BIG + H_AD_STRIP   # segment 2
    + H_BIG
    + H_MONTH_BOX + H_BIG + H_AD_STRIP   # segment 3
    + H_BLEED_BOTTOM
)  # = 7572 px = 641 mm


MONTH_NAMES = ["GRUDZIEŃ", "STYCZEŃ", "LUTY"]

def fetch_calendar_data(calendar_id):
    """
    Pobiera obiekt Calendar wraz z powiązanymi polami (GenericForeignKey).
    Django automatycznie pobierze odpowiednie modele (Text lub Image) dla field1/2/3
    oraz odpowiedni model dla stopki (Image, Color, Gradient).
    """
    qs = Calendar.objects.filter(id=calendar_id)
    
    # 1. Optymalizacja SQL (select_related)
    # Pobieramy ContentType, aby Django wiedziało, w jakich tabelach szukać danych
    qs = qs.select_related(
        "top_image",
        "year_data",
        "field1_content_type",
        "field2_content_type",
        "field3_content_type",
        "bottom_content_type",
    )

    # 2. Pobieranie danych (prefetch_related)
    # Django automatycznie obsłuży polimorfizm (czy to Text, czy Image)
    qs = qs.prefetch_related(
        "field1",
        "field2",
        "field3",
        "bottom"
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
    Przetwarza obiekt pola (Tekst lub Obraz).
    Dla obrazów: pobiera plik z URL/Path jeśli podano export_dir.
    Dla tekstu: zwraca parametry formatowania.
    """
    if not field_obj:
        return None

    # --- PRZYPADEK 1: OBRAZEK ---
    # Sprawdzamy czy obiekt ma atrybut 'path' (Twoja nowa nazwa) lub 'url' (stara nazwa)
    image_source = getattr(field_obj, "path", None) or getattr(field_obj, "url", None)

    if image_source:
        # Przygotowujemy podstawowy słownik zwrotny z geometrią
        result = {
            "field_number": field_number,  # Używamy argumentu funkcji, nie atrybutu obiektu
            "type": "image",
            "image_url": image_source,     # Domyślnie URL/Path z bazy
            "positionX": getattr(field_obj, "positionX", 0),
            "positionY": getattr(field_obj, "positionY", 0),
            "size": getattr(field_obj, "size", 1.0),
        }

        # Logika pobierania pliku (tylko jeśli mamy export_dir i jest to link http)
        if export_dir and image_source.startswith(("http://", "https://")):
            try:
                # Wyciągamy bezpieczną nazwę pliku
                # np. field1_obrazek.png
                original_name = os.path.basename(image_source.split("?")[0]) # split usuwa query params
                if not original_name: original_name = "image.png"
                
                filename = f"field{field_number}_{original_name}"
                dest_path = os.path.join(export_dir, filename)

                # Pobieranie
                response = requests.get(image_source, stream=True, timeout=10)
                if response.status_code == 200:
                    with open(dest_path, "wb") as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    
                    # Nadpisujemy URL ścieżką lokalną
                    result["image_url"] = dest_path
                else:
                    print(f"⚠️ Błąd pobierania pola {field_number}: HTTP {response.status_code}")
            
            except Exception as e:
                print(f"⚠️ Wyjątek przy pobieraniu pola {field_number}: {e}")
                # W razie błędu result['image_url'] pozostaje oryginalnym URL-em

        return result

    # --- PRZYPADEK 2: TEKST ---
    # Jeśli ma atrybut 'text' i nie jest pusty
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
    """Pobiera dane obrazu i zapisuje go lokalnie, jeśli rok ma być dodany."""
    if calendar.top_image_id:
        try:
            gen_img = GeneratedImage.objects.get(id=calendar.top_image_id)
        except GeneratedImage.DoesNotExist:
            print(f"GeneratedImage z id {calendar.top_image_id} nie istnieje.")
            
    return gen_img.url


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

def generate_header(top_image_path, data, export_dir, production_id=None):
    """
    Generuje plik główki kalendarza jako PSD.
    Skaluje obraz do 3957×2658 px i opcjonalnie nakłada rok.

    Returns:
        str | None: ścieżka do zapisanego pliku
    """
    year_data = data.get("year_data") or data.get("year")

    if not top_image_path or not os.path.exists(top_image_path):
        print("⚠️ Brak pliku obrazu główki.")
        return None

    output_path = os.path.join(export_dir, f"header_{production_id}.psd")

    try:
        with Image.open(top_image_path) as img:
            img = img.convert("RGBA")
            img_fitted = ImageOps.fit(
                img,
                (HEADER_WIDTH, HEADER_HEIGHT),
                method=Image.Resampling.LANCZOS,
            )

            if year_data:
                draw = ImageDraw.Draw(img_fitted)

                text_content = str(year_data.get("text", "2026"))
                font_size = int(float(year_data.get("size", 400)))
                pos_x = int(float(year_data.get("positionX", 50)))
                pos_y = int(float(year_data.get("positionY", 50)))
                text_color = year_data.get("color", "#FFFFFF")

                weight_raw = str(year_data.get("weight", "normal")).lower()
                is_bold = weight_raw in ["bold", "700", "800", "900", "bolder"]

                font_name = str(year_data.get("font", "arial"))
                font_path = get_font_path(font_name)
                font = _load_font(font_path, font_size)

                stroke_w = int(font_size * 0.03) if is_bold else 0
                if is_bold and stroke_w < 1:
                    stroke_w = 1

                print(
                    f"🖌️ Rok: '{text_content}' | Font: {font_path} "
                    f"| Bold: {is_bold} (Stroke: {stroke_w}px)"
                )

                draw.text(
                    (pos_x, pos_y),
                    text_content,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_w,
                    stroke_fill=text_color,
                )

            # Konwersja do RGB i zapis jako PSD
            img_rgb = img_fitted.convert("RGB")
            saved_path = _save_as_psd(img_rgb, output_path)

            print(f"✅ Główka: {saved_path} ({HEADER_WIDTH}×{HEADER_HEIGHT} px = 335×225 mm)")
            return saved_path

    except Exception as e:
        print(f"❌ Błąd generowania główki: {e}")
        return None
def generate_backing(data, export_dir, production_id=None):
    """
    Generuje plik pleców kalendarza jako PSD.

    Returns:
        str | None: ścieżka do zapisanego pliku
    """
    bottom_data = data.get("bottom", {})
    template_image_path = bottom_data.get("image_path") if bottom_data else None

    output_path = os.path.join(export_dir, f"backing_{production_id}.psd")

    print(
        f"ℹ️ Plecy: {BACKING_WIDTH}×{BACKING_HEIGHT} px "
        f"({BACKING_WIDTH/300*25.4:.0f}×{BACKING_HEIGHT/300*25.4:.0f} mm)"
    )

    try:
        base_img = Image.new("RGB", (BACKING_WIDTH, BACKING_HEIGHT), "white")

        # --- TŁO ---
        if template_image_path and os.path.exists(template_image_path):
            with Image.open(template_image_path) as src_bg:
                bg_layer = src_bg.convert("RGBA")
                bg_layer = ImageOps.fit(
                    bg_layer,
                    (BACKING_WIDTH, BACKING_HEIGHT),
                    method=Image.Resampling.LANCZOS,
                )
                base_img.paste(bg_layer, (0, 0))
                print(f"🖼️ Tło pleców wklejone")
        else:
            print("⚠️ Brak tła pleców — białe tło.")

        draw = ImageDraw.Draw(base_img)

        # --- 3 SEGMENTY ---
        raw_fields = data.get("fields", {})
        y = H_GLUE

        for i in range(1, 4):
            cal_y = y
            big1_y = cal_y + H_MONTH_BOX
            ad_y = big1_y + H_BIG
            next_y = ad_y + H_AD_STRIP + H_BIG

            # KALENDARIUM
            draw.rectangle(
                [(BOX_X, cal_y), (BOX_X + BOX_WIDTH, cal_y + H_MONTH_BOX)],
                fill="white", outline="#e5e7eb", width=5,
            )

            month_name = MONTH_NAMES[i - 1]
            m_font = _load_font("arial.ttf", 150)
            center_x = BOX_X + BOX_WIDTH / 2
            l, t, r, b = draw.textbbox((0, 0), month_name, font=m_font)
            draw.text(
                (center_x - (r - l) / 2, cal_y + 40),
                month_name, font=m_font, fill="#1d4ed8",
            )

            g_font = _load_font("arial.ttf", 100)
            g_text = "[Siatka dni]"
            gl, gt, gr, gb = draw.textbbox((0, 0), g_text, font=g_font)
            draw.text(
                (center_x - (gr - gl) / 2, cal_y + (H_MONTH_BOX - (gb - gt)) / 2 - gt),
                g_text, font=g_font, fill="#9ca3af",
            )

            # PASEK REKLAMOWY
            strip_img = Image.new("RGBA", (AD_CONTENT_WIDTH, H_AD_STRIP), (255, 255, 255, 0))
            strip_draw = ImageDraw.Draw(strip_img)

            config = raw_fields.get(str(i)) or raw_fields.get(i)
            scale = 1.0
            pos_x = 0
            pos_y = 0

            if config:
                try: scale = float(config.get("size", 1.0))
                except (ValueError, TypeError): scale = 1.0
                try: pos_x = int(float(config.get("positionX", 0)))
                except (ValueError, TypeError): pos_x = 0
                try: pos_y = int(float(config.get("positionY", 0)))
                except (ValueError, TypeError): pos_y = 0

                if config.get("text"):
                    text = config["text"]
                    try: f_size = int(float(config.get("size", 200)))
                    except (ValueError, TypeError): f_size = 200

                    font_ad = _load_font("arial.ttf", f_size)
                    text_color = config.get("color", "#333")

                    weight_val = config.get("weight") or config.get("font", {}).get("fontWeight")
                    is_bold = False
                    if weight_val:
                        w_str = str(weight_val).lower()
                        if "bold" in w_str or w_str in ["700", "800", "900"]:
                            is_bold = True
                        elif isinstance(weight_val, int) and weight_val >= 700:
                            is_bold = True

                    stroke_width = int(f_size / 40) if is_bold else 0
                    if is_bold and stroke_width < 1:
                        stroke_width = 1

                    tl, tt, tr, tb = strip_draw.textbbox(
                        (0, 0), text, font=font_ad, stroke_width=stroke_width
                    )
                    txt_x = (AD_CONTENT_WIDTH - (tr - tl)) / 2
                    txt_y = (H_AD_STRIP - (tb - tt)) / 2
                    strip_draw.text(
                        (txt_x, txt_y), text, font=font_ad,
                        fill=text_color, stroke_width=stroke_width, stroke_fill=text_color,
                    )

            # Obrazki w pasku
            for key, val in raw_fields.items():
                if not isinstance(val, dict):
                    continue
                if str(val.get("field_number")) == str(i) and val.get("image_url"):
                    img_source = val.get("image_url")
                    overlay = None
                    try:
                        if img_source.lower().startswith(("http://", "https://")):
                            resp = requests.get(img_source, timeout=10)
                            if resp.status_code == 200:
                                overlay = Image.open(BytesIO(resp.content)).convert("RGBA")
                        else:
                            local_path = os.path.normpath(img_source)
                            if os.path.exists(local_path):
                                overlay = Image.open(local_path).convert("RGBA")
                        if overlay:
                            new_w = max(1, int(overlay.width * scale))
                            new_h = max(1, int(overlay.height * scale))
                            overlay = overlay.resize((new_w, new_h), Image.Resampling.LANCZOS)
                            strip_img.paste(overlay, (pos_x, pos_y), overlay)
                    except Exception as e:
                        print(f"⚠️ Img segment {i}: {e}")

            base_img.paste(strip_img, (AD_PADDING_X, ad_y), strip_img)
            y = next_y

        # --- ZAPIS JAKO PSD ---
        saved_path = _save_as_psd(base_img, output_path)
        print(f"✅ Plecy: {saved_path} ({BACKING_WIDTH}×{BACKING_HEIGHT} px = 321×641 mm)")

        # Cleanup tła
        if template_image_path:
            temp_dir = os.path.dirname(os.path.normpath(template_image_path))
            if os.path.abspath(temp_dir) != os.path.abspath(export_dir):
                if os.path.exists(temp_dir):
                    try: shutil.rmtree(temp_dir)
                    except OSError: pass

        return saved_path

    except Exception as e:
        print(f"❌ Błąd pleców: {e}")
        import traceback
        traceback.print_exc()
        return None


def generate_calendar(data, top_image_path=None, upscaled_top_path=None, production_id=None):
    """
    Generuje kalendarz trójdzielny jako DWA osobne pliki PSD
    w folderze: calendar_{production_id}_{kod}/

    Pliki:
      header_{id}.psd   — główka  3957 × 2658 px (335 × 225 mm)
      backing_{id}.psd  — plecy   3789 × 7572 px (321 × 641 mm)

    Returns:
        dict: {"header": ścieżka, "backing": ścieżka, "export_dir": folder}
    """
    # 1. Tworzenie folderu eksportu
    export_dir = create_export_folder(production_id)

    result = {"header": None, "backing": None, "export_dir": export_dir}

    # 2. Główka
    header_source = upscaled_top_path or top_image_path
    if header_source:
        result["header"] = generate_header(header_source, data, export_dir, production_id)
    else:
        print("⚠️ Brak obrazu na główkę — pomijam.")

    # 3. Plecy
    result["backing"] = generate_backing(data, export_dir, production_id)

    # Podsumowanie
    print("\n" + "=" * 50)
    print(f"📋 KALENDARZ #{production_id}")
    print(f"   📁 Folder:  {export_dir}")
    print(f"   🖼️ Główka:  {result['header'] or '❌'}")
    print(f"   📄 Plecy:   {result['backing'] or '❌'}")
    print("=" * 50)

    return result