import os
import json
from pathlib import Path

from sql_utils import run_query
from nutrition_schema import NUTRITION_FIELDS

from groq import Groq
from dotenv import load_dotenv

# -------------------------------------------------------------------
# Chargement du .env
# -------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
ENV_PATH = BASE_DIR / ".env"

if ENV_PATH.exists():
    load_dotenv(ENV_PATH)
else:
    print("⚠️   .env introuvable dans agent_knowledge/ — clé API non chargée.")

# -------------------------------------------------------------------
# Lecture des prompts
# -------------------------------------------------------------------
PROMPT_CONTEXT = (BASE_DIR / "prompts" / "context.txt").read_text(encoding="utf-8")
PROMPT_TEMPLATE = (BASE_DIR / "prompts" / "prompt.txt").read_text(encoding="utf-8")

# -------------------------------------------------------------------
# Agent Knowledge
# -------------------------------------------------------------------
class KnowledgeAgent:
    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Variable d'environnement GROQ_API_KEY manquante (dans .env).")

        self.client = Groq(api_key=api_key)
        self.model = "llama-3.3-70b-versatile"   # modèle que tu veux utiliser

    # ----------------------------------------------------------------
    # Construction SQL via LLM
    # ----------------------------------------------------------------
    def build_sql_with_llm(self, user_goal: str) -> str:
        prompt = (
            PROMPT_CONTEXT
            + "\n\n"
            + PROMPT_TEMPLATE.format(
                user_goal=user_goal,
                columns=", ".join(NUTRITION_FIELDS)
            )
        )

        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "Tu génères uniquement des requêtes SQL SQLite valides."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            max_tokens=300
        )

        sql = resp.choices[0].message.content.strip()


        print("----- PROMPT COMPLET -----")
        print(prompt)
        print("---------------------------")


        print("----- Réponse LLM -----")
        print(sql)
        print("-----------------------")

        # Sécurité : si le LLM échoue ou renvoie du vide
        if not sql.lower().startswith("select"):
            print("⚠️   Le LLM a renvoyé une réponse invalide, fallback SQL utilisé.")
            return ""

        return sql

    # ----------------------------------------------------------------
    # SQL fallback "en dur"
    # ----------------------------------------------------------------
    def build_sql_from_goal(self, user_goal: str) -> str:
        goal = user_goal.lower()
        fields_quoted = [f'"{f}"' for f in NUTRITION_FIELDS]

        if "perdre" in goal or "maigrir" in goal:
            sql = f"""
                SELECT {", ".join(fields_quoted)}
                FROM foods
                ORDER BY "energie_règlement_ue_n°_1169_2011_kcal_100_g" ASC
                LIMIT 10
            """
        elif "muscle" in goal or "prise de masse" in goal:
            sql = f"""
                SELECT {", ".join(fields_quoted)}
                FROM foods
                ORDER BY "protéines_n_x_6.25_g_100_g" DESC
                LIMIT 10
            """
        else:
            sql = f"""
                SELECT {", ".join(fields_quoted)}
                FROM foods
                LIMIT 10
            """

        return sql.strip()

    # ----------------------------------------------------------------
    # Exécution de la requête
    # ----------------------------------------------------------------
    def query(self, user_goal: str, use_llm: bool = True) -> str:

        sql = ""
        if use_llm:
            sql = self.build_sql_with_llm(user_goal)

        # Si le LLM renvoie SQL vide ou mauvais : fallback automatique
        if not sql.strip():
            sql = self.build_sql_from_goal(user_goal)

        rows = run_query(sql)

        result = {
            "goal": user_goal,
            "sql": sql,
            "suggestions": rows
        }
        return json.dumps(result, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------
# Exécution directe (debug)
# -------------------------------------------------------------------
if __name__ == "__main__":
    agent = KnowledgeAgent()
    goal = "je veux perdre 2 kilos donnes des aliments"
    print(agent.query(goal, use_llm=True))
