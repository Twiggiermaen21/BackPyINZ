import os
import requests
from io import BytesIO
from PIL import Image

def load_image_robust(path_or_url):
    """
    Bezpiecznie pobiera i otwiera obrazek niezaleznie od jego formy (URL lub plik lokalny), 
    konwertujac do przestrzeni RGBA zgodnej z formatem compositingu (wklejania jako warstwy).
    Zabezpieczone obsluga wyjatkow (TimeOut, bledy dysku). Zwraca obiekt Image z biblioteki PIL lub None po niepowodzeniu.
    """
    if not path_or_url:
        return None

    try:
        # URL
        if path_or_url.startswith("http://") or path_or_url.startswith("https://"):
            print(f"Pobieranie URL: {path_or_url[:50]}...")
            response = requests.get(path_or_url, timeout=30)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
            return image.convert("RGBA")

        # plik lokalny
        else:
            local_path = os.path.normpath(path_or_url)
            if os.path.exists(local_path):
                image = Image.open(local_path)
                return image.convert("RGBA")
            else:
                print(f"Plik lokalny nie istnieje: {local_path}")
                return None

    except requests.exceptions.Timeout:
        print(f"Timeout przy pobieraniu: {path_or_url}")
        return None
    except Exception as e:
        print(f"Blad otwierania obrazu {path_or_url}: {e}")
        return None
