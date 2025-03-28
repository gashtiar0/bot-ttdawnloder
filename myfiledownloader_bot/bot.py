import os
import threading
import time
import asyncio
import requests
import telebot
import yt_dlp
import re
from shazamio import Shazam
from urllib.parse import quote
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, CallbackContext

# 🔑 تۆکینی بوت
BOT_TOKEN = "5964081352:AAFeEUNBhZVDy6uM0tAfmlB5jPIfAoX1G8s"

# 📁 شوێنی داگرتن
DOWNLOAD_DIR = "downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ئایدی خاوەنی بوت
OWNER_CHAT_ID = "5302690134"  # ئایدی تەلەگرامی خۆت دابنێ

# 📊 کوالێتیەکانی داگرتن
QUALITY_OPTIONS = {
    "360p": "bestvideo[height<=360]+bestaudio/best",
    "480p": "bestvideo[height<=480]+bestaudio/best",
    "720p": "bestvideo[height<=720]+bestaudio/best",
    "Audio": "bestaudio"
}

# 📋 لیستی بەکارهێنەرانی قەدەغەکراو - بە زانیارییەوە
BANNED_USERS = {}  # گۆڕدرا بۆ دیکشنەری بۆ پاراستنی هۆکاری باندکردن

# پاراستنی زانیاری بەکارهێنەران
USER_ANALYTICS = {}

def send_progress_message(bot, chat_id, message_id):
    """ پەیامی پێشکەوتن """
    dots = ['🔍', '🔍.', '🔍..', '🔍...']
    for i in range(10):
        try:
            bot.edit_message_text(
                chat_id=chat_id, 
                message_id=message_id, 
                text=f"🔎 بەدوای موزیکەکەدا دەگەڕێم {dots[i % 4]}\n⏳ تکایە پشوودەیەک بدە..."
            )
            time.sleep(1)
        except Exception:
            break

async def listuser(update: Update, context: CallbackContext):
    """ لیستی هەموو بەکارهێنەران """
    if str(update.effective_user.id) != OWNER_CHAT_ID:
        await update.message.reply_text("🚫 تەنها خاوەنی بۆت دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
        return

    if not USER_ANALYTICS:
        await update.message.reply_text("👥 هیچ بەکارهێنەرێک تاکو ئێستا بۆتەکەی بەکارنەهێناوە.")
        return

    # ژمارەی گشتی بەکارهێنەران
    total_users = len(USER_ANALYTICS)
    
    user_list = f"👥 لیستی بەکارهێنەران ({total_users} بەکارهێنەر):\n\n"
    for user_id, data in USER_ANALYTICS.items():
        username = data.get('username', 'بێ ناو')
        user_list += (
            f"🔹 یوزەرنەیم: {username}\n"
            f"   ئایدی: {user_id}\n"
            f"   ژمارەی بەکارهێنان: {data['count']}\n"
            f"   کۆتا لینک: {data.get('last_link', 'نییە')[:100] + '...' if data.get('last_link', '') and len(data.get('last_link', '')) > 100 else data.get('last_link', 'نییە')}\n"
            f"   کاتی دوایین بەکارهێنان: {data.get('last_used', 'نییە')}\n\n"
        )

    # ناردنی لیستەکە بە بەش بەش ئەگەر زۆر بوو
    if len(user_list) > 4000:
        for i in range(0, len(user_list), 4000):
            await update.message.reply_text(user_list[i:i+4000])
    else:
        await update.message.reply_text(user_list)

async def unban_user(update: Update, context: CallbackContext):
    """ فەرمانی لابردنی قەدەغەی بەکارهێنەر """
    if str(update.effective_user.id) != OWNER_CHAT_ID:
        await update.message.reply_text("🚫 تەنها خاوەنی بۆت دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
        return

    try:
        args = context.args
        if len(args) < 1:
            await update.message.reply_text("🔍 نموونە: /unban ئایدی یان یوزەرنەیم")
            return

        user_identifier = args[0]
        found = False

        # گەڕان بەپێی ئایدی یان ناو
        for user_id in list(BANNED_USERS.keys()):
            if (user_id == user_identifier) or (BANNED_USERS[user_id].get('username') == user_identifier):
                # بەدۆزراو دانا
                found = True
                username = BANNED_USERS[user_id].get('username', user_id)
                
                # لابردنی ئەندامە لە لیستی قەدەغەکراوەکان
                del BANNED_USERS[user_id]

                # ناردنی پەیامی بەخێرهاتنەوە بۆ بەکارهێنەر
                unban_message = (
                    f"🎉 بەخێربێیتەوە!\n"
                    f"قەدەغەکردنی تۆ لەسەر بۆتەکە هەڵگیراوەتەوە.\n"
                    f"ئێستا دەتوانیت دووبارە بۆتەکە بەکاربهێنیت."
                )

                # هەوڵدان بۆ ناردنی پەیام بۆ بەکارهێنەر
                try:
                    await context.bot.send_message(
                        chat_id=user_id, 
                        text=unban_message
                    )
                except Exception as e:
                    await update.message.reply_text(f"⚠️ نەمتوانی پەیوەندی بە بەکارهێنەرەکەوە بکەم: {e}")

                # ناردنی پەیام بۆ خاوەن بۆت
                await update.message.reply_text(f"🔓 {username} لە لیستی قەدەغەکراوەکان دەرکرا.")
                break

        if not found:
            await update.message.reply_text(f"❌ {user_identifier} لە لیستی قەدەغەکراوەکان نیە.")

    except Exception as e:
        await update.message.reply_text(f"❌ هەڵەیەک ڕووی دا: {e}")

async def listban(update: Update, context: CallbackContext):
    """ لیستی بەکارهێنەرانی قەدەغەکراو """
    if str(update.effective_user.id) != OWNER_CHAT_ID:
        await update.message.reply_text("🚫 تەنها خاوەنی بۆت دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
        return

    if not BANNED_USERS:
        await update.message.reply_text("✅ هیچ بەکارهێنەرێک قەدەغە نەکراوە.")
        return

    ban_list = "🚫 لیستی بەکارهێنەرانی قەدەغەکراو:\n\n"
    for user_id, data in BANNED_USERS.items():
        username = data.get('username', 'بێ ناو')
        reason = data.get('reason', 'هۆکار دیار نییە')
        date = data.get('date', 'نادیار')
        ban_list += f"• ئایدی: {user_id}\n  یوزەر: {username}\n  هۆکار: {reason}\n  بەرواری باندکردن: {date}\n\n"

    await update.message.reply_text(ban_list)

async def ban_user(update: Update, context: CallbackContext):
    """ فەرمانی قەدەغەکردنی بەکارهێنەر """
    if str(update.effective_user.id) != OWNER_CHAT_ID:
        await update.message.reply_text("🚫 تەنها خاوەنی بۆت دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
        return

    try:
        # شیکردنەوەی فەرمان
        args = context.args
        if len(args) < 2:
            await update.message.reply_text("🔍 نموونە: /ban ئایدی یان یوزەرنەیم هۆکاری باندکردن")
            return

        user_identifier = args[0]
        reason = " ".join(args[1:])
        
        # گەڕان بەدوای بەکارهێنەر لە ئەنالیتیکسدا
        user_id = None
        username = None
        
        # گەڕان ئایا ئەوە ئایدییە یان یوزەرنەیمە
        if user_identifier.isdigit():
            user_id = user_identifier
            # گەڕان بەدوای یوزەرنەیم
            for uid, data in USER_ANALYTICS.items():
                if uid == user_id:
                    username = data.get('username', 'بێ ناو')
                    break
        else:
            # ئەگەر یوزەرنەیم بێت گەڕان بەدوای ئایدی
            for uid, data in USER_ANALYTICS.items():
                if data.get('username') == user_identifier:
                    user_id = uid
                    username = user_identifier
                    break
        
        if not user_id:
            await update.message.reply_text("❌ بەکارهێنەر نەدۆزرایەوە، دڵنیابە بەکارهێنەر پێشتر بۆتەکەی بەکارهێناوە.")
            return
        
        # زیادکردنی بەکارهێنەر بۆ لیستی قەدەغەکراوەکان
        BANNED_USERS[user_id] = {
            'username': username,
            'reason': reason,
            'date': time.strftime("%Y-%m-%d %H:%M:%S")
        }

        # ناردنی پەیامی قەدەغەکردن بۆ بەکارهێنەر
        ban_message = (
            f"🚫 بەداخەوە، تۆ لە بەکارهێنانی بۆتەکە قەدەغە کراویت.\n"
            f"هۆکار: {reason}\n"
            f"بۆ زانیاری زیاتر پەیوەندی بە خاوەنی بۆتەوە بکە."
        )

        # هەوڵدان بۆ ناردنی پەیام بۆ بەکارهێنەر
        try:
            await context.bot.send_message(
                chat_id=user_id, 
                text=ban_message
            )
        except Exception as e:
            await update.message.reply_text(f"⚠️ نەمتوانی پەیوەندی بە بەکارهێنەرەکەوە بکەم: {e}")

        # ناردنی پەیام بۆ خاوەن بۆت
        await update.message.reply_text(f"🚫 بەکارهێنەری {username} (ئایدی: {user_id}) قەدەغە کرا\nهۆکار: {reason}")

    except Exception as e:
        await update.message.reply_text(f"❌ هەڵەیەک ڕووی دا: {e}")

async def check_user_ban(update: Update, context: CallbackContext) -> bool:
    """ پشکنین بۆ قەدەغەکردنی بەکارهێنەر """
    user = update.effective_user
    user_id = str(user.id)

    if user_id in BANNED_USERS:
        # بەدەستهێنانی هۆکاری قەدەغەکردن
        ban_info = BANNED_USERS[user_id]
        reason = ban_info.get('reason', 'هۆکار دیار نییە')
        
        ban_message = (
            "🚫 بەداخەوە، تۆ لە بەکارهێنانی بۆتەکە قەدەغە کراویت.\n"
            f"هۆکار: {reason}\n"
            "بۆ زانیاری زیاتر پەیوەندی بە خاوەنی بۆتەوە بکە."
        )
        await update.message.reply_text(ban_message)
        return False
    return True

async def forward_to_owner(update: Update, context: CallbackContext):
    """ فۆرواردکردنی پەیامەکانی بەکارهێنەران بۆ خاوەنی بۆت """
    user = update.effective_user
    message = update.effective_message
    
    # سەرەتا پشکنین ئایا بەکارهێنەر باند کراوە
    user_id = str(user.id)
    if user_id in BANNED_USERS:
        return False  # گەڕانەوە ئەگەر باند کرابوو
    
    # ئامادەکردنی تێکست بۆ خاوەنی بۆت
    username = f"@{user.username}" if user.username else user.full_name
    forward_text = (
        f"📩 پەیامێکی نوێ لە بەکارهێنەرەوە\n"
        f"👤 ناو: {user.full_name}\n"
        f"🆔 ئایدی: {user.id}\n"
        f"👥 یوزەرنەیم: {username}\n"
        f"⏰ کات: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        f"📝 پەیام: {message.text}"
    )
    
    # ناردنی پەیام بۆ خاوەنی بۆت
    await context.bot.send_message(
        chat_id=OWNER_CHAT_ID, 
        text=forward_text
    )
    
    return True

async def update_user_analytics(update: Update, context: CallbackContext):
    """ بەڕۆژکردنەوەی زانیاری بەکارهێنەران """
    try:
        user = update.effective_user
        message = update.effective_message
        user_id = str(user.id)
        username = f"@{user.username}" if user.username else user.full_name
        user_link = message.text or ''

        # پشکنین ئایا بەکارهێنەر باند کراوە
        if user_id in BANNED_USERS:
            return False
        
        # هەڵگرتنی زانیاری بەکارهێنەر
        if user_id not in USER_ANALYTICS:
            USER_ANALYTICS[user_id] = {
                'username': username,
                'count': 0,
                'last_link': '',
                'last_used': ''
            }

        USER_ANALYTICS[user_id]['count'] += 1
        USER_ANALYTICS[user_id]['last_link'] = user_link
        USER_ANALYTICS[user_id]['last_used'] = time.strftime("%Y-%m-%d %H:%M:%S")
        
        return True
    except Exception as e:
        print(f"هەڵە لە بەڕۆژکردنەوەی ئەنالیتیکسدا: {e}")
        return False

async def recognize_music(file_path):
    """ ناسینەوەی موزیک """
    try:
        shazam = Shazam()
        result = await shazam.recognize_song(file_path)
        
        if result and 'track' in result:
            track = result['track']
            return {
                'title': track.get('title', 'ناوی نەناسراو'),
                'artist': track.get('subtitle', 'هونەرمەندی نادیار'),
                'cover_image': track.get('images', {}).get('coverart', ''),
                'youtube_link': await search_youtube_link(track.get('title', ''), track.get('subtitle', ''))
            }
        return None
    except Exception as e:
        print(f"هەڵە لە ناسینەوەدا: {e}")
        return None

def download_full_song(song_name, artist):
    """ داگرتنی گۆرانی تەواو """
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_DIR, 'full_song.%(ext)s')
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_query = f"{song_name} {artist} official audio"
            result = ydl.extract_info(f"ytsearch1:{search_query}", download=True)
            return os.path.join(DOWNLOAD_DIR, 'full_song.mp3')
    except Exception as e:
        print(f"هەڵە لە داگرتنی گۆرانی تەواو: {e}")
        return None

async def search_youtube_link(song_name, artist):
    """ گەڕان بۆ لینکی یوتیوب """
    try:
        query = quote(f"{song_name} {artist} official audio")
        youtube_search_url = f"https://www.youtube.com/results?search_query={query}"
        return youtube_search_url
    except Exception as e:
        print(f"هەڵە لە گەڕانی یوتیوب: {e}")
        return None

async def start(update: Update, context: CallbackContext):
    """ /start بۆ دەستپێکردن """
    # پشکنین بۆ قەدەغەکردنی بەکارهێنەر
    if not await check_user_ban(update, context):
        return
    
    # بەڕۆژکردنەوەی زانیاری بەکارهێنەر
    await update_user_analytics(update, context)
    
    # فۆرواردکردنی پەیام بۆ خاوەنی بۆت
    await forward_to_owner(update, context)
    
    await update.message.reply_text("🎬 لینکی یوتیوب بنێرە بۆ داگرتن یان ناسینەوەی موزیک!")

async def handle_message(update: Update, context: CallbackContext):
    """ نەخشەدانەر بۆ هەموو پەیامەکان """
    # پشکنین بۆ قەدەغەکردنی بەکارهێنەر
    if not await check_user_ban(update, context):
        return
    
    # بەڕۆژکردنەوەی زانیاری بەکارهێنەر
    await update_user_analytics(update, context)
    
    # فۆرواردکردنی پەیام بۆ خاوەنی بۆت
    await forward_to_owner(update, context)
    
    # دواتر ڕۆشتن بۆ نەخشەی ئاسایی
    await choose_download_action(update, context)

async def choose_download_action(update: Update, context: CallbackContext):
    """ هەڵبژاردنی کاری داگرتن یان ناسینەوەی موزیک """
    url = update.message.text
    context.user_data["url"] = url

    keyboard = [
        [InlineKeyboardButton("🎥 داگرتنی ڤیدیۆ", callback_data="download_video"),
         InlineKeyboardButton("🎵 ناسینەوەی موزیک", callback_data="recognize_music")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text("📌 تکایە هەڵبژارەیەک دیاری بکە:", reply_markup=reply_markup)

async def choose_video_quality(update: Update, context: CallbackContext):
    """ هەڵبژاردنی کوالێتی ڤیدیۆ """
    query = update.callback_query
    url = context.user_data.get("url")

    keyboard = [
        [InlineKeyboardButton("🔹 360p", callback_data="360p"),
         InlineKeyboardButton("🔸 480p", callback_data="480p")],
        [InlineKeyboardButton("🔹 720p", callback_data="720p"),
         InlineKeyboardButton("🎵 تەنها دەنگ", callback_data="Audio")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text("📌 تکایە کوالێتی هەڵبژێرە:", reply_markup=reply_markup)

async def download_video(update: Update, context: CallbackContext):
    """ داگرتنی ڤیدیۆ بە کوالێتی دیاریکراو """
    query = update.callback_query
    quality = query.data
    url = context.user_data.get("url")

    if not url or quality not in QUALITY_OPTIONS:
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

async def recognize_and_send_music(update: Update, context: CallbackContext):
    """ ناسینەوە و ناردنی موزیک """
    query = update.callback_query
    url = context.user_data.get("url")

    # ناردنی پەیامی چاوەڕوانی
    status_message = await query.message.reply_text("🔎 بەدوای موزیکەکەدا دەگەڕێم...")
    
    # داگرتنی دەنگی ڤیدیۆکە
    audio_file = await download_audio_from_youtube(url)
    
    # ناسینەوەی موزیکەکە
    music_info = await recognize_music(audio_file)
    
    if music_info:
        # داگرتنی گۆرانی تەواو
        full_song_file = download_full_song(music_info['title'], music_info['artist'])
        
        # دروستکردنی پەیامی زانیاری
        response_text = f"🎵 موزیک دۆزرایەوە!\n\n" \
                        f"ناوی گۆرانی: {music_info['title']}\n" \
                        f"هونەرمەند: {music_info['artist']}"
        
        # ناردنی وێنەی بەرگ گەر هەبوو
        if music_info['cover_image']:
            try:
                cover_response = requests.get(music_info['cover_image'])
                if cover_response.status_code == 200:
                    cover_path = os.path.join(DOWNLOAD_DIR, 'cover.jpg')
                    with open(cover_path, 'wb') as f:
                        f.write(cover_response.content)
                    with open(cover_path, 'rb') as cover:
                        await query.message.reply_photo(photo=cover)
                    os.remove(cover_path)
            except Exception as e:
                print(f"هەڵە لە ناردنی وێنەی بەرگ: {e}")
        
        # ناردنی گۆرانی تەواو
        if full_song_file and os.path.exists(full_song_file):
            with open(full_song_file, 'rb') as audio:
                await query.message.reply_audio(audio=audio, 
                                                title=music_info['title'], 
                                                performer=music_info['artist'])
            os.remove(full_song_file)
        
        # زیادکردنی لینکی یوتیوب
        if music_info['youtube_link']:
            response_text += f"\n\n🔗 لینکی یوتیوب: {music_info['youtube_link']}"
        
        # سڕینەوەی پەیامی چاوەڕوانی
        await status_message.delete()
        
        # ناردنی زانیارییەکان
        await query.edit_message_text(response_text)
    else:
        # سڕینەوەی پەیامی چاوەڕوانی
        await status_message.delete()
        await query.edit_message_text("🤷‍♂️ نەمتوانی موزیکەکە بناسمەوە.")
    
    # سڕینەوەی فایلە کاتیەکان
    for file in ['temp_music.mp3', 'cover.jpg']:
        full_path = os.path.join(DOWNLOAD_DIR, file)
        if os.path.exists(full_path):
            os.remove(full_path)

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

async def download_audio_from_youtube(url):
    """ داگرتنی دەنگ لە یوتیوب """
    ydl_opts = {
        'format': 'bestaudio/best',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'outtmpl': os.path.join(DOWNLOAD_DIR, 'temp_music.%(ext)s')
    }
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    return os.path.join(DOWNLOAD_DIR, 'temp_music.mp3')

# فەرمانی نوێ بۆ ناردنی پەیام بۆ بەکارهێنەرێک
async def send_message_to_user(update: Update, context: CallbackContext):
    """ ناردنی پەیام بۆ بەکارهێنەرێک لەلایەن خاوەنی بۆتەوە """
    if str(update.effective_user.id) != OWNER_CHAT_ID:
        await update.message.reply_text("🚫 تەنها خاوەنی بۆت دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("🔍 نموونە: /send ئایدی پەیامەکەت")
        return
    
    user_id = args[0]
    message = " ".join(args[1:])
    
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=message
        )
        await update.message.reply_text(f"✅ پەیام بە سەرکەوتوویی نێردرا بۆ بەکارهێنەر {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ نەمتوانی پەیام بنێرم: {e}")

# فەرمانی نوێ بۆ ناردنی پەیام بۆ بەکارهێنەران (تاکەکەسی یان هەموویان)
async def send_message_command(update: Update, context: CallbackContext):
    """ ناردنی پەیام بۆ بەکارهێنەر یان هەموو بەکارهێنەران """
    if str(update.effective_user.id) != OWNER_CHAT_ID:
        await update.message.reply_text("🚫 تەنها خاوەنی بۆت دەتوانێت ئەم فەرمانە بەکاربهێنێت.")
        return

    message_text = update.message.text
    
    # شیکردنەوەی رێکخستنی پەیام
    message_pattern = r"/message\s+@(\w+)\s*:\s*(.*)"
    match = re.match(message_pattern, message_text, re.DOTALL)
    
    if not match:
        await update.message.reply_text("🔍 شێوازی نادروست. نموونە:\n/message @username : پەیامەکەت\n/message @everyone : پەیامەکەت")
        return
    
    target = match.group(1)
    message_content = match.group(2).strip()
    
    if not message_content:
        await update.message.reply_text("❌ تکایە پەیامێک بنووسە.")
        return
    
    # ئەگەر ئامانج بوو @everyone
    if target.lower() == "everyone":
        success_count = 0
        failed_count = 0
        
        # ناردنی پەیام بۆ هەموو بەکارهێنەران
        await update.message.reply_text("⏳ ناردنی پەیام بۆ هەموو بەکارهێنەران...")
        
        for user_id in USER_ANALYTICS.keys():
            try:
                # ناردنی پەیام
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"📢 ئاگاداری لە خاوەنی بۆتەوە:\n\n{message_content}"
                )
                success_count += 1
            except Exception as e:
                failed_count += 1
                print(f"هەڵە لە ناردنی پەیام بۆ {user_id}: {e}")
        
        # ئاگادارکردنەوەی خاوەنی بۆت لە ئەنجامەکان
        result_message = (
            f"✅ پەیام بۆ {success_count} بەکارهێنەر نێردرا.\n"
            f"❌ نەکرا بۆ {failed_count} بەکارهێنەر بنێردرێت."
        )
        
        await update.message.reply_text(result_message)
        
    else:
        # ناردنی پەیام بۆ تاکە کەسێک
        # گەڕان بەدوای بەکارهێنەر لە ئەنالیتیکسدا
        user_id = None
        
        # گەڕان بەدوای بەکارهێنەر بەپێی یوزەرنەیم
        for uid, data in USER_ANALYTICS.items():
            username = data.get('username', 'بێ ناو')
            if username == f"@{target}" or username == target:
                user_id = uid
                break
        
        if not user_id:
            await update.message.reply_text(f"❌ بەکارهێنەری @{target} نەدۆزرایەوە.")
            return
        
        try:
            # ناردنی پەیام
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 پەیام لە خاوەنی بۆتەوە:\n\n{message_content}"
            )
            await update.message.reply_text(f"✅ پەیام بۆ @{target} نێردرا.")
        except Exception as e:
            await update.message.reply_text(f"❌ هەڵە لە ناردنی پەیام: {e}")

def main():
    """ 🚀 بەڕێوەبردنی بوت """
    app = Application.builder().token(BOT_TOKEN).build()
    
    # هاندەرەکانی نوێ
    app.add_handler(CommandHandler("listuser", listuser))
    app.add_handler(CommandHandler("unban", unban_user))
    app.add_handler(CommandHandler("listban", listban))
    app.add_handler(CommandHandler("ban", ban_user))
    app.add_handler(CommandHandler("send", send_message_to_user))
    
    # زیادکردنی فەرمانی نوێی پەیام ناردن
    app.add_handler(MessageHandler(filters.COMMAND & filters.Regex(r"^/message"), send_message_command))
    
    # هاندەرەکانی پێشووتر
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(choose_video_quality, pattern="^download_video$"))
    app.add_handler(CallbackQueryHandler(download_video, pattern="^(360p|480p|720p|Audio)$"))
    app.add_handler(CallbackQueryHandler(recognize_and_send_music, pattern="^recognize_music$"))
    
    print("🤖 بوت بەردەستە!")
    app.run_polling()

if __name__ == "__main__":
    main()
