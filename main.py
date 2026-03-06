import logging
import os
import sys
import threading
import time
import asyncio
from datetime import datetime
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
from flask import Flask

# Tạo thư mục database nếu chưa có
db_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'database')
if not os.path.exists(db_dir):
    os.makedirs(db_dir)
    print(f"Đã tạo thư mục database: {db_dir}")

print("="*60)
print("ĐANG ĐỌC FILE .ENV...")
print("="*60)
try:
    with open('.env', 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key] = value.strip()
                print(f"✅ Đã đọc: {key}")
except FileNotFoundError:
    print("❌ KHÔNG TÌM THẤY FILE .ENV")
    print("Vui lòng tạo file .env với các biến môi trường cần thiết")
    sys.exit(1)
except Exception as e:
    print(f"❌ LỖI ĐỌC FILE .ENV: {e}")
    sys.exit(1)

print("="*60)

# Lấy BOT_TOKEN
BOT_TOKEN = os.getenv('BOT_TOKEN')

if not BOT_TOKEN:
    print("="*60)
    print("❌ LỖI: KHÔNG TÌM THẤY BOT_TOKEN")
    print("Vui lòng kiểm tra lại file .env")
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

# Tạo database (xử lý lỗi table đã tồn tại)
with app.app_context():
    try:
        db.create_all()
        logger.info("✅ ĐÃ TẠO DATABASE THÀNH CÔNG!")
    except Exception as e:
        if "already exists" in str(e):
            logger.info("ℹ️ Database đã tồn tại, tiếp tục...")
        else:
            logger.error(f"❌ LỖI TẠO DATABASE: {e}")

# Thiết lập webhook SePay
setup_sepay_webhook(app)

# Biến toàn cục để theo dõi trạng thái bot
_bot_running = False
_bot_thread = None
_bot_application = None

def run_bot():
    """Chạy bot Telegram trong thread riêng"""
    global _bot_running, _bot_application
    
    # Tạo event loop mới cho thread
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception as e:
        logger.error(f"❌ LỖI TẠO EVENT LOOP: {e}")
    
    if _bot_running:
        logger.info("ℹ️ Bot đã đang chạy, bỏ qua...")
        return
    
    try:
        logger.info("🚀 ĐANG KHỞI ĐỘNG BOT TELEGRAM...")
        
        # Tạo application
        application = Application.builder().token(BOT_TOKEN).build()
        _bot_application = application
        
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
        
        # Chạy bot (chặn thread này)
        application.run_polling(timeout=30, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ LỖI KHI CHẠY BOT: {e}")
        _bot_running = False
        _bot_application = None
        
        # Đợi 30 giây rồi thử lại
        logger.info("⏳ Thử lại sau 30 giây...")
        time.sleep(30)
        run_bot()

def start_bot_thread():
    """Khởi động bot trong một thread riêng biệt"""
    global _bot_thread
    if _bot_thread is None or not _bot_thread.is_alive():
        _bot_thread = threading.Thread(target=run_bot, daemon=True)
        _bot_thread.start()
        logger.info("🤖 THREAD BOT ĐÃ ĐƯỢC KHỞI TẠO")
        return True
    else:
        logger.info("ℹ️ Thread bot đã đang chạy")
        return False

@app.route('/')
def home():
    """Trang chủ kiểm tra bot đang chạy"""
    status = "✅ BOT ĐANG CHẠY" if _bot_running else "⏳ BOT ĐANG KHỞI ĐỘNG"
    thread_status = "✅ ĐANG CHẠY" if _bot_thread and _bot_thread.is_alive() else "⏳ CHƯA CHẠY"
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Bot Thuê SMS 24/7</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 40px;
                background-color: #f5f5f5;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                max-width: 800px;
                margin: 0 auto;
            }}
            h1 {{
                color: #2c3e50;
                border-bottom: 2px solid #3498db;
                padding-bottom: 10px;
            }}
            .status {{
                padding: 15px;
                margin: 20px 0;
                border-radius: 5px;
                font-weight: bold;
            }}
            .success {{
                background-color: #d4edda;
                color: #155724;
                border: 1px solid #c3e6cb;
            }}
            .info {{
                background-color: #d1ecf1;
                color: #0c5460;
                border: 1px solid #bee5eb;
            }}
            .warning {{
                background-color: #fff3cd;
                color: #856404;
                border: 1px solid #ffeeba;
            }}
            .bank-info {{
                background-color: #e2e3e5;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .footer {{
                margin-top: 30px;
                text-align: center;
                color: #7f8c8d;
                font-size: 0.9em;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 Bot Thuê SMS 24/7</h1>
            
            <div class="status success">
                <strong>🚀 TRẠNG THÁI SERVICE:</strong> ✅ ĐANG CHẠY
            </div>
            
            <div class="status { 'success' if _bot_running else 'warning' }">
                <strong>🤖 BOT TELEGRAM:</strong> {status}
            </div>
            
            <div class="status { 'success' if _bot_thread and _bot_thread.is_alive() else 'info' }">
                <strong>🧵 THREAD BOT:</strong> {thread_status}
            </div>
            
            <div class="bank-info">
                <h3>🏦 THÔNG TIN NGÂN HÀNG</h3>
                <p><strong>Ngân hàng:</strong> MBBank</p>
                <p><strong>Số tài khoản:</strong> <code>666666291005</code></p>
                <p><strong>Chủ tài khoản:</strong> NGUYEN THE LAM</p>
                <p><strong>Nội dung chuyển khoản:</strong> <code>NAP [MÃ GIAO DỊCH]</code></p>
            </div>
            
            <div class="bank-info">
                <h3>🔗 WEBHOOK SEPAY</h3>
                <p><strong>URL:</strong> <code>/webhook/sepay</code></p>
                <p><strong>Đầy đủ:</strong> <code>https://bot-thue-sms.onrender.com/webhook/sepay</code></p>
            </div>
            
            <div class="footer">
                <p>⏰ Thời gian hiện tại: {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</p>
                <p>⚡ Server đang chạy 24/7 trên Render</p>
            </div>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health():
    """Health check cho Render"""
    return {
        "status": "healthy",
        "bot": "running" if _bot_running else "starting",
        "thread": "alive" if _bot_thread and _bot_thread.is_alive() else "dead",
        "timestamp": datetime.now().isoformat()
    }, 200

@app.route('/webhook/sepay', methods=['POST'])
def sepay_webhook_handler():
    """Endpoint nhận webhook từ SePay"""
    from handlers.sepay import sepay_webhook
    return sepay_webhook()

# Khởi động bot thread ngay khi Flask app được khởi tạo
logger.info("🔄 ĐANG KHỞI ĐỘNG BOT THREAD...")
start_bot_thread()

# Phần này chỉ chạy khi file được chạy trực tiếp (dùng để test local)
if __name__ == '__main__':
    # Kiểm tra xem có đang chạy trên Render không
    if os.getenv('RENDER') == 'true':
        logger.info("🏭 Đang chạy trên Render - Gunicorn sẽ quản lý Flask")
        # Không làm gì thêm, gunicorn sẽ chạy app
    else:
        # Chạy local để test
        port = int(os.getenv('PORT', 8080))
        logger.info(f"🌐 CHẠY Ở CHẾ ĐỘ LOCAL - Flask sẽ chạy trên port {port}")
        logger.info("⚠️ Bot đã được khởi động trong thread riêng")
        app.run(host='0.0.0.0', port=port, debug=False)