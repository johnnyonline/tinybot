import os

from telegram import Bot


def _require_env(name: str) -> str:
    val = os.getenv(name, "")
    if not val:
        raise RuntimeError(f"!{name}")
    return val


BOT_ACCESS_TOKEN = _require_env("BOT_ACCESS_TOKEN")
GROUP_CHAT_ID = int(_require_env("GROUP_CHAT_ID"))
DEV_GROUP_CHAT_ID = int(_require_env("DEV_GROUP_CHAT_ID"))


async def notify_group_chat(
    text: str,
    parse_mode: str = "HTML",
    chat_id: int = GROUP_CHAT_ID,
    disable_web_page_preview: bool = True,
) -> None:
    try:
        bot = Bot(token=BOT_ACCESS_TOKEN)
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
        )
    except Exception as e:
        print(f"Failed to send message to group chat: {e}")
