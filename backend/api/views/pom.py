from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
import os
import time
import requests
from urllib.parse import urlparse
from django.core.files.base import ContentFile
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Podmień na nazwę swojej aplikacji i modelu
from ..models import GeneratedImage 

from django.conf import settings  # To potrzebne, żeby wiedzieć gdzie jest folder media

def download_single_image_logic(pk):
    """
    Pobiera jeden obrazek dla podanego ID.
    Zapisuje go fizycznie w folderze: /media/pobrane/
    NIE wymaga pola ImageField w modelu.
    """
    
    # 1. Konfiguracja bezpiecznej sesji (SSL fix)
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))

    try:
        obj = GeneratedImage.objects.get(pk=pk)
    except GeneratedImage.DoesNotExist:
        return {"success": False, "error": f"Nie znaleziono obrazu o ID {pk}"}

    current_url = obj.url 
    
    if not current_url:
        return {"success": False, "error": "Pole URL jest puste."}

    # Sprawdzamy czy to link zewnętrzny
    if current_url.startswith("http://") or current_url.startswith("https://"):
        print(f"⬇️ [ID: {pk}] Pobieranie z URL: {current_url}")
        
        try:
            response = session.get(current_url, timeout=30)
            
            if response.status_code == 200:
                # --- PRZYGOTOWANIE NAZWY PLIKU ---
                parsed = urlparse(current_url)
                file_name = os.path.basename(parsed.path)
                
                # Jeśli nazwa jest pusta, generujemy własną
                if not file_name or len(file_name) < 3:
                    file_name = f"img_{obj.id}_{int(time.time())}.png"

                # --- PRZYGOTOWANIE ŚCIEŻKI FOLDERU ---
                # Używamy settings.MEDIA_ROOT, aby trafić do folderu media w projekcie
                # Tworzymy podfolder 'pobrane' (możesz zmienić nazwę)
                save_dir = os.path.join(settings.MEDIA_ROOT, 'pobrane')
                
                # Jeśli folder nie istnieje, tworzymy go
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)

                # Pełna ścieżka, gdzie plik wyląduje
                full_file_path = os.path.join(save_dir, file_name)

                # --- FIZYCZNY ZAPIS PLIKU NA DYSK ---
                with open(full_file_path, 'wb') as f:
                    f.write(response.content)

                print(f"✅ [ID: {pk}] Zapisano na dysku: {full_file_path}")
                
                # Opcjonalnie: Możesz zaktualizować pole URL w bazie na ścieżkę lokalną
                # Względna ścieżka dla Django (np. do wyświetlania w <img src="...">)
                relative_path = f"/media/pobrane/{file_name}"
                
                # Odkomentuj poniższe, jeśli chcesz nadpisać link w bazie linkiem lokalnym:
                # obj.url = relative_path
                # obj.save()

                return {
                    "success": True, 
                    "message": "Pobrano pomyślnie", 
                    "local_path": full_file_path,
                    "url_path": relative_path,
                    "id": obj.id
                }
            else:
                return {"success": False, "error": f"HTTP {response.status_code}"}
                
        except Exception as e:
            print(f"❌ Błąd pobierania: {e}")
            return {"success": False, "error": str(e)}

    else:
        return {
            "success": False, 
            "message": "To nie jest link HTTP (prawdopodobnie plik już lokalny).",
            "current_value": str(current_url)
        }
@api_view(['GET'])
@permission_classes([AllowAny]) 
def download_single_image_view(request, pk):
    """
    Pobiera jeden konkretny obrazek wskazany przez ID w URL.
    Np. GET /api/download-img-gallery/55
    """
    try:
        # Uruchamiamy logikę z ID przekazanym w URL
        result = download_single_image_logic(pk)
        
        if result.get("success"):
            return JsonResponse(result, status=200)
        else:
            return JsonResponse(result, status=400)
            
    except Exception as e:
        return JsonResponse({
            "success": False, 
            "error": str(e)
        }, status=500)