

from ..models import *
from ..serializers import *
from ..pagination import *
from rest_framework.permissions import IsAuthenticated
from rest_framework import generics

# 🔸 StylArtystyczny
class StylArtystycznyCreate(generics.ListCreateAPIView):
    queryset = StylArtystyczny.objects.all()
    serializer_class = StylArtystycznySerializer
    permission_classes = [IsAuthenticated]

class StylArtystycznyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = StylArtystyczny.objects.all()
    serializer_class = StylArtystycznySerializer
    permission_classes = [IsAuthenticated]


# 🔸 Kompozycja
class KompozycjaCreate(generics.ListCreateAPIView):
    queryset = Kompozycja.objects.all()
    serializer_class = KompozycjaSerializer
    permission_classes = [IsAuthenticated]

class KompozycjaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Kompozycja.objects.all()
    serializer_class = KompozycjaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Kolorystyka
class KolorystykaCreate(generics.ListCreateAPIView):
    queryset = Kolorystyka.objects.all()
    serializer_class = KolorystykaSerializer
    permission_classes = [IsAuthenticated]

class KolorystykaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Kolorystyka.objects.all()
    serializer_class = KolorystykaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Atmosfera
class AtmosferaCreate(generics.ListCreateAPIView):
    queryset = Atmosfera.objects.all()
    serializer_class = AtmosferaSerializer
    permission_classes = [IsAuthenticated]

class AtmosferaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Atmosfera.objects.all()
    serializer_class = AtmosferaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Inspiracja
class InspiracjaCreate(generics.ListCreateAPIView):
    queryset = Inspiracja.objects.all()
    serializer_class = InspiracjaSerializer
    permission_classes = [IsAuthenticated]

class InspiracjaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Inspiracja.objects.all()
    serializer_class = InspiracjaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Tło
class TloCreate(generics.ListCreateAPIView):
    queryset = Tlo.objects.all()
    serializer_class = TloSerializer
    permission_classes = [IsAuthenticated]

class TloDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Tlo.objects.all()
    serializer_class = TloSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Perspektywa
class PerspektywaCreate(generics.ListCreateAPIView):
    queryset = Perspektywa.objects.all()
    serializer_class = PerspektywaSerializer
    permission_classes = [IsAuthenticated]

class PerspektywaDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Perspektywa.objects.all()
    serializer_class = PerspektywaSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Detale
class DetaleCreate(generics.ListCreateAPIView):
    queryset = Detale.objects.all()
    serializer_class = DetaleSerializer
    permission_classes = [IsAuthenticated]

class DetaleDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Detale.objects.all()
    serializer_class = DetaleSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Realizm
class RealizmCreate(generics.ListCreateAPIView):
    queryset = Realizm.objects.all()
    serializer_class = RealizmSerializer
    permission_classes = [IsAuthenticated]

class RealizmDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Realizm.objects.all()
    serializer_class = RealizmSerializer
    permission_classes = [IsAuthenticated]


# 🔸 Styl Narracyjny
class StylNarracyjnyCreate(generics.ListCreateAPIView):
    queryset = StylNarracyjny.objects.all()
    serializer_class = StylNarracyjnySerializer
    permission_classes = [IsAuthenticated]

class StylNarracyjnyDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = StylNarracyjny.objects.all()
    serializer_class = StylNarracyjnySerializer
    permission_classes = [IsAuthenticated]
