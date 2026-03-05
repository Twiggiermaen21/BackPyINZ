import os
from psd_tools import PSDImage
import requests  
from io import BytesIO
from PIL import Image,  ImageFont
try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    HAS_PSD = True
except ImportError:
    HAS_PSD = False
    print("⚠️ psd_tools nie zainstalowane — zapis PSD niedostępny, fallback na JPG.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts") 
from PIL import Image, ImageCms
import os
CMYK_PROFILE_PATH = os.path.join(
    # os.path.dirname(__file__), "profiles", "PSOuncoated_v3_FOGRA52.icc"
        os.path.dirname(__file__), "profiles", "FOGRA51_v3.icc"

)
def hex_to_rgb(hex_color):
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    else:
        raise ValueError("Nieprawidłowy format koloru HEX")

def get_gradient_css(start_color, end_color, direction):
  
    return f"linear-gradient({direction or 'to bottom'}, {start_color}, {end_color})"


def get_font_path(font_name):
    import os
    
    base_dir = os.path.dirname(os.path.abspath(__file__))
    fonts_dir = os.path.join(base_dir, "fonts")
   
    font_map = {
        "Arial": "arial.ttf",
        "Courier New": "cour.ttf",
        "Georgia": "georgia.ttf",
        "Tahoma": "tahoma.ttf",
        "Verdana": "verdana.ttf",
        "Roboto": "Roboto-Regular.ttf", 
    }

 
    filename = font_map.get(font_name, "arial.ttf")
    font_path = os.path.join(fonts_dir, filename)
 
    if not os.path.exists(font_path):
        
        fallback = os.path.join(fonts_dir, "arial.ttf")
        if os.path.exists(fallback):
            return fallback
        return "arial.ttf" 

    return font_path




def load_font(name_or_path, size):
    
    if not name_or_path.endswith((".ttf", ".otf")):
        font_filename = f"{name_or_path.lower()}.ttf"
    else:
        font_filename = name_or_path

    font_path = os.path.join(FONTS_DIR, font_filename)

    try:
        print(f"🔍 Próba ładowania fontu: '{name_or_path}' z rozmiarem {size}px")
        return ImageFont.truetype(font_path, size)
    except OSError:
        try:
        
            return ImageFont.truetype(name_or_path, size)
        except OSError:
            print(f"⚠️ Nie znaleziono '{font_path}'. Używam awaryjnie arial.ttf")
            try:

                return ImageFont.truetype(os.path.join(FONTS_DIR, "arial.ttf"), size)
            except OSError:
                return ImageFont.truetype("arial", size)
def load_image_robust(path_or_url):

    if not path_or_url:
        return None

    try:
      
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            print(f"⬇️ Pobieranie URL: {path_or_url[:50]}...")

            response = requests.get(path_or_url, timeout=30)
            response.raise_for_status() 
            image = Image.open(BytesIO(response.content))
            return image.convert("RGBA")

        else:
            local_path = os.path.normpath(path_or_url)
            if os.path.exists(local_path):
                image = Image.open(local_path)
                return image.convert("RGBA")
            else:
                print(f"⚠️ Plik lokalny nie istnieje: {local_path}")
                return None

    except requests.exceptions.Timeout:
        print(f"❌ Timeout (za długi czas oczekiwania) przy pobieraniu: {path_or_url}")
        return None
    except Exception as e:
        print(f"❌ Błąd otwierania obrazu {path_or_url}: {e}")
        return None



def create_export_folder(production_id, base_dir=None):
 
    if base_dir is None:
        base_dir = os.path.join(os.getcwd(), "media", "calendar_exports")


    folder_name = f"calendar_{production_id}"
    export_dir = os.path.join(base_dir, folder_name)
    os.makedirs(export_dir, exist_ok=True)

    print(f"📁 Folder eksportu: {export_dir}")
    return export_dir