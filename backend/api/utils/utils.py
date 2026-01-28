# calendar_export/utils.py
import os
import requests  
from io import BytesIO
from PIL import Image


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
    print("Folder z fontami:", font_name, fonts_dir)
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
    print("Ścieżka do fontu:", filename)
    if not os.path.exists(font_path):
        # Fallback na Arial w folderze fonts
        fallback = os.path.join(fonts_dir, "arial.ttf")
        if os.path.exists(fallback):
            return fallback
        return "arial.ttf" # Systemowy

    return font_path


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
