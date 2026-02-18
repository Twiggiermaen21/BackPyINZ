import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import io

# Ładowanie zmiennych środowiskowych
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_image(file, folder_name=None, file_name=None):
    """
    Upload obrazu do Cloudinary z automatyczną konwersją na JPG (sRGB).
    """
    try:
        # 1. Ustawiamy domyślne opcje konwersji
        options = {
            "format": "jpg",        # Wymusza zapis jako JPG
            "quality": "auto",      # Automatyczna optymalizacja jakości (zmniejsza wagę pliku)
            
            # Kluczowe dla Twojego projektu kalendarza (React nie lubi CMYK):
            "transformation": [
                {"color_space": "srgb"} # Wymusza konwersję kolorów do standardu ekranowego
            ]
        }

        if folder_name:
            options["folder"] = folder_name

        if file_name:
            # usuń rozszerzenie, jeśli przypadkiem ktoś podał
            file_name = os.path.splitext(file_name)[0]
            options["public_id"] = file_name

        # --- Obsługa typów wejściowych ---
        
        # Przypadek 1: Ścieżka do pliku (str)
        if isinstance(file, str):
            if not os.path.exists(file):
                print(f"❌ Plik nie istnieje: {file}")
                return None
            
            # Cloudinary sam otworzy plik ze ścieżki
            result = cloudinary.uploader.upload(file, **options)

        # Przypadek 2: Raw bytes
        elif isinstance(file, bytes):
            result = cloudinary.uploader.upload(io.BytesIO(file), **options)

        # Przypadek 3: File-like object (np. z formularza Django)
        else:
            # Ważne: Jeśli plik był już czytany, przewiń go na początek
            if hasattr(file, 'seek'):
                file.seek(0)
            result = cloudinary.uploader.upload(file, **options)

        url = result.get("secure_url")
        print(f"✅ Przesłano jako JPG: {result.get('public_id')}")
        print(f"🔗 URL: {url}")
        return url

    except Exception as e:
        print("❌ Błąd podczas przesyłania obrazu:", e)
        return None