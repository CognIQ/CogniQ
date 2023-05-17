import cogniq
import asyncio
import os
from cogniq.logging import setup_logger

logger = setup_logger(__name__)

bing_search_config = {
    "SLACK_BOT_TOKEN": os.environ.get("SEARCH_SLACK_BOT_TOKEN"),
    "SLACK_SIGNING_SECRET": os.environ.get("SEARCH_SLACK_SIGNING_SECRET"),
    "SLACK_APP_TOKEN": os.environ.get("SEARCH_SLACK_APP_TOKEN"),
    "HOST": os.environ.get("SEARCH_HOST") or "0.0.0.0",
    "PORT": os.environ.get("SEARCH_PORT") or "3000",
    "APP_ENV": os.environ.get("APP_ENV") or "production",

}

chat_gpt4_config = {
    "SLACK_BOT_TOKEN": os.environ.get("CHAT_SLACK_BOT_TOKEN"),
    "SLACK_SIGNING_SECRET": os.environ.get("CHAT_SLACK_SIGNING_SECRET"),
    "SLACK_APP_TOKEN": os.environ.get("CHAT_SLACK_APP_TOKEN"),
    "HOST": os.environ.get("CHAT_HOST") or "0.0.0.0",
    "PORT": os.environ.get("CHAT_PORT") or "3001",
    "APP_ENV": os.environ.get("APP_ENV") or "production",
}

async def async_main():
    bing_search = cogniq.bing_search.start(config=bing_search_config)
    chat_gpt4 = cogniq.chat_gpt4.start(config=chat_gpt4_config)
    await asyncio.gather(bing_search, chat_gpt4)


if __name__ == "__main__":
    asyncio.run(async_main())
