import requests
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import asyncio
import json
import os

# Telegram bot bilgileri
TELEGRAM_TOKEN = "8362907042:AAEFGa-3BLuUDxxx1qDd5DDuGyLxD313yy8"
CHAT_ID = "6611448494"

URL = "https://personeltemin.msb.gov.tr/duyurular"
LAST_FILE = "last_announcement.json"

def get_last_saved():
    if os.path.exists(LAST_FILE):
        with open(LAST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_title": ""}

def save_last(title):
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_title": title}, f, ensure_ascii=False, indent=2)

async def check_duyuru(app):
    while True:
        try:
            r = requests.get(URL, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            announcements = soup.find_all("a", class_="duyuruBaslik")
            if not announcements:
                await asyncio.sleep(3600)
                continue

            latest = announcements[0]
            title = latest.get_text().strip()
            link = "https://personeltemin.msb.gov.tr/" + latest["href"]

            last = get_last_saved()
            if title != last["last_title"]:
                save_last(title)
                await app.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"📢 *Yeni MSB Duyurusu Çıktı!*\n\n*{title}*\n🔗 {link}",
                    parse_mode="Markdown"
                )
                print("Yeni duyuru bulundu ve gönderildi.")
        except Exception as e:
            print("Hata:", e)
        await asyncio.sleep(3600)

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot çalışıyor!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))

    # Bot başlatıldıktan sonra async görev ekle
    async def on_startup(app):
        app.create_task(check_duyuru(app))

    app.post_init(on_startup)
    app.run_polling()  # asyncio.run() kullanmaya gerek yok
