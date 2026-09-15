from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, CommandObject
import asyncio

BOT_TOKEN = "YOUR_BOT_TOKEN" # BotFather'dan olingan token
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Saytdan t.me/bot?start=parametr orqali kirganda ishlaydigan xandler
@dp.message(CommandStart(deep_link=True))
async def handle_deep_link(message: types.Message, command: CommandObject):
    args = command.args  # Masalan: "premium_25", "premium_plus_50", "donate_100"
    
    if args.startswith("premium_plus"):
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Premium Plus Obuna",
            description="GHSU platformasi uchun Premium Plus tarifi",
            payload="payload_premium_plus",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium Plus", amount=50)], # 50 Stars
            need_phone_number=False
        )
    elif args.startswith("premium"):
        await bot.send_invoice(
            chat_id=message.chat.id,
            title="Premium Obuna",
            description="GHSU platformasi uchun Premium tarifi",
            payload="payload_premium",
            currency="XTR",
            prices=[types.LabeledPrice(label="Premium", amount=25)], # 25 Stars
            need_phone_number=False
        )
    elif args.startswith("donate"):
        # donate_50 ko'rinishidagi parametrdan Stars sonini ajratib olish
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

# Oddiy /start bosilganda
@dp.message(CommandStart())
async def handle_start(message: types.Message):
    await message.answer("Xush kelibsiz! GHSU platformasi rasmiy botiga xush kelibsiz.")

# To'lov oldidan tasdiqlash
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

# To'lov muvaffaqiyatli o'tganda
@dp.message(F.successful_payment)
async def process_successful_payment(message: types.Message):
    stars_amount = message.successful_payment.total_amount
    payload = message.successful_payment.invoice_payload

    if "premium_plus" in payload:
        await message.answer("Rahmat! Premium Plus obunangiz muvaffaqiyatli faollashtirildi! ✨")
    elif "premium" in payload:
        await message.answer("Rahmat! Premium obunangiz muvaffaqiyatli faollashtirildi! ⭐")
    else:
        await message.answer(f"Katta rahmat! Loyihani {stars_amount} Stars bilan qo'llab-quvvatlaganingiz uchun tashakkur! 🚀")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
