from django.contrib.auth.models import User
from rest_framework import serializers
from django.contrib.auth.tokens import default_token_generator
from .models import *
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model, password_validation
from django.utils.http import urlsafe_base64_decode
from django.utils import timezone
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.core.exceptions import ValidationError as DjangoValidationError
from .models import CalendarProduction
User = get_user_model()


class ProfileImageSerializer(serializers.ModelSerializer):
    profile_image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProfileImage
        fields = ["id", "profile_image", "profile_image_url"]

    def get_profile_image_url(self, obj):
        return obj.profile_image.url if obj.profile_image else None


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile = ProfileImageSerializer(required=False)
    
    class Meta:
        model = User
        # dodajemy first_name i last_name
        fields = ["id", "username", "email", "first_name", "last_name", "password", 'profile']


    def validate_email(self, value):
        """Sprawdza, czy email jest unikalny."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Użytkownik z tym adresem e-mail już istnieje.")
        return value

    def create(self, validated_data):
        print("🔧 Tworzenie użytkownika z danymi:", validated_data)
        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data.get("email", ""),
            first_name=validated_data.get("first_name", ""),
            last_name=validated_data.get("last_name", ""),
            password=validated_data["password"],
        )

          # Ustawiamy użytkownika jako nieaktywny do czasu aktywacji
        user.is_active = False
        user.save()
        print("✅ Utworzono użytkownika:", user.username)
        return user



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
    new_password = serializers.CharField(style={'input_type': 'password'})

    def validate(self, attrs):
        # 1. Dekodowanie UID i pobieranie użytkownika
        try:
            uid = urlsafe_base64_decode(attrs["uid"]).decode()
            user = User.objects.get(pk=uid)
        except Exception:
            raise serializers.ValidationError("Nieprawidłowy link resetujący")

        # 2. Sprawdzanie tokenu
        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError("Token wygasł lub jest nieprawidłowy")

        # 3. WALIDACJA HASŁA (To jest nowa część)
        try:
            # validate_password sprawdza zasady zdefiniowane w settings.py (AUTH_PASSWORD_VALIDATORS)
            # Przekazujemy 'user', aby sprawdzić, czy hasło nie jest zbyt podobne do loginu
           password_validation.validate_password(attrs["new_password"], user)
        except DjangoValidationError as e:
            # Przekazujemy błędy z Django do DRF pod kluczem 'new_password'
            # Frontend otrzyma np.: { "new_password": ["Hasło jest zbyt podobne do nazwy użytkownika.", "Hasło jest zbyt krótkie."] }
            raise serializers.ValidationError({"new_password": list(e.messages)})

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
        user = self.user

        # domyślnie brak zdjęcia
        profile_image_url = None

        if hasattr(user, "profile"):
            # 1️⃣ najpierw sprawdź `profile_image`
            if getattr(user.profile, "profile_image", None):
                try:
                    profile_image_url = user.profile.profile_image.url
                except Exception:
                    profile_image_url = None

            # 2️⃣ jeśli nie ma `profile_image`, sprawdź `photo`
            elif getattr(user.profile, "photo", None):
                try:
                    profile_image_url = user.profile.photo.url
                except Exception:
                    profile_image_url = None

        # 3️⃣ aktualizujemy dane użytkownika
        data.update({
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "is_staff": user.is_staff,      
                "is_superuser": user.is_superuser,
                "profile_image": profile_image_url,  
            },
            "Auth": "Database"
        })

        return data

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


              # wszystkie inne pola są opcjonalne
            "prompt": {"required": False, "allow_blank": True, "allow_null": True},
            "styl_artystyczny": {"required": False, "allow_null": True},
            "kompozycja": {"required": False, "allow_null": True},
            "kolorystyka": {"required": False, "allow_null": True},
            "atmosfera": {"required": False, "allow_null": True},
            "inspiracja": {"required": False, "allow_null": True},
            "tlo": {"required": False, "allow_null": True},
            "perspektywa": {"required": False, "allow_null": True},
            "detale": {"required": False, "allow_null": True},
            "realizm": {"required": False, "allow_null": True},
            "styl_narracyjny": {"required": False, "allow_null": True},
        }
        
class CalendarMonthFieldTextSerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarMonthFieldText
        fields = ["id", "created_at", "author", "text", "font", "weight", "color", "size"]
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
        fields = ["id", "created_at", "author", "start_color", "end_color", "direction",  "theme"]
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
        if value is None:
            return None

        result = {}
        # spróbuj pobrać URL, jeśli jest ImageField
        try:
            result['url'] = value.url
        except Exception:
            result['url'] = None

        # spróbuj pobrać ID, jeśli istnieje
        try:
            result['id'] = value.id
        except AttributeError:
            # jeśli wartość to string/ID
            result['id'] = value

        return result

class CalendarSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = ['id', 'name']  

class ImageSearchSerializer(serializers.ModelSerializer):
    class Meta:
        model = GeneratedImage
        fields = ['id', 'name', ]

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
            "bottom", "images_for_fields", "name"
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
                "positionX": obj.year_data.positionX,
                "positionY": obj.year_data.positionY,
            }
        return None

    # --- Pomocnik do serializacji field ---
    def serialize_field(self, instance):
        if not instance:
            return None # Zmieniono z [] na None, bo pola field1-3 to pojedyncze obiekty

        # Ponieważ field1/2/3 to GenericForeignKey, to jest to POJEDYNCZY obiekt, nie lista.
        # Ale Twoja funkcja obsługuje oba przypadki, więc jest OK.
        
        def serialize_single(item):
            if isinstance(item, CalendarMonthFieldText):
                data = CalendarMonthFieldTextSerializer(item).data
            elif isinstance(item, CalendarMonthFieldImage):
                data = CalendarMonthFieldImageSerializer(item).data
            else:
                return None
            
            # Dodajemy content_type_id
            data.update({
                "content_type_id": ContentType.objects.get_for_model(item).id,
            })
            return data

        if isinstance(instance, (list, tuple)):
            return [serialize_single(item) for item in instance]
        
        return serialize_single(instance)

    # --- POPRAWIONE METODY DLA PÓL ---
    # Używamy bezpośrednio obj.field1, bo prefetch w widoku wypełnił to pole.
    
    def get_field1(self, obj):
        return self.serialize_field(obj.field1)

    def get_field2(self, obj):
        return self.serialize_field(obj.field2)

    def get_field3(self, obj):
        return self.serialize_field(obj.field3)

    # --- Bottom ---
    def get_bottom(self, obj):
        # Tutaj obj.bottom jest OK
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
    
    # --- Images for fields ---
    def get_images_for_fields(self, obj):
        # Próbujemy pobrać z prefetch (to_attr), a jak nie ma, to ze standardowego setu
        # Zakładam, że related_name w modelu ImageForField to 'imageforfield_set' (domyślne)
        # lub zdefiniowałeś inne.
        
        # Jeśli w widoku masz to_attr="prefetched_images_for_fields", to zadziała pierwsze.
        # Jeśli nie, zadziała drugie (dodatkowe zapytanie do bazy, chyba że prefetch był bez to_attr).
        
        items = getattr(obj, "prefetched_images_for_fields", getattr(obj, "imageforfield_set", []))
        
        # Jeśli items to Manager (np. imageforfield_set), musimy wywołać .all()
        if hasattr(items, 'all'):
             items = items.all()
             
        return [ImageForFieldSerializer(f).data for f in items]


class CalendarProductionSerializer(serializers.ModelSerializer):
    calendar_name = serializers.CharField(source='calendar.name', read_only=True)

    class Meta:
        model = CalendarProduction
        fields = [
            "id",
            "calendar",
            "calendar_name", 
            "status",
            "quantity",
            "deadline",
            "production_note",
            "created_at",
            "updated_at",
            "finished_at",
        ]
        read_only_fields = ["status", "created_at", "updated_at", "finished_at"]

    def create(self, validated_data):
        request = self.context["request"]
        validated_data["author"] = request.user
        validated_data["status"] = "waiting"   # spójne z frontendem
        return super().create(validated_data)

    def update(self, instance, validated_data):
        print("Updating CalendarProduction instance with data:", self.context["request"].data)

        status = self.context["request"].data.get("status", instance.status)
        instance.status = status

        # inne pola aktualizuj normalnie (jeśli kiedyś będą edytowane)
        instance.quantity = validated_data.get("quantity", instance.quantity)
        instance.deadline = validated_data.get("deadline", instance.deadline)
        instance.production_note = validated_data.get("production_note", instance.production_note)

        # ✅ AUTOMATYCZNE ZAKOŃCZENIE
        if status in ["done", "rejected"]:
            instance.finished_at = timezone.now()

        instance.save()
        return instance

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
        read_only_fields = ['id']
class KompozycjaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kompozycja
        fields = '__all__'
        read_only_fields = ['id']
class KolorystykaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Kolorystyka
        fields = '__all__'
        read_only_fields = ['id']
class AtmosferaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Atmosfera
        fields = '__all__'
        read_only_fields = ['id']
class InspiracjaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inspiracja
        fields = '__all__'
        read_only_fields = ['id']
class TloSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tlo
        fields = '__all__'
        read_only_fields = ['id']
class PerspektywaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Perspektywa
        fields = '__all__'
        read_only_fields = ['id']
class DetaleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Detale
        fields = '__all__'
        read_only_fields = ['id']
class RealizmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Realizm
        fields = '__all__'
        read_only_fields = ['id']
class StylNarracyjnySerializer(serializers.ModelSerializer):
    class Meta:
        model = StylNarracyjny
        fields = '__all__'  
        read_only_fields = ['id']