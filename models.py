import sqlite3
import os
from contextlib import contextmanager
 
DB_PATH = os.environ.get("DB_PATH", "database/menu.db")
 
os.makedirs("database", exist_ok=True)
 
 
# ─── Connection helper ────────────────────────────────────────────────────────
@contextmanager
def get_db():
    """Context manager: always closes the connection, even on errors."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name: row["price"]
    conn.execute("PRAGMA journal_mode=WAL") # safe for concurrent reads
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
 
 
# ─── Schema ───────────────────────────────────────────────────────────────────
def create_database():
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS menu (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT    NOT NULL,
                price     REAL    NOT NULL,
                category  TEXT
            );
 
            -- session_id ties a cart to one browser/user
            CREATE TABLE IF NOT EXISTS orders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL,
                item_name  TEXT    NOT NULL,
                price      REAL    NOT NULL,
                quantity   INTEGER NOT NULL DEFAULT 1,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
 
            CREATE INDEX IF NOT EXISTS idx_orders_session
                ON orders(session_id);
        """)
 
 
# ─── Seed data ────────────────────────────────────────────────────────────────
SAMPLE_ITEMS = [
    ("Cheese Pizza",        250, "Main Course"),
    ("Paneer Burger",       180, "Snacks"),
    ("Veg Sandwich",        120, "Snacks"),
    ("Cold Coffee",         100, "Beverage"),
    ("Chocolate Shake",     150, "Beverage"),
    ("French Fries",         90, "Snacks"),
    ("Pasta Alfredo",       220, "Main Course"),
    ("Tandoori Paneer Roll",160, "Wraps"),
]
 
def insert_sample_data():
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM menu").fetchone()[0]
        if count == 0:
            conn.executemany(
                "INSERT INTO menu (item_name, price, category) VALUES (?, ?, ?)",
                SAMPLE_ITEMS,
            )
            print("✅ Sample data inserted.")
        else:
            print("⚠️  Menu already populated, skipping seed.")
 
 
# ─── Menu helpers ─────────────────────────────────────────────────────────────
def get_all_menu_items():
    with get_db() as conn:
        return conn.execute("SELECT * FROM menu ORDER BY category, item_name").fetchall()
 
 
def search_item(item_name: str):
    with get_db() as conn:
        return conn.execute(
            "SELECT * FROM menu WHERE LOWER(item_name) LIKE ?",
            (f"%{item_name.lower()}%",),
        ).fetchall()
 
 
def get_menu_by_category():
    """Returns {category: [rows]} dict — useful for formatted display."""
    items = get_all_menu_items()
    grouped: dict = {}
    for row in items:
        grouped.setdefault(row["category"], []).append(row)
    return grouped
 
 
# ─── Per-session cart helpers ─────────────────────────────────────────────────
def add_to_cart(session_id: str, item_name: str, quantity: int = 1) -> bool:
    """
    Returns True if item was found and added, False if item not on menu.
    Increments quantity if item already in this session's cart.
    """
    with get_db() as conn:
        item = conn.execute(
            "SELECT item_name, price FROM menu WHERE LOWER(item_name) = ?",
            (item_name.lower(),),
        ).fetchone()
 
        if not item:
            return False
 
        existing = conn.execute(
            "SELECT id, quantity FROM orders WHERE session_id=? AND LOWER(item_name)=?",
            (session_id, item_name.lower()),
        ).fetchone()
 
        if existing:
            conn.execute(
                "UPDATE orders SET quantity = quantity + ? WHERE id = ?",
                (quantity, existing["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO orders (session_id, item_name, price, quantity) VALUES (?,?,?,?)",
                (session_id, item["item_name"], item["price"], quantity),
            )
        return True
 
 
def get_cart(session_id: str):
    with get_db() as conn:
        return conn.execute(
            "SELECT item_name, price, quantity FROM orders WHERE session_id=?",
            (session_id,),
        ).fetchall()
 
 
def get_cart_total(session_id: str) -> float:
    with get_db() as conn:
        result = conn.execute(
            "SELECT COALESCE(SUM(price * quantity), 0) FROM orders WHERE session_id=?",
            (session_id,),
        ).fetchone()
        return result[0]
 
 
def clear_cart(session_id: str):
    with get_db() as conn:
        conn.execute("DELETE FROM orders WHERE session_id=?", (session_id,))
 
 
def remove_item_from_cart(session_id: str, item_name: str):
    with get_db() as conn:
        conn.execute(
            "DELETE FROM orders WHERE session_id=? AND LOWER(item_name)=?",
            (session_id, item_name.lower()),
        )
 
 
# ─── Completed orders archive (optional) ──────────────────────────────────────
def archive_order(session_id: str) -> float:
    """
    Moves current cart into a completed_orders table and clears the cart.
    Returns the final total.
    """
    with get_db() as conn:
        # Create archive table if it doesn't exist yet
        conn.execute("""
            CREATE TABLE IF NOT EXISTS completed_orders (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT    NOT NULL,
                item_name  TEXT    NOT NULL,
                price      REAL    NOT NULL,
                quantity   INTEGER NOT NULL,
                ordered_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cart = conn.execute(
            "SELECT item_name, price, quantity FROM orders WHERE session_id=?",
            (session_id,),
        ).fetchall()
 
        total = sum(r["price"] * r["quantity"] for r in cart)
 
        conn.executemany(
            "INSERT INTO completed_orders (session_id, item_name, price, quantity) VALUES (?,?,?,?)",
            [(session_id, r["item_name"], r["price"], r["quantity"]) for r in cart],
        )
        conn.execute("DELETE FROM orders WHERE session_id=?", (session_id,))
 
    return total
 
 
if __name__ == "__main__":
    create_database()
    insert_sample_data()
