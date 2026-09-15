import os
import asyncio
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
import uvicorn

# 1. FastAPI Web Server va Bot sozlamalari
app = FastAPI()
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 2. Telegram Bot logikasi (Deep Linking va Stars Payment)
@dp.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message, command: CommandObject):
    args = command.args
    
    if args.startswith("premium_plus"):
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Premium Plus Obuna",
            description="GHSU platformasi uchun Premium Plus tarifi",
            payload="payload_premium_plus",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium Plus", amount=50)],
            need_phone_number=False
        )
    elif args.startswith("premium"):
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Premium Obuna",
            description="GHSU platformasi uchun Premium tarifi",
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
    await message.answer("Xush kelibsiz! GHSU platformasi rasmiy botiga xush kelibsiz.")

@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    stars_amount = message.successful_payment.total_amount
    payload = message.successful_payment.invoice_payload

    if "premium_plus" in payload:
        await message.answer("Rahmat! Premium Plus obunangiz faollashtirildi! ✨")
    elif "premium" in payload:
        await message.answer("Rahmat! Premium obunangiz faollashtirildi! ⭐")
    else:
        await message.answer(f"Katta rahmat! Loyihani {stars_amount} Stars bilan qo'llab-quvvatlaganingiz uchun tashakkur! 🚀")

# 3. HTML Saytni ko'rsatish (Web Route)
@app.get("/", response_class=HTMLResponse)
async def read_index():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

# 4. Server va Botni bir vaqtda ishga tushirish (Lifespan)
@app.on_event("startup")
async def on_startup():
    asyncio.create_task(dp.start_polling(bot))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=10000)
