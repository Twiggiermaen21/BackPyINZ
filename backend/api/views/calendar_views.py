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
    
    # lookup_url_kwarg jest używany głównie w RetrieveAPIView (do pobrania jednego obiektu),
    # ale w ListAPIView pobieramy go ręcznie w get_queryset, więc ta linijka jest opcjonalna,
    # choć nie szkodzi.
    lookup_url_kwarg = "project_name"

    def get_queryset(self):
        user = self.request.user
        project_name = self.kwargs.get("project_name")

        # 1. Filtrowanie po autorze i nazwie projektu
        qs = Calendar.objects.filter(
            author=user,
            name=project_name
        )

        # 2. select_related
        # Pobieramy relacje FK oraz ContentType, aby Django wiedziało od razu,
        # w jakich tabelach szukać danych dla GenericForeignKey.
        qs = qs.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        # 3. prefetch_related
        # Wystarczy podać nazwy pól GenericForeignKey.
        # Django automatycznie pobierze dane z odpowiednich tabel (Text/Image dla fieldX,
        # oraz Color/Image/Gradient dla bottom) i przypisze je do obiektów.
        # Usuwamy 'to_attr' i sztywne QuerySety, bo ograniczałyby one typy pól.
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
    lookup_field = "pk"  # Domyślne, ale dla jasności zostawiamy

    def get_queryset(self):
        # 1. Podstawowe filtrowanie po autorze
        # Nie musisz filtrować po ID tutaj - RetrieveAPIView zrobi to automatycznie na końcu
        qs = Calendar.objects.filter(author=self.request.user)

        # 2. select_related
        # Pobieramy relacje 1-do-1 oraz ContentType dla pól generycznych
        qs = qs.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        # 3. prefetch_related
        # Wystarczy podać nazwy pól. Django automatycznie sprawdzi ContentType
        # i pobierze odpowiednie obiekty (CalendarMonthFieldText LUB CalendarMonthFieldImage)
        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom"  # To obsłuży BottomImage, BottomColor i BottomGradient
        )

        return qs


class CalendarCreateView(generics.ListCreateAPIView):
    serializer_class = CalendarSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CalendarPagination 

    def get_queryset(self):
        # 1. select_related
        # Pobieramy "sztywne" relacje oraz ContentType dla pól generycznych.
        # Pobranie *_content_type tutaj zapobiega dodatkowym zapytaniom SQL,
        # gdy Django będzie sprawdzać, z jakiej tabeli pobrać field1, field2 itd.
        qs = Calendar.objects.filter(author=self.request.user).select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        ).order_by("-created_at")

        # 2. prefetch_related
        # Usuwamy ImageForField, bo już go nie ma.
        # Usuwamy ręczne obiekty Prefetch z hardcodowanymi typami (np. field1 jako Text).
        #
        # Podając po prostu nazwy pól GenericForeignKey ("field1", "field2" itd.),
        # Django automatycznie:
        # a) Zbierze ID i ContentType dla każdego wiersza.
        # b) Zrobi jedno zapytanie do tabeli Text (dla rekordów tekstowych).
        # c) Zrobi jedno zapytanie do tabeli Image (dla rekordów obrazkowych).
        # d) "Sklei" to w Pythonie.
        
        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom"  # To obsłuży automatycznie BottomImage, BottomColor, BottomGradient
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
            
            # 1. Pobieramy metadane (JSON) o ułożeniu/treści
            # Zakładamy, że dla jednego pola przychodzi jeden główny obiekt konfiguracji
            raw_data = data.get(field_key)
            item_data = {}

            # Parsowanie JSON (jeśli to string)
            if raw_data:
                if isinstance(raw_data, str):
                    try:
                        item_data = json.loads(raw_data)
                    except ValueError:
                        item_data = {}
                elif isinstance(raw_data, dict):
                    item_data = raw_data

            # 2. Obsługa obrazka (Upload pliku LUB ścieżka z JSON)
            uploaded_file = self.request.FILES.get(file_key)
            final_image_path = item_data.get("image")  # Domyślnie to, co przyszło w JSON (np. obrazek z galerii)

            # Jeśli użytkownik wgrał nowy plik, ma on priorytet i nadpisuje path
            if uploaded_file:
                file_bytes = uploaded_file.read()
                filename = f"generated_{uuid.uuid4().hex}.png"
                
                # Uploadujemy TUTAJ, zanim stworzymy obiekt w bazie
                generated_url = upload_image(
                    file_bytes,
                    "generated_images",
                    filename
                )
                final_image_path = generated_url

            # 3. Tworzenie odpowiedniego obiektu (Tekst lub Obraz)
            field_obj = None

            # Przypadek A: To jest tekst
            if "text" in item_data and not uploaded_file: # file ma priorytet bycia obrazkiem
                field_obj = CalendarMonthFieldText.objects.create(
                    author=user,
                    text=item_data["text"],
                    font=item_data.get("font", {}).get("fontFamily"),
                    weight=item_data.get("font", {}).get("fontWeight"),
                    color=item_data.get("font", {}).get("fontColor"),
                    size=item_data.get("font", {}).get("fontSize"),
                )

            # Przypadek B: To jest obrazek (z uploadu lub z JSONa)
            elif final_image_path:
                field_obj = CalendarMonthFieldImage.objects.create(
                    author=user,
                    path=final_image_path,  # Tutaj trafia URL z uploadu lub z JSON
                    size=item_data.get("scale"),
                    positionX=item_data.get("positionX"),
                    positionY=item_data.get("positionY"),
                )

            # 4. Podpięcie pod Kalendarz (GenericForeignKey)
            if field_obj:
                ct = ContentType.objects.get_for_model(field_obj)
                
                # Ustawiamy content_type i object_id dynamicznie dla danego pola (field1/2/3)
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

            # 1. Pobranie kalendarza z bazy
            calendar = fetch_calendar_data(calendar_id)
            if not calendar:
                return Response({"error": f"Nie znaleziono kalendarza {calendar_id}"}, status=404)

            # 2. Folder tymczasowy na pobrane pliki (upscaling itp.)
            temp_dir = os.path.join(settings.MEDIA_ROOT, "calendar_temp", str(uuid.uuid4()))
            os.makedirs(temp_dir, exist_ok=True)

            # 3. Przygotowanie danych
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

            # Pola reklamowe
            all_fields = []
            for i in range(1, 4):
                all_fields.append((getattr(calendar, f"field{i}", None), i))
            for img in getattr(calendar, "prefetched_images_for_fields", []):
                all_fields.append((img, f"prefetched_image_{img.id}"))
            for field_obj, field_name in all_fields:
                data["fields"][field_name] = handle_field_data(field_obj, field_name, temp_dir)

            # 4. Upscaling główki
            upscaled_header_path = None
            if data["top_image"]:
                result = upscale_image_with_bigjpg(data["top_image"], temp_dir)
                upscaled_header_path = result["local_upscaled"]

            # 5. Upscaling tła pleców (jeśli obraz)
            if data["bottom"] and data["bottom"].get("type") == "image":
                result = upscale_image_with_bigjpg(data["bottom"]["url"], temp_dir)
                data["bottom"]["image_path"] = result["local_upscaled"]

            # =====================================================
            # 6. GENEROWANIE KALENDARZA — dwa pliki PSD w jednym folderze
            #    Folder: calendar_{production_id}_{kod}/
            #      ├── header_{production_id}.psd   (335 × 225 mm)
            #      └── backing_{production_id}.psd  (321 × 641 mm)
            # =====================================================
            calendar_files = generate_calendar(
                data=data,
                top_image_path=data["top_image"],
                upscaled_top_path=upscaled_header_path,
                production_id=production_id,
            )

            # 7. Aktualizacja statusu produkcji
            try:
                production = CalendarProduction.objects.get(id=production_id)
                production.status = "done"
                production.production_note = "Pliki PSD wygenerowane (główka + plecy)."
                production.finished_at = timezone.now()
                production.save()
                print(f"✅ Produkcja {production_id} → done")
            except CalendarProduction.DoesNotExist:
                print(f"⚠️ Nie znaleziono produkcji {production_id}")

            # 8. Cleanup temp
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
    # Jeśli to widok dla obsługi, warto rozważyć IsAdminUser, 
    # ale zostawiam IsAuthenticated zgodnie z Twoim kodem.
    permission_classes = [IsAuthenticated] 
    lookup_field = "pk"

    def get_queryset(self):
        # 1. Pobieramy wszystkie kalendarze (zakładamy, że staff może widzieć wszystko)
        qs = Calendar.objects.all()

        # 2. select_related
        # Optymalizacja zapytań SQL dla kluczy obcych i typów zawartości.
        # Pobranie *_content_type jest kluczowe dla wydajności GenericForeignKey.
        qs = qs.select_related(
            "top_image",
            "year_data",
            "field1_content_type",
            "field2_content_type",
            "field3_content_type",
            "bottom_content_type",
        )

        # 3. prefetch_related
        # Usuwamy ręczne definiowanie querysetów (np. wymuszanie Text dla field1).
        # Podając same nazwy pól, Django automatycznie sprawdzi, czy w danym wierszu
        # jest Tekst czy Obrazek i pobierze odpowiedni obiekt.
        # To samo dotyczy pola 'bottom' (Image/Color/Gradient).
        qs = qs.prefetch_related(
            "field1",
            "field2",
            "field3",
            "bottom"
        )
        
        # Usunięto: imageforfield_set (model nie istnieje)

        return qs
    

class DownloadCalendarStaffView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, pk, format=None):
        # 1. Budujemy poprawną ścieżkę: media/calendar_exports/calendar_{pk}
        calendar_dir = os.path.join(settings.MEDIA_ROOT, 'calendar_exports', f"calendar_{pk}")

        if not os.path.exists(calendar_dir) or not os.path.isdir(calendar_dir):
            # Debug w konsoli, żebyś wiedział co się dzieje
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