import logging
import os
import sys
import asyncio
from dotenv import load_dotenv
from telegram.ext import Application, CommandHandler, CallbackQueryHandler

# Load biến môi trường
load_dotenv()

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Lấy BOT_TOKEN
BOT_TOKEN = os.getenv('BOT_TOKEN')
if not BOT_TOKEN:
    logger.error("❌ KHÔNG TÌM THẤY BOT_TOKEN")
    sys.exit(1)

# Import handlers
try:
    from handlers.start import start_command
    from handlers.balance import balance_command
    from handlers.deposit import deposit_command, deposit_amount_callback, deposit_check_callback
    from handlers.callback import menu_callback
    logger.info("✅ Đã import handlers thành công")
except Exception as e:
    logger.error(f"❌ LỖI IMPORT HANDLERS: {e}")
    sys.exit(1)

async def main():
    """Chạy bot Telegram"""
    try:
        logger.info("🚀 BOT TELEGRAM ĐANG KHỞI ĐỘNG...")
        
        # Tạo application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("deposit", deposit_command))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(deposit_amount_callback, pattern="^deposit_amount_"))
        application.add_handler(CallbackQueryHandler(deposit_check_callback, pattern="^deposit_check_"))
        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
        
        logger.info("✅ BOT TELEGRAM ĐÃ KHỞI ĐỘNG THÀNH CÔNG!")
        
        # Chạy bot
        await application.run_polling(timeout=30, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ LỖI KHI CHẠY BOT: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Bot đã dừng")
    except Exception as e:
        logger.error(f"❌ LỖI: {e}")
        sys.exit(1)
