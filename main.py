"""
Chat Logger Plugin for LangBot

This plugin provides comprehensive chat logging functionality, recording group chat messages
and bot responses to a database with configurable filtering options.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from pkg.platform.types.events import GroupMessage
from pkg.plugin.context import BasePlugin, EventContext
from pkg.plugin.events import GroupMessageReceived, NormalMessageResponded
from pkg.plugin.loaders.manifest import PluginManifestLoader


def fl(msg: str) -> str:
    """Format log messages with plugin name"""
    return f"🧩 [ChatLogger] {msg}"

class Base(DeclarativeBase):
    """SQLAlchemy declarative base"""

    pass


class ChatRecord(Base):
    """Chat record model for database storage"""

    __tablename__ = 'group_msg'
    __table_args__ = {'schema': 'public'}

    id: Mapped[int] = mapped_column(sa.Integer, primary_key=True, autoincrement=True)
    datetime: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), default=datetime.now(tz=timezone.utc))
    user_id: Mapped[str] = mapped_column(sa.Text(), nullable=False)
    nickname: Mapped[Optional[str]] = mapped_column(sa.Text(), nullable=True)
    message: Mapped[str] = mapped_column(sa.Text(), nullable=True)
    group_id: Mapped[str] = mapped_column(sa.Text(), nullable=False)


class ChatLoggerPlugin(BasePlugin):
    """Chat Logger Plugin Implementation"""

    def __init__(self, host):
        super().__init__(host)

        self.engine: Optional[AsyncEngine] = None
        self.session_factory: Optional[async_sessionmaker] = None
        self.database_url: str = 'sqlite+aiosqlite:///./data/plugins/ChatLogger/chat_logs.db'
        self.bot_nickname: str = 'Self'
        self.include_bot_messages: bool = True
        self.group_whitelist: list[str] = []
        self.group_blacklist: list[str] = []

    async def initialize(self):
        """Initialize the plugin and database connection"""
        try:
            for loader in self.ap.plugin_mgr.loaders:
                if isinstance(loader, PluginManifestLoader):
                    loader.handler(GroupMessageReceived)(ChatLoggerPlugin.on_group_message_received)
                    loader.handler(NormalMessageResponded)(ChatLoggerPlugin.on_normal_message_responded)
                    break

            # Create necessary directories
            Path('./data/plugins/ChatLogger').mkdir(parents=True, exist_ok=True)

            # Load configuration
            config = self.config or {}
            self.database_url = config.get('database_url', self.database_url)
            self.bot_nickname = config.get('bot_nickname', self.bot_nickname)
            self.include_bot_messages = config.get('include_bot_messages', self.include_bot_messages)
            self.group_whitelist = config.get('group_whitelist', self.group_whitelist)
            self.group_blacklist = config.get('group_blacklist', self.group_blacklist)

            # Initialize database
            await self._init_database()

            self.ap.logger.info(fl('Chat Logger Plugin initialized with database'))
            self.ap.logger.info(fl(f'Group whitelist: {self.group_whitelist}'))
            self.ap.logger.info(fl(f'Group blacklist: {self.group_blacklist}'))
            self.ap.logger.info(fl(f'Include bot messages: {self.include_bot_messages}'))

        except Exception as e:
            self.ap.logger.error(fl(f'Failed to initialize Chat Logger Plugin: {e}'))
            raise

        self.ap.logger.info(fl("Initialized"))

    async def _init_database(self):
        """Initialize database connection and create tables"""
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.database_url,
                echo=False,  # Set to True for SQL debugging
                future=True,
            )

            # Create session factory
            self.session_factory = async_sessionmaker(bind=self.engine, expire_on_commit=False)

            # Create tables
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            self.ap.logger.info(fl('Database tables created successfully'))

        except Exception as e:
            self.ap.logger.error(fl(f'Database initialization failed: {e}'))
            raise

    def _should_log_group(self, group_id: str) -> bool:
        """Check if messages from this group should be logged"""
        group_id_str = str(group_id)

        # If whitelist is specified and group is not in it, don't log
        if self.group_whitelist and group_id_str not in self.group_whitelist:
            return False

        # If group is in blacklist, don't log
        if group_id_str in self.group_blacklist:
            return False

        return True

    async def _save_chat_record(
        self, user_id: str, nickname: Optional[str], message: str, group_id: str, is_bot_message: bool = False
    ):
        """Save a chat record to the database"""
        if not self.session_factory:
            self.ap.logger.warning(fl('Database not initialized, skipping record save'))
            return

        try:
            async with self.session_factory() as session:
                record = ChatRecord(
                    user_id=user_id,
                    nickname=nickname,
                    message=message,
                    datetime=datetime.now(tz=timezone.utc),
                    group_id=group_id
                )

                session.add(record)
                await session.commit()

                self.ap.logger.debug(fl(f'Saved chat record from user {user_id} in group {group_id}'))

        except Exception as e:
            self.ap.logger.error(fl(f'Failed to save chat record: {e}'))

    async def on_group_message_received(self, ctx: EventContext):
        """Handle group message received events"""
        try:
            event: GroupMessageReceived = ctx.event

            # Check if we should log this group
            if not self._should_log_group(event.launcher_id):
                return

            group_message = event.query.message_event
            if not isinstance(group_message, GroupMessage):
                return

            # Extract message text
            message_text = str(group_message.message_chain)

            # Skip empty messages
            if not message_text.strip():
                return

            # Get nickname if available
            nickname = group_message.sender.get_name()

            # Save the record
            await self._save_chat_record(
                user_id=str(group_message.sender.id),
                nickname=nickname,
                message=message_text,
                group_id=str(group_message.group.id),
                is_bot_message=False,
            )

        except Exception as e:
            self.ap.logger.error(fl(f'Error handling group message: {e}'))

    async def on_normal_message_responded(self, ctx: EventContext):
        """Handle bot response events"""
        try:
            # Skip if bot messages are not included
            if not self.include_bot_messages:
                return

            event: NormalMessageResponded = ctx.event

            # Only log group responses
            if event.launcher_type != 'group':
                return

            # Check if we should log this group
            if not self._should_log_group(event.launcher_id):
                return

            # Combine prefix and response text
            full_response = ''
            if event.prefix:
                full_response += event.prefix
            if event.response_text:
                full_response += event.response_text

            # Skip empty responses
            if not full_response.strip():
                return

            # Get bot user ID from adapter
            bot_user_id = ctx.event.query.adapter.bot_account_id

            # Save the bot response record
            await self._save_chat_record(
                user_id=str(bot_user_id),
                nickname=self.bot_nickname,
                message=full_response,
                group_id=str(event.launcher_id),
                is_bot_message=True,
            )

        except Exception as e:
            self.ap.logger.error(fl(f'Error handling bot response: {e}'))

    async def destroy(self):
        """Clean up resources when plugin is destroyed"""
        try:
            if self.engine:
                await self.engine.dispose()
                self.ap.logger.info(fl('Database connection closed'))
        except Exception as e:
            self.ap.logger.error(fl(f'Error during plugin cleanup: {e}'))
