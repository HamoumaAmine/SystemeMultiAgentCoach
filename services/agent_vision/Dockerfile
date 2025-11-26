# ============================================
# 1. Image de base
# ============================================
FROM python:3.12-slim

# ============================================
# 2. Dossier de travail dans le conteneur
# ============================================
WORKDIR /app

# ============================================
# 3. Dépendances système (compilation éventuelle)
# ============================================
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean

# ============================================
# 4. Installer les dépendances Python
# ============================================
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 5. Copier tout le code de l’agent_vision
# ============================================
COPY . /app

# ============================================
# 6. Exposer le port du service
# ============================================
EXPOSE 8008

# ============================================
# 7. Commande de lancement
# ============================================
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8008"]
