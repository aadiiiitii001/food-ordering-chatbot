from flask import Flask, render_template, request, jsonify
from models import search_item, create_database, insert_sample_data
import random

app = Flask(__name__)

# Initialize database
create_database()
insert_sample_data()

# Temporary order cart (reset each time server restarts)
cart = []

@app.route("/")
def home():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    global cart
    user_msg = request.json.get("message", "").lower().strip()

    if not user_msg:
        return jsonify({"reply": "Please say something 😊"})

    # 🧾 Show menu
    if "menu" in user_msg:
        results = search_item("")
        menu_list = [f"🍴 {r[1]} — ₹{r[2]}" for r in results]
        return jsonify({"reply": "Here's our menu:\n" + "\n".join(menu_list)})

    # 🛒 Add to cart / order items
    elif any(word in user_msg for word in ["order", "bring", "want", "add", "cart"]):
        ordered_items = []
        all_menu = search_item("")

        for item in all_menu:
            name = item[1].lower()
            price = item[2]
            if name in user_msg:
                ordered_items.append((name, price))
                cart.append((name, price))

        if not ordered_items:
            return jsonify({"reply": "❌ Sorry, that item isn't on the menu right now."})

        reply = "✅ Added to your cart: " + ", ".join([i[0].title() for i in ordered_items])
        total = sum([p for _, p in cart])
        reply += f"\n🛍️ Current total: ₹{total}"
        return jsonify({"reply": reply})

    # 🧾 Show current cart
    elif "show cart" in user_msg or "my order" in user_msg:
        if not cart:
            return jsonify({"reply": "🛒 Your cart is empty."})
        items = "\n".join([f"🍴 {i[0].title()} — ₹{i[1]}" for i in cart])
        total = sum([p for _, p in cart])
        return jsonify({"reply": f"🛍️ Your current cart:\n{items}\n\n💰 Total: ₹{total}"})

    # 🙏 Checkout / thank you
    elif any(word in user_msg for word in ["checkout", "done", "thank", "pay"]):
        if not cart:
            return jsonify({"reply": "🛒 Your cart is empty! Please order something first."})
        total = sum([p for _, p in cart])
        cart.clear()
        return jsonify({"reply": f"✅ Thank you for your order! Your total is ₹{total}. 😊"})

    # 🧹 Clear cart
    elif "clear" in user_msg or "cancel" in user_msg:
        cart.clear()
        return jsonify({"reply": "🧹 Cart cleared!"})

    # 🤖 Recommend dish
    elif "recommend" in user_msg:
        results = search_item("")
        suggestion = random.choice(results)
        return jsonify({"reply": f"🍽️ How about trying {suggestion[1]} for ₹{suggestion[2]}?"})

    # 💬 Default reply
    else:
        return jsonify({
            "reply": "🤖 I didn’t understand. Try:\n"
                     "- 'show menu'\n"
                     "- 'order cheese pizza'\n"
                     "- 'show cart'\n"
                     "- 'checkout'\n"
                     "- 'recommend me something'"
        })


if __name__ == "__main__":
    app.run(debug=True)
