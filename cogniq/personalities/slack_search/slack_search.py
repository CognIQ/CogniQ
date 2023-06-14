from cogniq.personalities import BasePersonality
from cogniq.slack import CogniqSlack
from cogniq.openai import CogniqOpenAI

from .ask import Ask


class SlackSearch(BasePersonality):
    def __init__(
        self, *, config: dict, cslack: CogniqSlack, copenai: CogniqOpenAI, **kwargs
    ):
        """
        SlackSearch personality
        Please call async_setup after initializing the personality.

        ```
        slack_search = SlackSearch(config=config, copenai=copenai)
        await slack_search.async_setup()
        ```

        Parameters:
        config (dict): Configuration for the Chat GPT4 personality with the following keys:
            OPENAI_MAX_TOKENS_RESPONSE (int): Maximum number of tokens to generate for the response.
            OPENAI_API_KEY (str): OpenAI API key.


        cslack (CogniqSlack): CogniqSlack instance.
        copenai (CogniqOpenAI): CogniqOpenAI instance.
        """
        self.config = config
        self.cslack = cslack
        self.copenai = copenai

        self.ask = Ask(config=config, cslack=cslack, copenai=copenai)

    async def async_setup(self):
        """
        Please call after initializing the personality.
        """
        await self.ask.async_setup()

    async def ask_task(self, *, event, reply_ts):
        """
        Executes the ask_task against all the personalities and returns the best or compiled response.
        """
        channel = event["channel"]
        message = event["text"]

        message_history = await self.cslack.openai_history.get_history(event=event)
        openai_response = await self.ask.ask(
            q=message,
            message_history=message_history,
        )
        # logger.debug(openai_response)
        await self.cslack.app.client.chat_update(
            channel=channel, ts=reply_ts, text=openai_response
        )

    async def ask_directly(self, *, q, message_history, context: dict, **kwargs):
        """
        Ask directly to the personality.
        """
        response = await self.ask.ask(
            q=q, message_history=message_history, context=context, **kwargs
        )
        return response

    @property
    def description(self):
        return "I search Slack for relevant conversations and respond to the query."
    
    @property
    def name(self):
        return "Slack Search"   
