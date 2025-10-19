# EPOSI Backend (Render)

FastAPI backend for:
- `/ask` → calls OpenAI (server-side key)
- `/api/messages` → simple chat storage (in-memory)
- `/api/settings` → doctor read-receipts toggle
- `/api/typing` → typing indicator

## Local run
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export OPENAI_API_KEY=sk-...    # mac/linux
# setx OPENAI_API_KEY sk-...    # windows powershell use: $env:OPENAI_API_KEY="sk-..."
uvicorn app:app --reload --port 8000
