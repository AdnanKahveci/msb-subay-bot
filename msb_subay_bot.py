import requests
from bs4 import BeautifulSoup
from telegram import Bot
import time
import json
import os

# Telegram bot bilgilerini buraya yaz
TELEGRAM_TOKEN = "8362907042:AAEFGa-3BLuUDxxx1qDd5DDuGyLxD313yy8"
CHAT_ID = "6611448494"

bot = Bot(token=TELEGRAM_TOKEN)

# En son kontrol edilen duyuruyu kaydetmek için
LAST_FILE = "last_announcement.json"

def get_last_saved():
    if os.path.exists(LAST_FILE):
        with open(LAST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_title": ""}

def save_last(title):
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_title": title}, f, ensure_ascii=False, indent=2)

def check_new_announcements():
    url = "https://personeltemin.msb.gov.tr/"
    r = requests.get(url, timeout=10)
    soup = BeautifulSoup(r.text, "html.parser")

    # Duyuru başlıklarını çek
    announcements = soup.find_all("a", class_="duyuruBaslik")
    if not announcements:
        return None

    latest = announcements[0]
    title = latest.text.strip()
    link = "https://personeltemin.msb.gov.tr/" + latest["href"]

    data = get_last_saved()
    if title != data["last_title"]:
        save_last(title)
        return {"title": title, "link": link}
    return None

def main():
    print("Bot çalışıyor... MSB duyuruları kontrol ediliyor.")
    while True:
        try:
            new = check_new_announcements()
            if new:
                message = f"📢 *Yeni MSB Duyurusu Çıktı!*\n\n*{new['title']}*\n🔗 {new['link']}"
                bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
                print("Yeni duyuru bulundu ve gönderildi.")
            time.sleep(3600)  # 1 saatte bir kontrol et
        except Exception as e:
            print("Hata:", e)
            time.sleep(600)  # hata olursa 10 dk sonra tekrar dene

if __name__ == "__main__":
    main()
