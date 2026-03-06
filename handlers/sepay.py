from flask import request, jsonify
import logging
from database.models import User, Transaction, db
from datetime import datetime
import os
import re

logger = logging.getLogger(__name__)

MB_ACCOUNT = os.getenv('MB_ACCOUNT', '666666291005')

def setup_sepay_webhook(app):
    @app.route('/webhook/sepay', methods=['POST'])
    def sepay_webhook():
        try:
            data = request.json
            logger.info(f"Nhận webhook từ SePay: {data}")
            
            if data.get('transferType') == 'in':
                account_number = data.get('accountNumber')
                amount = int(float(data.get('transferAmount', 0)))
                content = data.get('content', '')
                
                if account_number != MB_ACCOUNT:
                    return jsonify({"status": "ok"}), 200
                
                match = re.search(r'NAP\s*([A-Z0-9]{8})', content.upper())
                
                if match:
                    transaction_code = match.group(1)
                    
                    from main import app
                    with app.app_context():
                        transaction = Transaction.query.filter_by(
                            transaction_code=transaction_code,
                            status='pending'
                        ).first()
                        
                        if transaction and abs(transaction.amount - amount) <= 1000:
                            transaction.status = 'success'
                            transaction.updated_at = datetime.now()
                            
                            user = User.query.get(transaction.user_id)
                            if user:
                                user.balance += transaction.amount
                                db.session.commit()
                                logger.info(f"ĐÃ CỘNG {amount}đ CHO USER {user.user_id}")
            
            return jsonify({"status": "success"}), 200
            
        except Exception as e:
            logger.error(f"Lỗi xử lý webhook: {e}")
            return jsonify({"status": "error"}), 500
