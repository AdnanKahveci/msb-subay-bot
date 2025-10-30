import requests
from bs4 import BeautifulSoup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import asyncio
# Telegram bot bilgilerini buraya yaz
TELEGRAM_TOKEN = "8362907042:AAEFGa-3BLuUDxxx1qDd5DDuGyLxD313yy8"
CHAT_ID = "6611448494"

URL = "https://personeltemin.msb.gov.tr/duyurular"

async def check_duyuru(app):
    while True:
        try:
            r = requests.get(URL)
            soup = BeautifulSoup(r.text, "html.parser")
            duyurular = soup.find_all("a")
            for d in duyurular:
                text = d.get_text()
                if "Muvazzaf Subay" in text:
                    link = d.get("href")
                    await app.bot.send_message(chat_id=CHAT_ID, text=f"Yeni duyuru: {text}\n{link}")
        except Exception as e:
            print("Hata:", e)
        await asyncio.sleep(3600)  # 1 saatte bir kontrol

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Bot çalışıyor!")

if __name__ == "__main__":
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.create_task(check_duyuru(app))
    app.run_polling()
