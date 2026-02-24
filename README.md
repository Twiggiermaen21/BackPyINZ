<p align="center">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/Django_REST-ff1709?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Cloudinary-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white" />
</p>

# 🗓️ AI Calendar Generator — Backend

> **Serwer aplikacyjny do generowania kalendarzy trójdzielnych z grafikami AI, gotowych do profesjonalnego druku.**

System B2B umożliwiający drukarniom oferowanie klientom spersonalizowanych kalendarzy trójdzielnych z grafikami wygenerowanymi przez sztuczną inteligencję. Backend odpowiada za cały pipeline — od promptu tekstowego, przez generowanie i upscaling grafik, aż po eksport plików PSD w przestrzeni CMYK z odpowiednimi spadami drukarskimi.

---

## ✨ Kluczowe funkcjonalności

🎨 **Generowanie grafik AI** — integracja z Together AI (model FLUX.1-schnell) do tworzenia grafik na podstawie opisów tekstowych z inteligentnym budowaniem promptów

🔍 **Upscaling do rozdzielczości drukarskiej** — automatyczne powiększanie grafik przez Bigjpg API do wymaganego minimum 300 DPI

🖨️ **Eksport print-ready PSD** — generowanie wielowarstwowych plików PSD z konwersją RGB→CMYK, spadami i wymiarami zgodnymi z wymaganiami drukarni

☁️ **Zarządzanie zasobami** — przechowywanie i serwowanie grafik przez Cloudinary

🔐 **Uwierzytelnianie** — JWT + Google OAuth 2.0

📅 **Dane kalendarzowe** — automatyczne generowanie siatek miesięcznych z polskimi imieninami i świętami

---

## 🏗️ Architektura

```
┌─────────────────┐       HTTPS (REST API)       ┌──────────────────────┐
│   React App     │◄────────────────────────────►│  Django / Gunicorn   │
│   (Frontend)    │                               │  (DRF Backend)       │
└─────────────────┘                               └──────────┬───────────┘
                                                             │
                              ┌───────────────────────────────┼───────────────────────┐
                              │                               │                       │
                              ▼                               ▼                       ▼
                    ┌──────────────────┐          ┌─────────────────┐      ┌──────────────────┐
                    │   PostgreSQL     │          │   Together AI   │      │   Cloudinary     │
                    │   Database       │          │   FLUX + LLM   │      │   Cloud Storage  │
                    └──────────────────┘          └─────────────────┘      └──────────────────┘
                                                             │
                                                             ▼
                                                  ┌─────────────────┐
                                                  │   Bigjpg API    │
                                                  │   (Upscaling)   │
                                                  └─────────────────┘
```

---

## 📁 Struktura projektu

```
backend/
├── views/
│   ├── auth_views.py          # Rejestracja, logowanie, JWT, Google OAuth
│   ├── calendar_views.py      # CRUD kalendarzy, produkcja PSD
│   ├── image_views.py         # Generowanie i zarządzanie grafikami AI
│   ├── metadata_views.py      # Style, kompozycje, kolorystyki, atmosfery
│   └── profile_views.py       # Profil użytkownika, awatary
│
├── utils/
│   ├── image_generator.py     # Integracja z Together AI (FLUX.1-schnell)
│   ├── prompt_generator.py    # Budowanie promptów z parametrów użytkownika
│   ├── upscaling.py           # Integracja z Bigjpg API
│   ├── generation.py          # Pipeline generowania PSD (CMYK, spady)
│   ├── cloudinary_upload.py   # Upload i zarządzanie zasobami w chmurze
│   ├── services.py            # Logika biznesowa i helpery
│   └── fonts/                 # Czcionki do renderowania kalendarzy
│
├── models.py                  # ~20+ modeli Django ORM
├── serializers.py             # Serializery DRF
├── urls.py                    # Routing API
├── pagination.py              # Konfiguracja paginacji
├── admin.py                   # Panel administracyjny
└── tests.py                   # Testy
```

---

## 🗃️ Modele danych

| Model | Opis |
|-------|------|
| `Calendar` | Główny model kalendarza z konfiguracją |
| `CalendarProduction` | Status i pliki produkcji PSD |
| `CalendarMonthFieldText` | Teksty dla poszczególnych miesięcy |
| `CalendarMonthFieldImage` | Grafiki przypisane do miesięcy |
| `CalendarYearData` | Dane roczne (imieniny, święta) |
| `GeneratedImage` | Wygenerowane grafiki AI z metadanymi |
| `ImageForField` | Powiązanie grafik z polami kalendarza |
| `Upscaling` | Status i wyniki upscalingu |
| `ProfileImage` | Awatary użytkowników |
| `CalendarType` | Typy kalendarzy (trójdzielny, itp.) |
| `BottomImage` / `BottomColor` / `BottomGradient` | Konfiguracja dolnej części kalendarza |
| `StylArtystyczny` / `Kompozycja` / `Kolorystyka` | Parametry stylu grafik |
| `Atmosfera` / `Inspiracja` / `Tlo` | Parametry nastroju i tła |
| `Perspektywa` / `Detale` / `Realizm` | Parametry szczegółowości |
| `StylNarracyjny` | Styl narracji promptu |

---

## 🔌 API Endpoints

### 🔐 Autoryzacja
```
POST   /api/auth/register/          # Rejestracja użytkownika
POST   /api/auth/login/             # Logowanie (JWT)
POST   /api/auth/google/            # Logowanie przez Google OAuth
POST   /api/auth/token/refresh/     # Odświeżanie tokenu
```

### 📅 Kalendarze
```
GET    /api/calendars/              # Lista kalendarzy użytkownika
POST   /api/calendars/              # Utworzenie nowego kalendarza
GET    /api/calendars/:id/          # Szczegóły kalendarza
PUT    /api/calendars/:id/          # Aktualizacja kalendarza
DELETE /api/calendars/:id/          # Usunięcie kalendarza
POST   /api/calendars/:id/produce/  # Uruchomienie produkcji PSD
```

### 🎨 Grafiki AI
```
POST   /api/images/generate/        # Generowanie nowej grafiki
GET    /api/images/                  # Lista wygenerowanych grafik
POST   /api/images/:id/upscale/     # Upscaling grafiki
DELETE /api/images/:id/             # Usunięcie grafiki
```

### 📋 Metadane (style, kompozycje, itp.)
```
GET    /api/metadata/styles/        # Dostępne style artystyczne
GET    /api/metadata/compositions/  # Kompozycje
GET    /api/metadata/colors/        # Kolorystyki
GET    /api/metadata/atmospheres/   # Atmosfery
```

### 👤 Profil
```
GET    /api/profile/                # Dane profilu
PUT    /api/profile/                # Aktualizacja profilu
POST   /api/profile/avatar/         # Upload awatara
```

---

## ⚙️ Stos technologiczny

| Kategoria | Technologia |
|-----------|-------------|
| **Framework** | Django 5.x + Django REST Framework |
| **Baza danych** | PostgreSQL |
| **Uwierzytelnianie** | JWT (SimpleJWT) + Google OAuth 2.0 |
| **Generowanie grafik** | Together AI — FLUX.1-schnell |
| **Model językowy** | Together AI — Apriel-Instruct (budowanie promptów) |
| **Upscaling** | Bigjpg API |
| **Cloud storage** | Cloudinary |
| **Generowanie PSD** | Pillow + psd-tools (CMYK, 300 DPI) |
| **Serwer WSGI/ASGI** | Gunicorn / Uvicorn |

---

## 🖨️ Pipeline produkcji PSD

```
Parametry użytkownika
        │
        ▼
┌─────────────────────┐
│  Prompt Generator    │  ← LLM (Apriel-Instruct) buduje prompt
│  (styl, atmosfera,   │    z wybranych parametrów
│   kompozycja, ...)   │
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  FLUX.1-schnell     │  ← Generowanie grafiki 1024×1024
└─────────┬───────────┘
          ▼
┌─────────────────────┐
│  Bigjpg Upscaling   │  ← Powiększenie do rozdzielczości drukarskiej
└─────────┬───────────┘     (nagłówek: 3957×2658px / podkład: 3789×7572px)
          ▼
┌─────────────────────┐
│  PSD Generator      │  ← Konwersja RGB→CMYK, spady 3mm,
│                     │    warstwy: grafika + siatka + tekst
└─────────┬───────────┘
          ▼
    📄 Plik PSD
    (300 DPI, CMYK)
```

### Specyfikacja wymiarów

| Element | Wymiary [mm] | Wymiary [px] @ 300 DPI |
|---------|-------------|----------------------|
| Nagłówek kalendarza | 335 × 225 | 3957 × 2658 |
| Podkład kalendarza | 321 × 641 | 3789 × 7572 |

---

## 🚀 Uruchomienie

```bash
# Klonowanie repozytorium
git clone https://github.com/your-username/ai-calendar-backend.git
cd ai-calendar-backend

# Utworzenie wirtualnego środowiska
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Instalacja zależności
pip install -r requirements.txt

# Konfiguracja zmiennych środowiskowych
cp .env.example .env
# Uzupełnij klucze API w pliku .env

# Migracje bazy danych
python manage.py migrate

# Uruchomienie serwera deweloperskiego
python manage.py runserver
```

### Zmienne środowiskowe

```env
SECRET_KEY=your-django-secret-key
DATABASE_URL=postgres://user:pass@localhost:5432/calendar_db

TOGETHER_AI_API_KEY=your-together-ai-key
BIGJPG_API_KEY=your-bigjpg-key

CLOUDINARY_CLOUD_NAME=your-cloud-name
CLOUDINARY_API_KEY=your-cloudinary-key
CLOUDINARY_API_SECRET=your-cloudinary-secret

GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

---

## 📊 Statystyki testów

- **200+** wygenerowanych grafik AI w trakcie rozwoju
- **100+** pełnych cykli produkcji PSD
- Przetestowano spójność wizualną pomiędzy podglądem w przeglądarce a wygenerowanym plikiem PSD

---

## 📝 Licencja

Projekt realizowany w ramach pracy inżynierskiej.

---

<p align="center">
  <sub>Built with ❤️ and AI</sub>
</p>
