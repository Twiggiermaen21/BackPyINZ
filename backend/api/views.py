
from fileinput import filename
from django.contrib.auth.models import User
from rest_framework import generics,response,status

from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated,  AllowAny

from .utils.bottom import extend_to_aspect_31x81
from .models import *
from .serializers import *
from .utils.generation import generate_image_from_prompt
from .utils.upscaling import upscale_image_with_bigjpg
from .utils.cloudinary_upload import upload_image
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

# Create your views here.
class CreateUserView(generics.ListCreateAPIView):
    queryset= User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
class NoteListCreate(generics.ListCreateAPIView):
    serializer_class=NoteSerializer
    permission_classes=[IsAuthenticated]

    def get_queryset(self):
        user=self.request.user
        return Note.objects.filter(author=user)
    
    def perform_create(self,serializer):
        if serializer.is_valid():
            serializer.save(author=self.request.user)
        else:
            print(serializer.errors)
class NoteDelete(generics.DestroyAPIView):
     serializer_class=NoteSerializer
     permission_classes=[IsAuthenticated]
    
     def get_queryset(self):
        user=self.request.user
        return Note.objects.filter(author=user) 
class GenerateImage(generics.ListCreateAPIView):
    serializer_class = GenerateImageSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        data = self.request.data
        prompt = data.get('prompt')
        width = 1792
        height = 1232
        user = self.request.user 

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

        try:
            inspiration = Inspiracja.objects.get(id=inspiration_id)
            composition = Kompozycja.objects.get(id=composition_id)
            color = Kolorystyka.objects.get(id=color_id)
            style = StylArtystyczny.objects.get(id=style_id)

            atmosfera = Atmosfera.objects.filter(id=atmosfera_id).first()
            tlo = Tlo.objects.filter(id=tlo_id).first()
            perspektywa = Perspektywa.objects.filter(id=perspektywa_id).first()
            detale = Detale.objects.filter(id=detale_id).first()
            realizm = Realizm.objects.filter(id=realizm_id).first()
            styl_narracyjny = StylNarracyjny.objects.filter(id=styl_narracyjny_id).first()
        except Exception as e:
            raise ValueError(f"Invalid ID in one of the foreign keys: {e}")

        try:
            image_path = generate_image_from_prompt(
                base_prompt=prompt,
                width=width,
                height=height,
                inspiration=inspiration.nazwa,
                color=color.nazwa,
                composition=composition.nazwa,
                style=style.nazwa,
                atmosfera=atmosfera.nazwa if atmosfera else None,
                tlo=tlo.nazwa if tlo else None,
                perspektywa=perspektywa.nazwa if perspektywa else None,
                detale=detale.nazwa if detale else None,
                realizm=realizm.nazwa if realizm else None,
                styl_narracyjny=styl_narracyjny.nazwa if styl_narracyjny else None
            )
            generated_url = upload_image(image_path, "generated_images", os.path.basename(image_path))
            filename = os.path.basename(image_path)
            input_path = os.path.join(BASE_DIR, "backend", "images", filename)
            output_path = os.path.join(BASE_DIR, "backend", "images", f"extended_{filename}")
        except Exception as e:
            raise Exception(f"Image generation failed: {e}")

        # extend_to_aspect_31x81(image_path=input_path, output_path=output_path)

        # Zapisz obiekt i zachowaj go do zwrócenia w create
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

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        self.perform_create(serializer)

        return response.Response({
            "message": "Image generated successfully.",
            "url": self.generated_instance.url
        }, status=status.HTTP_201_CREATED)
    def get_queryset(self):
        return GeneratedImage.objects.all().order_by('-created_at')


class CalendarCreateView(generics.ListCreateAPIView):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


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


class StylArtystycznyCreate(generics.ListCreateAPIView):
    queryset = StylArtystyczny.objects.all()
    serializer_class = StylArtystycznySerializer
    permission_classes = [IsAuthenticated]

class KompozycjaCreate(generics.ListCreateAPIView):
    queryset = Kompozycja.objects.all()
    serializer_class = KompozycjaSerializer
    permission_classes = [IsAuthenticated]

class KolorystykaCreate(generics.ListCreateAPIView):
    queryset = Kolorystyka.objects.all()
    serializer_class = KolorystykaSerializer
    permission_classes = [IsAuthenticated]

class AtmosferaCreate(generics.ListCreateAPIView):
    queryset = Atmosfera.objects.all()
    serializer_class = AtmosferaSerializer
    permission_classes = [IsAuthenticated]

class InspiracjaCreate(generics.ListCreateAPIView):
    queryset = Inspiracja.objects.all()
    serializer_class = InspiracjaSerializer
    permission_classes = [IsAuthenticated]

class TloCreate(generics.ListCreateAPIView):
    queryset = Tlo.objects.all()
    serializer_class = TloSerializer
    permission_classes = [IsAuthenticated]

class PerspektywaCreate(generics.ListCreateAPIView):
    queryset = Perspektywa.objects.all()
    serializer_class = PerspektywaSerializer
    permission_classes = [IsAuthenticated]

class DetaleCreate(generics.ListCreateAPIView):
    queryset = Detale.objects.all()
    serializer_class = DetaleSerializer
    permission_classes = [IsAuthenticated]

class RealizmCreate(generics.ListCreateAPIView):
    queryset = Realizm.objects.all()
    serializer_class = RealizmSerializer
    permission_classes = [IsAuthenticated]

class StylNarracyjnyCreate(generics.ListCreateAPIView):
    queryset = StylNarracyjny.objects.all()
    serializer_class = StylNarracyjnySerializer
    permission_classes = [IsAuthenticated]