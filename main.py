mport logging
import os
import requests
import re
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from moviepy.editor import VideoFileClip

logging.basicConfig(level=logging.INFO)

TOKEN = os.environ.get("BOT_TOKEN")

def get_pinterest_video_url(url):
    try:
        response = requests.get(url, allow_redirects=True)
        match = re.search(r'"video_list":\{"V_720P":\{"url":"(.*?)"', response.text)
        if match:
            return match.group(1).replace('\\u002F', '/')
        return None
    except Exception as e:
        return None

def process_video(input_path, output_path):
    clip = VideoFileClip(input_path)
    w, h = clip.size
    target_ratio = 9/16
    if w/h > target_ratio:
        new_w = h * target_ratio
        x1 = (w - new_w) / 2
        x2 = x1 + new_w
        final_clip = clip.crop(x1=x1, y1=0, x2=x2, y2=h)
    else:
        new_h = w / target_ratio
        y1 = (h - new_h) / 2
        y2 = y1 + new_h
        final_clip = clip.crop(x1=0, y1=y1, x2=w, y2=y2)
    final_clip.write_videofile(output_path, codec="libx264", audio_codec="aac")
    clip.close()

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "pinterest.com" in text or "pin.it" in text:
        await update.message.reply_text("Videoyu indirip hazırlıyorum, azıcık bekle canım...")
        video_url = get_pinterest_video_url(text)
        if not video_url:
            await update.message.reply_text("Videoyu bulamadım valla, linki kontrol etsene.")
            return
        video_data = requests.get(video_url).content
        with open("temp_input.mp4", "wb") as f:
            f.write(video_data)
        try:
            process_video("temp_input.mp4", "temp_output.mp4")
            with open("temp_output.mp4", "rb") as video:
                await update.message.reply_video(video=video, caption="Al bakalım, tertemiz oldu!")
        except Exception as e:
            await update.message.reply_text("Ufak bir hata verdi ya, hallederiz.")
        finally:
            if os.path.exists("temp_input.mp4"): os.remove("temp_input.mp4")
            if os.path.exists("temp_output.mp4"): os.remove("temp_output.mp4")
    else:
        await update.message.reply_text("Bana Pinterest linki gönderirsen temizlerim.")

if name == 'main':
    application = ApplicationBuilder().token(TOKEN).build()
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    application.add_handler(message_handler)
    print("Bot is running...")
    application.run_polling()
