
import uuid
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated,  AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import *
from .serializers import *
from .pagination import *
from .utils.generation import generate_image_from_prompt
from .utils.upscaling import upscale_image_with_bigjpg
from .utils.cloudinary_upload import upload_image
from rest_framework.exceptions import ValidationError
import os
import json
from dotenv import load_dotenv
from google.oauth2 import id_token
from google.auth.transport import requests
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from rest_framework import generics, status, response
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from cloudinary.uploader import destroy
User = get_user_model()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


class UpdateProfileImageView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]

    def put(self, request):
        profile, _ = ProfileImage.objects.get_or_create(user=request.user)
        new_image = request.FILES.get("profile_image")

        if not new_image:
            return response.Response({"error": "Brak pliku."}, status=status.HTTP_400_BAD_REQUEST)

        # 🧹 Usunięcie starego zdjęcia z Cloudinary, jeśli istnieje
        old_image = profile.profile_image
        if old_image and hasattr(old_image, "public_id"):
            try:
                destroy(old_image.public_id)
            except Exception as e:
                print("⚠️ Błąd przy usuwaniu starego zdjęcia:", e)

        # 📤 Zapis nowego zdjęcia — automatyczny upload do Cloudinary
        profile.profile_image = new_image
        profile.save()

        serializer = ProfileImageSerializer(profile)
        return response.Response(serializer.data, status=status.HTTP_200_OK)

class CreateUserView(generics.ListCreateAPIView):
    queryset= User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AllowAny]

class MyTokenObtainPairView(TokenObtainPairView): 
    serializer_class = MyTokenObtainPairSerializer

class ProfileUpdateView(generics.UpdateAPIView):
    serializer_class = ProfileUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

class EmailUpdateView(generics.UpdateAPIView):
    serializer_class = EmailUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = request.user
        user.email = serializer.validated_data['email']
        user.save()
        return response.Response({"detail": "Email został zmieniony"}, status=status.HTTP_200_OK)

class PasswordChangeView(generics.UpdateAPIView):
    serializer_class = PasswordChangeSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response({"detail": "Hasło zostało zmienione"}, status=status.HTTP_200_OK)



class PasswordResetView(generics.GenericAPIView):
    serializer_class = PasswordResetSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return response.Response({"detail": "Email wysłany, jeśli użytkownik istnieje"}, status=200)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_link = f"http://localhost:5173/reset-password/{uid}/{token}/"
        
        send_mail(
            "Reset hasła",
            f"Kliknij w link aby zresetować hasło: {reset_link}",
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )

        return response.Response({"detail": "Email resetujący został wysłany"}, status=200)


class PasswordResetConfirmView(generics.GenericAPIView):
    serializer_class = PasswordResetConfirmSerializer
    permission_classes = [AllowAny]

    def post(self, request):
        print(request.data)  # <-- sprawdź, co faktycznie przychodzi
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return response.Response({"detail": "Hasło zostało zresetowane"}, status=200)


class GoogleAuthView(generics.GenericAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        token = request.data.get("credential")

        if not token:
            return response.Response({"error": "No token provided"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            idinfo = id_token.verify_oauth2_token(token, requests.Request(), os.getenv("CLIENT_ID"))
            email = idinfo.get("email")
            name = idinfo.get("name", "")
            google_picture = idinfo.get("picture")

            if not email:
                return response.Response({"error": "No email in token"}, status=status.HTTP_400_BAD_REQUEST)

            try:
                user = User.objects.get(email=email)
                created = False
            except User.DoesNotExist:
                user = User.objects.create_user(
                    username=email,
                    email=email,
                    first_name=name.split(" ")[0] if name else "",
                    last_name=" ".join(name.split(" ")[1:]) if name and len(name.split(" ")) > 1 else ""
                )
                created = True

            # 🔹 Szukamy zdjęcia profilowego (z modelu Profile, jeśli istnieje)
            profile_image_url = None

            if hasattr(user, "profile"):
                if getattr(user.profile, "profile_image", None):
                    try:
                        profile_image_url = user.profile.profile_image.url
                    except Exception:
                        profile_image_url = None

                elif getattr(user.profile, "photo", None):
                    try:
                        profile_image_url = user.profile.photo.url
                    except Exception:
                        profile_image_url = None

            # Jeśli brak zdjęcia w profilu, użyj zdjęcia z Google
            if not profile_image_url:
                profile_image_url = google_picture

            # 🔹 Tokeny JWT
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            return response.Response({
                "user": {
                    "id": user.id,
                    "email": user.email,
                    "username": user.username,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "is_staff": user.is_staff,     
                    "is_superuser": user.is_superuser,
                    "profile_image": profile_image_url,
                },
                "token": {
                    "access": access_token,
                    "refresh": str(refresh)
                },
                "created": created,
                "Auth": "Google"
            }, status=status.HTTP_200_OK)

        except ValueError:
            return response.Response({"error": "Invalid token"}, status=status.HTTP_403_FORBIDDEN)


class GenerateImage(generics.ListCreateAPIView):
    serializer_class = GenerateImageSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = ImagesPagination
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
            image_bytes = generate_image_from_prompt(
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

            filename = f"generated_{uuid.uuid4().hex}.png"
            generated_url = upload_image(
                            image_bytes,                     # bytes obrazu
                            "generated_images",
                            filename                           # nazwa pliku w Cloudinary
                        )
            # filename = os.path.basename(image_path)
            # input_path = os.path.join(BASE_DIR, "backend", "images", filename)
            # output_path = os.path.join(BASE_DIR, "backend", "images", f"extended_{filename}")
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


class CalendarUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Calendar.objects.filter(author=self.request.user)

    def update(self, request, *args, **kwargs):
        # print("=== UPDATE REQUEST DATA ===")
        # print("request.data:", request.data)
        # print("request.FILES:", request.FILES)
        # print("kwargs:", kwargs)
        # print("============================")

        calendar = self.get_object()
        old_calendar = Calendar.objects.get(author=self.request.user, id=kwargs["pk"])

        # kopia danych (dla bezpieczeństwa, QueryDict -> dict)
        data = request.data.copy()
        serializer = self.get_serializer(calendar, data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        # teraz konwersja ID → obiekt po walidacji
        top_image_id = serializer.validated_data.get("top_image")
        if isinstance(top_image_id, (int, str)):
            try:
                serializer.validated_data["top_image"] = GeneratedImage.objects.get(id=top_image_id)
            except GeneratedImage.DoesNotExist:
                return response.Response(
                    {"error": "Nie znaleziono obrazu o podanym ID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        

        # faktyczny update
        serializer.save()

         # --- AKTUALIZACJA POWIĄZANEGO YEAR_DATA ---
        year_data = old_calendar.year_data_id
        if year_data:
            try:
                year_data = CalendarYearData.objects.get(id=year_data)
            except CalendarYearData.DoesNotExist:
                return response.Response(
                    {"error": f"Nie znaleziono YearData o ID {year_data}"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            year_data_raw = data.get("year_data")

            if year_data_raw:
            # --- 1️⃣ Jeśli przyszło jako string JSON, parsujemy ---
                if isinstance(year_data_raw, str):
                    try:
                        year_data_obj = json.loads(year_data_raw)
                    except json.JSONDecodeError:
                        return response.Response(
                            {"error": "Niepoprawny format JSON w year_data"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    # już jest dict (np. przy JSON body zamiast FormData)
                    year_data_obj = year_data_raw
                    
        # --- 4️⃣ Aktualizujemy pola ---
                for field in ["text", "font", "weight", "size", "color", "position"]:
                    if field in year_data_obj:
                        setattr(year_data, field, year_data_obj[field])

                # --- 5️⃣ Zapis do bazy ---
                year_data.save()
        
    
        return response.Response(serializer.data, status=status.HTTP_200_OK)
    

class CalendarCreateView(generics.ListCreateAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CalendarPagination 


    def get_queryset(self):
        # select_related dla zwykłych FK/OneToOne
        qs = Calendar.objects.filter(author=self.request.user).select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        ).order_by("-created_at")

        # prefetch dla GenericForeignKey
        # field1
        field1_qs = CalendarMonthFieldText.objects.all()  # lub inny model, zależnie od typu
        qs = qs.prefetch_related(
            Prefetch(
                "field1",
                queryset=field1_qs,
                to_attr="prefetched_field1"
            )
        )

        # field2
        field2_qs = CalendarMonthFieldImage.objects.all()
        qs = qs.prefetch_related(
            Prefetch(
                "field2",
                queryset=field2_qs,
                to_attr="prefetched_field2"
            )
        )

        # field3
        field3_qs = CalendarMonthFieldText.objects.all()
        qs = qs.prefetch_related(
            Prefetch(
                "field3",
                queryset=field3_qs,
                to_attr="prefetched_field3"
            )
        )

        # bottom (może być BottomImage, BottomColor lub BottomGradient)
        bottom_models = [BottomImage, BottomColor, BottomGradient]
        for model in bottom_models:
            qs = qs.prefetch_related(
                Prefetch(
                    "bottom",
                    queryset=model.objects.all(),
                    to_attr=f"prefetched_bottom_{model.__name__}"
                )
            )


        image_for_field_qs = ImageForField.objects.filter(user=self.request.user)
        qs = qs.prefetch_related(
                Prefetch(
                    "imageforfield_set",  # reverse relacja z Calendar → ImageForField
                    queryset=image_for_field_qs,
                    to_attr="prefetched_images_for_fields"
                )
            )

        return qs

    def perform_create(self, serializer):
        data = self.request.data
        user = self.request.user
        name = data.get("name", "new calendar")
        
        image_from_disk = data.get("imageFromDisk", "false").lower() == "true"

        top_image_value = serializer.validated_data.get("top_image")

        if image_from_disk:
            if image_from_disk:
                if hasattr(top_image_value, "read"):  # UploadedFile
                    # odczyt obrazu bez zapisu na dysku
                    file_bytes = top_image_value.read()
                    filename = f"generated_{uuid.uuid4().hex}.png"
                    # odczyt wymiarów z pamięci
                    from PIL import Image
                    import io

                    with Image.open(io.BytesIO(file_bytes)) as img:
                        width, height = img.size
                        

                    # upload bezpośrednio z pamięci
                    generated_url = upload_image(
                        file_bytes,                    # bytes zamiast ścieżki
                        "generated_images",
                        filename
                    )
                    

                    # zapis w DB
                    image_instance = GeneratedImage.objects.create(
                        author=user,
                        width=width,
                        height=height,
                        url=generated_url
                    )
                    top_image_value = image_instance
                else:
                    raise ValidationError({"top_image": "Niepoprawny plik"})
        else:
            # Pobieramy istniejący GeneratedImage po ID
            try:
                image_instance = GeneratedImage.objects.get(id=top_image_value)
                top_image_value = image_instance
            except GeneratedImage.DoesNotExist:
                raise ValidationError({"top_image": "Nie znaleziono obrazu o podanym ID"})

        # --- 1. Tworzymy CalendarYearData ---
        year_data = None
        if data.get("yearText"):
            year_data = CalendarYearData.objects.create(
                author=user,
                text=data.get("yearText"),
                font=data.get("yearFontFamily"),
                weight=data.get("yearFontWeight"),
                size=str(data.get("yearFontSize")) if data.get("yearFontSize") else None,
                color=data.get("yearColor"),
                position=data.get("yearPositionX"),
                
            )

        # --- 2. Obsługa dolnej sekcji ---
        bottom_instance = None
        bottom_ct = None
        bottom_type = data.get("bottom_type")
        if bottom_type == "image":
            bottom_instance = BottomImage.objects.create(
                author=user,
                image_id=data.get("bottom_image")
            )
            bottom_ct = ContentType.objects.get_for_model(BottomImage)
        elif bottom_type == "color":
            bottom_instance = BottomColor.objects.create(
                author=user,
                color=data.get("bottom_color")
            )
            bottom_ct = ContentType.objects.get_for_model(BottomColor)
        else:
            bottom_instance = BottomGradient.objects.create(
                author=user,
                start_color=data.get("gradient_start_color"),
                end_color=data.get("gradient_end_color"),
                direction=data.get("gradient_direction"),
                theme=data.get("gradient_theme")
            )
            bottom_ct = ContentType.objects.get_for_model(BottomGradient)

        # --- 3. Tworzymy Calendar ---
        calendar = serializer.save(
            author=user,
            year_data=year_data,
            top_image=top_image_value,
            bottom_content_type=bottom_ct,
            bottom_object_id=bottom_instance.id if bottom_instance else None,
        )

        # --- 4. Obsługa field1/2/3 ---
        for i in range(1, 4):
            field_key = f"field{i}"
            items = data.getlist(field_key) if hasattr(data, "getlist") else data.get(field_key, [])
            for item in items:
                if isinstance(item, str):
                    try:
                        item = json.loads(item)  # bo FormData w axios może wysłać jako string
                    except Exception:
                        continue

                if "text" in item:
                    field_obj = CalendarMonthFieldText.objects.create(
                        author=user,
                        text=item["text"],
                        font=item.get("font", {}).get("fontFamily"),
                        weight=item.get("font", {}).get("fontWeight"),
                    )
                elif "image" in item:
                    field_obj = CalendarMonthFieldImage.objects.create(
                        author=user,
                        path=item["image"],
                        size=item.get("scale"),
                        position=item.get("positionX"),
                  
                    )
                else:
                    continue

                ct = ContentType.objects.get_for_model(field_obj)
                setattr(calendar, f"{field_key}_content_type", ct)
                setattr(calendar, f"{field_key}_object_id", field_obj.id)
                calendar.save()


        for i in range(1, 4): 
            raw = data.get(f"field{i}")  # bierzemy pierwszy element listy
            try:
                field_dict = json.loads(raw)       # zamiana stringa JSON na dict
            except json.JSONDecodeError:
                field_dict = {}
            image_is_true = field_dict.get("image", "false").lower() == "true"
            if image_is_true:
                # zakładam, że w request.FILES masz plik o kluczu np. "field1_image"
                
                file_obj = self.request.FILES.get(f"field{i}_image")  # <- FILES, nie data
                if file_obj:
                    file_bytes = file_obj.read()  # to są już bajty
                    filename = f"generated_{uuid.uuid4().hex}.png"
                    generated_url = upload_image(
                        file_bytes,   # używamy bytes, nie read() na bytes
                        "generated_images",
                        filename
                    )
                    print("Generated image URL:", generated_url)  
                    ImageForField.objects.create(
                    user=self.request.user,
                    calendar=calendar,       # Twój obiekt Calendar, który został zapisany wcześniej
                    field_number=i,
                    url=generated_url
                )

       
        print("Calendar created:", calendar.id)
        print("Payload:", data)


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

# 🔸 StylArtystyczny
class StylArtystycznyCreate(generics.ListCreateAPIView):
    queryset = StylArtystyczny.objects.all()
    serializer_class = StylArtystycznySerializer
    permission_classes = [IsAuthenticated]

class StylArtystycznyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = StylArtystyczny.objects.all()
    serializer_class = StylArtystycznySerializer
    permission_classes = [IsAuthenticated]


# 🔸 Kompozycja
class KompozycjaCreate(generics.ListCreateAPIView):
    queryset = Kompozycja.objects.all()
    serializer_class = KompozycjaSerializer
    permission_classes = [IsAuthenticated]

class KompozycjaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Kompozycja.objects.all()
    serializer_class = KompozycjaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Kolorystyka
class KolorystykaCreate(generics.ListCreateAPIView):
    queryset = Kolorystyka.objects.all()
    serializer_class = KolorystykaSerializer
    permission_classes = [IsAuthenticated]

class KolorystykaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Kolorystyka.objects.all()
    serializer_class = KolorystykaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Atmosfera
class AtmosferaCreate(generics.ListCreateAPIView):
    queryset = Atmosfera.objects.all()
    serializer_class = AtmosferaSerializer
    permission_classes = [IsAuthenticated]

class AtmosferaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Atmosfera.objects.all()
    serializer_class = AtmosferaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Inspiracja
class InspiracjaCreate(generics.ListCreateAPIView):
    queryset = Inspiracja.objects.all()
    serializer_class = InspiracjaSerializer
    permission_classes = [IsAuthenticated]

class InspiracjaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Inspiracja.objects.all()
    serializer_class = InspiracjaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Tło
class TloCreate(generics.ListCreateAPIView):
    queryset = Tlo.objects.all()
    serializer_class = TloSerializer
    permission_classes = [IsAuthenticated]

class TloDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tlo.objects.all()
    serializer_class = TloSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Perspektywa
class PerspektywaCreate(generics.ListCreateAPIView):
    queryset = Perspektywa.objects.all()
    serializer_class = PerspektywaSerializer
    permission_classes = [IsAuthenticated]

class PerspektywaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Perspektywa.objects.all()
    serializer_class = PerspektywaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Detale
class DetaleCreate(generics.ListCreateAPIView):
    queryset = Detale.objects.all()
    serializer_class = DetaleSerializer
    permission_classes = [IsAuthenticated]

class DetaleDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Detale.objects.all()
    serializer_class = DetaleSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Realizm
class RealizmCreate(generics.ListCreateAPIView):
    queryset = Realizm.objects.all()
    serializer_class = RealizmSerializer
    permission_classes = [IsAuthenticated]

class RealizmDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Realizm.objects.all()
    serializer_class = RealizmSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Styl Narracyjny
class StylNarracyjnyCreate(generics.ListCreateAPIView):
    queryset = StylNarracyjny.objects.all()
    serializer_class = StylNarracyjnySerializer
    permission_classes = [IsAuthenticated]

class StylNarracyjnyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = StylNarracyjny.objects.all()
    serializer_class = StylNarracyjnySerializer
    permission_classes = [IsAuthenticated]
