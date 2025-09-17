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
    Upload obrazu do Cloudinary.
    - file może być:
        • bytes
        • file-like object (np. UploadedFile)
        • ścieżka do pliku (str)
    """
    try:
        options = {}

        if folder_name:
            options["folder"] = folder_name

        if file_name:
            # usuń rozszerzenie, jeśli przypadkiem ktoś podał
            file_name = os.path.splitext(file_name)[0]
            options["public_id"] = file_name

        # obsługa typów wejściowych
        if isinstance(file, str):  # ścieżka do pliku
            if not os.path.exists(file):
                print(f"❌ Plik nie istnieje: {file}")
                return None
            result = cloudinary.uploader.upload(file, **options)

        elif isinstance(file, bytes):  # raw bytes
            result = cloudinary.uploader.upload(io.BytesIO(file), **options)

        else:  # file-like object (np. InMemoryUploadedFile)
            result = cloudinary.uploader.upload(file, **options)

        url = result.get("secure_url")
        print(f"✅ Przesłano jako: {result.get('public_id')}")
        print(f"🔗 URL: {url}")
        return url

    except Exception as e:
        print("❌ Błąd podczas przesyłania obrazu:", e)
        return None
