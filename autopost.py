import sqlite3
import asyncio
from pyrogram import Client, filters, idle, enums
from configparser import ConfigParser
import getopt
import sys




class DB():
    def __init__(self):
        db_path = config.get('MISC', 'DB_PATH')
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        self.cur.execute("create table if not exists autopost (source BIGINT, dest BIGINT, name TEXT)")

    def execute(self, *data):
        return self.cur.execute(*data)

    def commit(self):
        self.con.commit()

    def add(self, keys):
        sql = "INSERT INTO autopost("
        sql += ", ".join("`%s`" % k for k in PROPS)
        sql += ") VALUES ("
        sql += ", ".join("?" * len(PROPS))
        sql += ")"
        param = list(keys)
        self.execute(sql, param)
        self.commit()

    def delete(self, id, name, typ):
        sql = "DELETE FROM autopost WHERE "
        sql += typ
        sql += " = ? "
        sql += "AND NAME = ?"
        param = id
        param2 = name
        self.execute(sql, (param, param2,))
        self.commit()

    def get_sources_dests_names(self, typ):
        sql = "SELECT "
        sql += typ
        sql +=" FROM autopost WHERE "
        sql += typ
        sql +=" IS NOT NULL AND name NOT NULL"
        result = [job[0] for job in self.execute(sql)]
        if typ == "name":
            result = list(dict.fromkeys(result))
        return result

    def get_sources_dests_by_name(self, typ, name):
        sql = "SELECT "
        sql += typ
        sql += ' FROM autopost WHERE '
        sql += typ
        sql += ' IS NOT NULL AND name = ?'
        return [job[0] for job in self.execute(sql, (name,))]


    def get_dests_by_source(self, source):
        source_names = [job[0] for job in self.execute('select name from autopost where source=? and name is not null', (source,))]
        for source_name in source_names:
            dests = [job[0] for job in self.execute('select dest from autopost where dest is not null and name=?', (source_name,))]
            return dests

    def check_if_exist(self, id, name, typ):
            sql = "SELECT "
            sql += typ
            sql +=" FROM autopost WHERE "
            sql += typ
            sql +=" IS NOT NULL AND name = ?"
            if id in [job[0] for job in self.execute(sql, (name,))]:
                 return True
            return False

def telegram():
    client = Client("client",
    api_id=config.get('TELEGRAM', 'API_ID'),
    api_hash=config.get('TELEGRAM', 'API_HASH'),
    session_string=config.get('TELEGRAM', 'SESSION'))

    db = DB()
    lock = asyncio.Lock()
    processed_media_groups_ids = []

    client.start()
    my_id = client.get_me().id
    my_name = client.get_me().first_name
    log_channel = config.get('MISC', 'LOG_CHANNEL')

    ### special channel where only spicific messages get autoposted that match with defined captions ###
    if config.has_option("MISC", "SPECIAL_CHANNEL"):
        special_channel = config.get('MISC', 'SPECIAL_CHANNEL')
        captions_match = (config.get('MISC', 'CAPTIONS_MATCH')).split('\n')
    special_channel = None
    captions_match = None

    ### logs will be send to saved messages if not another chat id is defined in config ###
    if log_channel == "saved messages":
        log_channel = my_id
    client.send_message(log_channel, text=f"AUTOPOST started for {my_name} [`{my_id}`]")


    ### some utility functions ###

    async def get_name(id):
        try:
            chat = await client.get_chat(id)
            if chat.title is not None: name = chat.title
            else: name = chat.first_name
            if chat.username is not None: username = "@" + chat.username
            else: username = ""
        except:
            name = ""
            username = ""
        return [name, username]

    async def get_all_dialogs(msg, channel=False, group=False, private=False):
        if channel: chat_type = [enums.ChatType.CHANNEL]
        if group: chat_type = [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]
        if private: chat_type = [enums.ChatType.BOT, enums.ChatType.PRIVATE]
        async for dialog in client.get_dialogs():
            if dialog.chat.type in chat_type:
                id = dialog.chat.id
                name = dialog.chat.title
                if name is None: name = dialog.chat.first_name
                username = ""
                if dialog.chat.username is not None: username = "@" + dialog.chat.username
                msg += f"\n=> **{name} {username}** [`{id}`]"
        return msg

    async def add_source_dest(client, message, source=False, dest=False):
        id = int(message.text.split()[1])
        db_group = message.text.split()[2]
        names = await get_name(id)
        if source:
            x = "source"
            keys = [id, None, db_group]
        if dest:
            x = "dest"
            keys = [None, id, db_group]
        if db.check_if_exist(id, db_group, typ=x):
            new_msg = f"**{names[0]}** [`{id}`] already in {x} **{db_group}**"
            return await client.edit_message_text(message.chat.id, message.id, text=new_msg)
        db.add(keys)
        new_msg = f"**{names[0]}** [`{id}`] has been added to {x} **{db_group}**"
        await client.edit_message_text(message.chat.id, message.id, text=new_msg)

    async def delete_source_dest(client, message, source=False, dest=False):
        id = int(message.text.split()[1])
        db_group = message.text.split()[2]
        names = await get_name(id)
        if source:
            x = "source"
        if dest:
            x = "dest"
        if not db.check_if_exist(id, db_group, typ=x):
            new_msg = f"**{names[0]}** [`{id}`] not exist in {x} **{db_group}**"
            return await client.edit_message_text(message.chat.id, message.id, text=new_msg)
        db.delete(id, db_group, x)
        new_msg = f"**{names[0]}** [`{id}`] has been deleted from {x} **{db_group}**"
        await client.edit_message_text(message.chat.id, message.id, text=new_msg)

    async def check_special_channel(client, message):
        if (special_channel or captions_match) is None: return True
        if message.sender_chat.id == int(special_channel):
            if any(z for z in captions_match if z in message.caption):
                return True
            else: return False

    async def send_error_to_log(client, ex):
        ERROR = {}
        try:
            ERROR[str(ex)]
        except KeyError:
            ERROR.update({str(ex): ex})
            Error = f"**Error on autopost**\n\n`{ex}`"
            await client.send_message(log_channel, text=Error)


    ### message listner and sender ###

    @client.on_message(~filters.media_group & filters.photo | filters.video | filters.sticker | filters.animation | filters.video_note | filters.document)
    async def resend(client, message):
                    if message.sender_chat is not None and message.sender_chat.id in db.get_sources_dests_names("source"):
                        for chat in db.get_dests_by_source(message.sender_chat.id):
                            try:
                                if await check_special_channel(message) is False: return
                                await client.copy_message(int(chat), message.sender_chat.id, message.id, caption="")
                            except Exception as ex:
                                await send_error_to_log(client, ex)

    @client.on_message(filters.media_group)
    async def media_group(client, message):
        if message.sender_chat is not None and message.sender_chat.id in db.get_sources_dests_names("source"):
            for chat in db.get_dests_by_source(message.sender_chat.id):
                async with lock:
                    if message.media_group_id in processed_media_groups_ids:
                        return
                    processed_media_groups_ids.append(message.media_group_id)
                try:
                    await client.copy_media_group(int(chat), message.sender_chat.id, message.id, captions="")
                except Exception as ex:
                                await send_error_to_log(client, ex)


    ### command handler ###

    @client.on_message(filters.me & filters.text & filters.regex(".listdb"))
    async def list_db(client, message):
        count = len(db.get_sources_dests_names("name", ))
        msg = f"**{count} groups in database:**\n"
        for group in db.get_sources_dests_names("name"):
            channels = db.get_sources_dests_by_name("source", group)
            count = len(channels)
            msg += f"\n**{group}** source ({count}):\n"
            for channel in channels:
                names = await get_name(channel)
                msg += f"=> **{names[0]} {names[1]}** [`{channel}`]\n"
            channels = db.get_sources_dests_by_name("dest", group)
            count = len(channels)
            msg += f"\n**{group}** dest ({count}):\n"
            for channel in channels:
                names = await get_name(channel)
                msg += f"=> **{names[0]} {names[1]}** [`{channel}`]\n"
        await client.edit_message_text(message.chat.id, message.id, text=msg)

    @client.on_message(filters.me & filters.text & filters.regex(".listchannel"))
    async def list_channels(client, message):
        msg = f"**all channels:**\n"
        new_msg = await get_all_dialogs(msg, channel=True)
        await client.edit_message_text(message.chat.id, message.id, text=new_msg)

    @client.on_message(filters.me & filters.text & filters.regex(".listgroup"))
    async def list_groups(client, message):
        msg = f"**all groups:**\n"
        new_msg = await get_all_dialogs(msg, group=True)
        await client.edit_message_text(message.chat.id, message.id, text=new_msg)

    @client.on_message(filters.me & filters.text & filters.regex(".listprivate"))
    async def list_privates(client, message):
        msg = f"**all private chats:**\n"
        new_msg = await get_all_dialogs(msg, private=True)
        await client.edit_message_text(message.chat.id, message.id, text=new_msg)

    @client.on_message(filters.me & filters.text & filters.regex(r"\.asource\s([^\s]*|$)\s(.*|$)"))
    async def add_source(client, message):
        await add_source_dest(client, message, source=True)

    @client.on_message(filters.me & filters.text & filters.regex(r"\.adest\s([^\s]*|$)\s(.*|$)"))
    async def add_dest(client, message):
        await add_source_dest(client, message, dest=True)

    @client.on_message(filters.me & filters.text & filters.regex(r"\.dsource\s([^\s]*|$)\s(.*|$)"))
    async def delete_source(client, message):
        await delete_source_dest(client, message, source=True)

    @client.on_message(filters.me & filters.text & filters.regex(r"\.ddest\s([^\s]*|$)\s(.*|$)"))
    async def delete_dest(client, message):
        await delete_source_dest(client, message, dest=True)

    idle()


if __name__ == "__main__":

    opts, args = getopt.getopt(sys.argv[1:], "hqdc:", ["help"])
    def readopt(name):
        global opts
        for e in opts:
            if e[0] == name:
                return e[1]
        return None

    if readopt("-c") is not None:
            configpath = readopt("-c")
    else: configpath = 'config.ini'

    config = ConfigParser()
    config.read(configpath)

    PROPS = ("source", "dest", "name")

    telegram()