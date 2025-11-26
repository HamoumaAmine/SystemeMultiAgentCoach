# ============================================
# 1. Image de base
# ============================================
FROM python:3.12-slim

# ============================================
# 2. Dossier de travail dans le conteneur
# ============================================
WORKDIR /app

# ============================================
# 3. Dépendances système (pour éventuelles libs C)
# ============================================
RUN apt-get update && apt-get install -y \
    build-essential \
    && apt-get clean

# ============================================
# 4. Installation des dépendances Python
# ============================================
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# ============================================
# 5. Copier tout le code de l'agent_knowledge
#    (app/, knowledge_agent.py, db/, prompts/, etc.)
# ============================================
COPY . /app

# ============================================
# 6. Exposer le port du service
# ============================================
EXPOSE 8007

# ============================================
# 7. Commande de lancement
# ============================================
# On lance l'app FastAPI définie dans app/main.py
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
