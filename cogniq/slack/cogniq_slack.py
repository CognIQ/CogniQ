import logging
from slack_bolt.async_app import AsyncApp
from aiohttp import web

from .history.openai_history import OpenAIHistory
from .history.anthropic_history import AnthropicHistory


class CogniqSlack:
    def __init__(
        self, *, config: dict, logger: logging.Logger
    ):
        """
        Slack bot with given configuration, app, and logger.

        Parameters:
        config (dict): Configuration for the Slack app with the following keys:
            SLACK_BOT_TOKEN (str): Slack bot token.
            SLACK_SIGNING_SECRET (str): Slack signing secret.
            HOST (str, default='0.0.0.0'): Host on which the app will be started.
            PORT (str or int, default=3000): Port on which the app will be started.
            APP_ENV (str, either 'production' or 'development'): Environment in which the app is running.
            SLACK_APP_TOKEN (str, optional): Slack app token. Required if APP_ENV is 'development'.
            HISTORY_CLASS (class, optional): Class to use for storing and retrieving history formatted for LLM consumption. Defaults to OpenAIHistory.

        logger (logging.Logger): Logger to log information about the app's status.
        """
        self.logger = logger
        self.config = config

        self.app = AsyncApp(
            token=self.config["SLACK_BOT_TOKEN"],
            signing_secret=self.config["SLACK_SIGNING_SECRET"],
            logger=self.logger,
        )

        self.anthropic_history = AnthropicHistory(app=self.app, logger=self.logger)
        self.openai_history = OpenAIHistory(app=self.app, logger=self.logger)

        # Set defaults
        self.config.setdefault("HOST", "0.0.0.0")
        self.config.setdefault("PORT", 3000)
        self.config.setdefault("APP_ENV", "production")
        self.config.setdefault("HISTORY_CLASS", OpenAIHistory)

        if self.config["APP_ENV"] == "development" and not self.config.get(
            "SLACK_APP_TOKEN"
        ):
            raise ValueError("SLACK_APP_TOKEN is required in development mode")

        self.history = self.config["HISTORY_CLASS"](app=self.app, logger=self.logger)

    async def start(self):
        """
        This method starts the app.

        It performs the following steps:
        1. Initializes an instance of `AsyncApp` with the Slack bot token, signing secret, and logger.
        2. Creates a `History` object for tracking app events and logging history.
        3. Sets up event registrations for the Slack app by calling the registered functions with the `app` instance.
        4. Logs a message indicating that the Slack app is starting.
        5. If the app environment is set to 'production', the app starts listening on the specified port.
           It awaits the `app.start()` method to start the app server.
        6. If the app environment is set to 'development', it starts the app using the Socket Mode Handler.
           It creates an instance of `AsyncSocketModeHandler` with the `app` instance and the Slack app token.
           It awaits the `handler.start_async()` method to start the app in development mode.

        Note:
        - If the app environment is 'development', make sure to provide the `SLACK_APP_TOKEN` in the configuration.
        - The app will keep running until it is manually stopped or encounters an error.
        """
        self.logger.info("Starting Slack app!!")
        if self.config["APP_ENV"] == "production":
            # Run the web_app directly from aiohttp for greater control over the event loop
            await web._run_app(
                self.app.web_app(), host=self.config["HOST"], port=self.config["PORT"]
            )

        if self.config["APP_ENV"] == "development":
            from slack_bolt.adapter.socket_mode.aiohttp import (
                AsyncSocketModeHandler,
            )

            handler = AsyncSocketModeHandler(self.app, self.config["SLACK_APP_TOKEN"])
            await handler.start_async()