#Agent Interface — Coach Sportif Multi-Agents


##Fonctionnalités principales
 API HTTP (FastAPI)

Expose des endpoints REST pour interagir avec le coach.

 Communication inter-agents (MCP)

Envoie des messages JSON standardisés :

{
  "message_id": "...",
  "from": "agent_interface",
  "to": "agent_cerveau",
  "type": "request",
  "payload": { ... },
  "context": { ... }
}

 Appel de l’agent_cerveau

Transmet la demande utilisateur au cerveau → récupère une réponse → la renvoie à l’utilisateur.

 Schémas Pydantic

Validation propre des entrées/sorties (UserMessage, CoachResponse).

 Root + healthcheck

Routes utilitaires pour tester si l’agent fonctionne.

##Architecture interne
agent_interface/
│

└── app/

    ├── main.py               # FastAPI + routes principales
    
    ├── routers/
    
    │     └── coach.py        # Endpoint /coach
    
    ├── models/
    
    │     └── schemas.py      # UserMessage, CoachResponse
    
    ├── core/
    
    │     └── config.py       # Variables d'environnement (URL des agents)
    
    └── mcp/
    
          └── client.py       # Fonction send_mcp() pour parler aux autres agents

##Endpoints disponibles
GET /

Message simple :

{ "message": "Agent Interface is running" }

GET /health

Vérifie si l’agent tourne :

{ "status": "ok" }

POST /coach
Body attendu :
{
  "user_id": "amine",
  "text": "Je veux un programme pour perdre du poids"
}

##Comportement :

L’agent_interface reçoit la requête.

Il construit un message MCP.

Il l’envoie à AGENT_CERVEAU_URL.

Il récupère payload.answer.

Il renvoie la réponse à l’utilisateur.

📝 Réponse typique (si agent_cerveau répond bien) :
{
  "answer": "Salut…"
}

##Lancer l’agent_interface

Depuis le dossier :

cd services/agent_interface/app
python -m uvicorn main:app --reload --port 8000

Tu verras :

Uvicorn running on http://127.0.0.1:8000

🧪 Tester en local

🔥 Ouvre le Swagger interactif :

👉 http://127.0.0.1:8000/docs

Tu y trouveras :

/

/health

/coach



##Ce que j’ai implémenté dans l’agent_interface

✓ Création de la structure complète du service
✓ Mise en place de FastAPI
✓ Endpoints /, /health, /coach
✓ Client MCP (send_mcp())
✓ Schémas Pydantic (UserMessage, CoachResponse)
✓ Configuration par variable d’environnement (AGENT_CERVEAU_URL)
✓ Test du service en local avec Uvicorn
✓ Préparation pour communication avec les autres agents (cerveau, mood, memory, etc.)
