import os
import sqlite3
import asyncio
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import uvicorn

# --- SOZLAMALAR ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_USERNAME = "Sizing_Telegram_Nikeringiz"  # Masalan: "GhsuAdmin" (@ siz yozing)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- BAZA (SQLite) SOZLAMALARI ---
def init_db():
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            plan TEXT DEFAULT 'Free',
            expiry_date TEXT,
            total_donated INTEGER DEFAULT 0
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS promo_codes (
            code TEXT PRIMARY KEY,
            discount_percent INTEGER,
            is_active INTEGER DEFAULT 1
        )
    """)
    cursor.execute("INSERT OR IGNORE INTO promo_codes VALUES ('GHSU2026', 20, 1)")
    conn.commit()
    conn.close()

init_db()

class PromoState(StatesGroup):
    waiting_for_code = State()

# --- LIFESPAN (Server & Bot) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    polling_task.cancel()

app = FastAPI(lifespan=lifespan)

# --- HELPER FUNKSIYALAR ---
def get_user(user_id, username):
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if not user:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?)", (user_id, username))
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
    conn.close()
    return user

def update_user_plan(user_id, plan_name, days=30):
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    expiry = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("UPDATE users SET plan = ?, expiry_date = ? WHERE user_id = ?", (plan_name, expiry, user_id))
    conn.commit()
    conn.close()

def add_donation(user_id, amount):
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET total_donated = total_donated + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

# --- BOT HANDLERLARI ---

@dp.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message, command: CommandObject):
    get_user(message.from_user.id, message.from_user.username)
    args = command.args

    if args.startswith("premium_plus"):
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Premium Plus Obuna",
            description="30 kunlik Premium Plus tarifi",
            payload="payload_premium_plus",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium Plus", amount=50)],
            need_phone_number=False
        )
    elif args.startswith("premium"):
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Premium Obuna",
            description="30 kunlik Premium tarifi",
            payload="payload_premium",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium", amount=25)],
            need_phone_number=False
        )
    elif args.startswith("donate"):
        try:
            amount = int(args.split("_")[1])
        except (IndexError, ValueError):
            amount = 10

        await bot.send_invoice(
            chat_id=message.chat.id,
            title="GHSU Loyihasiga Donat",
            description=f"Loyiha rivojiga {amount} Stars donat qilish",
            payload=f"payload_donate_{amount}",
            currency="XTR",
            prices=[types.LabeledPrice(label="Donat", amount=amount)],
            need_phone_number=False
        )

@dp.message(CommandStart())
async def handle_start(message: types.Message):
    get_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "👋 Xush kelibsiz! GHSU Company rasmiy botiga ulandingiz.\n\n"
        "📜 Buyruqlar:\n"
        "/promo - Promo-kod kiritish va chegirma olish\n"
        "/top - Eng ko'p donat qilganlar reytingi\n"
        "/myplan - Obuna holatini tekshirish"
    )

@dp.message(Command("promo"))
async def ask_promo(message: types.Message, state: FSMContext):
    await message.answer("🎟️ Promo-kodingizni kiriting:")
    await state.set_state(PromoState.waiting_for_code)

@dp.message(PromoState.waiting_for_code)
async def process_promo(message: types.Message, state: FSMContext):
    code = message.text.strip().upper()
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT discount_percent FROM promo_codes WHERE code = ? AND is_active = 1", (code,))
    promo = cursor.fetchone()
    conn.close()

    if promo:
        discount = promo[0]
        new_price = int(25 * (100 - discount) / 100)
        await message.answer(f"✅ Promo-kod tasdiqlandi! Premium tarif {discount}% chegirma bilan: **{new_price} Stars**.")
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Chegirmali Premium Obuna",
            description=f"Promo-kod qo'llanilgan ({discount}% chegirma)",
            payload="payload_premium_promo",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium (Chegirma)", amount=new_price)],
            need_phone_number=False
        )
    else:
        await message.answer("❌ Noto'g'ri yoki muddati o'tgan promo-kod!")
    await state.clear()

@dp.message(Command("top"))
async def show_top_donators(message: types.Message):
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, total_donated FROM users WHERE total_donated > 0 ORDER BY total_donated DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()

    if not top_users:
        await message.answer("🏆 Hozircha donat qilganlar ro'yxati bo'sh.")
        return

    text = "🏆 **Top Donat Qilganlar Reytingi (GHSU):**\n\n"
    for idx, (username, total) in enumerate(top_users, 1):
        uname = f"@{username}" if username else "Anonim"
        text += f"{idx}. {uname} — ⭐ {total} Stars\n"

    await message.answer(text, parse_mode="Markdown")

@dp.message(Command("myplan"))
async def check_my_plan(message: types.Message):
    user = get_user(message.from_user.id, message.from_user.username)
    plan, expiry = user[2], user[3]
    if plan == 'Free':
        await message.answer("Sizda hozircha **Bepul (Free)** tarif aktiv.")
    else:
        await message.answer(f"✨ Tarifingiz: **{plan}**\n⏳ Tugash muddati: {expiry}")

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    current_username = message.from_user.username
    if not current_username or current_username.lower() != ADMIN_USERNAME.lower():
        await message.answer("❌ Sizga bu bo'limga kirishga ruxsat berilmadi.")
        return

    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM users WHERE plan != 'Free'")
    total_premium = cursor.fetchone()[0]

    cursor.execute("SELECT SUM(total_donated) FROM users")
    total_stars_donated = cursor.fetchone()[0] or 0
    conn.close()

    admin_text = (
        f"👑 **GHSU Admin Paneli**\n\n"
        f"👥 Jami foydalanuvchilar: **{total_users} ta**\n"
        f"⭐ Faol Premium a'zolar: **{total_premium} ta**\n"
        f"🎁 Jami yig'ilgan donat: **{total_stars_donated} Stars**\n"
    )
    await message.answer(admin_text, parse_mode="Markdown")

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username
    get_user(user_id, username)
    
    total = message.successful_payment.total_amount
    payload = message.successful_payment.invoice_payload

    if "premium_plus" in payload:
        update_user_plan(user_id, "Premium Plus", days=30)
        await message.answer("✨ Tabriklaymiz! 30 kunlik **Premium Plus** obunangiz faollashtirildi!")
    elif "premium" in payload:
        update_user_plan(user_id, "Premium", days=30)
        await message.answer("⭐ Tabriklaymiz! 30 kunlik **Premium** obunangiz faollashtirildi!")
    else:
        add_donation(user_id, total)
        await message.answer(f"🚀 Katta rahmat! Loyihamizni {total} Stars bilan qo'llab-quvvatladingiz!")

# --- FASTAPI ENDPOINTLARI ---

@app.get("/api/top-donators")
async def get_top_donators():
    conn = sqlite3.connect("ghsu_database.db")
    cursor = conn.cursor()
    cursor.execute("SELECT username, total_donated FROM users WHERE total_donated > 0 ORDER BY total_donated DESC LIMIT 10")
    top_users = cursor.fetchall()
    conn.close()
    
    result = []
    for username, total in top_users:
        result.append({
            "username": f"@{username}" if username else "Anonim",
            "total": total
        })
    return result

@app.get("/", response_class=HTMLResponse)
async def read_index():
    if os.path.exists("index.html"):
        with open("index.html", "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>index.html topilmadi</h1>"

if __name__ == "__main__":
    port = int(os.getenv("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
