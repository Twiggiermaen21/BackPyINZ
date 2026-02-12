
import uuid
from rest_framework.permissions import IsAuthenticated,  AllowAny
from ..models import *
from ..serializers import *
from ..pagination import *
from ..utils.generation import generate_image_from_prompt
from ..utils.upscaling import upscale_image_with_bigjpg
from ..utils.cloudinary_upload import upload_image
import os
from dotenv import load_dotenv
from rest_framework import generics, status, response
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


class GenerateImage(generics.ListCreateAPIView):
    serializer_class = GenerateImageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ImagesPagination

    def perform_create(self, serializer):
        data = self.request.data
        print("📥 Odebrane dane z requestu:", data)

        prompt = data.get('prompt', None)
        width = 1792
        height = 1200
        user = self.request.user 
        print(f"👤 Użytkownik: {user}")
        print(f"🧠 Prompt: {prompt}")

        # Pobieramy ID (mogą być None)
        inspiration_id = data.get('inspiracja')
        composition_id = data.get('kompozycja')
        color_id = data.get('kolorystyka')
        style_id = data.get('styl_artystyczny')
        atmosfera_id = data.get('atmosfera')
        tlo_id = data.get('tlo')
        perspektywa_id = data.get('perspektywa')
        detale_id = data.get('detale')
        realizm_id = data.get('realizm')
        styl_narracyjny_id = data.get('styl_narracyjny')

        print("🧩 Odebrane ID:")
        print({
            "inspiracja": inspiration_id,
            "kompozycja": composition_id,
            "kolorystyka": color_id,
            "styl_artystyczny": style_id,
            "atmosfera": atmosfera_id,
            "tlo": tlo_id,
            "perspektywa": perspektywa_id,
            "detale": detale_id,
            "realizm": realizm_id,
            "styl_narracyjny": styl_narracyjny_id,
        })

        # Pobieramy obiekty powiązane tylko jeśli istnieje ID
        inspiration = Inspiracja.objects.filter(id=inspiration_id).first() if inspiration_id else None
        composition = Kompozycja.objects.filter(id=composition_id).first() if composition_id else None
        color = Kolorystyka.objects.filter(id=color_id).first() if color_id else None
        style = StylArtystyczny.objects.filter(id=style_id).first() if style_id else None
        atmosfera = Atmosfera.objects.filter(id=atmosfera_id).first() if atmosfera_id else None
        tlo = Tlo.objects.filter(id=tlo_id).first() if tlo_id else None
        perspektywa = Perspektywa.objects.filter(id=perspektywa_id).first() if perspektywa_id else None
        detale = Detale.objects.filter(id=detale_id).first() if detale_id else None
        realizm = Realizm.objects.filter(id=realizm_id).first() if realizm_id else None
        styl_narracyjny = StylNarracyjny.objects.filter(id=styl_narracyjny_id).first() if styl_narracyjny_id else None

        print("📚 Obiekty powiązane:")
        print({
            "inspiracja": inspiration.nazwa if inspiration else None,
            "kompozycja": composition.nazwa if composition else None,
            "kolorystyka": color.nazwa if color else None,
            "styl_artystyczny": style.nazwa if style else None,
            "atmosfera": atmosfera.nazwa if atmosfera else None,
            "tlo": tlo.nazwa if tlo else None,
            "perspektywa": perspektywa.nazwa if perspektywa else None,
            "detale": detale.nazwa if detale else None,
            "realizm": realizm.nazwa if realizm else None,
            "styl_narracyjny": styl_narracyjny.nazwa if styl_narracyjny else None,
        })

        # Przygotowanie danych do funkcji generate_image_from_prompt
        try:
            print("⚙️ Wywołuję generate_image_from_prompt()...")
            image_bytes = generate_image_from_prompt(
                base_prompt=prompt if prompt else None,
                width=width,
                height=height,
                inspiration=inspiration.nazwa if inspiration else None,
                color=color.nazwa if color else None,
                composition=composition.nazwa if composition else None,
                style=style.nazwa if style else None,
                atmosfera=atmosfera.nazwa if atmosfera else None,
                tlo=tlo.nazwa if tlo else None,
                perspektywa=perspektywa.nazwa if perspektywa else None,
                detale=detale.nazwa if detale else None,
                realizm=realizm.nazwa if realizm else None,
                styl_narracyjny=styl_narracyjny.nazwa if styl_narracyjny else None
            )
            print("✅ Obraz wygenerowany (bytes length):", len(image_bytes))
        except Exception as e:
            print("❌ Błąd podczas generowania obrazu:", str(e))
            raise

        try:
            filename = f"generated_{uuid.uuid4().hex}.png"
            print(f"💾 Upload obrazu jako: {filename}")
            generated_url = upload_image(image_bytes, "generated_images", filename)
            print("🌐 URL wygenerowanego obrazu:", generated_url)
        except Exception as e:
            print("❌ Błąd podczas uploadu obrazu:", str(e))
            raise

        # Zapisujemy instancję
        self.generated_instance = serializer.save(
            author=user,
            prompt=prompt,
            width=width,
            height=height,
            url=generated_url,
            inspiracja=inspiration,
            kompozycja=composition,
            kolorystyka=color,
            styl_artystyczny=style,
            atmosfera=atmosfera,
            tlo=tlo,
            perspektywa=perspektywa,
            detale=detale,
            realizm=realizm,
            styl_narracyjny=styl_narracyjny
        )

        print("📝 Obraz zapisany w bazie jako:", self.generated_instance.id)


    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return response.Response({
            "message": "Image generated successfully.",
            "url": self.generated_instance.url
        }, status=status.HTTP_201_CREATED)

    def get_queryset(self):
        # Pobranie użytkownika
        user = self.request.user
        
        # Pobranie parametru z query params
        project_name = self.request.query_params.get('project_name', None)
        
        # Podstawowy queryset dla danego użytkownika
        queryset = GeneratedImage.objects.filter(author=user)
        
        # Jeśli podano project_name, filtruj też po nazwie projektu
        if project_name:
            queryset = queryset.filter(project__name=project_name)
        
        # Posortuj malejąco po dacie utworzenia
        return queryset.order_by('-created_at')
    
    
class ImagesByProjectView(generics.ListAPIView):
    serializer_class = GenerateImageSerializer
    permission_classes = [IsAuthenticated]

    lookup_url_kwarg = "project_name"

    def get_queryset(self):
        user = self.request.user
        project_name = self.kwargs.get("project_name")

        # Podstawowy queryset dla użytkownika
        qs = GeneratedImage.objects.filter(author=user)

        # Filtr po nazwie projektu, jeśli podano
        if project_name:
            qs = qs.filter(name=project_name)

        # Posortuj malejąco po dacie utworzenia
        return qs.order_by("-created_at")
class ImageSearchBarView(generics.ListAPIView):
    serializer_class = ImageSearchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None 


    def get_queryset(self):
        
        return GeneratedImage.objects.filter(
            author=self.request.user,
                ).order_by("-created_at")
