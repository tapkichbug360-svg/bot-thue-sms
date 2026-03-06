import logging
import os
import sys
import threading
import time
from datetime import datetime
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from flask import Flask

# Tạo thư mục database nếu chưa có
db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)

print("Đang đọc file .env...")
try:
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value.strip()
                print(f"Đã đọc: {key}")
except Exception as e:
    print(f"LỖI ĐỌC FILE .ENV: {e}")
    sys.exit(1)

BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("="*60)
    print("LỖI: KHÔNG TÌM THẤY BOT_TOKEN")
    print("="*60)
    sys.exit(1)

print(f"✅ TÌM THẤY BOT_TOKEN: {BOT_TOKEN[:15]}...")

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

# Import database
from database.models import db, init_db

# Import handlers
from handlers.start import start_command
from handlers.balance import balance_command
from handlers.deposit import deposit_command, deposit_amount_callback, deposit_check_callback
from handlers.callback import menu_callback
from handlers.sepay import setup_sepay_webhook

# Tạo Flask app
app = Flask(__name__)

# Đường dẫn database
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database', 'bot.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Tạo database
with app.app_context():
    try:
        db.create_all()
        logger.info("✅ ĐÃ TẠO DATABASE THÀNH CÔNG!")
    except Exception as e:
        if "already exists" in str(e):
            logger.info("ℹ️ Database đã tồn tại, tiếp tục...")
        else:
            logger.error(f"LỖI TẠO DATABASE: {e}")

# Thiết lập webhook SePay
setup_sepay_webhook(app)

# Biến toàn cục
_bot_running = False
_bot_thread = None

def run_bot():
    """Chạy bot Telegram trong thread riêng"""
    global _bot_running
    
    if _bot_running:
        logger.info("Bot đã đang chạy, bỏ qua...")
        return
    
    try:
        logger.info("🚀 ĐANG KHỞI ĐỘNG BOT TELEGRAM...")
        
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
        _bot_running = True
        
        # Chạy bot
        application.run_polling(timeout=30, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ LỖI KHI CHẠY BOT: {e}")
        _bot_running = False
        time.sleep(30)

@app.route('/')
def home():
    status = "✅ BOT ĐANG CHẠY" if _bot_running else "⏳ BOT ĐANG KHỞI ĐỘNG"
    return f"""
    <html>
        <head><title>Bot Thuê SMS</title></head>
        <body style="font-family: Arial; padding: 20px;">
            <h1>🤖 Bot Thuê SMS 24/7</h1>
            <p><strong>Trạng thái:</strong> {status}</p>
            <p><strong>MBBank:</strong> 666666291005 - NGUYEN THE LAM</p>
            <p><strong>SePay Webhook:</strong> /webhook/sepay</p>
            <p><strong>Bot Telegram:</strong> @thue_sms_online_bot</p>
            <hr>
            <p><em>Server đang chạy: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</em></p>
        </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy", "bot": "running" if _bot_running else "starting"}, 200

# Hàm khởi động bot
def start_bot():
    global _bot_thread
    if _bot_thread is None or not _bot_thread.is_alive():
        _bot_thread = threading.Thread(target=run_bot, daemon=True)
        _bot_thread.start()
        logger.info("🤖 THREAD BOT ĐÃ ĐƯỢC KHỞI TẠO")

# Khởi động bot khi app khởi tạo
start_bot()

# Phần này chỉ chạy khi file được chạy trực tiếp
if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
