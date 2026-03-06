import logging
import os
import sys
import multiprocessing
import time
from datetime import datetime
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

# Import handlers - sẽ được import trong process con
# from handlers.start import start_command
# from handlers.balance import balance_command
# from handlers.deposit import deposit_command, deposit_amount_callback, deposit_check_callback
# from handlers.callback import menu_callback
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

# Biến toàn cục để theo dõi tiến trình bot
_bot_process = None

def run_bot_process():
    """Hàm này sẽ chạy trong một tiến trình riêng - KHÔNG dùng chung Flask app"""
    import asyncio
    import logging
    import os
    from telegram.ext import Application, CommandHandler, CallbackQueryHandler
    
    # Cấu hình logging cho process con
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
    logger = logging.getLogger("bot_process")
    
    # Import handlers trong process con
    from handlers.start import start_command
    from handlers.balance import balance_command
    from handlers.deposit import deposit_command, deposit_amount_callback, deposit_check_callback
    from handlers.callback import menu_callback
    
    # Tạo event loop mới cho process này
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        logger.info("✅ Đã tạo event loop cho bot process")
    except Exception as e:
        logger.error(f"❌ LỖI TẠO EVENT LOOP: {e}")
        return
    
    try:
        logger.info("🚀 BOT PROCESS ĐANG KHỞI ĐỘNG...")
        
        # Lấy token từ biến môi trường (đã được kế thừa từ process cha)
        token = os.getenv('BOT_TOKEN')
        if not token:
            logger.error("❌ KHÔNG TÌM THẤY BOT_TOKEN trong process con")
            return
        
        # Tạo application
        application = Application.builder().token(token).build()
        
        # Command handlers
        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("balance", balance_command))
        application.add_handler(CommandHandler("deposit", deposit_command))
        
        # Callback handlers
        application.add_handler(CallbackQueryHandler(deposit_amount_callback, pattern="^deposit_amount_"))
        application.add_handler(CallbackQueryHandler(deposit_check_callback, pattern="^deposit_check_"))
        application.add_handler(CallbackQueryHandler(menu_callback, pattern="^menu_"))
        
        logger.info("✅ BOT PROCESS ĐÃ KHỞI ĐỘNG THÀNH CÔNG!")
        
        # Chạy bot (chặn process này)
        application.run_polling(timeout=30, drop_pending_updates=True)
        
    except Exception as e:
        logger.error(f"❌ LỖI TRONG BOT PROCESS: {e}")
        import traceback
        traceback.print_exc()

def start_bot_process():
    """Khởi động bot trong một tiến trình riêng"""
    global _bot_process
    if _bot_process is None or not _bot_process.is_alive():
        _bot_process = multiprocessing.Process(target=run_bot_process, daemon=True)
        _bot_process.start()
        logger.info(f"🤖 TIẾN TRÌNH BOT ĐÃ ĐƯỢC KHỞI TẠO VỚI PID: {_bot_process.pid}")
        return True
    else:
        logger.info(f"ℹ️ Tiến trình bot đã đang chạy với PID: {_bot_process.pid}")
        return False

@app.route('/')
def home():
    """Trang chủ kiểm tra bot đang chạy"""
    bot_status = "✅ BOT ĐANG CHẠY" if _bot_process and _bot_process.is_alive() else "❌ BOT KHÔNG CHẠY"
    pid_info = f"PID: {_bot_process.pid}" if _bot_process and _bot_process.is_alive() else "Chưa khởi động"
    
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
                <strong>🚀 FLASK SERVER:</strong> ✅ ĐANG CHẠY
            </div>
            
            <div class="status { 'success' if _bot_process and _bot_process.is_alive() else 'warning' }">
                <strong>🤖 BOT TELEGRAM:</strong> {bot_status}<br>
                <strong>🆔 PID:</strong> {pid_info}
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
        "bot": "running" if _bot_process and _bot_process.is_alive() else "stopped",
        "pid": _bot_process.pid if _bot_process and _bot_process.is_alive() else None,
        "timestamp": datetime.now().isoformat()
    }, 200

@app.route('/webhook/sepay', methods=['POST'])
def sepay_webhook_handler():
    """Endpoint nhận webhook từ SePay"""
    from handlers.sepay import sepay_webhook
    return sepay_webhook()

# Khởi động bot process ngay khi Flask app được khởi tạo
logger.info("🔄 ĐANG KHỞI ĐỘNG TIẾN TRÌNH BOT...")
start_bot_process()

# Phần này chỉ chạy khi file được chạy trực tiếp
if __name__ == '__main__':
    # Kiểm tra xem có đang chạy trên Render không
    if os.getenv('RENDER') == 'true':
        logger.info("🏭 Đang chạy trên Render - Gunicorn sẽ quản lý Flask")
        # Không làm gì thêm, gunicorn sẽ chạy app
    else:
        # Chạy local để test
        port = int(os.getenv('PORT', 8080))
        logger.info(f"🌐 CHẠY Ở CHẾ ĐỘ LOCAL - Flask sẽ chạy trên port {port}")
        app.run(host='0.0.0.0', port=port, debug=False)