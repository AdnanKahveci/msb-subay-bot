import requests
from bs4 import BeautifulSoup
from telegram.ext import Application, ContextTypes, CommandHandler
from aiohttp import web
import json
import os
import logging
import asyncio

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8362907042:AAEFGa-3BLuUDxxx1qDd5DDuGyLxD313yy8"
CHAT_ID = "6611448494"
URL = "https://personeltemin.msb.gov.tr/duyurular"
LAST_FILE = "last_announcement.json"
PORT = int(os.environ.get('PORT', 10000))

def get_last_saved():
    if os.path.exists(LAST_FILE):
        with open(LAST_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"last_title": ""}

def save_last(title):
    with open(LAST_FILE, "w", encoding="utf-8") as f:
        json.dump({"last_title": title}, f, ensure_ascii=False, indent=2)

first_run = True

async def check_duyuru_loop(application: Application):
    global first_run
    await asyncio.sleep(10)
    
    while True:
        try:
            logger.info("Duyurular kontrol ediliyor...")
            r = requests.get(URL, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            announcements = soup.find_all("a", class_="duyuruBaslik")
            
            if not announcements:
                logger.warning("Duyuru bulunamadı.")
                await asyncio.sleep(3600)
                continue

            latest = announcements[0]
            title = latest.get_text().strip()
            link = "https://personeltemin.msb.gov.tr" + latest["href"]
            last = get_last_saved()
            
            if first_run:
                first_run = False
                if not last["last_title"]:
                    save_last(title)
                    logger.info(f"İlk çalıştırma: Mevcut duyuru kaydedildi: {title}")
                else:
                    logger.info(f"İlk çalıştırma: Son kaydedilen duyuru: {last['last_title']}")
            elif title != last["last_title"]:
                save_last(title)
                await application.bot.send_message(
                    chat_id=CHAT_ID,
                    text=f"📢 *Yeni MSB Duyurusu Çıktı!*\n\n*{title}*\n🔗 {link}",
                    parse_mode="Markdown"
                )
                logger.info(f"✅ Yeni duyuru bulundu ve gönderildi: {title}")
            else:
                logger.info("Yeni duyuru yok.")
        except Exception as e:
            logger.error(f"❌ Hata: {e}", exc_info=True)
        
        await asyncio.sleep(3600)

async def health_check(request):
    """Health check endpoint - Render'ın kontrol etmesi için"""
    return web.Response(text="✅ MSB Bot is running!", content_type="text/plain")

async def status(request):
    """Bot durumu endpoint"""
    last = get_last_saved()
    status_text = f"""
    🤖 MSB Duyuru Bot Durumu
    
    Son Kontrol Edilen Duyuru: {last.get('last_title', 'Henüz kontrol edilmedi')}
    Bot Durumu: Aktif ✅
    Kontrol Sıklığı: Her 1 saat
    """
    return web.Response(text=status_text, content_type="text/plain")

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="✅ Bot çalışıyor! MSB duyuruları her saat kontrol ediliyor."
    )

async def post_init(application: Application):
    asyncio.create_task(check_duyuru_loop(application))
    logger.info("🚀 Duyuru kontrol görevi başlatıldı!")

async def start_bot(app_web):
    """Telegram botunu başlat"""
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.post_init = post_init
    
    # Bot'u başlat ama polling'i manuel yönet
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        allowed_updates=["message"],
        drop_pending_updates=True
    )
    
    # Web app'e bot'u ekle (temizlik için)
    app_web['bot'] = application
    logger.info("🤖 Telegram bot başlatıldı!")

async def cleanup(app_web):
    """Temizlik işlemleri"""
    if 'bot' in app_web:
        await app_web['bot'].updater.stop()
        await app_web['bot'].stop()
        await app_web['bot'].shutdown()
        logger.info("Bot kapatıldı")

def main():
    # Web uygulaması oluştur
    app_web = web.Application()
    app_web.router.add_get('/', health_check)
    app_web.router.add_get('/health', health_check)
    app_web.router.add_get('/status', status)
    
    # Startup ve cleanup
    app_web.on_startup.append(start_bot)
    app_web.on_cleanup.append(cleanup)
    
    logger.info(f"🌐 Web sunucusu port {PORT}'da başlatılıyor...")
    
    # Web sunucusunu çalıştır
    web.run_app(app_web, host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    main()