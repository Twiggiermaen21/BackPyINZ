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
    class Meta:
        model = BottomImage
        fields = ["id", "created_at", "author", "image"]
        read_only_fields = ["id", "created_at", "author"]

class BottomColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomColor
        fields = ["id", "created_at", "author", "color"]
        read_only_fields = ["id", "created_at", "author"]

class BottomGradientSerializer(serializers.ModelSerializer):
    class Meta:
        model = BottomGradient
        fields = ["id", "created_at", "author", "start_color", "end_color", "direction", "theme"]
        read_only_fields = ["id", "created_at", "author"]

        

class CalendarSerializer(serializers.ModelSerializer):
    year_data = serializers.SerializerMethodField()
    field1 = serializers.SerializerMethodField()
    field2 = serializers.SerializerMethodField()
    field3 = serializers.SerializerMethodField()
    bottom = serializers.SerializerMethodField()
    top_image_url = serializers.SerializerMethodField()

    class Meta:
        model = Calendar
        fields = [
            "id", "created_at", "author",
            "top_image", "top_image_url",
            "year_data",
            "field1", "field2", "field3",
            "bottom",
        ]
        read_only_fields = ["id", "created_at", "top_image_url"]

    # --- Top image url ---
    def get_top_image_url(self, obj):
        return getattr(obj.top_image, "url", None)

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

            # dodajemy content_type i id
            data.update({
                "content_type_id": ContentType.objects.get_for_model(item).id,
               
            })
            return data

        # lista / QuerySet
        if isinstance(instance, (list, tuple)):
            return [serialize_single(item) for item in instance]

        # pojedynczy obiekt
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

        # content_type i id
        data.update({
            "content_type_id": ContentType.objects.get_for_model(instance).id,
            
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