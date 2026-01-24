import uuid
from django.contrib.contenttypes.models import ContentType
from django.db.models import Prefetch
from rest_framework.permissions import IsAuthenticated
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
    get_year_data, 
    handle_field_data, 
    handle_bottom_data,
    handle_top_image,
    process_top_image_with_year,
      process_calendar_bottom)
from ..utils.upscaling import upscale_image_with_bigjpg



class CalendarDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Calendar.objects.all()
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # ograniczamy do kalendarzy użytkownika
        
        return Calendar.objects.filter(author=self.request.user)

class CalendarUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Calendar.objects.filter(author=self.request.user)

    def update(self, request, *args, **kwargs):
    

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
                for field in ["text", "font", "weight", "size", "color", "positionX", "positionY"]:
                    if field in year_data_obj:
                        setattr(year_data, field, year_data_obj[field])

                # --- 5️⃣ Zapis do bazy ---
                year_data.save()
        
    
        return response.Response(serializer.data, status=status.HTTP_200_OK)
    

class CalendarByProjectView(generics.ListAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]

    lookup_url_kwarg = "project_name"

    def get_queryset(self):
        user = self.request.user
        name = self.kwargs.get("project_name")  # teraz to nazwa, nie id
        qs = Calendar.objects.filter(
            author=user,
            name=name
        ).select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        qs = qs.prefetch_related(
            Prefetch("field1", queryset=CalendarMonthFieldText.objects.all()),
            Prefetch("field2", queryset=CalendarMonthFieldImage.objects.all()),
            Prefetch("field3", queryset=CalendarMonthFieldText.objects.all()),
        )

        # POPRAWIONE
        qs = qs.prefetch_related(
            Prefetch("bottom", queryset=BottomImage.objects.all(), to_attr="bottom_images"),
            Prefetch("bottom", queryset=BottomColor.objects.all(), to_attr="bottom_colors"),
            Prefetch("bottom", queryset=BottomGradient.objects.all(), to_attr="bottom_gradients"),
        )

        qs = qs.prefetch_related(
            Prefetch(
                "imageforfield_set",
                queryset=ImageForField.objects.filter(user=user),
                to_attr="prefetched_images_for_fields",
            )
        )

   

        print(qs.query)
        return qs


class CalendarByIdView(generics.RetrieveAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "pk"   # domyślnie może być też 'pk'

    def get_queryset(self, request, *args, **kwargs):
        user = self.request.user

        qs = Calendar.objects.filter(author=user, id=kwargs["pk"]).select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        qs = qs.prefetch_related(
            Prefetch("field1", queryset=CalendarMonthFieldText.objects.all()),
            Prefetch("field2", queryset=CalendarMonthFieldImage.objects.all()),
            Prefetch("field3", queryset=CalendarMonthFieldText.objects.all()),
        )

        qs = qs.prefetch_related(
            Prefetch("bottom", queryset=BottomImage.objects.all(), to_attr="bottom_images"),
            Prefetch("bottom", queryset=BottomColor.objects.all(), to_attr="bottom_colors"),
            Prefetch("bottom", queryset=BottomGradient.objects.all(), to_attr="bottom_gradients"),
        )

        qs = qs.prefetch_related(
            Prefetch(
                "imageforfield_set",
                queryset=ImageForField.objects.filter(user=user),
                to_attr="prefetched_images_for_fields",
            )
        )

        return qs


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
        print("dada",data)
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
                        color=item.get("font", {}).get("fontColor"),
                        size =item.get("font", {}).get("fontSize"),
                       
                    )
                elif "image" in item:
                    field_obj = CalendarMonthFieldImage.objects.create(
                        author=user,
                        path=item["image"],
                        size=item.get("scale"),
                        positionX=item.get("positionX"),
                        positionY=item.get("positionY"),
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
                    
                    ImageForField.objects.create(
                    user=self.request.user,
                    calendar=calendar,       # Twój obiekt Calendar, który został zapisany wcześniej
                    field_number=i,
                    url=generated_url
                )

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
            if not calendar_id:
                return Response({"error": "Brak id_kalendarz w danych żądania"}, status=400)

            # 1. Pobieranie danych kalendarza
            calendar = fetch_calendar_data(calendar_id)
            if not calendar:
                return Response({"error": f"Nie znaleziono kalendarza o id {calendar_id}"}, status=404)

            # 2. Tworzenie katalogu eksportu
            export_dir = os.path.join(settings.MEDIA_ROOT, "calendar_exports", str(uuid.uuid4()))
            os.makedirs(export_dir, exist_ok=True)
            print(f"📁 Utworzono katalog eksportu: {export_dir}")


            # 3. Przygotowanie struktury danych JSON
            data = {
                "calendar_id": calendar.id,
                "author": str(calendar.author),
                "created_at": str(calendar.created_at),
                "fields": {},
                "bottom": None,
                "top_image": None,
                "year": get_year_data(calendar), # Pobieranie danych roku
            }

            # 4. Obsługa Top Image (pobieranie lokalne, jeśli ma być naniesiony rok)
            # data["top_image"] będzie albo URL, albo lokalną ścieżką
            data["top_image"] = handle_top_image(calendar, export_dir)


            # 5. Obsługa Bottom (obraz, kolor, gradient)
            data["bottom"] = handle_bottom_data(calendar.bottom, export_dir)
            # 6. Obsługa pól (Field1-3 + prefetched)
            all_fields = []
            for i in range(1, 4):
                all_fields.append((getattr(calendar, f"field{i}", None), i)) 
            
            for img in getattr(calendar, "prefetched_images_for_fields", []):
                all_fields.append((img, f"prefetched_image_{img.id}"))

            for field_obj, field_name in all_fields:
                data["fields"][field_name] = handle_field_data(field_obj, field_name, export_dir)


            # 8. Zapis JSON
            json_path = os.path.join(export_dir, "data.json")
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

            with open(json_path, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
            
            if (loaded_data["top_image"] ):
                result = upscale_image_with_bigjpg(loaded_data["top_image"],export_dir)
                upscaled_path = result["local_upscaled"]
                print(f"Ścieżka do pliku: {upscaled_path}")
            if (loaded_data["bottom"]['type'] == 'image' ):
                result = upscale_image_with_bigjpg(loaded_data["bottom"]["url"],export_dir)
                data["bottom"]["image_path"] = result["local_upscaled"]
            # 7. Rysowanie tekstu roku na Top Image i upload do Cloudinary
            if data["top_image"] and data.get("year"):
                process_top_image_with_year(upscaled_path, data,)
                
            # 8. Nanoszenie fileds na bottom 
                process_calendar_bottom(data,upscaled_path)

            return Response({
                "message": "Dane kalendarza zostały przetworzone, a obraz wgrany do Cloudinary.",
                "folder": export_dir,
                "json_path": json_path,
                "top_image_final_url": data["top_image"] # Końcowy URL obrazu z naniesionym rokiem
            })

        except Exception as e:
            print("❌ Nieoczekiwany błąd:", e)
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


class IsStaffPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class CalendarProductionStaffList(generics.ListAPIView):
    serializer_class = CalendarProductionSerializer
    permission_classes = [IsAuthenticated,IsStaffPermission]
    pagination_class = CalendarPagination

    def get_queryset(self):
        return (
            CalendarProduction.objects
            .select_related("calendar", "author")
            .order_by("-created_at")
        )

    
class StaffCalendarProductionRetrieveUpdate(generics.RetrieveUpdateAPIView):
    serializer_class = CalendarProductionSerializer
    permission_classes = [IsAuthenticated, IsStaffPermission]
    lookup_field = 'pk'

   

    def get_queryset(self):
        return CalendarProduction.objects.all()

    def perform_update(self, serializer):
        print( "StaffCalendarProductionRetrieveUpdate view initialized" )
        print(self.request.data)
   
   
        # automatycznie zaktualizuje updated_at dzięki auto_now=True w modelu
        serializer.save()


class CalendarByIdStaffView(generics.RetrieveAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    lookup_url_kwarg = "pk"   # domyślnie może być też 'pk'

    def get_queryset(self):
      
        qs = Calendar.objects.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        qs = qs.prefetch_related(
            Prefetch("field1", queryset=CalendarMonthFieldText.objects.all()),
            Prefetch("field2", queryset=CalendarMonthFieldImage.objects.all()),
            Prefetch("field3", queryset=CalendarMonthFieldText.objects.all()),
        )

        qs = qs.prefetch_related(
            Prefetch("bottom", queryset=BottomImage.objects.all(), to_attr="bottom_images"),
            Prefetch("bottom", queryset=BottomColor.objects.all(), to_attr="bottom_colors"),
            Prefetch("bottom", queryset=BottomGradient.objects.all(), to_attr="bottom_gradients"),
        )

        qs = qs.prefetch_related(
            Prefetch(
                "imageforfield_set",
               queryset=ImageForField.objects.all(),
                to_attr="prefetched_images_for_fields",
            )
        )

        return qs
