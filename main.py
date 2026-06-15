import logging
import os
import requests
import re
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from moviepy.editor import VideoFileClip

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ.get("8700248975:AAF-FJeHnr6PgtlcJ-kK4k3raxstSGmyoRc")

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot aktif!")
    
    def log_message(self, format, *args):
        pass  # HTTP log spamini kapat

def run_web_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

def get_pinterest_video_url(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=15)
        
        patterns = [
            r'"V_720P":\{"url":"(.*?)"',
            r'"V_480P":\{"url":"(.*?)"',
            r'"V_360P":\{"url":"(.*?)"',
            r'contentUrl":"(https://v\.pinimg\.com[^"]+\.mp4[^"]*)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, response.text)
            if match:
                return match.group(1).replace('\\u002F', '/')
        
        logging.warning("Pinterest video URL bulunamadı.")
        return None
    except Exception as e:
        logging.error(f"Pinterest URL hatası: {e}")
        return None

def process_video(input_path, output_path):
    clip = VideoFileClip(input_path)
    w, h = clip.size
    target_ratio = 9 / 16

    if w / h > target_ratio:
        new_w = int(h * target_ratio)
        x1 = (w - new_w) / 2
        x2 = x1 + new_w
        final_clip = clip.crop(x1=x1, y1=0, x2=x2, y2=h)
    else:
        new_h = int(w / target_ratio)
        y1 = (h - new_h) / 2
        y2 = y1 + new_h
        final_clip = clip.crop(x1=0, y1=y1, x2=w, y2=y2)

    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
    clip.close()
    final_clip.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    if "pinterest.com" in text or "pin.it" in text:
        await update.message.reply_text("Videoyu indirip hazırlıyorum, azıcık bekle canım...")

        video_url = get_pinterest_video_url(text)
        if not video_url:
            await update.message.reply_text("Videoyu bulamadım valla, linki kontrol etsene.")
            return

        try:
            video_data = requests.get(video_url, timeout=30).content
        except Exception as e:
            logging.error(f"Video indirme hatası: {e}")
            await update.message.reply_text("Videoyu indiremedim, bir sorun çıktı.")
            return

        with open("temp_input.mp4", "wb") as f:
            f.write(video_data)

        try:
            process_video("temp_input.mp4", "temp_output.mp4")

            video_size = os.path.getsize("temp_output.mp4")
            if video_size > 50 * 1024 * 1024:
                await update.message.reply_text("Video 50MB'ı geçiyor, Telegram'a gönderemedim maalesef.")
                return

            with open("temp_output.mp4", "rb") as video:
                await update.message.reply_video(video=video, caption="Al bakalım, tertemiz oldu!")

        except Exception as e:
            logging.error(f"Video işleme hatası: {e}")
            await update.message.reply_text("Video işlenirken bir hata oluştu, tekrar dener misin?")

        finally:
            if os.path.exists("temp_input.mp4"):
                os.remove("temp_input.mp4")
            if os.path.exists("temp_output.mp4"):
                os.remove("temp_output.mp4")
    else:
        await update.message.reply_text("Bana Pinterest linki gönderirsen temizlerim.")

if __name__ == '__main__':
    threading.Thread(target=run_web_server, daemon=True).start()
    application = ApplicationBuilder().token(TOKEN).build()
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(message_handler)
    print("Bot is running...")
    application.run_polling()
