import os
import sys
import time
import re
import asyncio
import configparser
import psutil 
import requests
import random
import string
import platform
from datetime import datetime

from pyrogram import Client, filters, idle, enums
from pyrogram.errors import FloodWait

# ==========================================
# ⚙️ 1. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ
# ==========================================

START_TIME = time.time()
LOCAL_BANNER = "banner.jpg"

if not os.path.exists("modules"):
    os.makedirs("modules")

config = configparser.ConfigParser()
config.read("config.ini")

# Создаем конфиг, если нет
if not config.has_section('pyrogram'):
    print("⚙️ Первичная настройка...")
    api_id = input("Введи API_ID: ")
    api_hash = input("Введи API_HASH: ")
    
    config.add_section('pyrogram')
    config.set('pyrogram', 'api_id', api_id)
    config.set('pyrogram', 'api_hash', api_hash)

# Проверяем секцию логов
if not config.has_section('bot_logs'):
    config.add_section('bot_logs')
    config.set('bot_logs', 'bot_token', '')
    config.set('bot_logs', 'log_chat_id', '')

with open("config.ini", "w") as f:
    config.write(f)

api_id = config['pyrogram']['api_id']
api_hash = config['pyrogram']['api_hash']

app = Client(
    "Rikki_Product_Userbot",
    api_id=api_id,
    api_hash=api_hash,
    plugins=dict(root="modules") 
)

# --- ХЕЛПЕРЫ ---

def save_config(token=None, chat_id=None):
    config.read("config.ini")
    if not config.has_section('bot_logs'): config.add_section('bot_logs')
    if token: config.set('bot_logs', 'bot_token', token)
    if chat_id: config.set('bot_logs', 'log_chat_id', str(chat_id))
    with open("config.ini", "w") as f: config.write(f)

def random_str(length=4):
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))

def send_via_requests(token, chat_id, text):
    if not token or not chat_id: return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
        )
    except: pass

async def generate_info_text(client):
    def get_time_str(seconds):
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        return f"{int(d)}d {int(h)}h {int(m)}m" if d > 0 else f"{int(h)}h {int(m)}m {int(s)}s"

    uptime = get_time_str(int(time.time() - START_TIME))
    cpu = psutil.cpu_percent()
    ram = psutil.virtual_memory().percent
    
    def bar(p): return "▰" * int(p/10) + "▱" * (10 - int(p/10))
    me = await client.get_me()
    text = (
        f"🚀 **Система Запущена!**\n\n"
        f"👤 **Владелец:** {me.mention}\n"
        f"⏳ **Uptime:** `{uptime}`\n\n"
        f"⚙️ **CPU:** `{cpu}%`\n{bar(cpu)}\n"
        f"🧠 **RAM:** `{ram}%`\n{bar(ram)}\n"
        f"💻 **Система:** `{platform.system()} {platform.release()}`"
    )
    return text

def send_log_to_bot(token, chat_id, text, photo_path=None):
    if not token or not chat_id: return
    try:
        if photo_path and os.path.exists(photo_path):
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            with open(photo_path, 'rb') as f:
                requests.post(url, data={'chat_id': chat_id, 'caption': text, 'parse_mode': 'Markdown'}, files={'photo': f})
        else:
            requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown"})
    except: pass


# ==========================================
# 🚀 2. АВТО-НАСТРОЙКА (С ЗАДЕРЖКАМИ)
# ==========================================
async def auto_setup_logs(client):
    print("🔄 Проверка системы логов...")
    config.read("config.ini")
    token = config.get('bot_logs', 'bot_token', fallback="")
    chat_id = config.get('bot_logs', 'log_chat_id', fallback="")
    
    # Флаг валидации токена
    if token:
        try:
            r = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
            if not r.get("ok"):
                print("❌ Текущий токен невалиден.")
                token = "" 
            else:
                bot_username = r["result"]["username"]
        except:
            token = ""

    # Если токена нет - пробуем создать
    if not token:
        print("🤖 Пробую создать бота автоматически...")
        try:
            bot_name = f"LogBot_{random_str(3)}"
            bot_user = f"Ublog_{random_str(5)}_bot"
            
            # --- ШАГ 1: /newbot ---
            print("⏳ Пишу /newbot (жду 3 сек)...")
            await client.send_message("BotFather", "/newbot")
            await asyncio.sleep(3) # КУЛДАУН
            
            # --- ШАГ 2: Имя ---
            print(f"⏳ Отправляю имя {bot_name} (жду 3 сек)...")
            await client.send_message("BotFather", bot_name)
            await asyncio.sleep(3) # КУЛДАУН
            
            # --- ШАГ 3: Username ---
            print(f"⏳ Отправляю юзернейм {bot_user} (жду 6 сек)...")
            await client.send_message("BotFather", bot_user)
            await asyncio.sleep(6) # БОЛЬШОЙ КУЛДАУН
            
            # Читаем ответ BotFather
            last_msg = ""
            async for msg in client.get_chat_history("BotFather", limit=1):
                last_msg = msg.text
            
            if "HTTP API" in last_msg:
                token = last_msg.split("HTTP API:")[1].strip().split("\n")[0]
                save_config(token=token)
                print(f"✅ Бот создан автоматически: @{bot_user}")
                bot_username = bot_user
            elif "Sorry" in last_msg or "attempts" in last_msg:
                print("\n❌ BotFather требует перерыв.")
                print("👇 Введите токен любого существующего бота вручную:")
                token = input("TOKEN: ").strip()
                save_config(token=token)
                r = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
                if r.get("ok"): bot_username = r["result"]["username"]
                else: return
            else:
                print(f"❌ Ответ BotFather: {last_msg}")
                token = input("👇 Введите токен вручную: ").strip()
                save_config(token=token)
                r = requests.get(f"https://api.telegram.org/bot{token}/getMe").json()
                bot_username = r["result"]["username"]

        except Exception as e:
            print(f"❌ Ошибка авто-создания: {e}")
            return

    # 2. Создаем группу (если нет)
    if not chat_id:
        print("📂 Создаю группу логов (жду 2 сек)...")
        try:
            await asyncio.sleep(2)
            chat = await client.create_supergroup(f"Logs | {random_str(3)}", "System Logs")
            chat_id = chat.id
            save_config(chat_id=chat_id)
            print(f"✅ Группа создана: {chat_id}")
        except Exception as e:
            print(f"❌ Ошибка группы: {e}")
            return

    # 3. Выдаем админку
    print(f"🔗 Добавляю бота @{bot_username}...")
    try:
        await asyncio.sleep(2)
        await client.add_chat_members(chat_id, bot_username)
        await client.promote_chat_member(
            chat_id, bot_username,
            privileges=enums.ChatPrivileges(can_manage_chat=True, can_delete_messages=True, can_invite_users=True, can_pin_messages=True)
        )
    except: pass

    # Финал
    print("🚀 Отправка статуса...")
    info_text = await generate_info_text(client)
    send_log_to_bot(token, chat_id, "🎉 **Юзербот успешно запущен!**\n\n" + info_text, LOCAL_BANNER)
    print("✅ Готово.")


# ==========================================
# 💻 3. ВСТРОЕННЫЕ КОМАНДЫ
# ==========================================

@app.on_message(filters.command("info", prefixes=".") & filters.me)
async def info_cmd(client, message):
    await message.edit("🔄 **Data Analysis...**")
    text = await generate_info_text(client)
    if os.path.exists(LOCAL_BANNER):
        await message.delete()
        await client.send_photo(message.chat.id, LOCAL_BANNER, caption=text)
    else:
        await message.edit(text)

@app.on_message(filters.command("log", prefixes=".") & filters.me)
async def log_cmd(client, message):
    config.read("config.ini")
    token = config.get('bot_logs', 'bot_token', fallback=None)
    chat_id = config.get('bot_logs', 'log_chat_id', fallback=None)
    if not token or not chat_id: return await message.edit("❌ Логи не настроены.")
    text = message.text.split(maxsplit=1)[1] if len(message.command) > 1 else "Ping"
    send_log_to_bot(token, chat_id, f"📝 **User Log:** {text}")
    await message.edit("✅")

# ==========================================
# 📦 4. МОДУЛИ И ПОМОЩЬ
# ==========================================

@app.on_message(filters.command("help", prefixes=".") & filters.me)
async def help_cmd(client, message):
    args = message.text.split(maxsplit=1)
    if len(args) == 1:
        files = [f[:-3] for f in os.listdir("modules") if f.endswith(".py")]
        files.sort()
        mod_list = ", ".join([f"`{f}`" for f in files]) if files else "(Пусто)"
        text = (
            "**🤖 Rikki Product Userbot**\n\n"
            "**🔹 Системные:** `.info`, `.log`, `.ping`, `.restart`, `.purge`\n"
            "**🔹 Менеджер:** `.lm`, `.dl`, `.modules`\n\n"
            "**📦 Модули:**\n" + mod_list + "\n\n"
            "ℹ️ `.help <имя>`"
        )
        await message.edit(text)
        return

    name = args[1].replace(".", "")
    if not os.path.exists(f"modules/{name}.py"): return await message.edit("❌ Нет модуля.")
    try:
        loaded = sys.modules.get(f"modules.{name}")
        desc = loaded.__help__ if hasattr(loaded, "__help__") else "Нет описания."
        await message.edit(f"**📦 Модуль:** `{name}`\n\n{desc}")
    except: await message.edit("❌ Ошибка.")

@app.on_message(filters.command("modules", prefixes=".") & filters.me)
async def modules_cmd(client, message):
    await message.edit("🔄 Loading...")
    files = [f for f in os.listdir("modules") if f.endswith(".py")]
    files.sort()
    txt = "**📦 Installed Modules:**\n\n"
    for f in files:
        name = f[:-3]; desc = "— ..."
        try:
            m = sys.modules.get(f"modules.{name}")
            if hasattr(m, "__help__"): desc = f"— {m.__help__.strip().splitlines()[0]}"
        except: pass
        txt += f"🔹 `{name}` {desc}\n"
    await message.edit(txt)

@app.on_message(filters.command("lm", prefixes=".") & filters.me)
async def lm_cmd(client, message):
    if not message.reply_to_message or not message.reply_to_message.document: return await message.edit("❌ Ответь на файл.")
    doc = message.reply_to_message.document
    if not doc.file_name.endswith(".py"): return await message.edit("❌ Нужен .py")
    await message.edit(f"📥 Скачиваю `{doc.file_name}`...")
    await client.download_media(message.reply_to_message, f"modules/{doc.file_name}")
    await message.edit("✅ Рестарт..."); os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.command("dl", prefixes=".") & filters.me)
async def dl_cmd(client, message):
    try:
        name = message.command[1]
        if not name.endswith(".py"): name += ".py"
        os.remove(f"modules/{name}")
        await message.edit(f"🗑 `{name}` удален! Рестарт..."); os.execl(sys.executable, sys.executable, *sys.argv)
    except: await message.edit("❌ Имя?")

# ==========================================
# 🛠 5. УТИЛИТЫ
# ==========================================
@app.on_message(filters.command("ping", prefixes=".") & filters.me)
async def ping(c, m):
    s = time.time(); await m.edit("Pong!"); await m.edit(f"Pong! 🏓 `{round((time.time()-s)*1000)}ms`")

@app.on_message(filters.command("restart", prefixes=".") & filters.me)
async def restart(c, m):
    await m.edit("🔄 Перезагрузка..."); os.execl(sys.executable, sys.executable, *sys.argv)

@app.on_message(filters.command("purge", prefixes=".") & filters.me)
async def purge(c, m):
    if not m.reply_to_message: return await m.edit("❌ Reply needed.")
    await m.delete()
    ids = []
    async for msg in c.get_chat_history(m.chat.id):
        ids.append(msg.id)
        if msg.id == m.reply_to_message.id: break
    await c.delete_messages(m.chat.id, ids)
    t = await c.send_message(m.chat.id, f"✅ Cleaned {len(ids)}"); await asyncio.sleep(3); await t.delete()

@app.on_message(filters.command("type", prefixes=".") & filters.me)
async def type_cmd(client, message):
    try: text = message.text.split(maxsplit=1)[1]
    except: return
    tbp = ""
    for char in text:
        tbp += char
        try: await message.edit(tbp + "▒"); await asyncio.sleep(0.05)
        except FloodWait as e: await asyncio.sleep(e.value)
    await message.edit(tbp)

@app.on_message(filters.command("calc", prefixes=".") & filters.me)
async def calc_cmd(client, message):
    try: expr = message.text.split(maxsplit=1)[1]; val = eval(expr); await message.edit(f"🔢 `{expr}` = **{val}**")
    except: await message.edit("❌ Error.")

# ==========================================
# ▶️ 6. ГЛАВНЫЙ ЗАПУСК
# ==========================================
async def main():
    print("🚀 Запуск клиента...")
    await app.start()
    await auto_setup_logs(app)
    print("✅ Работаем! (Ctrl+C для выхода)")
    await idle()
    await app.stop()

if __name__ == "__main__":
    app.run(main())