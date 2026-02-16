# calendar_export/utils.py
import os
import uuid
from psd_tools import PSDImage
import requests  
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageOps
try:
    from psd_tools import PSDImage
    from psd_tools.api.layers import PixelLayer
    HAS_PSD = True
except ImportError:
    HAS_PSD = False
    print("⚠️ psd_tools nie zainstalowane — zapis PSD niedostępny, fallback na JPG.")



def hex_to_rgb(hex_color):
    """Konwertuje kolor w formacie HEX na krotkę RGB."""
    # Usuń znak '#' jeśli istnieje
    hex_color = hex_color.lstrip("#")
    
    # Rozdziel na R, G, B i konwertuj na int
    if len(hex_color) == 6:
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    else:
        # Możesz dodać obsługę skróconego formatu #RGB na #RRGGBB, ale to jest uproszczona wersja
        raise ValueError("Nieprawidłowy format koloru HEX")

def get_gradient_css(start_color, end_color, direction):
    """Generuje string CSS dla gradientu."""
    return f"linear-gradient({direction or 'to bottom'}, {start_color}, {end_color})"


def get_font_path(font_name):
    import os
    """
    Mapuje nazwy fontów z Frontendu na pliki w folderze 'fonts' (obok skryptu).
    """
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

    # Pobieramy nazwę pliku, domyślnie arial.ttf
    filename = font_map.get(font_name, "arial.ttf")
    font_path = os.path.join(fonts_dir, filename)
 
    if not os.path.exists(font_path):
        # Fallback na Arial w folderze fonts
        fallback = os.path.join(fonts_dir, "arial.ttf")
        if os.path.exists(fallback):
            return fallback
        return "arial.ttf" # Systemowy

    return font_path

def _load_font(name_or_path, size):
    """Bezpieczne ładowanie czcionki z fallbackiem."""
    try:
        return ImageFont.truetype(name_or_path, size)
    except OSError:
        try:
            return ImageFont.truetype("arial.ttf", size)
        except OSError:
            return ImageFont.load_default()


def load_image_robust(path_or_url):
    """
    Inteligentna funkcja otwierająca obrazek.
    - Jeśli to URL (https://): pobiera go z timeoutem 30s.
    - Jeśli to ścieżka lokalna (D:\): otwiera plik z dysku.
    """
    if not path_or_url:
        return None

    try:
        # 1. Obsługa URL (Cloudinary / Internet)
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            print(f"⬇️ Pobieranie URL: {path_or_url[:50]}...")
            # Ustawiamy timeout na 30 sekund, żeby uniknąć błędu SSL Handshake
            response = requests.get(path_or_url, timeout=30)
            response.raise_for_status() # Rzuć błąd, jeśli status nie jest 200 OK
            image = Image.open(BytesIO(response.content))
            return image.convert("RGBA")

        # 2. Obsługa plików lokalnych (Windows paths)
        else:
            # Normalizacja ścieżki (zamiana \ na / lub odwrotnie w zależności od systemu)
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


def _save_as_psd(pil_image, output_path):
    """Zapisuje obraz PIL jako PSD. Fallback na JPG CMYK jeśli brak psd_tools."""
    if HAS_PSD:
        psd = PSDImage.new(mode="CMYK", size=pil_image.size)
        layer = PixelLayer.frompil(pil_image, psd)
        psd.append(layer)
        psd.save(output_path)
    else:
        # Fallback: JPG CMYK
        fallback_path = output_path.replace(".psd", "_CMYK.jpg")
        img_cmyk = pil_image.convert("CMYK")
        img_cmyk.save(fallback_path, format="JPEG", dpi=(300, 300), quality=95, subsampling=0)
        output_path = fallback_path
    return output_path


def create_export_folder(production_id, base_dir=None):
    """
    Tworzy folder eksportu: calendar_{production_id}_{krótki_kod}/
    Zwraca ścieżkę do folderu.
    """
    if base_dir is None:
        base_dir = os.path.join(os.getcwd(), "media", "calendar_exports")

    short_code = uuid.uuid4().hex[:8]
    folder_name = f"calendar_{production_id}_{short_code}"
    export_dir = os.path.join(base_dir, folder_name)
    os.makedirs(export_dir, exist_ok=True)

    print(f"📁 Folder eksportu: {export_dir}")
    return export_dir