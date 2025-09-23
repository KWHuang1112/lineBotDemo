import json
import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage,
    QuickReply, QuickReplyButton, MessageAction
)

# 嘗試載入 RapidFuzz（推薦），沒有則用 difflib 備援
try:
    from rapidfuzz import process, fuzz
    HAS_RAPIDFUZZ = True
except Exception:
    from difflib import get_close_matches
    HAS_RAPIDFUZZ = False

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

# 載入 FAQ
with open("faq.json", "r", encoding="utf-8") as f:
    FAQ = json.load(f)

# 展平成候選池
flat = []
for category, items in FAQ.items():
    for key, value in items.items():
        if isinstance(value, str):
            answer = value
            aliases = []
        elif isinstance(value, dict):
            answer = value.get("answer", "")
            aliases = value.get("aliases", []) or []
        else:
            continue
        for k in [key] + aliases:
            flat.append({
                "key": k,
                "canonical": key,
                "answer": answer,
                "category": category
            })

CHOICES = [entry["key"] for entry in flat]

def search_faq_fuzzy(user_msg: str, high_threshold=75, suggest_threshold=40, top_k=3):
    """
    回傳 (模式, 資料)
    - ("answer", "文字") → 直接回覆
    - ("suggest", [ (canonical, answer) ... ]) → 顯示 Quick Reply
    - ("fallback", "文字") → 回覆 fallback
    """
    msg = (user_msg or "").strip()
    if not msg:
        return "fallback", "請問有什麼我可以幫忙的嗎？"

    if HAS_RAPIDFUZZ:
        best = process.extractOne(msg, CHOICES, scorer=fuzz.token_sort_ratio)
        if best:
            matched_key, score, idx = best
            if score >= high_threshold:
                return "answer", flat[idx]["answer"]
            elif score >= suggest_threshold:
                top = process.extract(msg, CHOICES, scorer=fuzz.token_sort_ratio, limit=top_k)
                seen = set()
                suggestions = []
                for k, s, index in top:
                    can = flat[index]["canonical"]
                    if can in seen:
                        continue
                    seen.add(can)
                    suggestions.append((can, flat[index]["answer"]))
                return "suggest", suggestions
        return "fallback", "抱歉，我不太確定這個問題。請直接聯絡房東或提供更多細節。"
    else:
        from difflib import get_close_matches
        matches = get_close_matches(msg, CHOICES, n=1, cutoff=0.6)
        if matches:
            idx = CHOICES.index(matches[0])
            return "answer", flat[idx]["answer"]
        return "fallback", "抱歉，我不太確定這個問題。請直接聯絡房東或提供更多細節。"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text
    mode, data = search_faq_fuzzy(user_msg)

    if mode == "answer":
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=data))

    elif mode == "suggest":
        # Quick Reply：點下去就是答案
        quick_items = [
            QuickReplyButton(action=MessageAction(label=can, text=ans))
            for can, ans in data
        ]
        msg = TextSendMessage(
            text="你是不是想問以下問題？",
            quick_reply=QuickReply(items=quick_items)
        )
        line_bot_api.reply_message(event.reply_token, msg)

    else:  # fallback
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=data))

if __name__ == "__main__":
    app.run(port=5000, debug=True)


