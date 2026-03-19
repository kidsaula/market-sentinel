import json
import requests
from datetime import datetime, timezone, timedelta
from config import TELEGRAM_TOKEN, USERS_FILE, NEWS_LOG_FILE

def load_users():
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

def save_user(chat_id):
    users = load_users()
    if chat_id not in users:
        users.append(chat_id)
        with open(USERS_FILE, "w") as f:
            json.dump(users, f)
        print(f"✅ Novo usuário salvo: {chat_id}")

def load_news_log(max_days=7):
    """Carrega UUIDs vistos, descartando entradas mais antigas que max_days."""
    try:
        with open(NEWS_LOG_FILE, "r") as f:
            data = json.load(f)
        # Compatibilidade com formato antigo (lista de UUIDs sem timestamp)
        if isinstance(data, list):
            return {}
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_days)
        return {
            uuid: ts for uuid, ts in data.items()
            if datetime.fromisoformat(ts) > cutoff
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_news_log(log: dict, new_ids: set):
    """Adiciona novos UUIDs com timestamp atual e persiste."""
    now = datetime.now(timezone.utc).isoformat()
    log.update({uuid: now for uuid in new_ids})
    with open(NEWS_LOG_FILE, "w") as f:
        json.dump(log, f)

def check_new_users():
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, timeout=15).json()
        for result in response.get("result", []):
            message = result.get("message")
            if message and message.get("text") == "/start":
                save_user(message["chat"]["id"])
    except Exception as e:
        print(f"❌ Erro ao checar novos usuários: {e}")
