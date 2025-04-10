import os
from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent
)
import httpx
import asyncio

# ==== 讀取環境變數 ====
YOUR_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
YOUR_CHANNEL_SECRET = os.environ.get("LINE_CHANNEL_SECRET")
YOUR_GROK_TOKEN = os.environ.get("GROK_API_KEY")

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
GROK_MODEL_NAME = "grok-3-latest"

# ==== 設定 LINE Bot 連線 ====
configuration = Configuration(access_token=YOUR_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(YOUR_CHANNEL_SECRET)

# ==== 建立 Flask App ====
app = Flask(__name__)

# ==== 呼叫 Grok API 產生回覆 ====
async def query_grok(prompt):
    headers = {
        "Authorization": f"Bearer {YOUR_GROK_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROK_MODEL_NAME,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(GROK_API_URL, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            reply_content = result['choices'][0]['message']['content']
            return reply_content
    except Exception as e:
        print(f"Grok連線失敗，錯誤：{e}")
        return "Grok 暫時離開地球了，請稍後再試～ 🚀"

# ==== 接收 LINE Webhook ====
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)
    print("Received Request body:", body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'

# ==== 收到訊息時的處理 ====
@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        print("Received message:", event.message.text)
        
        response_text = asyncio.run(query_grok(event.message.text))
        
        print("Grok response:", response_text)
        
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=response_text)]
            )
        )

# ==== 啟動 Server ====
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=True)
