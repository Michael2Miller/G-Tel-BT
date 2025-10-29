import os
import logging
import google.generativeai as genai
from telegram import Update, constants
from telegram.ext import Application, CommandHandler, ContextTypes

# إعداد تسجيل الدخول (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- جلب المتغيرات الأساسية ---
try:
    BOT_TOKEN = os.environ['BOT_TOKEN'] 
    GEMINI_API_KEY = os.environ['GEMINI_API_KEY']
except KeyError as e:
    logger.critical(f"FATAL ERROR: Environment variable {e} is not set.")
    exit(f"Missing environment variable: {e}")

# --- إعداد واجهة Gemini ---
try:
    genai.configure(api_key=GEMINI_API_KEY)
except Exception as e:
    logger.critical(f"Failed to configure Gemini: {e}")
    exit(f"Gemini configuration error: {e}")

# --- (الدالة الجديدة) كاشف الموديلات ---
async def list_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ترسل للمستخدم قائمة بال موديلات المتاحة."""
    try:
        await update.message.reply_text("Checking available models for your API key...")
        
        # --- (هذا هو السطر الذي تم تصحيحه) ---
        # genAi (خاطئ) -> genai (صحيح)
        models_list = genai.list_models()
        # ------------------------------------
        
        response_text = "✅ **Available Models:**\n\n"
        
        # إنشاء قائمة بال موديلات التي تدعم الدردشة (generateContent)
        for m in models_list:
            if 'generateContent' in m.supported_generation_methods:
                response_text += f"• `{m.name}`\n"
        
        # إزالة الشرطة المائلة الزائدة للرسالة الأخيرة
        response_text = response_text.replace(r"\_", "_")

        await update.message.reply_text(response_text, parse_mode=constants.ParseMode.MARKDOWN_V2)

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        await update.message.reply_text(f"An error occurred: {e}")

# --- الدالة الرئيسية ---
def main():
    # إعداد البوت
    application = Application.builder().token(BOT_TOKEN).build()

    # إضافة معالج واحد فقط: /start
    application.add_handler(CommandHandler("start", list_models))

    # تشغيل البوت
    logger.info("Bot is starting (Model Finder Mode)...")
    application.run_polling()

if __name__ == '__main__':
    main()
