import logging
import os
import sys
from datetime import datetime
from flask import Flask
from database.models import db, init_db
from handlers.sepay import setup_sepay_webhook

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

@app.route('/')
def home():
    return f"""
    <!DOCTYPE html>
    <html>
    <head><title>SePay Webhook Server</title></head>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🏦 SePay Webhook Server</h1>
        <p><strong>Trạng thái:</strong> ✅ ĐANG CHẠY</p>
        <p><strong>MBBank:</strong> 666666291005 - NGUYEN THE LAM</p>
        <p><strong>Webhook URL:</strong> <code>/webhook/sepay</code></p>
        <p><strong>Thời gian:</strong> {datetime.now().strftime('%H:%M:%S %d/%m/%Y')}</p>
    </body>
    </html>
    """

@app.route('/health')
def health():
    return {"status": "healthy"}, 200

@app.route('/webhook/sepay', methods=['POST'])
def sepay_webhook_handler():
    from handlers.sepay import sepay_webhook
    return sepay_webhook()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)
