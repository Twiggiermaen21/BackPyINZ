
import uuid
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated,  AllowAny
from rest_framework_simplejwt.views import TokenObtainPairView
from ..models import *
from ..serializers import *
from ..pagination import *
from ..utils.generation import generate_image_from_prompt
from ..utils.upscaling import upscale_image_with_bigjpg
from ..utils.cloudinary_upload import upload_image
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
