<p align="center">
  <img src="https://img.shields.io/badge/Django-092E20?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/Django_REST-ff1709?style=for-the-badge&logo=django&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-316192?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/Cloudinary-3448C5?style=for-the-badge&logo=cloudinary&logoColor=white" />
  <img src="https://img.shields.io/badge/Docker-2CA5E0?style=for-the-badge&logo=docker&logoColor=white" />
</p>

# 🗓️ AI Calendar Generator — Backend

> **Serwer aplikacyjny do generowania kalendarzy trójdzielnych z grafikami AI, gotowych do profesjonalnego druku.**

System B2B umożliwiający drukarniom oferowanie klientom spersonalizowanych kalendarzy trójdzielnych z grafikami wygenerowanymi przez sztuczną inteligencję. Backend odpowiada za cały pipeline — od promptu tekstowego, przez generowanie i upscaling grafik, aż po eksport gotowych plików PDF w przestrzeni CMYK gotowych do druku.

---

## ✨ Kluczowe funkcjonalności

🎨 **Generowanie grafik AI** — integracja z Together AI (model FLUX.1-schnell) do tworzenia grafik na podstawie opisów tekstowych z inteligentnym budowaniem promptów

🔍 **Upscaling do rozdzielczości drukarskiej** — automatyczne powiększanie grafik przez Bigjpg API do wymaganego minimum 300 DPI

🖨️ **Eksport print-ready PDF** — generowanie plików PDF z konwersją RGB→CMYK, spady i wymiary zgodne z wymaganiami drukarni

☁️ **Zarządzanie zasobami** — przechowywanie i serwowanie grafik przez Cloudinary

🔐 **Uwierzytelnianie** — JWT + Google OAuth 2.0

📅 **Dane kalendarzowe** — automatyczne generowanie siatek miesięcznych z polskimi imieninami i świętami

---

## 🏗️ Architektura

```
┌─────────────────┐                               ┌──────────────────────┐
│   React App     │◄────────────────────────────► │  Django / Gunicorn   │
│   (Frontend)    │                               │  (DRF Backend)       │
└─────────────────┘                               └──────────┬───────────┘
                                                             │
                              ┌───────────────────────────────┼───────────────────────┐
                              │                               │                       │
                              ▼                               ▼                       ▼
                    ┌──────────────────┐          ┌─────────────────┐      ┌──────────────────┐
                    │   PostgreSQL     │          │   Together AI   │      │   Cloudinary     │
                    │   Database       │          │   FLUX + LLM    │      │   Cloud Storage  │
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
├── api/                     # Główna aplikacja Django
│   ├── views/
│   │   ├── auth_views.py          # Rejestracja, logowanie, JWT, Google OAuth
│   │   ├── calendar_views.py      # CRUD kalendarzy, produkcja PDF
│   │   ├── color_views.py         # CRUD elementów interfejsu
│   │   ├── image_views.py         # Generowanie i zarządzanie grafikami AI
│   │   ├── metadata_views.py      # Style, kompozycje, kolorystyki, atmosfery
│   │   └── profile_views.py       # Profil użytkownika, awatary
│   │
│   ├── utils/
│   │   ├── calendar_generator/    # Skrypty generowania kalendarza i PDF
│   │   │   ├── colors.py
│   │   │   ├── config.py
│   │   │   ├── data_fetcher.py
│   │   │   ├── data_handlers.py
│   │   │   ├── file_utils.py
│   │   │   ├── fonts.py
│   │   │   ├── gradients.py
│   │   │   ├── images.py
│   │   │   ├── pdf_generator.py
│   │   │   ├── pdf_utils.py
│   │   │   ├── fonts/           # Czcionki wykorzystywane w PDF
│   │   │   └── profiles/        # Profile ICC CMYK
│   │   │
│   │   ├── image_generation/      # Skrypty dot. generowania obrazów AI
│   │   │   ├── generation.py
│   │   │   ├── image_generator.py
│   │   │   └── prompt_generator.py
│   │   │
│   │   ├── cloudinary_upload.py   # Upload i zarządzanie zasobami w chmurze
│   │   └── upscaling.py           # Integracja z Bigjpg API
│   │
│   ├── models.py                  # ~20+ modeli Django ORM
│   ├── serializers.py             # Serializery DRF
│   ├── urls.py                    # Routing API
│   ├── pagination.py              # Konfiguracja paginacji
│   └── tests.py                   # Testy
```

---

## 🗃️ Modele danych

| Model | Opis |
|-------|------|
| `Calendar` | Główny model kalendarza z konfiguracją |
| `CalendarProduction` | Status i pliki produkcji PDF |
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
POST   /api/calendars/:id/produce/  # Uruchomienie produkcji PDF
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
| **Framework** | ![Django](https://img.shields.io/badge/Django-092E20?style=flat&logo=django&logoColor=white) ![Django REST](https://img.shields.io/badge/DRF-ff1709?style=flat&logo=django&logoColor=white) |
| **Baza danych** | ![PostgreSQL](https://img.shields.io/badge/PostgreSQL-316192?style=flat&logo=postgresql&logoColor=white) |
| **Uwierzytelnianie** | JWT (SimpleJWT) + Google OAuth 2.0 |
| **Generowanie grafik** | HTML/JS integration with Together AI — FLUX.1-schnell |
| **Model językowy** | Together AI — Apriel-Instruct (budowanie promptów) |
| **Upscaling** | Bigjpg API |
| **Cloud storage** | ![Cloudinary](https://img.shields.io/badge/Cloudinary-3448C5?style=flat&logo=cloudinary&logoColor=white) |
| **Generowanie PDF** | ReportLab / PyPDF (CMYK, 300 DPI) |
| **Serwer WSGI/ASGI** | Gunicorn / Uvicorn |
| **Konteneryzacja** | ![Docker](https://img.shields.io/badge/Docker-2CA5E0?style=flat&logo=docker&logoColor=white) |

---

## 🖨️ Pipeline produkcji PDF

```
Parametry użytkownika
        │
        ▼
┌─────────────────────┐
│  Prompt Generator   │  ← LLM (Apriel-Instruct) buduje prompt
│  (styl, atmosfera,  │    z wybranych parametrów
│   kompozycja, ...)  │
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
│  PDF Generator      │  ← Konwersja RGB→CMYK, aplikowanie siatki
│                     │    miesiąca z polskimi świętami, składanie
│                     │    nagłówka i podkładu
└─────────┬───────────┘
          ▼
    📄 Plik PDF
    (Zgodny z CMYK)
```

### Specyfikacja wymiarów

| Element | Wymiary [mm] | Wymiary [px] @ 300 DPI |
|---------|-------------|----------------------|
| Nagłówek kalendarza | 335 × 225 | 3957 × 2658 |
| Podkład kalendarza | 321 × 641 | 3789 × 7572 |

---

## 🚀 Uruchomienie

### 🐳 Uruchomienie w Dockerze (Rekomendowane)

Najszybszym sposobem na uruchomienie aplikacji jest użycie Dockera. Upewnij się, że masz zainstalowanego Dockera w swoim systemie.

```bash
# Klonowanie repozytorium
git clone https://github.com/Twiggiermaen21/BackPyINZ.git
cd BackPyINZ

# Skopiowanie pliku konfiguracyjnego środowiska
cp backend/.env.example backend/.env
# UWAGA: Edytuj plik backend/.env i uzupełnij klucze API przed uruchomieniem aplikacji.

# Zbudowanie obrazu Dockera
docker build -t ai-calendar-backend ./backend

# Uruchomienie kontenera na porcie 8000
docker run -d -p 8000:8000 --env-file ./backend/.env ai-calendar-backend
```

### 💻 Uruchomienie lokalne (bez Dockera)

Jeżeli wolisz uruchamiać projekt klasycznie w wirtualnym środowisku:

```bash
# Klonowanie repozytorium
git clone https://github.com/Twiggiermaen21/BackPyINZ.git
cd BackPyINZ
cd backend

# Utworzenie wirtualnego środowiska
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Instalacja zależności
pip install -r requirements.txt

# Konfiguracja zmiennych środowiskowych
cp .env.example .env
# Uzupełnij klucze API w pliku .env przed wystartowaniem serwera

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
- **100+** pełnych cykli produkcji PDF
- Przetestowano spójność wizualną pomiędzy podglądem w przeglądarce a wygenerowanym plikiem PDF

---

## 📝 Licencja

Projekt realizowany w ramach pracy inżynierskiej.

---
