from pydantic import BaseModel

class UserMessage(BaseModel):
    user_id: str
    text: str

class CoachResponse(BaseModel):
    answer: str
