import json
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

app = Flask(__name__)

# 你的 Line Bot 設定
line_bot_api = LineBotApi("QWP/44tPHE6I9WImke71sjq0b2EXvqqiYrgBfg0GE1t8grLcvMBDn87oPhNI7nn+V/o+CeVKbt90E1Sq8o6r+UwcoMEeiAC6nxRHHnyVJob4P3Vd0ZWB7N+rPjLMtB1ta+hkDutf/EsC+frEp+EXEgdB04t89/1O/w1cDnyilFU=") # YOUR_CHANNEL_ACCESS_TOKEN
handler = WebhookHandler("dd28e8b684c1e2e8b9fd0a370cb89945") # YOUR_CHANNEL_SECRET

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
    app.run(port=5000, debug=True)
