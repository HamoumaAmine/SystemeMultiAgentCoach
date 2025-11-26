FROM python:3.10-slim

# -----------------------------
# 1. Dépendances système utiles
# -----------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# -----------------------------
# 2. Dossier de travail
# -----------------------------
WORKDIR /app

# -----------------------------
# 3. Installer les requirements
# -----------------------------
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------
# 4. Copier tout le code
# -----------------------------
COPY . /app

# IMPORTANT :
# On s’assure que la base SQLite existe
RUN touch /app/agent_memory.db

# -----------------------------
# 5. Lancer le service
# -----------------------------
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
