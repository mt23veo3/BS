import csv
from services.constants import TRADE_LOG

def safe_load_csv(path):
    result = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                result.append(row)
    except Exception:
        pass
    return result

def get_all_orders(page=1, page_size=50):
    orders = safe_load_csv(TRADE_LOG)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "total": len(orders),
        "page": page,
        "page_size": page_size,
        "orders": orders[start:end]
    }

def get_open_orders():
    orders = safe_load_csv(TRADE_LOG)
    return [o for o in orders if o.get("status", "").lower() == "open"]

def get_closed_orders():
    orders = safe_load_csv(TRADE_LOG)
    return [o for o in orders if o.get("status", "").lower() == "closed"]

def get_order_by_id(order_id):
    orders = safe_load_csv(TRADE_LOG)
    for o in orders:
        if o.get("order_id", "") == order_id:
            return o
    return {}