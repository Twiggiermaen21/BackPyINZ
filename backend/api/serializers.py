from django.contrib.auth.models import User
from rest_framework import serializers
from .models import *

class UserSerializer (serializers.ModelSerializer):
    class Meta:
        model = User
        fields =["id","username","password"]
        extra_kwargs={"password":{"write_only":True}}

    def create(self, validated_data):
        user=User.objects.create_user(**validated_data)
        return user
    
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
            "tlo", "perspektywa", "detale", "realizm", "styl_narracyjny"
        ]
        extra_kwargs = {
            "author": {"read_only": True},
            "width": {"read_only": True},
            "height": {"read_only": True},
            "url": {"read_only": True},
            "created_at": {"read_only": True},
        }
        
class CalendarSerializer(serializers.ModelSerializer):
    top_image_url = serializers.SerializerMethodField()
    bottom_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Calendar
        fields = [
            "id", "created_at", "author",
            "top_image", "top_image_url",
            "bottom_type", "bottom_image", "bottom_image_url",
            "bottom_color", "gradient_start_color", "gradient_end_color",
            "gradient_direction", "gradient_theme"
        ]
        read_only_fields = ["id", "created_at", "author", "top_image_url", "bottom_image_url"]

    def get_top_image_url(self, obj):
        return obj.top_image.url if obj.top_image and obj.top_image.url else None

    def get_bottom_image_url(self, obj):
        return obj.bottom_image.url if obj.bottom_image and obj.bottom_image.url else None

    def validate(self, data):
        bottom_type = data.get("bottom_type")

        if bottom_type == "image":
            if not data.get("bottom_image"):
                raise serializers.ValidationError({
                    "bottom_image": "Dla typu 'image' wymagane jest pole bottom_image."
                })

        elif bottom_type == "color":
            if not data.get("bottom_color"):
                raise serializers.ValidationError({
                    "bottom_color": "Dla typu 'color' wymagane jest pole bottom_color."
                })

        elif bottom_type == "gradient":
            missing = []
            if not data.get("gradient_start_color"):
                missing.append("gradient_start_color")
            if not data.get("gradient_end_color"):
                missing.append("gradient_end_color")
            if missing:
                raise serializers.ValidationError({
                    field: "To pole jest wymagane dla gradientu." for field in missing
                })

        elif bottom_type == "theme-gradient":
            if not data.get("gradient_theme"):
                raise serializers.ValidationError({
                    "gradient_theme": "Dla themed gradient wymagane jest gradient_theme."
                })

        return data


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