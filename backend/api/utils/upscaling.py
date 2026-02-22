import os
import requests  
from django.conf import settings # <--- DODANY IMPORT
from bigjpg import Bigjpg, Styles, Noises, EnlargeValues

def upscale_image_with_bigjpg(image_url, export_dir, enlarge):
    current_stage = "Inicjalizacja funkcji"
    
    # <--- ZMIANA: Tworzymy stałą ścieżkę do media/pobrane --->
    # Używamy settings.MEDIA_ROOT, co automatycznie celuje w Twój folder "media"
    pobrane_dir = os.path.join(settings.MEDIA_ROOT, "pobrane")
    
    enlarge_value = EnlargeValues._4x  # Domyślna wartość, jeśli nie zostanie podana
    if enlarge == 4:
        enlarge_value = EnlargeValues._4x
    elif enlarge == 8:
        enlarge_value = EnlargeValues._8x
        
    try:
        current_stage = "Autoryzacja Bigjpg"
        bigjpg = Bigjpg(os.getenv("BIGJPG_KEY"))
        
        print("🚀 Starting upscaling with Bigjpg...")
        print(f"url: {image_url}")
        current_stage = "Wysyłanie żądania do API (enlarge)"
        image_info = bigjpg.enlarge(
            style=Styles.Photo,
            noise=Noises.Highest,
            enlarge_value=enlarge_value,
            image_url=image_url
        )
        
        current_stage = "Pobieranie URL przetworzonego obrazu"
        upscaled_url_from_api = image_info.get_url() 

        current_stage = "Weryfikacja katalogu eksportu"
        # Sprawdzamy i tworzymy folder "pobrane", jeśli go nie ma
        if not os.path.exists(pobrane_dir):
            os.makedirs(pobrane_dir)

        current_stage = "Ustalanie nazwy pliku"
        existing_files = os.listdir(pobrane_dir)
        existing_numbers = []
        for filename in existing_files:
            if filename.startswith("enlarged_image_") and filename.endswith(".png"):
                num_part = filename[len("enlarged_image_"):-4]
                if num_part.isdigit():
                    existing_numbers.append(int(num_part))
        next_number = max(existing_numbers, default=0) + 1

        local_filename = f"enlarged_image_{next_number}.png"
        # Podpinamy nową ścieżkę do zapisu
        upscaled_path = os.path.join(pobrane_dir, local_filename)

        current_stage = f"Pobieranie pliku (requests) z: {upscaled_url_from_api}"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }
        
        response = requests.get(upscaled_url_from_api, headers=headers, stream=True)
        
        if response.status_code == 200:
            with open(upscaled_path, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            print(f"✅ Image saved manually to: {upscaled_path}")
        else:
            raise Exception(f"Błąd pobierania pliku. Status code: {response.status_code}")

        return {
            "bigjpg_url": upscaled_url_from_api,
            "local_upscaled": upscaled_path,
        }

    except Exception as e:
        print("\n" + "="*40)
        print(f"❌ WYSTĄPIŁ BŁĄD!")
        print(f"📍 Etap, w którym program się wywalił: '{current_stage}'")
        print(f"⚠️ Treść błędu: {e}")
        print("="*40 + "\n")
        return None