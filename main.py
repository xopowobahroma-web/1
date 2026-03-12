import logging
import sys
from flask import Flask, request

logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def webhook():
    logger.debug("🔥🔥🔥 ВЕБХУК ВЫЗВАН! 🔥🔥🔥")
    logger.debug(f"Path: {request.path}")
    logger.debug(f"Method: {request.method}")
    logger.debug(f"Data: {request.get_data(as_text=True)}")
    return 'ok', 200

@app.route('/')
def index():
    logger.debug("👋 Корневой путь '/'")
    return "Bot is running!"
