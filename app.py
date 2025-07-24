import os
import aiohttp
import jwt
from aiohttp import web
from dotenv import load_dotenv
from botbuilder.schema import Activity
from botbuilder.core import (
    BotFrameworkAdapter,
    BotFrameworkAdapterSettings,
    TurnContext,
    ActivityHandler
)

# Load environment variables
load_dotenv()

APP_ID = os.getenv("ID", "YOUR_APP_ID")
APP_SECRET = os.getenv("PASS", "YOUR_APP_SECRET")
APP_TENANT_ID = os.getenv("TENANT", "YOUR_TENANT_ID")

# Adapter settings
adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_SECRET)
adapter = BotFrameworkAdapter(adapter_settings)


# Bot logic
class MyBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        text = turn_context.activity.text.strip().lower()
        if text == "hello":
            await turn_context.send_activity("Hi! How can I help you today?")
        else:
            await turn_context.send_activity(f"You said: {text}")


bot = MyBot()


# Routes
async def on_message(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise web.HTTPUnauthorized(reason="Authorization header missing or incorrect")

    token = auth_header.split(" ")[1]
    try:
        jwt.decode(token, options={"verify_signature": False})
    except jwt.InvalidTokenError:
        raise web.HTTPUnauthorized(reason="Invalid JWT token")

    body = await request.json()
    activity = Activity().deserialize(body)
    response = await adapter.process_activity(activity, token, bot.on_turn)
    return web.Response(status=response.status)


async def get_token(request):
    url = f"https://login.microsoftonline.com/{APP_TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": APP_ID,
        "client_secret": APP_SECRET,
        "scope": "https://graph.microsoft.com/.default"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=data) as res:
            token_data = await res.json()
            return web.json_response(token_data)


async def hello_test(request):
    name = request.match_info.get("name", "unknown")
    body = await request.text()
    if "hello" in body.lower() or "hi" in body.lower():
        return web.Response(text=f"Hi {name}")
    return web.Response(text=f"Connected, {name}", status=200)


# Web server setup
app = web.Application()
app.add_routes([
    web.post("/api/messages", on_message),
    web.get("/api/get_token", get_token),
    web.get("/api/prompt/{name}", hello_test),
])

# Required for Azure: listen on 0.0.0.0:8000
if __name__ == "__main__":
    web.run_app(app, host="0.0.0.0", port=8000)
