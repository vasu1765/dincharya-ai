# Gateway test scope

Future tests should mock Telegram and HTTP: private-chat authorization, invalid
webhook responses, timeouts, reply splitting, and failure logging. Do not use a
production bot token or start polling. Phase A leaves gateway behavior unchanged.
