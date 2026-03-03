import io
import shutil
import uuid
from django.contrib.contenttypes.models import ContentType
from django.http import FileResponse, Http404
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from ..models import *
from ..serializers import *
from ..pagination import *
from ..utils.cloudinary_upload import upload_image
from rest_framework.exceptions import ValidationError
import json
from rest_framework import generics, status, response, permissions
from django.conf import settings
import os
from ..utils.services import (
    fetch_calendar_data,
    generate_calendar, 
    get_year_data, 
    handle_field_data, 
    handle_bottom_data,
    handle_top_image)
from ..utils.upscaling import upscale_image_with_bigjpg
import zipfile
from django.db import close_old_connections 

class CalendarDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Calendar.objects.filter(author=self.request.user)

class CalendarUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Calendar.objects.filter(author=self.request.user)

    def update(self, request, *args, **kwargs):
    

        calendar = self.get_object()
        old_calendar = Calendar.objects.get(author=self.request.user, id=kwargs["pk"])

        data = request.data.copy()
        serializer = self.get_serializer(calendar, data=data, partial=True)
        serializer.is_valid(raise_exception=True)

        top_image_id = serializer.validated_data.get("top_image")
        if isinstance(top_image_id, (int, str)):
            try:
                serializer.validated_data["top_image"] = GeneratedImage.objects.get(id=top_image_id)
            except GeneratedImage.DoesNotExist:
                return response.Response(
                    {"error": "Nie znaleziono obrazu o podanym ID"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        
        serializer.save()
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
                if isinstance(year_data_raw, str):
                    try:
                        year_data_obj = json.loads(year_data_raw)
                    except json.JSONDecodeError:
                        return response.Response(
                            {"error": "Niepoprawny format JSON w year_data"},
                            status=status.HTTP_400_BAD_REQUEST,
                        )
                else:
                    year_data_obj = year_data_raw
                    
                for field in ["text", "font", "weight", "size", "color", "positionX", "positionY"]:
                    if field in year_data_obj:
                        setattr(year_data, field, year_data_obj[field])

                year_data.save()
        
    
        return response.Response(serializer.data, status=status.HTTP_200_OK)
    

class CalendarByProjectView(generics.ListAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "project_name"

    def get_queryset(self):
        user = self.request.user
        project_name = self.kwargs.get("project_name")
        qs = Calendar.objects.filter(  author=user, name=project_name  )

        qs = qs.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )


        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom"
        )

        return qs

class CalendarByIdView(generics.RetrieveAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = "pk" 

    def get_queryset(self):
        qs = Calendar.objects.filter(author=self.request.user)
        qs = qs.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom" 
        )

        return qs


class CalendarCreateView(generics.ListCreateAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CalendarPagination 

    def get_queryset(self):
       
        qs = Calendar.objects.filter(author=self.request.user).select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        ).order_by("-created_at")

        
        
        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom"  
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
                if hasattr(top_image_value, "read"):  
                    
                    file_bytes = top_image_value.read()
                    filename = f"generated_{uuid.uuid4().hex}.png"
                    
                    from PIL import Image
                    import io

                    with Image.open(io.BytesIO(file_bytes)) as img:
                        width, height = img.size

                    generated_url = upload_image(
                        file_bytes,                    
                        "generated_images",
                        filename
                    )
                    
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
                positionX=data.get("yearPositionX"),
                positionY=data.get("yearPositionY"),
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
            file_key = f"field{i}_image"
            raw_data = data.get(field_key)
            item_data = {}

            if raw_data:
                if isinstance(raw_data, str):
                    try:
                        item_data = json.loads(raw_data)
                    except ValueError:
                        item_data = {}
                elif isinstance(raw_data, dict):
                    item_data = raw_data

            uploaded_file = self.request.FILES.get(file_key)
            final_image_path = item_data.get("image")  

            if uploaded_file:
                file_bytes = uploaded_file.read()
                filename = f"generated_{uuid.uuid4().hex}.png"
                generated_url = upload_image(
                    file_bytes,
                    "generated_images",
                    filename
                )
                final_image_path = generated_url

            field_obj = None
            if "text" in item_data and not uploaded_file:
                field_obj = CalendarMonthFieldText.objects.create(
                    author=user,
                    text=item_data["text"],
                    font=item_data.get("font", {}).get("fontFamily"),
                    weight=item_data.get("font", {}).get("fontWeight"),
                    color=item_data.get("font", {}).get("fontColor"),
                    size=item_data.get("font", {}).get("fontSize"),
                )

         
            elif final_image_path:
                field_obj = CalendarMonthFieldImage.objects.create(
                    author=user,
                    path=final_image_path,  
                    size=item_data.get("scale"),
                    positionX=item_data.get("positionX"),
                    positionY=item_data.get("positionY"),
                )

      
            if field_obj:
                ct = ContentType.objects.get_for_model(field_obj)
                setattr(calendar, f"{field_key}_content_type", ct)
                setattr(calendar, f"{field_key}_object_id", field_obj.id)
                calendar.save()

class CalendarSearchBarView(generics.ListAPIView):
    serializer_class = CalendarSearchSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None 

    def get_queryset(self):
        
        return Calendar.objects.filter(
            author=self.request.user,
                ).order_by("-created_at")


class CalendarPrint(generics.CreateAPIView): 

    def create(self, request, *args, **kwargs):
        try:
            calendar_id = request.data.get("id_kalendarz")
            production_id = request.data.get("id_production")
            if not calendar_id:
                return Response({"error": "Brak id_kalendarz"}, status=400)

            calendar = fetch_calendar_data(calendar_id)
            if not calendar:
                return Response({"error": f"Nie znaleziono kalendarza {calendar_id}"}, status=404)

            temp_dir = os.path.join(settings.MEDIA_ROOT, "calendar_temp", str(uuid.uuid4()))
            os.makedirs(temp_dir, exist_ok=True)

            data = {
                "calendar_id": calendar.id,
                "author": str(calendar.author),
                "created_at": str(calendar.created_at),
                "fields": {},
                "bottom": None,
                "top_image": None,
                "year": get_year_data(calendar),
            }

            data["top_image"] = handle_top_image(calendar, temp_dir)
            data["bottom"] = handle_bottom_data(calendar.bottom, temp_dir)

            all_fields = []
            for i in range(1, 4):
                all_fields.append((getattr(calendar, f"field{i}", None), i))
            for img in getattr(calendar, "prefetched_images_for_fields", []):
                all_fields.append((img, f"prefetched_image_{img.id}"))
            for field_obj, field_name in all_fields:
                data["fields"][field_name] = handle_field_data(field_obj, field_name, temp_dir)

            upscaled_header_path = None
            if data["top_image"]:
                result = upscale_image_with_bigjpg(data["top_image"], temp_dir, 4)
                upscaled_header_path = result["local_upscaled"]

            if data["bottom"] and data["bottom"].get("type") == "image":
                result = upscale_image_with_bigjpg(data["bottom"]["url"], temp_dir, 8)
                data["bottom"]["image_path"] = result["local_upscaled"]


            calendar_files = generate_calendar(
                data=data,
                top_image_path=data["top_image"],
                upscaled_top_path=upscaled_header_path,
                production_id=production_id,
            )


            close_old_connections()
            
            try:
                production = CalendarProduction.objects.get(id=production_id)
                production.status = "done"
                production.finished_at = timezone.now()
                production.save()
                print(f"✅ Produkcja {production_id} → done")
            except CalendarProduction.DoesNotExist:
                print(f"⚠️ Nie znaleziono produkcji {production_id}")


            try:
                shutil.rmtree(temp_dir)
            except OSError:
                pass

            return Response({
                "message": "Kalendarz wygenerowany — dwa pliki PSD.",
                "export_dir": calendar_files["export_dir"],
                "header_path": calendar_files["header"],
                "backing_path": calendar_files["backing"],
            })

        except Exception as e:
            close_old_connections()
            print(f"❌ Błąd: {e}")
            import traceback
            traceback.print_exc()
            return Response({"error": str(e)}, status=500)
        
class CalendarProductionRetrieveDestroy(generics.RetrieveDestroyAPIView):
    serializer_class = CalendarProductionSerializer
    permission_classes = [IsAuthenticated]

    lookup_field = 'pk' 
    
    def get_queryset(self):
        
        user = self.request.user
        return (
            CalendarProduction.objects
            .filter(author=user)
            .select_related("calendar", "author")
        )


class CalendarProductionList(generics.ListCreateAPIView):
    serializer_class = CalendarProductionSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CalendarPagination

    def get_queryset(self):
        user = self.request.user
        return (
            CalendarProduction.objects
            .filter(author=user)
            .select_related("calendar", "author")
            .order_by("-created_at")
        )

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)




class CalendarProductionStaffList(generics.ListAPIView):
    serializer_class = CalendarProductionSerializer
    permission_classes = [IsAuthenticated,IsAdminUser]
    pagination_class = CalendarPagination

    def get_queryset(self):
        return (
            CalendarProduction.objects
            .select_related("calendar", "author")
            .order_by("-created_at")
        )

    
class StaffCalendarProductionRetrieveUpdate(generics.RetrieveUpdateAPIView):
    serializer_class = CalendarProductionSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    lookup_field = 'pk'
    
    def get_queryset(self):
        return CalendarProduction.objects.all()

    def perform_update(self, serializer):
        print( "StaffCalendarProductionRetrieveUpdate view initialized" )
        serializer.save()

class CalendarByIdStaffView(generics.RetrieveAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated] 
    lookup_field = "pk"

    def get_queryset(self):
        qs = Calendar.objects.all()
        qs = qs.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom"
        )
        return qs
    

class DownloadCalendarStaffView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk, format=None):
        calendar_dir = os.path.join(settings.MEDIA_ROOT, 'calendar_exports', f"calendar_{pk}")

        if not os.path.exists(calendar_dir) or not os.path.isdir(calendar_dir):
            print(f"BŁĄD: Nie znaleziono folderu: {calendar_dir}")
            raise Http404(f"Nie znaleziono folderu dla kalendarza: calendar_{pk}")

        zip_buffer = io.BytesIO()
        files_found = False

        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for filename in os.listdir(calendar_dir):
                file_path = os.path.join(calendar_dir, filename)
                if os.path.isfile(file_path):
                    zip_file.write(file_path, arcname=filename)
                    files_found = True

        if not files_found:
             raise Http404("Folder kalendarza jest pusty.")

        zip_buffer.seek(0)
        final_zip_filename = f"calendar_{pk}_package.zip"

        response = FileResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = f'attachment; filename="{final_zip_filename}"'
        response['Access-Control-Expose-Headers'] = 'Content-Disposition'

        return response