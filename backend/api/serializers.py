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
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = BottomImage
        fields = ["id", "image", "image_url"]

    def get_image_url(self, obj):
        return getattr(obj.image, "url", None)


class BottomColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomColor
        fields = ["id", "color"]


class BottomGradientSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomGradient
        fields = ["id", "start_color", "end_color", "direction", "theme"]

        

class CalendarSerializer(serializers.ModelSerializer):
    top_image_url = serializers.SerializerMethodField()
    year_data = CalendarYearDataSerializer(read_only=True)
    bottom = serializers.SerializerMethodField()

    class Meta:
        model = Calendar
        fields = [
            "id", "created_at", "author",
            "top_image", "top_image_url",
            "year_data",
            "field1_object_id", "field2_object_id", "field3_object_id",
            "bottom_content_type", "bottom_object_id", "bottom",
        ]
        read_only_fields = ["id", "created_at", "author", "top_image_url", "bottom"]

    def get_top_image_url(self, obj):
        return getattr(obj.top_image, "url", None)

    def get_bottom(self, obj):
        if isinstance(obj.bottom, BottomImage):
            return BottomImageSerializer(obj.bottom).data
        elif isinstance(obj.bottom, BottomColor):
            return BottomColorSerializer(obj.bottom).data
        elif isinstance(obj.bottom, BottomGradient):
            return BottomGradientSerializer(obj.bottom).data
        return None


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