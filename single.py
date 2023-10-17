from __future__ import annotations
from typing import *

import logging

logger = logging.getLogger(__name__)

import asyncio

from cogniq.config import APP_URL
from cogniq.slack import CogniqSlack
from cogniq.openai import CogniqOpenAI
from cogniq.personalities import TaskManager


class Single:
    def __init__(self):
        # Initialize the slack bot
        self.cslack = CogniqSlack()

        self.copenai = CogniqOpenAI()

        # Setup the personalities
        self.task_manager = TaskManager(cslack=self.cslack, copenai=self.copenai)
        # Finally, register the app_mention and message events
        self.register_app_mention()
        self.register_message()

    async def start(self) -> None:
        """
        Starts one Slack bot instance, and multiple personalities.
        """
        await self.task_manager.async_setup()
        await self.cslack.start()

    async def first_response(self, *, context: Dict[str, Any], original_ts: str) -> Dict[str, str]:
        """
        This method is called when the bot is called.
        """
        try:
            response = await context["say"](
                f"Let me figure that out...",
                thread_ts=original_ts,
            )
            return response
        except Exception as e:
            logger.error(e)
            raise e

    async def _dispatch(self, *, event: Dict[str, str], context: Dict[str, Any], original_ts: str) -> None:
        reply = await self.first_response(context=context, original_ts=original_ts)
        reply_ts = reply["ts"]
        thread_ts = original_ts

        # Text from the event
        text = event.get("text")

        # TODO: setup stream callback
        _dispatch_task = asyncio.create_task(
            self.task_manager.ask_task(
                event=event,
                reply_ts=reply_ts,
                context=context,
                thread_ts=thread_ts,
            )
        )

    async def dispatch(self, *, event: Dict[str, str], context: Dict[str, Any]) -> None:
        original_ts = event["ts"]
        bot_token = context.get("bot_token")
        app_url = APP_URL

        if bot_token is not None:
            try:
                await self._dispatch(event=event, context=context, original_ts=original_ts)
            except Exception as e:
                logger.error(e)
                raise e
        else:
            await context["say"](
                f"Sorry, I don't think I'm installed in this workspace. Please install me using <{app_url}/slack/install|this link>.",
                thread_ts=original_ts,
            )

    def register_app_mention(self) -> None:
        @self.cslack.app.event("app_mention")
        async def handle_app_mention(event: Dict[str, str], context: Dict[str, Any]) -> None:
            logger.info(f"app_mention: {event.get('text')}")
            await self.dispatch(event=event, context=context)

    def register_message(self) -> None:
        @self.cslack.app.event("message")
        async def handle_message_events(event: Dict[str, str], context: Dict[str, Any]) -> None:
            logger.info(f"message: {event.get('text')}")
            channel_type = event["channel_type"]
            if channel_type == "im":
                await self.dispatch(event=event, context=context)
