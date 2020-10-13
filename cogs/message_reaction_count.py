from datetime import datetime

from discord.ext import commands
import discord
import config
import sqlalchemy
from discord.ext import commands
from sqlalchemy import DATETIME, Column, Integer, MetaData, Table, exc
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
from sqlalchemy_views import CreateView

TOKEN = config.token
Base = declarative_base()

engine = sqlalchemy.create_engine('sqlite:///emoji_count.sqlite3', echo=True)


class MessageReaction(Base):
    """
    message_reaction テーブル定義
    TODO: テーブル定義は別ファイルに分離したい。
    """
    id = Column(Integer, primary_key=True)
    message_id = Column(Integer, nullable=False)
    emoji_id = Column(Integer, nullable=False)
    user_id = Column(Integer, nullable=False)
    created_at = Column(DATETIME, nullable=False)
    __tablename__ = 'message_reaction'


Base.metadata.create_all(bind=engine, checkfirst=True)


class MessageReactionCount(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # View追加 TODO: テーブル、View作成は別ファイルに分離したい。
        if not engine.dialect.has_table(engine, 'reaction_count'):
            view = Table('reaction_count', MetaData())
            definition = text("SELECT emoji_id, count(emoji_id) as count FROM message_reaction GROUP BY emoji_id")
            create_view = CreateView(view, definition)
            print(str(create_view.compile()).strip())
            engine.execute(create_view)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """
        リアクション追加
        :param payload:
        :return:
        """
        # 2020/10/05 今回unicodeの絵文字はカウントしない。
        if payload.emoji.is_unicode_emoji():
            return

        # ギルド外の絵文字はカウントしない
        if self.bot.get_emoji(payload.emoji.id) is None:
            return

        self.__save_message_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """
        リアクション削除
        :param payload:
        :return:
        """
        # 2020/10/05 今回unicodeの絵文字は登録しないめ、不要
        if payload.emoji.is_unicode_emoji():
            return

        # ギルド外の絵文字は登録しないので終了
        if self.bot.get_emoji(payload.emoji.id) is None:
            return

        self.__delete_message_reaction(payload)

    @commands.command(pass_context=True)
    async def emoji_ranking(self, ctx):
        reaction_count = self.__get_reaction_count()
        embed = self.__create_emoji_ranking_embed(reaction_count)
        await ctx.send(embed=embed)

    def __create_emoji_ranking_embed(self, reaction_count):
        """
        絵文字ランキングEmbed作成
        :return:
        """
        embed = discord.Embed(title="絵文字ランキング")
        embed.add_field(name="トータル", value=self.__create_ranking_embed_field_value(reaction_count))
        return embed

    def __create_ranking_embed_field_value(self, reaction_count):
        reaction = ""

        rank = 1
        for row in reaction_count:
            if rank == 1:
                reaction += ":first_place:  "
            elif rank == 2:
                reaction += ":second_place:  "
            elif rank == 3:
                reaction += ":third_place:  "
            else:
                reaction += str(rank).zfill(2) + '. '

            print(self.bot.get_emoji(id=row.emoji_id))

            reaction += str(self.bot.get_emoji(id=row.emoji_id)) + "--" + str(row.count) + "回\n"
            rank = rank + 1

        if reaction == "":
            reaction = "絵文字は現在使用されていません。"

        return reaction

    def __save_message_reaction(self, payload):
        """
        message_reaction 登録
        :param payload:
        :return:
        """
        session = sessionmaker(bind=engine)()
        try:
            message_reaction = MessageReaction()
            message_reaction.message_id = payload.message_id
            message_reaction.user_id = payload.user_id
            message_reaction.emoji_id = payload.emoji.id
            message_reaction.created_at = datetime.now()
            session.add(instance=message_reaction)
            session.commit()
        except exc.SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def __delete_message_reaction(self, payload):
        """
        message_reaction 物理削除
        :param payload:
        :return:
        """
        session = sessionmaker(bind=engine)()
        try:
            session.query(MessageReaction) \
                .filter(
                MessageReaction.message_id == payload.message_id,
                MessageReaction.user_id == payload.user_id,
                MessageReaction.emoji_id == payload.emoji.id
            ).delete()
            session.commit()
        except exc.SQLAlchemyError as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def __get_reaction_count(self):
        """
        reaction_countから使用回数を取得する。
        :return:
        """
        session = sessionmaker(bind=engine)()
        return session.execute("select emoji_id, count from reaction_count order by count desc")

    @property
    def config(self):
        return __import__('config')


def setup(bot):
    bot.add_cog(MessageReactionCount(bot))
