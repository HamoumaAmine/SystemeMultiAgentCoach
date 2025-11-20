import os

class Settings:
    AGENT_CERVEAU_URL: str = os.getenv(
        "AGENT_CERVEAU_URL",
        "http://agent_cerveau:8001"
    )

settings = Settings()
