from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY
from datetime import datetime

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


# ─────────────────────────────────────────────
#  USERS
# ─────────────────────────────────────────────

def get_or_create_user(telegram_id: int, username: str) -> dict:
    """Повертає користувача або створює нового."""
    res = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    if res.data:
        return res.data[0]
    new = supabase.table("users").insert({
        "telegram_id": telegram_id,
        "username": username,
        "coins": 0
    }).execute()
    return new.data[0]


def get_user_by_telegram_id(telegram_id: int) -> dict | None:
    res = supabase.table("users").select("*").eq("telegram_id", telegram_id).execute()
    return res.data[0] if res.data else None


def get_user_by_id(user_id: int) -> dict | None:
    res = supabase.table("users").select("*").eq("id", user_id).execute()
    return res.data[0] if res.data else None


def update_coins(user_id: int, delta: int) -> int:
    """Додає або знімає монети. Повертає новий баланс."""
    user = get_user_by_id(user_id)
    new_balance = max(0, user["coins"] + delta)
    supabase.table("users").update({"coins": new_balance}).eq("id", user_id).execute()
    return new_balance


def set_trade_link(user_id: int, trade_link: str):
    supabase.table("users").update({"trade_link": trade_link}).eq("id", user_id).execute()


def get_top_users(limit: int = 10) -> list:
    res = supabase.table("users").select("username, coins").order("coins", desc=True).limit(limit).execute()
    return res.data


# ─────────────────────────────────────────────
#  PROMOCODES
# ─────────────────────────────────────────────

def get_promocode(code: str) -> dict | None:
    res = supabase.table("promocodes").select("*").eq("code", code).execute()
    return res.data[0] if res.data else None


def is_promo_used_by_user(user_id: int, promocode_id: int) -> bool:
    res = supabase.table("user_promocodes")\
        .select("*")\
        .eq("user_id", user_id)\
        .eq("promocode_id", promocode_id)\
        .execute()
    return bool(res.data)


def use_promocode(user_id: int, promo: dict) -> int:
    """Активує промокод: списує використання, записує зв'язок та транзакцію."""
    # Зменшуємо uses_left
    supabase.table("promocodes").update({"uses_left": promo["uses_left"] - 1})\
        .eq("id", promo["id"]).execute()

    # Фіксуємо що юзер використав цей промокод
    supabase.table("user_promocodes").insert({
        "user_id": user_id,
        "promocode_id": promo["id"]
    }).execute()

    # Нараховуємо монети
    new_balance = update_coins(user_id, promo["reward"])

    # Транзакція
    add_transaction(user_id, "earn", promo["reward"], f"Промокод: {promo['code']}")

    return new_balance


def create_promocode(code: str, reward: int, uses: int) -> bool:
    """Повертає False якщо промокод вже існує."""
    existing = get_promocode(code)
    if existing:
        return False
    supabase.table("promocodes").insert({
        "code": code,
        "reward": reward,
        "uses_left": uses
    }).execute()
    return True


def list_promocodes() -> list:
    res = supabase.table("promocodes").select("*").order("id", desc=True).execute()
    return res.data


def delete_promocode(code: str) -> bool:
    promo = get_promocode(code)
    if not promo:
        return False
    supabase.table("promocodes").delete().eq("id", promo["id"]).execute()
    return True


# ─────────────────────────────────────────────
#  TRANSACTIONS
# ─────────────────────────────────────────────

def add_transaction(user_id: int, tx_type: str, amount: int, description: str):
    supabase.table("transactions").insert({
        "user_id": user_id,
        "type": tx_type,
        "amount": amount,
        "description": description,
        "date": datetime.utcnow().isoformat()
    }).execute()


def get_user_transactions(user_id: int, limit: int = 10) -> list:
    res = supabase.table("transactions")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("date", desc=True)\
        .limit(limit)\
        .execute()
    return res.data


# ─────────────────────────────────────────────
#  REQUESTS (заявки на обмін)
# ─────────────────────────────────────────────

def create_request(user_id: int, item_name: str, cost: int) -> dict:
    res = supabase.table("requests").insert({
        "user_id": user_id,
        "item_name": item_name,
        "cost": cost,
        "status": "pending"
    }).execute()
    return res.data[0]


def get_pending_requests() -> list:
    res = supabase.table("requests")\
        .select("*, users(telegram_id, username, trade_link)")\
        .eq("status", "pending")\
        .order("id")\
        .execute()
    return res.data


def get_request_by_id(request_id: int) -> dict | None:
    res = supabase.table("requests")\
        .select("*, users(telegram_id, username, coins, trade_link)")\
        .eq("id", request_id)\
        .execute()
    return res.data[0] if res.data else None


def update_request_status(request_id: int, status: str):
    supabase.table("requests").update({"status": status}).eq("id", request_id).execute()


def get_user_requests(user_id: int) -> list:
    res = supabase.table("requests")\
        .select("*")\
        .eq("user_id", user_id)\
        .order("id", desc=True)\
        .execute()
    return res.data
