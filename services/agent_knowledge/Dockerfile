# services/agent_knowledge/Dockerfile

FROM python:3.10-slim

WORKDIR /app

# dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# code de l'agent
COPY app ./app
COPY db ./db
COPY prompts ./prompts
COPY knowledge_agent.py nutrition_schema.py sql_utils.py ./

EXPOSE 8007

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007"]
