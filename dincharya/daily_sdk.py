"""Pinned Telegram SDK against an in-process Bot API recorder. No network transport."""
import asyncio
from importlib.metadata import version
import json

from telegram import Bot
from telegram.request import BaseRequest

from dincharya.personal_recorded import Recorder


class RecordedRequest(BaseRequest):
    def __init__(self, recorder):
        self.recorder = recorder
        self.incoming = []

    @property
    def read_timeout(self):
        return 2.0

    async def initialize(self):
        pass

    async def shutdown(self):
        pass

    async def do_request(self, url, method, request_data=None, **timeouts):
        operation = url.rsplit("/", 1)[-1]
        params = request_data.parameters if request_data else {}
        if operation == "getMe":
            result = {"id": self.recorder.bot, "is_bot": True, "first_name": "Fixture"}
        elif operation == "getUpdates":
            if params.get("limit") != 1 or params.get("timeout") != 0:
                raise ValueError("Unexpected polling scope")
            result, self.incoming = self.incoming, []
        else:
            response = self.recorder(operation, params)
            result = response["result"]
            if isinstance(result, dict):
                result = {**result, "date": 1, "from": {**result["from"], "first_name": "Fixture"}}
                if not result.get("reply_markup"):
                    result.pop("reply_markup", None)
        return 200, json.dumps({"ok": True, "result": result}).encode()


class RecordedSDK(Recorder):
    def __init__(self, owner, bot, allocate, reserve, stopped):
        if version("python-telegram-bot") != "21.11.1":
            raise RuntimeError("Unexpected Telegram SDK")
        super().__init__(owner, bot, allocate)
        self.reserve, self.stopped = reserve, stopped
        self.loop = asyncio.Runner()
        # Both request slots are replaced before the SDK initializes.
        self.backend = Recorder(owner, bot, allocate)
        self.wire = RecordedRequest(self.backend)
        self.client = Bot(token=f"{bot}:synthetic", base_url="https://fixture.invalid/bot",
                          base_file_url="https://fixture.invalid/file/bot", request=self.wire, get_updates_request=self.wire)
        self.loop.run(self.client.initialize())
        if self.client.id != bot:
            raise RuntimeError("Recording identity mismatch")

    def poll_one(self, raw):
        if self.stopped():
            raise RuntimeError("Recording stopped")
        self.wire.incoming = [raw]
        batch = self.loop.run(self.client.get_updates(limit=1, timeout=0))
        if len(batch) != 1:
            raise RuntimeError("Unexpected recorded batch")
        return batch[0].to_dict()

    def __call__(self, method, body):
        permitted = {"sendMessage": self.client.send_message, "editMessageText": self.client.edit_message_text,
                     "answerCallbackQuery": self.client.answer_callback_query}
        if method not in permitted or self.stopped() or self.reserve() is not True:
            raise RuntimeError("Recording fenced")
        result = self.loop.run(permitted[method](**body))
        payload = result if isinstance(result, bool) else result.to_dict()
        if method == "sendMessage" and body.get("reply_markup") and payload.get("reply_markup") != body["reply_markup"]:
            raise RuntimeError("Preview buttons differ from the proposal")
        return {"ok": True, "result": payload}

    def close(self):
        try:
            self.loop.run(self.client.shutdown())
        finally:
            self.loop.close()
