import logging

logger = logging.getLogger(__name__)
import os
import time
from datetime import datetime
from logging import Logger
from typing import Optional
from uuid import uuid4

import sqlalchemy
from databases import Database
from slack_sdk.oauth.installation_store import Bot, Installation
from slack_sdk.oauth.installation_store.async_installation_store import (
    AsyncInstallationStore,
)
from slack_sdk.oauth.installation_store.sqlalchemy import SQLAlchemyInstallationStore
from sqlalchemy import and_, desc, Table, MetaData


from .exceptions.user_token_not_found import UserTokenNotFound


class InstallationStore(AsyncInstallationStore):
    database_url: str
    client_id: str
    metadata: MetaData
    installations: Table
    bots: Table

    def __init__(
        self,
        client_id: str,
        database_url: str,
        logger: Logger = logging.getLogger(__name__),
    ):
        self.client_id = client_id
        self.database_url = database_url
        self._logger = logger
        self.metadata = MetaData()
        self.installations = SQLAlchemyInstallationStore.build_installations_table(
            metadata=self.metadata,
            table_name=SQLAlchemyInstallationStore.default_installations_table_name,
        )
        self.bots = SQLAlchemyInstallationStore.build_bots_table(
            metadata=self.metadata,
            table_name=SQLAlchemyInstallationStore.default_bots_table_name,
        )

    @property
    def logger(self) -> Logger:
        return self._logger

    async def async_save(self, installation: Installation):
        async with Database(self.database_url) as database:
            async with database.transaction():
                i = installation.to_dict()
                i["client_id"] = self.client_id
                await database.execute(self.installations.insert(), i)
                b = installation.to_bot().to_dict()
                b["client_id"] = self.client_id
                await database.execute(self.bots.insert(), b)

    async def async_find_bot(
        self,
        *,
        enterprise_id: Optional[str],
        team_id: Optional[str],
        is_enterprise_install: Optional[bool],
    ) -> Optional[Bot]:
        c = self.bots.c
        query = (
            self.bots.select()
            .where(
                and_(
                    c.enterprise_id == enterprise_id,
                    c.team_id == team_id,
                    c.is_enterprise_install == is_enterprise_install,
                )
            )
            .order_by(desc(c.installed_at))
            .limit(1)
        )
        async with Database(self.database_url) as database:
            result = await database.fetch_one(query)
            # logger.info("found bot: %s" % result)
            if result:
                return Bot(
                    app_id=result["app_id"],
                    enterprise_id=result["enterprise_id"],
                    team_id=result["team_id"],
                    bot_token=result["bot_token"],
                    bot_id=result["bot_id"],
                    bot_user_id=result["bot_user_id"],
                    bot_scopes=result["bot_scopes"],
                    installed_at=result["installed_at"],
                )
            else:
                return None

    async def async_find_user_token(self, *, context: Optional[dict]) -> Optional[str]:
        """
        Find the user token of a specific user or of the user who installed the app.
        If the user token doesn't exist, prompt the user to install the app.
        """
        try:
            enterprise_id = context["authorize_result"]["enterprise_id"]
            team_id = context["team_id"]
            is_enterprise_install = context["is_enterprise_install"]
            user_id = context["user_id"]
        except KeyError:
            logger.error("Unable to find enterprise_id, team_id, or is_enterprise_install in context")
            return None

        c = self.installations.c
        conditions = [
            c.enterprise_id == enterprise_id,
            c.team_id == team_id,
            c.is_enterprise_install == is_enterprise_install,
            c.user_id == user_id,
        ]

        query = self.installations.select().where(and_(*conditions)).order_by(desc(c.installed_at)).limit(1)

        async with Database(self.database_url) as database:
            result = await database.fetch_one(query)
            if result:
                return result["user_token"]
            else:
                raise UserTokenNotFound(user_id=user_id)
