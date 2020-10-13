import json
import sys
import traceback
from collections import deque

import config
import discord
from discord.ext import commands

description = """
もくもくオンライン勉強会用汎用Bot
"""

initial_extensions = (
    'cogs.message_reaction_count',
)


def _prefix_callable(bot, msg):
    """
    prefix
    :param bot:
    :param msg:
    :return:
    """
    user_id = bot.user.id

    base = [f'<@!{user_id}> ', f'<@{user_id}> ']
    if msg.guild is None:
        base.append('!')
        base.append('?')
    else:
        base.append('¥')
    return base


class DiscordStudyBot(commands.AutoShardedBot):
    def __init__(self):
        # Bot基本情報セット？
        allowed_mentions = discord.AllowedMentions(roles=False, everyone=False, users=True)
        super().__init__(command_prefix=_prefix_callable, description=description,
                         pm_help=None, help_attrs=dict(hidden=True),
                         fetch_offline_members=False, heartbeat_timeout=150.0,
                         allowed_mentions=allowed_mentions)

        #
        self.client_id = config.client_id

        self._prev_events = deque(maxlen=10)
        # cog load
        for extension in initial_extensions:
            try:
                self.load_extension(extension)
            except Exception as e:
                print(f'Failed to load extension {extension}.', file=sys.stderr)
                traceback.print_exc()

    def run(self):
        """

        :return:
        """
        try:
            super().run(config.token, reconnect=True)
        finally:
            with open('prev_events.log', 'w', encoding='utf-8') as fp:
                for data in self._prev_events:
                    try:
                        x = json.dumps(data, ensure_ascii=True, indent=4)
                    except Exception as e:
                        fp.write(f'{data}\n')
                    else:
                        fp.write(f'{x}\n')

    @property
    def config(self):
        return __import__('config')
