import os
from PIL import ImageFont

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FONTS_DIR = os.path.join(BASE_DIR, "fonts")

def get_font_path(font_name):
    """
    Translacja miedzy rynkowymi nazwami fontow (z frontendu) a ich fizycznymi 
    plikami TTF dostepnymi lokalnie na hoście backendowym w folderze fonts/.
    Zawsze zapobiega bledom - dostarcza fallback 'arial.ttf' gdy zadany font u kogos nie wystepuje.
    """
    font_map = {
        "Arial": "arial.ttf",
        "Courier New": "cour.ttf",
        "Georgia": "georgia.ttf",
        "Tahoma": "tahoma.ttf",
        "Verdana": "verdana.ttf",
        "Roboto": "Roboto-Regular.ttf", 
    }

    filename = font_map.get(font_name, "arial.ttf")
    font_path = os.path.join(FONTS_DIR, filename)
 
    if not os.path.exists(font_path):
        fallback = os.path.join(FONTS_DIR, "arial.ttf")
        if os.path.exists(fallback):
            return fallback
        return "arial.ttf"

    return font_path

def load_font(name_or_path, size):
    """
    Kaskadowo stara sie zaladowac obiekt czcionki z TrueType z biblioteki PIL.
    Pozwala ominac problem rozszerzen i wielkosci znakow, oferujac inteligentny mechanizm awaryjnego (fallback) ladowania Ariala, by nie zepsuc zapisu zadania generatora kalendarzy (w wypadku awarii zewnetrznego fontu). 
    """
    if not name_or_path.endswith((".ttf", ".otf")):
        font_filename = f"{name_or_path.lower()}.ttf"
    else:
        font_filename = name_or_path

    font_path = os.path.join(FONTS_DIR, font_filename)

    try:
        print(f"Ladowanie fontu: '{name_or_path}' z rozmiarem {size}px")
        return ImageFont.truetype(font_path, size)
    except OSError:
        try:
            return ImageFont.truetype(name_or_path, size)
        except OSError:
            print(f"Nie znaleziono '{font_path}'. Uzywam awaryjnie arial.ttf")
            try:
                return ImageFont.truetype(os.path.join(FONTS_DIR, "arial.ttf"), size)
            except OSError:
                return ImageFont.truetype("arial", size)
