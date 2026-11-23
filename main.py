from fastapi import FastAPI
from pydantic import BaseModel

import agent

app = FastAPI(title="Personal Action Agent")


class ChatIn(BaseModel):
    user_id: str
    text: str


class ConfirmIn(BaseModel):
    user_id: str
    action_id: str
    approved: bool


@app.post("/chat")
def chat(body: ChatIn):
    return agent.chat(body.user_id, body.text)


@app.post("/confirm")
def confirm(body: ConfirmIn):
    return agent.confirm(body.user_id, body.action_id, body.approved)


@app.get("/health")
def health():
    return {"ok": True}
