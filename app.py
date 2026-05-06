import os
import random
import uuid
import re
 
from flask import Flask, render_template, request, jsonify, session
from models import (
    create_database, insert_sample_data,
    get_all_menu_items, get_menu_by_category, search_item,
    add_to_cart, get_cart, get_cart_total, clear_cart,
    remove_item_from_cart, archive_order,
)
 
# ── Optional: Claude AI for NLP (set ANTHROPIC_API_KEY in .env to enable) ─────
try:
    import anthropic
    AI_CLIENT = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    AI_ENABLED = True
except Exception:
    AI_CLIENT = None
    AI_ENABLED = False
 
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-me-in-production")  # REQUIRED for sessions
 
create_database()
insert_sample_data()
 
 
# ─── Helpers ──────────────────────────────────────────────────────────────────
 
def get_session_id() -> str:
    """Each browser gets its own cart via Flask session."""
    if "session_id" not in session:
        session["session_id"] = str(uuid.uuid4())
    return session["session_id"]
 
 
def format_menu() -> str:
    grouped = get_menu_by_category()
    lines = []
    for category, items in grouped.items():
        lines.append(f"\n📂 {category}")
        for item in items:
            lines.append(f"  🍴 {item['item_name']} — ₹{item['price']:.0f}")
    return "Here's our menu:" + "\n".join(lines)
 
 
def format_cart(session_id: str) -> str:
    cart = get_cart(session_id)
    if not cart:
        return "🛒 Your cart is empty."
    lines = [f"  🍴 {r['item_name']} × {r['quantity']} — ₹{r['price'] * r['quantity']:.0f}" for r in cart]
    total = get_cart_total(session_id)
    return "🛍️ Your cart:\n" + "\n".join(lines) + f"\n\n💰 Total: ₹{total:.0f}"
 
 
def find_items_in_text(text: str) -> list[str]:
    """
    Scan user message for menu item names.
    Returns list of matched item names (exact DB spelling).
    """
    all_items = get_all_menu_items()
    found = []
    for item in all_items:
        if item["item_name"].lower() in text:
            found.append(item["item_name"])
    return found
 
 
def extract_quantity(text: str) -> int:
    """Extract a number from text like '2 pizzas' → 2. Defaults to 1."""
    match = re.search(r"\b([1-9])\b", text)
    return int(match.group(1)) if match else 1
 
 
# ─── AI-powered intent detection (optional) ───────────────────────────────────
 
def detect_intent_with_ai(user_msg: str) -> dict:
    """
    Ask Claude to parse the user's message and return structured JSON intent.
    Falls back gracefully if API is unavailable.
    """
    menu_names = [row["item_name"] for row in get_all_menu_items()]
    prompt = f"""You are the backend of a food ordering chatbot.
Menu items: {menu_names}
 
User message: "{user_msg}"
 
Reply ONLY with a JSON object, no markdown:
{{
  "intent": one of ["show_menu", "add_to_cart", "show_cart", "checkout", "clear_cart", "remove_item", "recommend", "greet", "unknown"],
  "items": [list of menu item names the user wants, exact spelling from the menu],
  "quantity": integer (default 1)
}}"""
 
    response = AI_CLIENT.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    import json
    return json.loads(response.content[0].text)
 
 
# ─── Rule-based intent detection (fallback) ───────────────────────────────────
 
def detect_intent_rule_based(text: str) -> dict:
    t = text.lower()
    quantity = extract_quantity(t)
 
    if any(w in t for w in ["menu", "what do you have", "food", "dishes", "show items"]):
        return {"intent": "show_menu", "items": [], "quantity": 1}
 
    if any(w in t for w in ["show cart", "my order", "my cart", "what did i order"]):
        return {"intent": "show_cart", "items": [], "quantity": 1}
 
    if any(w in t for w in ["checkout", "done", "pay", "place order", "confirm"]):
        return {"intent": "checkout", "items": [], "quantity": 1}
 
    if any(w in t for w in ["clear cart", "cancel", "remove all", "start over"]):
        return {"intent": "clear_cart", "items": [], "quantity": 1}
 
    if any(w in t for w in ["recommend", "suggest", "surprise me", "what's good", "best"]):
        return {"intent": "recommend", "items": [], "quantity": 1}
 
    if any(w in t for w in ["remove", "delete", "take out"]):
        items = find_items_in_text(t)
        return {"intent": "remove_item", "items": items, "quantity": 1}
 
    if any(w in t for w in ["order", "want", "add", "get me", "bring", "i'll have", "give me"]):
        items = find_items_in_text(t)
        return {"intent": "add_to_cart", "items": items, "quantity": quantity}
 
    if any(w in t for w in ["hi", "hello", "hey", "good morning", "good evening"]):
        return {"intent": "greet", "items": [], "quantity": 1}
 
    # Last attempt: maybe they just typed an item name
    items = find_items_in_text(t)
    if items:
        return {"intent": "add_to_cart", "items": items, "quantity": quantity}
 
    return {"intent": "unknown", "items": [], "quantity": 1}
 
 
def parse_intent(user_msg: str) -> dict:
    if AI_ENABLED:
        try:
            return detect_intent_with_ai(user_msg)
        except Exception as e:
            print(f"⚠️  AI intent failed, falling back to rules: {e}")
    return detect_intent_rule_based(user_msg)
 
 
# ─── Routes ───────────────────────────────────────────────────────────────────
 
@app.route("/")
def home():
    return render_template("index.html")
 
 
@app.route("/chat", methods=["POST"])
def chat():
    user_msg = request.json.get("message", "").strip()
    if not user_msg:
        return jsonify({"reply": "Please say something 😊"})
 
    sid = get_session_id()
    parsed = parse_intent(user_msg)
    intent = parsed.get("intent", "unknown")
    items = parsed.get("items", [])
    qty = parsed.get("quantity", 1)
 
    # ── Show menu ──────────────────────────────────────────────────────────────
    if intent == "show_menu":
        return jsonify({"reply": format_menu()})
 
    # ── Greet ─────────────────────────────────────────────────────────────────
    elif intent == "greet":
        return jsonify({"reply": "👋 Hello! I'm your food assistant. Type 'menu' to see our dishes, or just tell me what you'd like to order!"})
 
    # ── Add to cart ───────────────────────────────────────────────────────────
    elif intent == "add_to_cart":
        if not items:
            return jsonify({"reply": "❌ I couldn't find that item on our menu. Type 'menu' to see what we have."})
        added = []
        for item_name in items:
            if add_to_cart(sid, item_name, qty):
                added.append(item_name)
        if not added:
            return jsonify({"reply": "❌ Sorry, none of those items are on our menu right now."})
        total = get_cart_total(sid)
        reply = "✅ Added: " + ", ".join(added)
        if qty > 1:
            reply += f" × {qty}"
        reply += f"\n🛍️ Cart total: ₹{total:.0f}"
        return jsonify({"reply": reply})
 
    # ── Show cart ─────────────────────────────────────────────────────────────
    elif intent == "show_cart":
        return jsonify({"reply": format_cart(sid)})
 
    # ── Remove item ───────────────────────────────────────────────────────────
    elif intent == "remove_item":
        if not items:
            return jsonify({"reply": "❌ Which item should I remove? (e.g. 'remove cheese pizza')"})
        for item_name in items:
            remove_item_from_cart(sid, item_name)
        return jsonify({"reply": f"🗑️ Removed {', '.join(items)} from your cart.\n" + format_cart(sid)})
 
    # ── Checkout ──────────────────────────────────────────────────────────────
    elif intent == "checkout":
        cart = get_cart(sid)
        if not cart:
            return jsonify({"reply": "🛒 Your cart is empty! Please add items first."})
        total = archive_order(sid)
        return jsonify({"reply": f"🎉 Order placed! Your total is ₹{total:.0f}.\nThank you! Estimated delivery: 30–40 minutes. 🛵"})
 
    # ── Clear cart ────────────────────────────────────────────────────────────
    elif intent == "clear_cart":
        clear_cart(sid)
        return jsonify({"reply": "🧹 Cart cleared. Start fresh anytime!"})
 
    # ── Recommend ─────────────────────────────────────────────────────────────
    elif intent == "recommend":
        all_items = get_all_menu_items()
        pick = random.choice(all_items)
        return jsonify({"reply": f"🍽️ I'd recommend the **{pick['item_name']}** for ₹{pick['price']:.0f}! It's one of our best. Want to add it? Just say 'add {pick['item_name']}'"})
 
    # ── Unknown ───────────────────────────────────────────────────────────────
    else:
        return jsonify({
            "reply": (
                "🤖 I didn't quite get that. Try:\n"
                "• 'show menu'\n"
                "• 'order cheese pizza'\n"
                "• 'add 2 french fries'\n"
                "• 'show cart'\n"
                "• 'remove paneer burger'\n"
                "• 'checkout'\n"
                "• 'recommend me something'"
            )
        })
 
 
# ─── API endpoints (bonus — useful for a future mobile app) ───────────────────
 
@app.route("/api/menu", methods=["GET"])
def api_menu():
    items = get_all_menu_items()
    return jsonify([dict(row) for row in items])
 
 
@app.route("/api/cart", methods=["GET"])
def api_cart():
    sid = get_session_id()
    cart = get_cart(sid)
    return jsonify({
        "items": [dict(row) for row in cart],
        "total": get_cart_total(sid),
    })
 
 
if __name__ == "__main__":
    app.run(debug=True)
