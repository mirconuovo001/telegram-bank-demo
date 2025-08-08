import os, asyncio
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from bot.db import init_db, get_pool

# --- Env ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN non impostato (env).")

# --- Aiogram ---
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def on_start(message: types.Message):
    """Crea/aggiorna utente al primo /start e mostra il saldo."""
    user_id = message.from_user.id
    username = (message.from_user.username or "")[:64]

    pool = get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users(telegram_id, username)
            VALUES($1, $2)
            ON CONFLICT (telegram_id) DO UPDATE SET
                username = EXCLUDED.username,
                updated_at = NOW();
        """, user_id, username)
        row = await conn.fetchrow("SELECT balance FROM users WHERE telegram_id=$1", user_id)

    saldo = row["balance"]
    await message.answer(f"Bot attivo ✅\nSaldo attuale: € {saldo:.2f}")

# --- Mini web server per Render (porta obbligatoria) ---
async def handle_root(request):
    return web.Response(text="ok")

async def start_web_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/health", handle_root)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))  # Render fornisce $PORT
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    # Mantieni vivo il server
    while True:
        await asyncio.sleep(3600)

async def main():
    await init_db()  # prepara DB e tabelle
    # Avvia in parallelo: HTTP + bot
    await asyncio.gather(
        start_web_app(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())

import asyncio
from aiohttp import web

async def handle(request):
    return web.Response(text="ok")

async def health(request):
    return web.Response(text="healthy")

app = web.Application()
app.router.add_get("/", handle)
app.router.add_get("/health", health)

loop = asyncio.get_event_loop()

# Avvia sia il bot sia il mini server HTTP
async def main():
    from aiogram import executor
    loop.create_task(web._run_app(app, host="0.0.0.0", port=10000))
    executor.start_polling(dp, skip_updates=True)

if __name__ == "__main__":
    loop.run_until_complete(main())

