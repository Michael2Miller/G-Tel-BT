import os
import logging
import google.generativeai as genai
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, constants
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from telegram.error import BadRequest

# إعداد تسجيل الدخول (Logging) لرؤية الأخطاء
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- جلب المتغيرات الـ 4 من Railway ---
try:
    BOT_TOKEN = os.environ['BOT_TOKEN'] 
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
    CHANNEL_ID = os.environ['CHANNEL_ID']
    CHANNEL_INVITE_LINK = os.environ['CHANNEL_INVITE_LINK']
except KeyError as e:
    logger.critical(f"FATAL ERROR: Environment variable {e} is not set.")
    exit(f"Missing environment variable: {e}")

# --- إعداد واجهة Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
    
    # --- (هذا هو التصحيح الأول: تغيير اسم الموديل) ---
    gemini_model = genai.GenerativeModel('gemini-1.0-pro')
    # ----------------------------------------------

except Exception as e:
    logger.critical(f"Failed to configure Gemini: {e}")
    exit(f"Gemini configuration error: {e}")


# --- (الدالة الأهم) التحقق المستمر من الاشتراك ---
async def is_user_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    تتحقق هذه الدالة مما إذا كان المستخدم عضواً في القناة.
    """
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_ID, user_id=user_id)
        if member.status in ['member', 'administrator', 'creator']:
            return True
        else:
            # حالته 'left' أو 'kicked'
            return False
    except BadRequest as e:
        if "user not found" in e.message:
            logger.warning(f"User {user_id} not found in channel, likely not joined.")
            return False
        else:
            logger.error(f"Error checking channel membership for {user_id}: {e}")
            return False # نفترض أنه غير مشترك إذا حدث خطأ
    except Exception as e:
        logger.error(f"Unexpected error checking membership for {user_id}: {e}")
        return False

# --- (الدالة المساعدة) إرسال رسالة "الجدار" (اطلب الاشتراك) ---
async def send_join_channel_message(update: Update):
    """
    ترسل الرسالة التي تطلب من المستخدم الاشتراك.
    """
    keyboard = [
        [
            InlineKeyboardButton("🔗 Join Channel", url=CHANNEL_INVITE_LINK),
            InlineKeyboardButton("✅ I have joined", callback_data="check_join")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    sender = update.message.reply_text if update.message else update.callback_query.message.reply_text
    
    # --- (تم التعديل: إضافة 'r' لإزالة التحذيرات) ---
    await sender(
        r"👋 **Welcome to the free Gemini Bot\!**" + "\n\n"
        r"To use this bot for free, you are required to join our official channel\." + "\n\n"
        r"**Why join?**" + "\n\n"
        r"1️⃣ It **unlocks** your free access to the bot\." + "\n\n"
        r"2️⃣ You'll **discover** our other free bots\." + "\n\n"
        r"3️⃣ You'll get all **updates** and support alerts\." + "\n\n\n"
        r"Please join the channel, then return here and press the button below\.",
        reply_markup=reply_markup,
        parse_mode=constants.ParseMode.MARKDOWN_V2
    )

# --- معالج أمر /start ---
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if await is_user_subscribed(user_id, context):
        # الحالة 4: المستخدم العائد (المشترك)
        
        # --- (هذا هو التصحيح الثاني: إضافة 'r' وإصلاح '!') ---
        await update.message.reply_text(
            r"👋 **Welcome back\!**" + "\n\n"  # <--- تم الإصلاح
            r"You're all set\. Just send your question\.",
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
    else:
        # الحالة 1: المستخدم الجديد (غير مشترك)
        await send_join_channel_message(update)

# --- معالج الرسائل النصية (Gemini) ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if await is_user_subscribed(user_id, context):
        # الحالة 2 (الاستخدام العادي): المستخدم مشترك، أرسل إلى Gemini
        user_text = update.message.text
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
            response = gemini_model.generate_content(user_text)
            
            # إرسال رد Gemini كنص عادي (لتجنب أي أخطاء تنسيق من Gemini)
            await update.message.reply_text(response.text) 
            
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            # --- (تم التعديل: إضافة 'r' لإزالة التحذيرات) ---
            await update.message.reply_text(r"Sorry, I couldn't process your request at the moment\. Please try again later\.", parse_mode=constants.ParseMode.MARKDOWN_V2)
    
    else:
        # الحالة 1 أو 3: المستخدم غير مشترك (أو غادر)، أظهر له الجدار
        await send_join_channel_message(update)

# --- معالج ضغطة الزر [✅ I have joined] ---
async def handle_join_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    
    await query.answer("Checking your membership...") # رد مرئي مؤقت
    
    if await is_user_subscribed(user_id, context):
        # الحالة 2 (نجاح): انضم فعلاً
        
        # --- (هذا هو التصحيح الثالث: إضافة 'r' وإصلاح '!') ---
        await query.edit_message_text(
            r"🎉 **Verification Complete\!**" + "\n\n"  # <--- تم الإصلاح
            r"Thank you for joining\. Your account is now active\." + "\n\n"
            r"You can now send me any question, and I will answer using Gemini\.",
            reply_markup=None, # إزالة الأزرار
            parse_mode=constants.ParseMode.MARKDOWN_V2
        )
    else:
        # الحالة 1 (فشل): لم ينضم بعد
        await query.answer("Please subscribe to the channel to be allowed to use the bot.", show_alert=True)

# --- الدالة الرئيسية ---
def main():
    # إعداد البوت
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_join_check, pattern="^check_join$"))

    # تشغيل البوت
    logger.info("Bot is starting (Simplified Mode)...")
    application.run_polling()

if __name__ == '__main__':
    main()
