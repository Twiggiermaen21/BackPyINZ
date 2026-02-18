import os
import requests  # <--- Konieczny import do ręcznego pobierania
from bigjpg import Bigjpg, Styles, Noises, EnlargeValues

def upscale_image_with_bigjpg(image_url, export_dir):
    current_stage = "Inicjalizacja funkcji"
    
    try:
        current_stage = "Autoryzacja Bigjpg"
        bigjpg = Bigjpg(os.getenv("BIGJPG_KEY"))
        
        print("🚀 Starting upscaling with Bigjpg...")

        current_stage = "Wysyłanie żądania do API (enlarge)"
        image_info = bigjpg.enlarge(
            style=Styles.Photo,
            noise=Noises.Highest,
            enlarge_value=EnlargeValues._4x,
            image_url=image_url
        )
        
        # Biblioteka sama czeka na zakończenie procesu wewnątrz metody enlarge/wait
        # Ale musimy wyciągnąć URL ZANIM spróbujemy pobrać
        
        current_stage = "Pobieranie URL przetworzonego obrazu"
        # Czasami trzeba poczekać chwilę, biblioteka to robi, 
        # ale tutaj pobieramy sam link do gotowego pliku
        upscaled_url_from_api = image_info.get_url() 

        # ---------------------------------------------------------
        # ZMIANA: RĘCZNA OBSŁUGA PLIKÓW I POBIERANIA
        # ---------------------------------------------------------

        current_stage = "Weryfikacja katalogu eksportu"
        if not os.path.exists(export_dir):
            os.makedirs(export_dir)

        current_stage = "Ustalanie nazwy pliku"
        existing_files = os.listdir(export_dir)
        existing_numbers = []
        for filename in existing_files:
            if filename.startswith("enlarged_image_") and filename.endswith(".png"):
                num_part = filename[len("enlarged_image_"):-4]
                if num_part.isdigit():
                    existing_numbers.append(int(num_part))
        next_number = max(existing_numbers, default=0) + 1

        local_filename = f"enlarged_image_{next_number}.png"
        upscaled_path = os.path.join(export_dir, local_filename)

        current_stage = f"Pobieranie pliku (requests) z: {upscaled_url_from_api}"
        
        # Używamy nagłówka User-Agent, aby udawać przeglądarkę i uniknąć błędu 403
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