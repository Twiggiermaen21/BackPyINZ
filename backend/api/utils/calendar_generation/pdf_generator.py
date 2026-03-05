import os
import requests
import shutil
from io import BytesIO
from PIL import Image, ImageDraw, ImageOps
from .config import (HEADER_WIDTH, HEADER_HEIGHT, BACKING_WIDTH, BACKING_HEIGHT,
                     H_CONNECT, H_MONTH_BOX, BOX_X, BOX_WIDTH, AD_PADDING_X, AD_CONTENT_WIDTH)
from .fonts import load_font
from .pdf_utils import save_as_pdf
from .file_utils import create_export_folder

def generate_header(top_image_path, data, export_dir, production_id=None):
    """
    Klonuje i skaluje obraz glowki, aplikuje na niego tekst roku (jesli zostal przelazany) 
    z uwzglednieniem offsetow dla spadow, a nastepnie eksportuje gotowy plik jako PDF (CMYK).
    """
    year_data = data.get("year_data") or data.get("year")

    REACT_WIDTH = 3720
    REACT_HEIGHT = 2430
    
    if not top_image_path or not os.path.exists(top_image_path):
        print("Brak pliku obrazu glowki.")
        return None

    output_path = os.path.join(export_dir, f"header_{production_id}.pdf")
 
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
                    f"Rok: '{text_content}' | Offset spadow: ({bleed_offset_x}, {bleed_offset_y}) | "
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
            saved_path = save_as_pdf(img_rgb, output_path)

            print(f"Glowka: {saved_path} ({HEADER_WIDTH}x{HEADER_HEIGHT} px)")
            return saved_path

    except Exception as e:
        print(f"Blad generowania glowki: {e}")
        return None
    
def generate_backing(data, export_dir, production_id=None):
    """
    Buduje caly dokument "plecow" kalendarza na bazie ustawien: tlo dolnej czesci, 
    trzy kalendaria, nakladanie pol tekstowych i obrazkowych predefiniowanych uzytkownika. 
    Gotowa plansze z odpowiednimi marginesami eksportuje do pliku PDF (CMYK).
    """
    bottom_data = data.get("bottom", {})
    template_image_path = bottom_data.get("image_path") if bottom_data else None

    output_path = os.path.join(export_dir, f"backing_{production_id}.pdf")

    print(
        f"Plecy: {BACKING_WIDTH}x{BACKING_HEIGHT} px "
        f"({BACKING_WIDTH/300*25.4:.0f}x{BACKING_HEIGHT/300*25.4:.0f} mm)"
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
                print(f"Tlo plecow wklejone (start Y: {H_CONNECT} px)")
        else:
            print("Brak tla plecow — biale tlo.")

        draw = ImageDraw.Draw(base_img)

        raw_fields = data.get("fields", {})
        y = H_CONNECT + 120

        H_AD_STRIP_NEW = 360
        GAP_AFTER_CAL = 90
        GAP_AFTER_AD = 210
        GAP_AFTER_AD_LAST = 120

        for i in range(1, 4):
            cal_y = y

            draw.rectangle(
                [(BOX_X, cal_y), (BOX_X + BOX_WIDTH, cal_y + H_MONTH_BOX)],
                fill="white", outline="#e5e7eb", width=5,
            )

            center_x = BOX_X + BOX_WIDTH / 2
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

                    base_stroke = max(1, int(f_size * 0.015))
                    stroke_width = base_stroke + (int(f_size / 40) if is_bold else 0)

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
                        print(f"Tekst za szeroki ({text_width}px > {max_width}px). Podzielono na {len(lines)} linie:")
                        for i, line in enumerate(lines):
                            print(f"   -> Linia {i+1}: '{line}'")
                        print("="*40)
                        
                    else:
                        final_text = text
                        print(f"Tekst miesci sie w jednej linii.")

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
                        print(f"Img segment {i}: {e}")

            base_img.paste(strip_img, (AD_PADDING_X, ad_y), strip_img)

            if i < 3:
                y = ad_y + H_AD_STRIP_NEW + GAP_AFTER_AD
            else:
                y = ad_y + H_AD_STRIP_NEW + GAP_AFTER_AD_LAST

        saved_path = save_as_pdf(base_img, output_path)
        print(f"Plecy: {saved_path} ({BACKING_WIDTH}x{BACKING_HEIGHT} px = 321x641 mm)")

        if template_image_path:
            temp_dir = os.path.dirname(os.path.normpath(template_image_path))
            if os.path.abspath(temp_dir) != os.path.abspath(export_dir):
                if os.path.exists(temp_dir):
                    try: shutil.rmtree(temp_dir)
                    except OSError: pass

        return saved_path

    except Exception as e:
        print(f"Blad plecow: {e}")
        import traceback
        traceback.print_exc()
        return None

def generate_calendar(data, top_image_path=None, upscaled_top_path=None, production_id=None):
    """
    Glowny orkiestrator zlecenia druku. Przygotowuje foldery robocze, a nastepnie deleguje 
    wykonanie odpowiednio do `generate_header` (glowka) i `generate_backing` (plecy). Zwraca sciezki PDFow.
    """
    export_dir = create_export_folder(production_id)

    result = {"header": None, "backing": None, "export_dir": export_dir}

    header_source = upscaled_top_path or top_image_path
    if header_source:
        result["header"] = generate_header(header_source, data, export_dir, production_id)
    else:
        print("Brak obrazu na glowke — pomijam.")

    result["backing"] = generate_backing(data, export_dir, production_id)

    print("\n" + "=" * 50)
    print(f"KALENDARZ #{production_id}")
    print(f"   Folder:  {export_dir}")
    print(f"   Glowka:  {result['header'] or 'BRAK'}")
    print(f"   Plecy:   {result['backing'] or 'BRAK'}")
    print("=" * 50)

    return result
