
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
        height = 1232
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
        return GeneratedImage.objects.filter(author=self.request.user).order_by('-created_at')

class GenerateImageToImageSDXLView(generics.ListCreateAPIView):
    queryset = OutpaintingSDXL.objects.all()
    serializer_class = OutpaintingSDXLSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        data = serializer.validated_data
        image_name=data.get("input_image") 
      

        name_only = os.path.splitext(image_name.url)[0]


        input_image_path = os.path.join(BASE_DIR, "backend", "images", f"{name_only[17:]}.png")
        output_dir = "./out"

        # generate_extended_calendar_background(
        #     input_image_path=input_image_path,
        #     output_dir=output_dir,
        #     output_format="png"
        # )

        output_file = os.path.join(output_dir, "kalendarz_extended_0.png")

        instance = serializer.save(
            output_file=output_file,
            output_format="png"
        )

        # Można dorzucić dodatkowe pole np. z URL
        self.extra_response_data = {"url": f"/media/{output_file}"}

    # def perform_create(self,serializer):
    #     if serializer.is_valid():
    #         serializer.save(input_image=self.request.input_image)
    #     else:
    #         print(serializer.errors)

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        if hasattr(self, 'extra_response_data'):
            resp.data.update(self.extra_response_data)
        return resp

    def get(self, request, *args, **kwargs):
        return response.Response(
            {"detail": "Method GET not allowed on this endpoint."},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )
class UpscalingView(generics.ListCreateAPIView):
    serializer_class = UpscalingSerializer
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        data = serializer.validated_data
        image_name = data.get("input_image") 

        # Budujemy poprawny HTTP URL
        filename_only = f"{os.path.splitext(image_name.url)[0][17:]}.png"
        input_image_url = "https://res.cloudinary.com/dhgml9qt5/image/upload/v1752673115/generated_image_45_ryv4e2.jpg"
        # self.request.build_absolute_uri(f"/static_images/{filename_only}")

        print("Upscaling image:", input_image_url)

        try:
            result = upscale_image_with_bigjpg(input_image_url)
            # Możesz tu zrobić np. serializer.save(...) jeśli chcesz zapisywać w DB
        except Exception as e:
            raise Exception(f"Upscaling failed: {e}")

        # Dodajemy to co zwrócił bigjpg do odpowiedzi
        self.extra_response_data = {"bigjpg_result": result}

    def create(self, request, *args, **kwargs):
        resp = super().create(request, *args, **kwargs)
        if hasattr(self, 'extra_response_data'):
            resp.data.update(self.extra_response_data)
        return resp
