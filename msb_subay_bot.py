import requests
from bs4 import BeautifulSoup
from telegram.ext import Application, ContextTypes, CommandHandler
import json
import os
import logging

# Logging ayarla
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

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

async def check_duyuru_job(context: ContextTypes.DEFAULT_TYPE):
    """Job queue ile çalışan duyuru kontrol fonksiyonu"""
    try:
        logger.info("Duyurular kontrol ediliyor...")
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        announcements = soup.find_all("a", class_="duyuruBaslik")
        
        if not announcements:
            logger.warning("Duyuru bulunamadı.")
            return

        latest = announcements[0]
        title = latest.get_text().strip()
        link = "https://personeltemin.msb.gov.tr" + latest["href"]

        last = get_last_saved()
        
        # İlk çalıştırma kontrolü
        if 'first_run' not in context.bot_data:
            context.bot_data['first_run'] = False
            if not last["last_title"]:
                save_last(title)
                logger.info(f"İlk çalıştırma: Mevcut duyuru kaydedildi: {title}")
            else:
                logger.info(f"İlk çalıştırma: Son kaydedilen duyuru: {last['last_title']}")
            return
        
        # Yeni duyuru kontrolü
        if title != last["last_title"]:
            save_last(title)
            await context.bot.send_message(
                chat_id=CHAT_ID,
                text=f"📢 *Yeni MSB Duyurusu Çıktı!*\n\n*{title}*\n🔗 {link}",
                parse_mode="Markdown"
            )
            logger.info(f"✅ Yeni duyuru bulundu ve gönderildi: {title}")
        else:
            logger.info("Yeni duyuru yok.")
            
    except Exception as e:
        logger.error(f"❌ Hata: {e}", exc_info=True)

async def start(update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="✅ Bot çalışıyor! MSB duyuruları her saat kontrol ediliyor."
    )

async def post_init(application: Application):
    """Bot başlatıldıktan sonra arka plan görevini başlat"""
    # Her saat tekrarlayan bir job ekle
    application.job_queue.run_repeating(
        check_duyuru_job,
        interval=3600,  # 3600 saniye = 1 saat
        first=10,  # İlk kontrolü 10 saniye sonra yap
        name="duyuru_checker"
    )
    logger.info("🚀 Bot başlatıldı, duyuru kontrolü her saat yapılacak!")

def main():
    """Ana fonksiyon"""
    # Application oluştur
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    
    # Komut handler'ı ekle
    application.add_handler(CommandHandler("start", start))
    
    # post_init callback'i ayarla
    application.post_init = post_init
    
    logger.info("🤖 Bot başlatılıyor...")
    
    # Bot'u çalıştır
    application.run_polling(allowed_updates=["message"])

if __name__ == "__main__":
    main()