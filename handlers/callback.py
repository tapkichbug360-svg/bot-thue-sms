from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext as Context
from database.models import User, Rental
from datetime import datetime

async def menu_callback(update: Update, context: Context):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'menu_main':
        keyboard = [
            [InlineKeyboardButton("📱 Thuê số", callback_data='menu_rent')],
            [InlineKeyboardButton("💰 Số dư", callback_data='menu_balance')],
            [InlineKeyboardButton("📥 Nạp tiền", callback_data='menu_deposit')],
            [InlineKeyboardButton("📋 Lịch sử", callback_data='menu_history')],
            [InlineKeyboardButton("❓ Hướng dẫn", callback_data='menu_help')],
            [InlineKeyboardButton("👤 Tài khoản", callback_data='menu_profile')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🏠 **MENU CHÍNH**", reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == 'menu_balance':
        from handlers.balance import balance_command
        await balance_command(update, context)
    
    elif data == 'menu_deposit':
        from handlers.deposit import deposit_command
        await deposit_command(update, context)
    
    elif data == 'menu_rent':
        await query.edit_message_text("📱 Tính năng thuê số đang phát triển...")
    
    elif data == 'menu_history':
        user = update.effective_user
        from main import app
        with app.app_context():
            rentals = Rental.query.filter_by(user_id=user.id).order_by(Rental.created_at.desc()).limit(10).all()
        
        if not rentals:
            text = "📋 Bạn chưa có lịch sử thuê số nào."
        else:
            text = "📋 **LỊCH SỬ THUÊ SỐ (10 gần nhất)**\n\n"
            for r in rentals:
                status = "✅" if r.status == 'success' else "⏳"
                text += f"{status} {r.created_at.strftime('%H:%M %d/%m')} - {r.service_name}: {r.phone_number}\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == 'menu_help':
        text = """❓ **HƯỚNG DẪN SỬ DỤNG**

1️⃣ **Nạp tiền:**
   • Chọn "Nạp tiền" → Chọn số tiền
   • Chuyển khoản đến **MBBank 666666291005 - NGUYEN THE LAM**
   • Bấm "ĐÃ CHUYỂN KHOẢN"

2️⃣ **Thuê số:**
   • Tính năng đang phát triển

3️⃣ **Hủy số:**
   • Tính năng đang phát triển

⚠️ **LƯU Ý:**
• Không sử dụng cho mục đích bất hợp pháp
• Mọi giao dịch đều được ghi lại"""
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    elif data == 'menu_profile':
        user = update.effective_user
        from main import app
        with app.app_context():
            db_user = User.query.filter_by(user_id=user.id).first()
            created = db_user.created_at.strftime('%d/%m/%Y %H:%M') if db_user else 'N/A'
            balance = db_user.balance if db_user else 0
        
        text = f"""👤 **THÔNG TIN CÁ NHÂN**

• **ID:** {user.id}
• **Tên:** {user.first_name}
• **Username:** @{user.username or 'Không có'}
• **Ngày tham gia:** {created}
• **Số dư:** {balance:,}đ"""
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data='menu_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
