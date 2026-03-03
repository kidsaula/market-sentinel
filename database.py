import json
import requests
from config import TELEGRAM_TOKEN, USERS_FILE

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

def check_new_users():
    url = f"https://api.telegram.org{TELEGRAM_TOKEN}/getUpdates"
    
    try:
        response = requests.get(url, timeout=15).json()
        for result in response.get("result", []):
            message = result.get("message")
            if message and message.get("text") == "/start":
                save_user(message["chat"]["id"])
    except Exception as e:
        print(f"❌ Erro ao checar novos usuários: {e}")
