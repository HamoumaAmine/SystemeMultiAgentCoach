FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# SQLite va créer agent_memory.db dans /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8003"]
