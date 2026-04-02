import os
from supabase import create_client

# Railway автоматично підставить ці дані з розділу Variables
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(URL, KEY)

# --- РОБОТА З КОРИСТУВАЧАМИ ---

def get_or_create_user(tg_id, username):
    res = supabase.table("users").select("*").eq("telegram_id", tg_id).execute()
    if res.data:
        return res.data[0]
    
    data = {"telegram_id": tg_id, "username": username, "coins": 0}
    ins = supabase.table("users").insert(data).execute()
    return ins.data[0]

def get_user_by_telegram_id(tg_id):
    res = supabase.table("users").select("*").eq("telegram_id", tg_id).execute()
    return res.data[0] if res.data else None

def update_coins(user_id, delta):
    # Отримуємо поточний баланс за внутрішнім ID бази
    res = supabase.table("users").select("coins").eq("id", user_id).execute()
    if not res.data:
        return 0
    new_balance = res.data[0]["coins"] + delta
    # Оновлюємо баланс
    supabase.table("users").update({"coins": new_balance}).eq("id", user_id).execute()
    return new_balance

def get_top_users(limit=50):
    res = supabase.table("users").select("*").order("coins", desc=True).limit(limit).execute()
    return res.data

def set_trade_link(user_id, link):
    supabase.table("users").update({"trade_link": link}).eq("id", user_id).execute()

# --- РОБОТА З ПРОМОКОДАМИ ---

def get_promocode(code):
    res = supabase.table("promocodes").select("*").eq("code", code.upper().strip()).execute()
    return res.data[0] if res.data else None

def list_all_promocodes():
    res = supabase.table("promocodes").select("*").execute()
    return res.data

def create_promocode(code, reward, uses):
    data = {"code": code.upper().strip(), "reward": reward, "uses_left": uses}
    try:
        res = supabase.table("promocodes").insert(data).execute()
        return len(res.data) > 0
    except:
        return False

def use_promocode(user_id, promo):
    # ФІКС: Використовуємо твою назву таблиці user_promocodes
    supabase.table("user_promocodes").insert({
        "user_id": user_id, 
        "promo_id": promo["id"]
    }).execute()
    
    # Мінусуємо кількість спроб у промокоду
    supabase.table("promocodes").update({
        "uses_left": promo["uses_left"] - 1
    }).eq("id", promo["id"]).execute()
    
    # Нараховуємо монети користувачеві
    return update_coins(user_id, promo["reward"])

def is_promo_used_by_user(user_id, promo_id):
    # ФІКС: Використовуємо твою назву таблиці user_promocodes
    res = supabase.table("user_promocodes").select("*").eq("user_id", user_id).eq("promo_id", promo_id).execute()
    return len(res.data) > 0

# --- РОБОТА ІЗ ЗАЯВКАМИ ---

def create_request(user_id, item_name, cost):
    data = {"user_id": user_id, "item_name": item_name, "cost": cost, "status": "pending"}
    res = supabase.table("requests").insert(data).execute()
    # Після створення заявки віднімаємо монети
    update_coins(user_id, -cost)
    return res.data[0]

def get_user_requests(user_id):
    res = supabase.table("requests").select("*").eq("user_id", user_id).execute()
    return res.data

def get_pending_requests():
    # Запит із приєднанням даних користувача
    res = supabase.table("requests").select("*, users(*)").eq("status", "pending").execute()
    return res.data
