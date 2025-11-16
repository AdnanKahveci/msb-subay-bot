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
URL = "https://personeltemin.msb.gov.tr/Anasayfa/Duyurular"
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

async def check_duyuru_loop(application: Application):
    # İlk başta bilgilendirme mesajı gönder
    try:
        await application.bot.send_message(
            chat_id=CHAT_ID,
            text="🚀 *Bot Başlatıldı!*\n\nDuyuru kontrolü başlıyor...\n⏰ Kontrol sıklığı: Her 1 saat",
            parse_mode="Markdown"
        )
        logger.info("✅ Başlangıç mesajı gönderildi")
    except Exception as e:
        logger.error(f"❌ Başlangıç mesajı hatası: {e}")
    
    await asyncio.sleep(10)
    
    first_check = True
    
    while True:
        try:
            logger.info("📡 Duyurular kontrol ediliyor...")
            r = requests.get(URL, timeout=10)
            soup = BeautifulSoup(r.text, "html.parser")
            announcements = soup.find_all("a", class_="duyuruBaslik")
            
            if not announcements:
                logger.warning("⚠️ Duyuru bulunamadı.")
                await asyncio.sleep(3600)
                continue

            latest = announcements[0]
            title = latest.get_text().strip()
            link = "https://personeltemin.msb.gov.tr" + latest["href"]
            last = get_last_saved()
            
            logger.info(f"📄 Bulunan duyuru: {title}")
            logger.info(f"💾 Kayıtlı duyuru: {last.get('last_title', 'Yok')}")
            
            # İlk kontrol - sadece kaydet, mesaj gönderme
            if first_check:
                first_check = False
                if not last["last_title"]:
                    # Hiç kayıt yoksa, şimdiki duyuruyu kaydet
                    save_last(title)
                    logger.info(f"💾 İlk kayıt: {title}")
                    await application.bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"💾 *İlk Kayıt Yapıldı*\n\nMevcut duyuru kaydedildi. Bundan sonra yeni duyuru çıktığında bildirim alacaksınız.\n\n_{title}_",
                        parse_mode="Markdown"
                    )
                else:
                    logger.info(f"✅ Kayıtlı duyuru mevcut: {last['last_title']}")
                    # Eğer farklıysa, yeni duyuru var demektir
                    if title != last["last_title"]:
                        save_last(title)
                        await application.bot.send_message(
                            chat_id=CHAT_ID,
                            text=f"📢 *Yeni MSB Duyurusu Çıktı!*\n\n*{title}*\n\n🔗 {link}",
                            parse_mode="Markdown"
                        )
                        logger.info(f"🎉 İlk kontrolde yeni duyuru bulundu ve gönderildi!")
                continue
            
            # Sonraki kontroller - değişiklik varsa bildir
            if title != last["last_title"]:
                save_last(title)
                try:
                    await application.bot.send_message(
                        chat_id=CHAT_ID,
                        text=f"📢 *Yeni MSB Duyurusu Çıktı!*\n\n*{title}*\n\n🔗 {link}",
                        parse_mode="Markdown"
                    )
                    logger.info(f"✅ Yeni duyuru bildirildi: {title}")
                except Exception as e:
                    logger.error(f"❌ Bildirim gönderilemedi: {e}")
            else:
                logger.info("ℹ️ Yeni duyuru yok.")
                
        except Exception as e:
            logger.error(f"❌ Kontrol hatası: {e}", exc_info=True)
        
        logger.info("⏰ 1 saat bekleniyor...")
        await asyncio.sleep(3600)

async def health_check(request):
    return web.Response(text="✅ MSB Bot is running!", content_type="text/plain")

async def status(request):
    last = get_last_saved()
    status_text = f"""🤖 MSB Duyuru Bot Durumu
    
Son Kontrol Edilen Duyuru: 
{last.get('last_title', 'Henüz kontrol edilmedi')}

Bot Durumu: Aktif ✅
Kontrol Sıklığı: Her 1 saat
Chat ID: {CHAT_ID}
"""
    return web.Response(text=status_text, content_type="text/plain")

async def check_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Manuel kontrol komutu"""
    await update.message.reply_text("🔍 Duyurular kontrol ediliyor...")
    try:
        r = requests.get(URL, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        announcements = soup.find_all("a", class_="duyuruBaslik")
        
        if announcements:
            latest = announcements[0]
            title = latest.get_text().strip()
            link = "https://personeltemin.msb.gov.tr" + latest["href"]
            last = get_last_saved()
            
            if title == last.get("last_title"):
                await update.message.reply_text(f"ℹ️ *Güncel Duyuru*\n\n{title}\n\n🔗 {link}", parse_mode="Markdown")
            else:
                await update.message.reply_text(f"🆕 *Yeni Duyuru Tespit Edildi!*\n\n{title}\n\n🔗 {link}", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ Duyuru bulunamadı.")
    except Exception as e:
        await update.message.reply_text(f"❌ Hata: {e}")

async def reset_command(update, context: ContextTypes.DEFAULT_TYPE):
    """Kayıtlı duyuruyu sıfırla"""
    if os.path.exists(LAST_FILE):
        os.remove(LAST_FILE)
        await update.message.reply_text("🗑️ Kayıtlı duyuru silindi. Bir sonraki kontrolde mevcut duyuru kaydedilecek.")
    else:
        await update.message.reply_text("ℹ️ Zaten kayıtlı duyuru yok.")

async def start_command(update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="✅ *Bot Çalışıyor!*\n\nKomutlar:\n/check - Manuel kontrol\n/reset - Kayıtlı duyuruyu sıfırla",
        parse_mode="Markdown"
    )

async def post_init(application: Application):
    asyncio.create_task(check_duyuru_loop(application))
    logger.info("🚀 Duyuru kontrol görevi başlatıldı!")

async def start_bot(app_web):
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("check", check_command))
    application.add_handler(CommandHandler("reset", reset_command))
    application.post_init = post_init
    
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        allowed_updates=["message"],
        drop_pending_updates=True
    )
    
    app_web['bot'] = application
    logger.info("🤖 Telegram bot başlatıldı!")

async def cleanup(app_web):
    if 'bot' in app_web:
        await app_web['bot'].updater.stop()
        await app_web['bot'].stop()
        await app_web['bot'].shutdown()
        logger.info("Bot kapatıldı")

def main():
    app_web = web.Application()
    app_web.router.add_get('/', health_check)
    app_web.router.add_get('/health', health_check)
    app_web.router.add_get('/status', status)
    
    app_web.on_startup.append(start_bot)
    app_web.on_cleanup.append(cleanup)
    
    logger.info(f"🌐 Web sunucusu port {PORT}'da başlatılıyor...")
    web.run_app(app_web, host='0.0.0.0', port=PORT)

if __name__ == "__main__":
    main()
