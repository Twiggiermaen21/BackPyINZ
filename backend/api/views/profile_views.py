
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated,  AllowAny
from ..models import *
from ..serializers import *
from ..pagination import *
from rest_framework import generics, status, response
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from cloudinary.uploader import destroy


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
    