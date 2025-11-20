FROM python:3.10-slim

WORKDIR /app

# Copier le code
COPY . /app

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 8000

# Lancer l'API FastAPI
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
