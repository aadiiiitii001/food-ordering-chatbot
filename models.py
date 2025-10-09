import sqlite3
import os

DB_PATH = "database/menu.db"

# ✅ Ensure database folder exists
os.makedirs("database", exist_ok=True)


def create_database():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Menu Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            price REAL NOT NULL,
            category TEXT
        )
    """)

    # Order Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def insert_sample_data():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    sample_items = [
        ("Cheese Pizza", 250, "Main Course"),
        ("Paneer Burger", 180, "Snacks"),
        ("Veg Sandwich", 120, "Snacks"),
        ("Cold Coffee", 100, "Beverage"),
        ("Chocolate Shake", 150, "Beverage"),
        ("French Fries", 90, "Snacks"),
        ("Pasta Alfredo", 220, "Main Course"),
        ("Tandoori Paneer Roll", 160, "Wraps"),
    ]

    cursor.execute("SELECT COUNT(*) FROM menu")
    count = cursor.fetchone()[0]

    if count == 0:
        cursor.executemany("INSERT INTO menu (item_name, price, category) VALUES (?, ?, ?)", sample_items)
        print("✅ Sample data inserted successfully!")
    else:
        print("⚠️ Data already exists, skipping insertion.")

    conn.commit()
    conn.close()


# 🍽️ Fetch all menu items
def get_all_menu_items():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu")
    data = cursor.fetchall()
    conn.close()
    return data


# 🔍 Search for item in the menu
def search_item(item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE LOWER(item_name) LIKE ?", (f"%{item_name.lower()}%",))
    data = cursor.fetchall()
    conn.close()
    return data


# 🛒 Add item to order
def add_to_order(item_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, price FROM menu WHERE LOWER(item_name)=?", (item_name.lower(),))
    result = cursor.fetchone()

    if result:
        cursor.execute("INSERT INTO orders (item_name, price) VALUES (?, ?)", (result[0], result[1]))
        conn.commit()

    conn.close()


# 📋 Get current order
def get_current_order():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT item_name, price FROM orders")
    order = cursor.fetchall()
    conn.close()
    return order


# 🧹 Clear current order
def clear_order():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM orders")
    conn.commit()
    conn.close()


# Initialize database & data
if __name__ == "__main__":
    create_database()
    insert_sample_data()