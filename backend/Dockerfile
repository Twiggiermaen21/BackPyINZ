FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Kopiowanie i instalacja pakietów
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiowanie kodu aplikacji
COPY . .

# Wystawienie portu 8000
EXPOSE 8000

# Uruchomienie serwera deweloperskiego Django
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]