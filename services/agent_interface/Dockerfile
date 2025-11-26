# ============================================
# 1. Base Python légère
# ============================================
FROM python:3.12-slim

# ============================================
# 2. Répertoire de travail
# ============================================
WORKDIR /app

# ============================================
# 3. Installation des dépendances système
# (indispensable pour certaines libs Python)
# ============================================
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && apt-get clean

# ============================================
# 4. Installation des dépendances Python
# ============================================
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 5. Copier tout le code de l’agent_interface
# ============================================
COPY . /app

# ============================================
# 6. Créer le répertoire d’uploads
# ============================================
RUN mkdir -p /app/uploads

# ============================================
# 7. Exposer le port FastAPI
# ============================================
EXPOSE 8000

# ============================================
# 8. Commande de lancement Uvicorn
# ============================================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
