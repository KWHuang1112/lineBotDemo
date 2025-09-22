import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
app = Flask(__name__)

# 從環境變數讀取
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

if LINE_CHANNEL_ACCESS_TOKEN is None or LINE_CHANNEL_SECRET is None:
    print("❌ 請確認 Render 上有設定環境變數")
    exit(1)

# 初始化 LineBotApi 和 WebhookHandler
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# 載入 FAQ JSON
with open("faq.json", "r", encoding="utf-8") as f:
    FAQ = json.load(f)

def search_faq(user_msg: str) -> str:
    """
    簡單的關鍵字搜尋：
    遍歷 FAQ JSON，若 key 出現在用戶訊息中，就回覆對應答案
    """
    for category, items in FAQ.items():
        for key, answer in items.items():
            if key in user_msg:
                return answer
    return "抱歉，機器人無法回答這個問題。"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)

    app.logger.info("Request body: " + body)
    app.logger.info("Signature: " + signature)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("Invalid signature. Check your Channel Secret/Access Token.")
        abort(400)

    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    reply = search_faq(user_msg)
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

if __name__ == "__main__":
#    app.run(port=5000, debug=True)
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")))







