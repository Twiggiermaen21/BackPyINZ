import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader

# Ładowanie zmiennych środowiskowych
load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_image(file_path, folder_name=None, file_name=None):
    if not os.path.exists(file_path):
        print(f"❌ Plik nie istnieje: {file_path}")
        return None

    try:
        options = {}

        if folder_name:
            options["folder"] = folder_name

        if file_name:
            # usuń rozszerzenie jeśli przypadkiem ktoś poda
            file_name = os.path.splitext(file_name)[0]
            options["public_id"] = file_name

        result = cloudinary.uploader.upload(file_path, **options)
        url = result.get("secure_url")
        print(f"✅ Przesłano jako: {result.get('public_id')}")
        print(f"🔗 URL: {url}")
        return url

    except Exception as e:
        print("❌ Błąd podczas przesyłania obrazu:", e)
        return None

