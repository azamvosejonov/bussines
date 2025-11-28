from flask import Blueprint, request, jsonify
from app import db
from app.models import User, Business
from flask_jwt_extended import jwt_required, get_jwt_identity
import telegram
import os

notifications_bp = Blueprint('notifications', __name__)

def check_business_access(biz_id):
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if user.role == 'admin':
        return True
    business = Business.query.get(biz_id)
    return business and business.owner_id == user.id

@notifications_bp.route('/notifications/telegram-config', methods=['POST'])
@jwt_required()
def config_telegram(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    bot_token = data['bot_token']
    chat_id = data['chat_id']
    # Store in business settings
    business = Business.query.get(biz_id)
    settings = business.settings or {}
    settings['telegram'] = {'bot_token': bot_token, 'chat_id': chat_id}
    business.settings = settings
    db.session.commit()
    return jsonify({'message': 'Telegram configured'}), 200

@notifications_bp.route('/notifications/send', methods=['POST'])
@jwt_required()
def send_notification(biz_id):
    if not check_business_access(biz_id):
        return jsonify({'message': 'Access denied'}), 403
    data = request.get_json()
    message = data['message']
    business = Business.query.get(biz_id)
    settings = business.settings or {}
    telegram_config = settings.get('telegram')
    if not telegram_config:
        return jsonify({'message': 'Telegram not configured'}), 400

    bot = telegram.Bot(token=telegram_config['bot_token'])
    try:
        bot.send_message(chat_id=telegram_config['chat_id'], text=message)
        return jsonify({'message': 'Notification sent'}), 200
    except Exception as e:
        return jsonify({'message': str(e)}), 500
