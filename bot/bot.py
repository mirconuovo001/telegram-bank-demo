import asyncio, os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from bot.db import init_db, get_pool

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN non impostato (env).")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(message: types.Message):
    """Crea/aggiorna utente al primo /start e mostra il saldo."""
    user_id = message.from_user.id
    username = (message.from_user.username or "")[:64]

    pool = get_pool()
    async with pool.acquire() as conn:
        # UPSERT per creare o aggiornare l'utente
        await conn.execute("""
            INSERT INTO users(telegram_id, username)
            VALUES($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                updated_at = NOW();
        """, user_id, username)

        row = await conn.fetchrow(
            "SELECT balance FROM users WHERE telegram_id=$1", user_id
        )

    saldo = row["balance"]
    await message.answer(f"Bot attivo ✅\nSaldo attuale: € {saldo:.2f}")

async def main():
    await init_db()          # prepara DB e tabelle
    await dp.start_polling(bot)  # avvia il bot (polling)

if __name__ == "__main__":
    asyncio.run(main())
