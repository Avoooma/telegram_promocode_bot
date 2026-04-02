import os
from supabase import create_client

# Дані з Variables у Railway
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
    # Отримуємо баланс
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
    # ВИПРАВЛЕНО: назва колонки promocode_id (як у твоєму SQL)
    supabase.table("user_promocodes").insert({
        "user_id": user_id, 
        "promocode_id": promo["id"]
    }).execute()
    
    # Зменшуємо ліміт використань
    supabase.table("promocodes").update({
        "uses_left": promo["uses_left"] - 1
    }).eq("id", promo["id"]).execute()
    
    # Нараховуємо монети
    return update_coins(user_id, promo["reward"])

def is_promo_used_by_user(user_id, promo_id):
    # ВИПРАВЛЕНО: назва колонки promocode_id (як у твоєму SQL)
    res = supabase.table("user_promocodes").select("*").eq("user_id", user_id).eq("promocode_id", promo_id).execute()
    return len(res.data) > 0

# --- РОБОТА ІЗ ЗАЯВКАМИ ---

def create_request(user_id, item_name, cost):
    data = {"user_id": user_id, "item_name": item_name, "cost": cost, "status": "pending"}
    res = supabase.table("requests").insert(data).execute()
    # Списуємо монети одразу при створенні заявки
    update_coins(user_id, -cost)
    return res.data[0]

def get_user_requests(user_id):
    res = supabase.table("requests").select("*").eq("user_id", user_id).execute()
    return res.data

def get_pending_requests():
    # Запит із приєднанням даних користувача (users)
    res = supabase.table("requests").select("*, users(*)").eq("status", "pending").execute()
    return res.data

def delete_promocode(promo_id):
    # Спочатку видаляємо всі записи про використання цього коду (інакше база не дасть видалити сам код)
    supabase.table("user_promocodes").delete().eq("promocode_id", promo_id).execute()
    # Тепер видаляємо сам промокод
    res = supabase.table("promocodes").delete().eq("id", promo_id).execute()
    return len(res.data) > 0

def get_user_transactions(user_id, limit=5):
    res = supabase.table("transactions").select("*").eq("user_id", user_id).order("date", desc=True).limit(limit).execute()
    return res.data
