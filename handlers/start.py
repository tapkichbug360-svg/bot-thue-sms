from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext as Context
from database.models import User, db
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

MB_ACCOUNT = os.getenv('MB_ACCOUNT', '666666291005')
MB_NAME = os.getenv('MB_NAME', 'NGUYEN THE LAM')

async def start_command(update: Update, context: Context):
    user = update.effective_user
    
    from main import app
    with app.app_context():
        existing_user = User.query.filter_by(user_id=user.id).first()
        if not existing_user:
            new_user = User(
                user_id=user.id,
                username=user.username or user.first_name,
                balance=0,
                created_at=datetime.now(),
                last_active=datetime.now()
            )
            db.session.add(new_user)
            db.session.commit()
            logger.info(f"Người dùng mới: {user.id} - {user.first_name}")
        else:
            existing_user.last_active = datetime.now()
            db.session.commit()
    
    keyboard = [
        [InlineKeyboardButton("📱 Thuê số", callback_data='menu_rent')],
        [InlineKeyboardButton("💰 Số dư", callback_data='menu_balance')],
        [InlineKeyboardButton("📥 Nạp tiền", callback_data='menu_deposit')],
        [InlineKeyboardButton("📋 Lịch sử", callback_data='menu_history')],
        [InlineKeyboardButton("❓ Hướng dẫn", callback_data='menu_help')],
        [InlineKeyboardButton("👤 Tài khoản", callback_data='menu_profile')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_msg = f"""🎉 **Chào mừng {user.first_name} đến với Bot Thuê SMS 24/7!**

🤖 Bot cung cấp dịch vụ thuê số điện thoại ảo:
• Facebook • Google • Telegram • Tiktok • Shopee

⚠️ **TUÂN THỦ PHÁP LUẬT:**
• Nghiêm cấm lừa đảo, cá độ, bank ảo
• Vi phạm sẽ khóa tài khoản

💰 **Giá thuê:** Giá gốc + 1.000đ

🏦 **MBBANK**
💳 **Số TK:** {MB_ACCOUNT}
👤 **Chủ TK:** **{MB_NAME}**

✅ **Tích hợp SePay - Tự động cộng tiền**"""
    
    await update.message.reply_text(welcome_msg, reply_markup=reply_markup, parse_mode='Markdown')
