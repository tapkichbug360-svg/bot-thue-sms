from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext as Context
from database.models import User, Transaction, db
from datetime import datetime
import logging
import random
import string
import os

logger = logging.getLogger(__name__)

MB_ACCOUNT = os.getenv('MB_ACCOUNT', '666666291005')
MB_NAME = os.getenv('MB_NAME', 'NGUYEN THE LAM')
MB_BIN = os.getenv('MB_BIN', '970422')

async def deposit_command(update: Update, context: Context):
    transaction_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
    
    context.user_data['pending_deposit'] = {
        'code': transaction_code,
        'amount': None
    }
    
    amounts = [20000, 50000, 100000, 200000, 500000, 1000000]
    keyboard = []
    row = []
    for i, amount in enumerate(amounts):
        btn = InlineKeyboardButton(f"{amount:,}đ", callback_data=f"deposit_amount_{amount}")
        row.append(btn)
        if len(row) == 2 or i == len(amounts)-1:
            keyboard.append(row)
            row = []
    
    keyboard.append([InlineKeyboardButton("🔙 Quay lại", callback_data="menu_main")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""🏦 **NẠP TIỀN QUA MBBANK**

💳 **Số TK:** {MB_ACCOUNT}
👤 **Chủ TK:** {MB_NAME}
🏦 **Ngân hàng:** MBBank

📝 **Nội dung:** NAP {transaction_code}

💰 **Chọn số tiền:**"""
    
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def deposit_amount_callback(update: Update, context: Context):
    query = update.callback_query
    await query.answer()
    
    amount = int(query.data.split('_')[2])
    pending = context.user_data.get('pending_deposit', {})
    transaction_code = pending.get('code')
    
    if not transaction_code:
        await query.edit_message_text("❌ Có lỗi xảy ra!")
        return
    
    from main import app
    with app.app_context():
        user = update.effective_user
        transaction = Transaction(
            user_id=user.id,
            amount=amount,
            type='deposit',
            status='pending',
            transaction_code=transaction_code,
            description=f'Nạp {amount}đ qua MBBank',
            created_at=datetime.now()
        )
        db.session.add(transaction)
        db.session.commit()
    
    content = f"NAP {transaction_code}"
    qr_url = f"https://img.vietqr.io/image/{MB_BIN}-{MB_ACCOUNT}-compact2.png?amount={amount}&addInfo={content}&accountName={MB_NAME}"
    
    keyboard = [
        [InlineKeyboardButton("✅ ĐÃ CHUYỂN KHOẢN", callback_data=f"deposit_check_{transaction_code}")],
        [InlineKeyboardButton("💰 Nạp tiếp", callback_data="menu_deposit")],
        [InlineKeyboardButton("📱 Thuê số", callback_data="menu_rent")],
        [InlineKeyboardButton("🔙 Menu chính", callback_data="menu_main")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_photo(
        chat_id=update.effective_chat.id,
        photo=qr_url,
        caption=f"""🏦 **THÔNG TIN CHUYỂN KHOẢN**

💳 **STK:** {MB_ACCOUNT}
👤 **Chủ TK:** {MB_NAME}
💰 **Số tiền:** {amount:,}đ
📝 **Nội dung:** {content}

✅ **Bấm nút sau khi chuyển - SePay tự động cộng tiền!**""",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )
    
    await query.delete_message()

async def deposit_check_callback(update: Update, context: Context):
    query = update.callback_query
    await query.answer()
    
    transaction_code = query.data.split('_')[2]
    
    from main import app
    with app.app_context():
        transaction = Transaction.query.filter_by(transaction_code=transaction_code).first()
        
        if not transaction:
            await query.edit_message_text("❌ Không tìm thấy giao dịch!")
            return
        
        if transaction.status == 'pending':
            await query.edit_message_text(
                f"""⏳ **ĐANG CHỜ XÁC NHẬN TỪ SEPAY**

Mã GD: {transaction_code}
Số tiền: {transaction.amount:,}đ

✅ SePay sẽ tự động cộng tiền khi nhận được giao dịch thật!""",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text("✅ Giao dịch đã được xử lý!")
