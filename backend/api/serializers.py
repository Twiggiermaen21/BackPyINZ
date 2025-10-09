from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from .models import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, password_validation
from django.utils.http import urlsafe_base64_decode
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        # dodajemy first_name i last_name
        fields = ["id", "username", "email", "first_name", "last_name", "password"]

    def create(self, validated_data):
        # tworzymy usera z dodatkowym polami first_name, last_name i email
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
        )
        return user
User = get_user_model()


class ProfileUpdateSerializer(serializers.ModelSerializer):
    username = serializers.CharField(required=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "username"]

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username=value).exists():
            raise serializers.ValidationError("Nazwa użytkownika jest już zajęta.")
        return value

class EmailUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email już jest zajęty.")
        return value

class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Aktualne hasło jest nieprawidłowe")
        return value

    def validate_new_password(self, value):
        password_validation.validate_password(value)
        return value

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
class PasswordResetSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=6)

    def validate(self, attrs):
        try:
            uid = urlsafe_base64_decode(attrs["uid"]).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            raise serializers.ValidationError("Nieprawidłowy link resetujący")

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Token wygasł lub jest nieprawidłowy")

        attrs["user"] = user
        return attrs

    def save(self, **kwargs):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save()
        return user

class SendEmailSerializer(serializers.Serializer):
    email = serializers.EmailField()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        print(self.user.id)
        print(self.user.username)
        # dodajemy własne dane usera do odpowiedzi
        data.update({
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "email": self.user.email,
                "first_name": self.user.first_name,
                "last_name": self.user.last_name,
                "photo": self.user.profile.photo.url if hasattr(self.user, 'profile') and self.user.profile.photo else None,
            },
            "Auth": "Database"
        })

        return data


class NoteSerializer(serializers.ModelSerializer):
    class Meta:
            model = Note
            fields =["id","title","content","created_at","author"]
            extra_kwargs ={"author":{"read_only":True}}

class GenerateImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = [
            "id", "author", "prompt", "width", "height", "url", "created_at",
            "styl_artystyczny", "kompozycja", "kolorystyka", "atmosfera", "inspiracja",
            "tlo", "perspektywa", "detale", "realizm", "styl_narracyjny", "name"
        ]
        extra_kwargs = {
            "author": {"read_only": True},
            "width": {"read_only": True},
            "height": {"read_only": True},
            "url": {"read_only": True},
            "created_at": {"read_only": True},
        }
        
class CalendarMonthFieldTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarMonthFieldText
        fields = ["id", "created_at", "author", "text", "font", "weight"]
        read_only_fields = ["id", "created_at", "author"]

class CalendarMonthFieldImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarMonthFieldImage
        fields = ["id", "created_at", "author", "path", "positionX", "positionY", "size"]
        read_only_fields = ["id", "created_at", "author"]

class CalendarYearDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarYearData
        fields = ["id", "text", "font", "weight", "size", "color", "positionX", "positionY"]
        read_only_fields = ["id", "created_at", "author"]

class BottomImageSerializer(serializers.ModelSerializer):
    url = serializers.ImageField(source='image', read_only=True)

    class Meta:
        model = BottomImage
        fields = ["id", "created_at", "author", "image", "url"]
        read_only_fields = ["id", "created_at", "author"]

class BottomColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomColor
        fields = ["id", "created_at", "author", "color"]
        read_only_fields = ["id", "created_at", "author"]

class BottomGradientSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomGradient
        fields = ["id", "created_at", "author", "start_color", "end_color", "direction", "strength", "theme"]
        read_only_fields = ["id", "created_at", "author"]


class ImageForFieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImageForField
        fields = ['id', 'user', 'calendar', 'field_number', 'url', 'created_at']
        read_only_fields = ['id', 'user', 'created_at']

class TopImageField(serializers.Field):
    """
    Pole, które przyjmuje:
    - Plik (UploadedFile)
    - ID istniejącego obrazka (string/int)
    """

    def to_internal_value(self, data):
        if hasattr(data, "read"):
            # to jest plik
            return data
        # traktujemy jako ID
        return str(data)

    def to_representation(self, value):
        try:
            # jeśli jest plikiem ImageField w modelu, zwracamy URL
            return value.url
        except Exception:
            # jeśli ID lub string
            return value        

class CalendarSerializer(serializers.ModelSerializer):
    top_image = TopImageField(required=False, allow_null=True)
    top_image_url = serializers.SerializerMethodField()
    year_data = serializers.SerializerMethodField()
    field1 = serializers.SerializerMethodField()
    field2 = serializers.SerializerMethodField()
    field3 = serializers.SerializerMethodField()
    bottom = serializers.SerializerMethodField()
    images_for_fields = serializers.SerializerMethodField() 

    class Meta:
        model = Calendar
        fields = [
            "id", "created_at", "author",
            "top_image", "top_image_url",
            "year_data", "field1", "field2", "field3",
            "bottom","images_for_fields","name"
        ]
        read_only_fields = ["id", "created_at", "top_image_url"]

    # --- Top image URL ---
    def get_top_image_url(self, obj):
        if hasattr(obj.top_image, "url"):
            return obj.top_image.url
        return None

    # --- Year data ---
    def get_year_data(self, obj):
        if obj.year_data:
            return {
                "id": obj.year_data.id,
                "text": obj.year_data.text,
                "font": obj.year_data.font,
                "weight": obj.year_data.weight,
                "size": obj.year_data.size,
                "color": obj.year_data.color,
                "positionX": getattr(obj.year_data, "positionX", None),
                "positionY": getattr(obj.year_data, "positionY", None),
            }
        return None

    # --- Pomocnik do serializacji field ---
    def serialize_field(self, instance):
        if not instance:
            return []

        def serialize_single(item):
            if isinstance(item, CalendarMonthFieldText):
                data = CalendarMonthFieldTextSerializer(item).data
            elif isinstance(item, CalendarMonthFieldImage):
                data = CalendarMonthFieldImageSerializer(item).data
            else:
                return None
            data.update({
                "content_type_id": ContentType.objects.get_for_model(item).id,
            })
            return data

        if isinstance(instance, (list, tuple)):
            return [serialize_single(item) for item in instance]
        return serialize_single(instance)

    # --- Pola field1 / field2 / field3 ---
    def get_field1(self, obj):
        return self.serialize_field(getattr(obj, "prefetched_field1", None))

    def get_field2(self, obj):
        return self.serialize_field(getattr(obj, "prefetched_field2", None))

    def get_field3(self, obj):
        return self.serialize_field(getattr(obj, "prefetched_field3", None))

    # --- Bottom ---
    def get_bottom(self, obj):
        instance = getattr(obj, "bottom", None)
        if not instance:
            return None

        if isinstance(instance, BottomImage):
            data = BottomImageSerializer(instance).data
        elif isinstance(instance, BottomColor):
            data = BottomColorSerializer(instance).data
        elif isinstance(instance, BottomGradient):
            data = BottomGradientSerializer(instance).data
        else:
            return None

        data.update({
            "content_type_id": ContentType.objects.get_for_model(instance).id,
        })
        return data
    
    def get_images_for_fields(self, obj):
        return [ImageForFieldSerializer(f).data for f in getattr(obj, "prefetched_images_for_fields", [])]

class OutpaintingSDXLSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutpaintingSDXL
        fields = '__all__'
        extra_kwargs = {
                       "output_file":{"read_only":True},
                       "output_format":{"read_only":True},
                       "right":{"read_only":True},
                       "left":{"read_only":True},
                       "up":{"read_only":True},
                       "down":{"read_only":True}}

class UpscalingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Upscaling
        fields = '__all__'
        extra_kwargs = {
            "output_file": {"read_only": True},
            "upscale_factor": {"read_only": True},
            "created_at": {"read_only": True}
        }


class StylArtystycznySerializer(serializers.ModelSerializer):
    class Meta:
        model = StylArtystyczny
        fields = '__all__'

class KompozycjaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kompozycja
        fields = '__all__'

class KolorystykaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kolorystyka
        fields = '__all__'

class AtmosferaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atmosfera
        fields = '__all__'

class InspiracjaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inspiracja
        fields = '__all__'

class TloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tlo
        fields = '__all__'

class PerspektywaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perspektywa
        fields = '__all__'

class DetaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detale
        fields = '__all__'

class RealizmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Realizm
        fields = '__all__'

class StylNarracyjnySerializer(serializers.ModelSerializer):
    class Meta:
        model = StylNarracyjny
        fields = '__all__'