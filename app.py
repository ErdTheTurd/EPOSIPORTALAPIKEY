from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os, httpx, uuid, datetime as dt
from typing import Optional, Literal, List

# ----- Config -----
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    print("WARNING: OPENAI_API_KEY not set")

ALLOWED_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# ----- App -----
app = FastAPI(title="EPOSI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in ALLOWED_ORIGINS if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Models -----
Role = Literal["doctor", "patient"]
Status = Literal["sending", "sent", "delivered", "read"]

class MessageIn(BaseModel):
    id: Optional[str] = None
    role: Role
    text: str
    time: Optional[str] = None
    senderName: Optional[str] = None

class MessageOut(BaseModel):
    id: str
    role: Role
    text: str
    time: str
    status: Status
    senderName: Optional[str] = None

class SettingsOut(BaseModel):
    doctorAllowsReadReceipts: bool

class TypingOut(BaseModel):
    doctorTyping: bool

# ----- In-memory store (replace with a DB later) -----
MESSAGES: List[MessageOut] = []
SETTINGS = SettingsOut(doctorAllowsReadReceipts=True)
TYPING = TypingOut(doctorTyping=False)

def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()

# ----- Routes -----
@app.get("/")
def root():
    return {"status": "ok"}

# AI: proxy to OpenAI (server holds the key)
@app.post("/ask")
async def ask(req: Request):
    data = await req.json()
    question = data.get("question", "").strip()
    if not question:
        raise HTTPException(400, "Missing 'question'")
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are an AI assistant for El Paso Orthopedic and Spine Institute."},
            {"role": "user", "content": question}
        ],
        "temperature": 0.2
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post("https://api.openai.com/v1/chat/completions",
                              headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()
        answer = data["choices"][0]["message"]["content"]
        return {"answer": answer, "sources": []}

# Chat: list
@app.get("/api/messages", response_model=List[MessageOut])
def list_messages():
    return MESSAGES

# Chat: create
@app.post("/api/messages", response_model=MessageOut)
def create_message(m: MessageIn):
    mid = m.id or str(uuid.uuid4())
    t = m.time or now_iso()
    # Doctor sends from website => patient sees Delivered; adjust as needed.
    status: Status = "delivered" if m.role == "patient" else "sent"
    out = MessageOut(
        id=mid, role=m.role, text=m.text, time=t, status=status,
        senderName=m.senderName
    )
    MESSAGES.append(out)
    return out

# Settings: doctor controls read receipts
@app.get("/api/settings", response_model=SettingsOut)
def get_settings():
    return SETTINGS

@app.post("/api/settings", response_model=SettingsOut)
def set_settings(body: SettingsOut):
    global SETTINGS
    SETTINGS = body
    return SETTINGS

# Typing indicator
@app.get("/api/typing", response_model=TypingOut)
def get_typing():
    return TYPING

@app.post("/api/typing", response_model=TypingOut)
def set_typing(body: TypingOut):
    global TYPING
    TYPING = body
    return TYPING
