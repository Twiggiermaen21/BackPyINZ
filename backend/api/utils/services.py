
import os
import requests
from django.db.models import Prefetch
from PIL import Image, ImageDraw, ImageFont, ImageOps
from ..models import Calendar, CalendarYearData, GeneratedImage
from .utils import save_as_psd, create_export_folder, hex_to_rgb, get_font_path, load_font
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


Image.MAX_IMAGE_PIXELS=140000000
# --- GŁÓWKA ---
HEADER_WIDTH = 3960       
HEADER_HEIGHT = 2670      

# --- PLECY ---
BACKING_WIDTH = 3780      # 12.63 cali = 321 mm
H_CONNECT =330              # 1.10 cali = 28 mm (łączenie główki z plecami)
H_GLUE = 120              #  0.40 cali =  10 mm  (klejenie główki na górze)
H_MONTH_BOX = 1650        #  5.50 cali = 140 mm  (kalendarium)
H_BIG = 264               #  0.88 cali =  22 mm  (linia bigowania)
H_AD_STRIP = 360         #  1.18 cali =  30 mm  (pasek reklamowy)
H_BLEED_BOTTOM = 120      #  0.40 cali =  10 mm  (spad dolny)

BOX_WIDTH = 3543           # 11.81 cali = 300 mm  (szer. kalendarium/reklamy)
BOX_X = (BACKING_WIDTH - BOX_WIDTH) // 2   # 123 px (centrowanie)

AD_PADDING_X = BOX_X
AD_CONTENT_WIDTH = BOX_WIDTH

# Łączna wysokość pleców
BACKING_HEIGHT = 7290


MONTH_NAMES = ["GRUDZIEŃ", "STYCZEŃ", "LUTY"]

def fetch_calendar_data(calendar_id):
  
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
                    print(f"⚠️ Błąd pobierania pola {field_number}: HTTP {response.status_code}")
            
            except Exception as e:
                print(f"⚠️ Wyjątek przy pobieraniu pola {field_number}: {e}")
               

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
    if calendar.top_image_id:
        try:
            gen_img = GeneratedImage.objects.get(id=calendar.top_image_id)
        except GeneratedImage.DoesNotExist:
            print(f"GeneratedImage z id {calendar.top_image_id} nie istnieje.")
            
    return gen_img.url


def create_gradient_vertical(size, start_rgb, end_rgb):
  
    width, height = size
   
    gradient_h = 256
    base = Image.new('RGB', (1, gradient_h))
    pixels = base.load()
    
    for y in range(gradient_h):
        t = y / (gradient_h - 1)
        
        pixels[0, y] = interpolate_color(start_rgb, end_rgb, t)
        
    return base.resize((width, height), Image.Resampling.BICUBIC)

def create_radial_gradient_css(size, start_rgb, end_rgb, center=(0.5, 0.5), offset_y=0):
    width, height = size
    small_w = 400
    small_h = int(400 * (height / width))
    
    base = Image.new('RGB', (small_w, small_h))
    pixels = base.load()
    
    relative_offset = offset_y / height

    target_cy_normalized = center[1] + relative_offset
    
    cx = int(small_w * center[0])
    cy = int(small_h * target_cy_normalized)
    
    max_dist = math.sqrt(max(cx, small_w - cx)**2 + max(cy, small_h - cy)**2)
    
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
    w, h = size
    diagonal = math.sqrt(w**2 + h**2)
    canvas_side = int(diagonal * 1.5) 
    cycle_height = int(diagonal * 0.40)

    if cycle_height < 10: cycle_height = 10

 
    strip_h = 256 
    strip = Image.new('RGB', (1, strip_h))
    px = strip.load()
    
    for y in range(strip_h):
        t = y / (strip_h - 1)
        if t <= 0.5:
            local_t = t * 2
            px[0, y] = interpolate_color(start_rgb, end_rgb, local_t)
        else:
            local_t = (t - 0.5) * 2
            px[0, y] = interpolate_color(end_rgb, start_rgb, local_t)
            

    cycle_img = strip.resize((canvas_side, cycle_height), Image.Resampling.BICUBIC)
    
    repeats = (canvas_side // cycle_height) + 2
    full_pattern = Image.new('RGB', (canvas_side, cycle_height * repeats))
    
    for i in range(repeats):
        full_pattern.paste(cycle_img, (0, i * cycle_height))
 
    rotated = full_pattern.rotate(45, resample=Image.Resampling.BICUBIC, expand=False)
 
    center_x, center_y = rotated.width // 2, rotated.height // 2
    left = center_x - w // 2
    top = center_y - h // 2
    
    return rotated.crop((left, top, left + w, top + h))


def create_liquid_css(size, start_rgb, end_rgb):
    
    w, h = size
    diagonal = int(math.sqrt(w**2 + h**2))
    
    grad = create_gradient_vertical((diagonal, diagonal), start_rgb, end_rgb)
    
    rotated = grad.rotate(-45, resample=Image.Resampling.BICUBIC)
    
    center_x, center_y = rotated.width // 2, rotated.height // 2
    left = center_x - w // 2
    top = center_y - h // 2
    return rotated.crop((left, top, left + w, top + h))

def generate_bottom_bg_image(width, height, bg_color, end_color, theme, variant):
    rgb_start = hex_to_rgb(bg_color)
    rgb_end = hex_to_rgb(end_color)
    
    if theme == "aurora":
        
        return create_radial_gradient_css((width, height), rgb_start, rgb_end, center=(0.3, 0.3))
        
    elif theme == "liquid":
      
        return create_liquid_css((width, height), rgb_start, rgb_end)
        
    elif theme == "waves":
      
        return create_waves_css((width, height), rgb_start, rgb_end)
        
    else:
        if variant == "horizontal":
       
            grad = create_gradient_vertical((height, width), rgb_start, rgb_end)
            return grad.rotate(90, expand=True)
            
        elif variant == "radial":
            return create_radial_gradient_css((width, height), rgb_start, rgb_end, center=(0.5, 0.5))
            
        elif variant == "diagonal":
           
            return create_liquid_css((width, height), rgb_start, rgb_end)
            
        else: 
           
            return create_gradient_vertical((width, height), rgb_start, rgb_end)



def handle_bottom_data(bottom_obj, export_dir):
   
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

    year_data = data.get("year_data") or data.get("year")

    REACT_WIDTH = 3720
    REACT_HEIGHT = 2430
    
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

                bleed_offset_x = (HEADER_WIDTH - REACT_WIDTH) / 2
                bleed_offset_y = (HEADER_HEIGHT - REACT_HEIGHT) / 2

                raw_x = float(year_data.get("positionX", 50))
                raw_y = float(year_data.get("positionY", 50))
                
                pos_x = int(raw_x + bleed_offset_x)
                pos_y = int(raw_y + bleed_offset_y)

                text_content = str(year_data.get("text", "2026"))
                font_size = int(float(year_data.get("size", 400)))
                text_color = year_data.get("color", "#FFFFFF")

                weight_raw = str(year_data.get("weight", "normal")).lower()
                is_bold = weight_raw in ["bold", "700", "800", "900", "bolder"]
                font_name = str(year_data.get("font", "arial"))
                font = load_font(font_name, font_size)

                stroke_w = int(font_size * 0.025) if is_bold else 0
                if is_bold and stroke_w < 1:
                    stroke_w = 1

                print(
                    f"🖌️ Rok: '{text_content}' | Offset spadów: ({bleed_offset_x}, {bleed_offset_y}) | "
                    f"Poz: ({pos_x}, {pos_y})"
                )

                draw.text(
                    (pos_x, pos_y),
                    text_content,
                    font=font,
                    fill=text_color,
                    stroke_width=stroke_w,
                    stroke_fill=text_color,
                )

            img_rgb = img_fitted.convert("RGB")
            saved_path = save_as_psd(img_rgb, output_path) 

            print(f"✅ Główka: {saved_path} ({HEADER_WIDTH}×{HEADER_HEIGHT} px)")
            return saved_path

    except Exception as e:
        print(f"❌ Błąd generowania główki: {e}")
        return None
    
def generate_backing(data, export_dir, production_id=None):
  
    bottom_data = data.get("bottom", {})
    template_image_path = bottom_data.get("image_path") if bottom_data else None

    output_path = os.path.join(export_dir, f"backing_{production_id}.psd")

    print(
        f"ℹ️ Plecy: {BACKING_WIDTH}×{BACKING_HEIGHT} px "
        f"({BACKING_WIDTH/300*25.4:.0f}×{BACKING_HEIGHT/300*25.4:.0f} mm)"
    )

    try:
        base_img = Image.new("RGB", (BACKING_WIDTH, BACKING_HEIGHT), "white")

        if template_image_path and os.path.exists(template_image_path):
            with Image.open(template_image_path) as src_bg:
                bg_layer = src_bg.convert("RGBA")
                bg_height = BACKING_HEIGHT - H_CONNECT
                bg_layer = ImageOps.fit(
                    bg_layer,
                    (BACKING_WIDTH, bg_height),
                    method=Image.Resampling.LANCZOS,
                )
                
                base_img.paste(bg_layer, (0, H_CONNECT))
                print(f"🖼️ Tło pleców wklejone (start Y: {H_CONNECT} px)")
        else:
            print("⚠️ Brak tła pleców — białe tło.")

        draw = ImageDraw.Draw(base_img)

        raw_fields = data.get("fields", {})
        y = H_CONNECT + 120  

        H_AD_STRIP_NEW = 360
        GAP_AFTER_CAL = 90
        GAP_AFTER_AD = 210
        GAP_AFTER_AD_LAST = 120

        for i in range(1, 4):
            cal_y = y

            # KALENDARIUM
            draw.rectangle(
                [(BOX_X, cal_y), (BOX_X + BOX_WIDTH, cal_y + H_MONTH_BOX)],
                fill="white", outline="#e5e7eb", width=5,
            )

            month_name = MONTH_NAMES[i - 1]
            m_font = load_font("arial.ttf", 150)
            center_x = BOX_X + BOX_WIDTH / 2
            l, t, r, b = draw.textbbox((0, 0), month_name, font=m_font)
            draw.text(
                (center_x - (r - l) / 2, cal_y + 40),
                month_name, font=m_font, fill="#1d4ed8",
            )

            g_font = load_font("arial.ttf", 100)
            g_text = "[Siatka dni]"
            gl, gt, gr, gb = draw.textbbox((0, 0), g_text, font=g_font)
            draw.text(
                (center_x - (gr - gl) / 2, cal_y + (H_MONTH_BOX - (gb - gt)) / 2 - gt),
                g_text, font=g_font, fill="#9ca3af",
            )

         
            ad_y = cal_y + H_MONTH_BOX + GAP_AFTER_CAL

            strip_img = Image.new("RGBA", (AD_CONTENT_WIDTH, H_AD_STRIP_NEW), (255, 255, 255, 0))
            strip_draw = ImageDraw.Draw(strip_img)

            config = raw_fields.get(str(i)) or raw_fields.get(i)
            scale = 1.0
            pos_x = 0
            pos_y = 0
            print(config)
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

                    font_ad = load_font(config.get("font", "arial.ttf"), f_size)
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
                    if is_bold and stroke_width < 1: stroke_width = 1

                    tl, tt, tr, tb = strip_draw.textbbox((0, 0), text, font=font_ad, stroke_width=stroke_width)
                    text_width = tr - tl
                    max_width = AD_CONTENT_WIDTH - 40

                    if text_width > max_width:
                        lines = []
                        current_line = ""
                        
                        for char in text:
                            test_line = current_line + char
                            tl_test, _, tr_test, _ = strip_draw.textbbox((0, 0), test_line, font=font_ad, stroke_width=stroke_width)
                            test_width_current = tr_test - tl_test

                            if test_width_current <= max_width:
                                current_line = test_line
                            else:
                               
                                if current_line:
                                    lines.append(current_line)
                            
                                current_line = char

                        if current_line:
                            lines.append(current_line)
                            
                        final_text = "\n".join(lines)

                        print("="*40)
                        print(f"⚠️ Tekst za szeroki ({text_width}px > {max_width}px). Podzielono na {len(lines)} linie (cięcie po znakach):")
                        for i, line in enumerate(lines):
                            print(f"   -> Linia {i+1}: '{line}'")
                        print("="*40)
                        # -----------------------------------
                        
                    else:
                        
                        final_text = text
                        print(f"✅ Tekst mieści się w jednej linii. Brak dzielenia.")

                    tl, tt, tr, tb = strip_draw.textbbox((0, 0), final_text, font=font_ad, stroke_width=stroke_width)

                    txt_x = (AD_CONTENT_WIDTH - (tr - tl)) / 2 - tl
                    txt_y = (H_AD_STRIP_NEW - (tb - tt)) / 2 - tt

                    strip_draw.multiline_text(
                        (txt_x, txt_y), final_text, font=font_ad,
                        fill=text_color, stroke_width=stroke_width, stroke_fill=text_color,
                        align="center"
                    )

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

            if i < 3:
                y = ad_y + H_AD_STRIP_NEW + GAP_AFTER_AD
            else:
                y = ad_y + H_AD_STRIP_NEW + GAP_AFTER_AD_LAST

     
        saved_path = save_as_psd(base_img, output_path)
        print(f"✅ Plecy: {saved_path} ({BACKING_WIDTH}×{BACKING_HEIGHT} px = 321×641 mm)")

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
    export_dir = create_export_folder(production_id)

    result = {"header": None, "backing": None, "export_dir": export_dir}

  
    header_source = upscaled_top_path or top_image_path
    if header_source:
        result["header"] = generate_header(header_source, data, export_dir, production_id)
    else:
        print("⚠️ Brak obrazu na główkę — pomijam.")

 
    result["backing"] = generate_backing(data, export_dir, production_id)

   
    print("\n" + "=" * 50)
    print(f"📋 KALENDARZ #{production_id}")
    print(f"   📁 Folder:  {export_dir}")
    print(f"   🖼️ Główka:  {result['header'] or '❌'}")
    print(f"   📄 Plecy:   {result['backing'] or '❌'}")
    print("=" * 50)

    return result