import os
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import io

load_dotenv()

cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET")
)

def upload_image(file, folder_name=None, file_name=None):
    try:
        options = {
            "format": "jpg", 
            "quality": "auto",  
            "transformation": [
                {"color_space": "srgb"} 
            ]
        }

        if folder_name:
            options["folder"] = folder_name

        if file_name:
    
            file_name = os.path.splitext(file_name)[0]
            options["public_id"] = file_name

        if isinstance(file, str):
            if not os.path.exists(file):
                print(f"❌ Plik nie istnieje: {file}")
                return None

            result = cloudinary.uploader.upload(file, **options)

        elif isinstance(file, bytes):
            result = cloudinary.uploader.upload(io.BytesIO(file), **options)

        else:
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