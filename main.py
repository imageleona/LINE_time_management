import os

from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException
from linebot.v3 import WebhookParser
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent

import handlers

load_dotenv()

CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]
CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]

app = FastAPI()
parser = WebhookParser(CHANNEL_SECRET)

_config = Configuration(access_token=CHANNEL_ACCESS_TOKEN)


@app.post("/callback")
async def callback(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        events = parser.parse(body.decode("utf-8"), signature)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid signature")

    with ApiClient(_config) as api_client:
        line_bot_api = MessagingApi(api_client)

        for event in events:
            if not isinstance(event, MessageEvent):
                continue
            if not isinstance(event.message, TextMessageContent):
                continue

            user_id = event.source.user_id
            text = event.message.text

            command, argument = handlers.parse_command(text)
            reply_text = handlers.dispatch(command, argument, user_id)

            line_bot_api.reply_message(
                ReplyMessageRequest(
                    reply_token=event.reply_token,
                    messages=[TextMessage(text=reply_text)],
                )
            )

    return {"status": "ok"}
