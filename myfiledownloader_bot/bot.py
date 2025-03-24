import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext

# 🔑 تۆکینی بوت
BOT_TOKEN = "7885852596:AAG1UUV3U8UXFxYhOfHP0GXZw30LYxwHIWU"

# 📁 شوێنی داگرتن
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 📊 ئەو کوالێتیانەی کە بەکارهێنەر دەبژێرد
QUALITY_OPTIONS = {
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "Audio": "bestaudio"
}

async def start(update: Update, context: CallbackContext):
    """ /start بۆ دەستپێکردن """
    await update.message.reply_text("🎬 لینکێکی یوتوب بنێرە بۆ داگرتن!")

async def choose_quality(update: Update, context: CallbackContext):
    """ بەکارهێنەر کوالێتی دیاری بکات """
    url = update.message.text
    context.user_data["url"] = url  # 🌐 پاشەکەوتکردنی URL

    # 📌 هەڵبژاردنەکان
    keyboard = [
        [InlineKeyboardButton("🔹 360p", callback_data="360p"),
         InlineKeyboardButton("🔸 480p", callback_data="480p")],
        [InlineKeyboardButton("🔹 720p", callback_data="720p"),
         InlineKeyboardButton("🎵 تەنها دەنگ", callback_data="Audio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("📌 تکایە کوالێتی هەڵبژێرە:", reply_markup=reply_markup)

async def download_video(update: Update, context: CallbackContext):
    """ داگرتنی ڤیدیۆ بە کوالێتی دیاریکراو """
    query = update.callback_query
    quality = query.data
    url = context.user_data.get("url")

    if not url:
        await query.answer("❌ هیچ لینکێک نەدۆزرایەوە، دوبارە بنێرە.")
        return

    await query.answer()
    await query.edit_message_text(f"⏳ داگرتنی {quality} دەستی دەکات...")

    filename = await download_youtube(url, QUALITY_OPTIONS[quality])

    if filename:
        file_path = os.path.join(DOWNLOAD_DIR, filename)
        await query.edit_message_text("✅ داگرتن تەواو بوو! ناردن دەستی دەکات...")

        # 📤 ناردنی ڤیدیۆ یان دەنگ
        with open(file_path, "rb") as file:
            if "Audio" in quality:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=file)
            else:
                await context.bot.send_video(chat_id=query.message.chat_id, video=file)

        os.remove(file_path)  # 📌 ڕەشکردنەوەی فایڵ
    else:
        await query.edit_message_text("❌ داگرتن سەرکەوتوو نەبوو.")

async def download_youtube(url, format_code):
    """ داگرتنی ڤیدیۆ یان دەنگ بە کوالێتی دیاریکراو """
    ydl_opts = {
        "format": format_code,
        "outtmpl": os.path.join(DOWNLOAD_DIR, "%(title)s.%(ext)s"),
        "merge_output_format": "mp4"
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return os.path.basename(ydl.prepare_filename(info))

def main():
    """ 🚀 بەڕێوەبردنی بوت """
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, choose_quality))
    app.add_handler(CallbackQueryHandler(download_video))

    print("🤖 بوت بەردەستە!")
    app.run_polling()

if __name__ == "__main__":
    main()
