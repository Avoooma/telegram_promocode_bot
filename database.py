import os
from supabase import create_client

# Дані з Variables у Railway
URL = os.getenv("SUPABASE_URL")
KEY = os.getenv("SUPABASE_KEY")
supabase = create_client(URL, KEY)

# --- НОВА ФУНКЦІЯ: ЗАПИС ТРАНЗАКЦІЇ ---

def add_transaction(user_id, t_type, amount, description):
    """
    Додає запис у таблицю transactions.
    user_id — це внутрішній ID користувача (int4) з таблиці users.
    """
    try:
        data = {
            "user_id": user_id,
            "type": t_type,
            "amount": amount,
            "description": description
        }
        supabase.table("transactions").insert(data).execute()
    except Exception as e:
        print(f"Помилка запису транзакції: {e}")

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
    res = supabase.table("users").select("coins").eq("id", user_id).execute()
    if not res.data:
        return 0
    new_balance = res.data[0]["coins"] + delta
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
    # 1. Реєструємо використання коду юзером
    supabase.table("user_promocodes").insert({
        "user_id": user_id, 
        "promocode_id": promo["id"]
    }).execute()
    
    # 2. Зменшуємо ліміт використань самого коду
    supabase.table("promocodes").update({
        "uses_left": promo["uses_left"] - 1
    }).eq("id", promo["id"]).execute()
    
    # 3. ДОДАЄМО ЗАПИС В ІСТОРІЮ
    add_transaction(user_id, "ПРОМОКОД", promo["reward"], f"Активація коду: {promo['code']}")
    
    # 4. Нараховуємо монети
    return update_coins(user_id, promo["reward"])

def is_promo_used_by_user(user_id, promo_id):
    res = supabase.table("user_promocodes").select("*").eq("user_id", user_id).eq("promocode_id", promo_id).execute()
    return len(res.data) > 0

# --- РОБОТА ІЗ ЗАЯВКАМИ ---

def create_request(user_id, item_name, cost):
    # 1. Створюємо саму заявку
    data = {"user_id": user_id, "item_name": item_name, "cost": cost, "status": "pending"}
    res = supabase.table("requests").insert(data).execute()
    
    # 2. ДОДАЄМО ЗАПИС ПРО СПИСАННЯ В ІСТОРІЮ
    add_transaction(user_id, "СПИСАННЯ", -cost, f"Заявка: {item_name}")
    
    # 3. Списуємо монети з балансу
    update_coins(user_id, -cost)
    return res.data[0] if res.data else None

def get_user_requests(user_id):
    res = supabase.table("requests").select("*").eq("user_id", user_id).execute()
    return res.data

def get_pending_requests():
    res = supabase.table("requests").select("*, users(*)").eq("status", "pending").execute()
    return res.data

def delete_promocode(promo_id):
    supabase.table("user_promocodes").delete().eq("promocode_id", promo_id).execute()
    res = supabase.table("promocodes").delete().eq("id", promo_id).execute()
    return len(res.data) > 0

# --- ІСТОРІЯ ТРАНЗАКЦІЙ ---

def get_user_transactions(user_id, limit=5):
    res = supabase.table("transactions").select("*").eq("user_id", user_id).order("date", desc=True).limit(limit).execute()
    return res.data
