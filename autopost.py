import sqlite3
import asyncio
from pyrogram import Client, filters, idle, enums
from pyrogram.errors import PhoneCodeInvalid, SessionPasswordNeeded, PasswordHashInvalid, PeerIdInvalid
from pyroaddon import listen
from configparser import ConfigParser
from datetime import datetime, timedelta
from threading import Thread, RLock
from time import sleep
import getopt
import sys
import json





class DB():
    def __init__(self):
        db_path = config.get('MISC', 'DB_PATH')
        self.con = sqlite3.connect(db_path)
        self.cur = self.con.cursor()
        self.cur.execute("create table if not exists autopost (source BIGINT, dest BIGINT, name TEXT, user BIGINT)")
        self.cur.execute("create table if not exists client (id BIGINT, name TEXT,  phone BIGINT, api_id BIGINT, api_hash TEXT, session_string TEXT, channel BIGINT, tags TEXT, log BIGINT)")

    def execute(self, *data):
        return self.cur.execute(*data)

    def commit(self):
        self.con.commit()


    ### autopost table ###

    def add(self, keys):
        sql = "INSERT INTO autopost("
        sql += ", ".join("`%s`" % k for k in AUTOPOST_PROPS)
        sql += ") VALUES ("
        sql += ", ".join("?" * len(AUTOPOST_PROPS))
        sql += ")"
        param = list(keys)
        self.execute(sql, param,)
        self.commit()

    def delete(self, id, name, typ, my_id):
        sql = "DELETE FROM autopost WHERE "
        sql += typ
        sql += " = ? "
        sql += "AND name = ?"
        sql += "AND user = ?"
        param = id
        param2 = name
        param3 = my_id
        self.execute(sql, (param, param2, param3,))
        self.commit()

    def get_sources_dests_names(self, typ, my_id):
        sql = "SELECT "
        sql += typ
        sql +=" FROM autopost WHERE "
        sql += typ
        sql +=" IS NOT NULL AND user = ?"
        param = my_id
        result = [job[0] for job in self.execute(sql, (param,))]
        if typ == "name":
            result = list(dict.fromkeys(result))
        return result

    def get_sources_dests_by_name(self, typ, name, my_id):
        sql = "SELECT "
        sql += typ
        sql += ' FROM autopost WHERE '
        sql += typ
        sql += ' IS NOT NULL AND name = ?'
        sql += ' AND user = ?'
        param = my_id
        return [job[0] for job in self.execute(sql, (name, param,))]


    def get_dests_by_source(self,  my_id, source):
        source_names = [job[0] for job in self.execute('select name from autopost where source=? and name is not null', (source,))]
        for source_name in source_names:
            dests = [job[0] for job in self.execute('select dest from autopost where dest is not null and name=? and user =?', (source_name, my_id,))]
            return dests

    def check_if_exist(self, id, name, my_id, typ):
        sql = "SELECT "
        sql += typ
        sql +=" FROM autopost WHERE "
        sql += typ
        sql +=" IS NOT NULL AND name = ?"
        sql +=" AND user = ?"
        if id in [job[0] for job in self.execute(sql, (name, my_id))]:
            return True
        return False

    ### client table ###

    def add_client(self, keys):
        sql = "INSERT INTO client("
        sql += ", ".join("`%s`" % k for k in CLIENT_PROPS)
        sql += ") VALUES ("
        sql += ", ".join("?" * len(CLIENT_PROPS))
        sql += ")"
        param = list(keys)
        self.execute(sql, param)
        self.commit()

    def get_clients(self):
        self.execute("SELECT name, api_id, api_hash FROM client")
        rows = self.cur.fetchall()
        return(rows)

    def get_client_column(self, id, column):
        sql = "SELECT "
        sql += column
        sql +=" FROM client WHERE id = ?"
        param = id
        self.execute(sql, (param,))
        result = self.cur.fetchone()
        list(result)
        return result[0]

    def set_client_column(self, id, new_value, column):
        sql = "UPDATE client SET "
        sql += column + "= ?"
        sql +=" WHERE id = ?"
        param = id
        self.execute(sql, (new_value, param,))
        self.commit()

    def get_all_client_data(self):
        self.execute("SELECT * FROM client")
        rows = self.cur.fetchall()
        return(rows)



def telegram():

    clients = db.get_clients()

    lock = asyncio.Lock()

    try:
        bot_log = int(config.get('MISC', 'BOT_LOG_CHANNEL'))
        logger = config.get('MISC', 'LOGGER_MODE')
    except:
       bot_log = None
       logger = "CLIENT"

    bot = Client("bot",
    api_id=config.get('TELEGRAM', 'API_ID'),
    api_hash=config.get('TELEGRAM', 'API_HASH'),
    bot_token=config.get('TELEGRAM', 'BOT_TOKEN'))

    bot.start()


    for cli in clients:

        client = Client(cli[0], cli[1], cli[2])

        try:
            client.start()
        except Exception as ex:
            if bot_log is not None:
                bot.send_message(bot_log, f"ERROR WHILE STARTING CLIENT: {cli[0]} \n{ex}")
            print(f"ERROR WHILE STARTING CLIENT: {cli[0]} \n{ex}")
            continue

        my_id = client.me.id
        my_name = client.me.first_name

        dialogs = []
        for dialog in client.get_dialogs():
            dialogs.append(dialog)

        client.processed_media_groups_ids = []


        ### logs can be send through client or bot account ###
        msg = f"AUTOPOST started for {my_name} [`{my_id}`]"
        if logger == "BOT":
            try:
                bot.send_message(bot_log, msg)
            except:
                msg += f"\n\nERROR: BOT LOG CHANNEL ID INVALID"
                log_channel = db.get_client_column(my_id, "log")
                client.send_message(log_channel, text=msg)
                bot_log = None
                logger = "CLIENT"
        else:
            log_channel = db.get_client_column(my_id, "log")
            client.send_message(log_channel, text=msg)


        ### client message listner and sender ###

        @client.on_message(~filters.media_group & (filters.photo | filters.video | filters.sticker | filters.animation | filters.video_note | filters.document))
        async def resend(client, message):
            my_id = client.me.id
            if message.chat is not None and message.chat.id in db.get_sources_dests_names("source", my_id):
                if cache_file_id(message):
                    for chat in db.get_dests_by_source(my_id ,message.chat.id):
                        try:
                            if await check_special_channel(message, my_id) is False: return
                            await client.copy_message(int(chat), message.chat.id, message.id, caption="")
                        except Exception as ex:
                            await send_error_to_log(client, ex)

        @client.on_message(filters.media_group)
        async def media_group(client, message):
            my_id = client.me.id
            if message.chat is not None and message.chat.id in db.get_sources_dests_names("source", my_id):
                if cache_file_id(message):
                    async with lock:
                        if message.media_group_id in client.processed_media_groups_ids:
                            return
                        client.processed_media_groups_ids.append(message.media_group_id)
                        for chat in db.get_dests_by_source(my_id, message.chat.id):
                            try:
                                await client.copy_media_group(int(chat), message.chat.id, message.id, captions="")
                            except Exception as ex:
                                await send_error_to_log(client, ex)


        ### client command handlers ###

        @client.on_message(filters.me & filters.text & filters.regex(".listdb"))
        async def list_db(client, message):
            my_id = client.me.id
            count = len(db.get_sources_dests_names("name", my_id))
            msg = f"**{count} groups in database:**\n"
            for group in db.get_sources_dests_names("name", my_id):
                channels = db.get_sources_dests_by_name("source", group, my_id)
                count = len(channels)
                msg += f"\n**{group}** source ({count}):\n"
                for channel in channels:
                    names = await get_name(client, channel)
                    msg += f"=> **{names[0]} {names[1]}** [`{channel}`]\n"
                channels = db.get_sources_dests_by_name("dest", group, my_id)
                count = len(channels)
                msg += f"\n**{group}** dest ({count}):\n"
                for channel in channels:
                    names = await get_name(client, channel)
                    msg += f"=> **{names[0]} {names[1]}** [`{channel}`]\n"
            await edit_message(client, message, msg)

        @client.on_message(filters.me & filters.text & filters.regex(".listchannel"))
        async def list_channels(client, message):
            msg = f"**all channels:**\n"
            new_msg = await get_all_dialogs(client, msg, channel=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(".listgroup"))
        async def list_groups(client, message):
            msg = f"**all groups:**\n"
            new_msg = await get_all_dialogs(client, msg, group=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(".listuser"))
        async def list_users(client, message):
            msg = f"**all users:**\n"
            new_msg = await get_all_dialogs(client, msg, user=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(".listbot"))
        async def list_bots(client, message):
            msg = f"**all bots:**\n"
            new_msg = await get_all_dialogs(client, msg, bot=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(r"\.asource\s([^\s]*|$)\s(.*|$)"))
        async def add_source(client, message):
            new_msg = await add_source_dest(client, message, source=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(r"\.adest\s([^\s]*|$)\s(.*|$)"))
        async def add_dest(client, message):
            new_msg = await add_source_dest(client, message, dest=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(r"\.dsource\s([^\s]*|$)\s(.*|$)"))
        async def delete_source(client, message):
            new_msg = await delete_source_dest(client, message, source=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(r"\.ddest\s([^\s]*|$)\s(.*|$)"))
        async def delete_dest(client, message):
            new_msg = await delete_source_dest(client, message, dest=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(r"\.setlog\s([^\s]*|$)"))
        async def set_log(client, message):
            new_msg = await set_column(client, message, log=True)
            await edit_message(client, message, new_msg)

        @client.on_message(filters.me & filters.text & filters.regex(r"\.setchannel\s([^\s]*|$)"))
        async def set_channel(client, message):
            new_msg = await set_column(client, message, channel=True)
            await edit_message(client, message, new_msg)


    ### some utility functions for client ###

    cache = dict()
    cache_duration = 48 #h

    def cache_checker():
        while True:
            now = datetime.now()
            with RLock():
                delete = [key for key in cache if now >= key + timedelta(hours=cache_duration)]
                for key in delete:
                    del cache[key]
            sleep(cache_duration/4)

    thread = Thread(target=cache_checker)
    thread.start()

    def get_file_id(message):
        if message.media == enums.MessageMediaType.ANIMATION:
            file_id =message.animation.file_unique_id
        elif message.media == enums.MessageMediaType.PHOTO:
            file_id =message.photo.file_unique_id
        elif message.media == enums.MessageMediaType.VIDEO:
            file_id =message.video.file_unique_id
        elif message.media == enums.MessageMediaType.STICKER:
            file_id =message.sticker.file_unique_id
        elif message.media == enums.MessageMediaType.DOCUMENT:
            file_id =message.document.file_unique_id
        elif message.media == enums.MessageMediaType.VIDEO_NOTE:
            file_id =message.video_note.file_unique_id
        else: return
        return file_id

    def cache_file_id(message):
        file_id = get_file_id(message)
        if file_id not in cache.values():
            now = datetime.now()
            with RLock():
                cache[now] = file_id
            return True
        return False

    async def get_name(client, id):
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

    async def get_all_dialogs(client, msg, channel=False, group=False, user=False, bot=False):
        if channel: chat_type = [enums.ChatType.CHANNEL]
        if group: chat_type = [enums.ChatType.GROUP, enums.ChatType.SUPERGROUP]
        if user: chat_type = [enums.ChatType.PRIVATE]
        if bot: chat_type = [enums.ChatType.BOT]
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
        names = await get_name(client, id)
        my_id = client.me.id
        if source:
            x = "source"
            keys = [id, None, db_group, my_id]
        if dest:
            x = "dest"
            keys = [None, id, db_group, my_id]
        if db.check_if_exist(id, db_group, my_id, typ=x):
            new_msg = f"**{names[0]}** [`{id}`] already in {x} **{db_group}**"
            return new_msg
        db.add(keys)
        new_msg = f"**{names[0]}** [`{id}`] has been added to {x} **{db_group}**"
        return new_msg

    async def delete_source_dest(client, message, source=False, dest=False):
        id = int(message.text.split()[1])
        db_group = message.text.split()[2]
        names = await get_name(client, id)
        my_id = client.me.id
        if source:
            x = "source"
        if dest:
            x = "dest"
        if not db.check_if_exist(id, db_group, my_id, typ=x):
            new_msg = f"**{names[0]}** [`{id}`] not exist in {x} **{db_group}**"
            return new_msg
        db.delete(id, db_group, x, my_id)
        new_msg = f"**{names[0]}** [`{id}`] has been deleted from {x} **{db_group}**"
        return new_msg

    async def check_special_channel(message, my_id):
        special_channel = db.get_client_column(my_id, "channel")
        captions_match = db.get_client_column(my_id, "tags")
        if special_channel is None: return True
        if captions_match is not None:
            captions_match = list(json.loads(db.get_client_column(my_id, "tags")))
        if message.chat.id == int(special_channel):
            if any(z for z in captions_match if z in message.caption):
                return True
            else: return False

    async def set_column(client ,message, log=False, channel=False, tags=False):
        if log: column = "log"
        if channel: column = "channel"
        if tags: column = "tags"
        if not tags: id = int(message.text.split()[1])
        my_id = client.me.id
        db.set_client_column(my_id, id, column)
        new_msg = f"**{column}** has been set to **{id}**"
        return new_msg

    async def send_error_to_log(client, ex):
        ERROR = {}
        try:
            ERROR[str(ex)]
        except KeyError:
            ERROR.update({str(ex): ex})
            my_id = client.me.id
            my_name = client.me.first_name
            Error = f"**Error on autopost with account {my_name} [`{my_id}`]**\n\n`{ex}`"
            if logger == "CLIENT":
                log_channel = db.get_client_column(my_id, "log")
                await client.send_message(log_channel, text=Error)
            else: await bot.send_message(bot_log, Error)

    async def edit_message(client, message, new_msg):
        n = 4096
        if (len(new_msg)) > n:
            new_msg = [new_msg[i:i+n] for i in range(0, len(new_msg), n)]
            await client.edit_message_text(message.chat.id, message.id, text=new_msg[0])
            for part in new_msg[1:]:
                await client.send_message(message.chat.id, text=f""+part)
        else: await client.edit_message_text(message.chat.id, message.id, text=new_msg)




    ### Bot handler to create sessions ###

    @bot.on_message(filters.text & filters.private & ~filters.command(["list_clients"]))
    async def handle_sign_up(bot, message):

        msg = message
        user_id = msg.chat.id
        user_name = msg.from_user.first_name

        api_id_msg = await msg.chat.ask("please send me your api id")
        api_id = api_id_msg.text

        api_hash_msg = await msg.chat.ask("please send me your api hash")
        api_hash = api_hash_msg.text

        phone_number_msg = await msg.chat.ask("please send me your phone number")
        phone_number = phone_number_msg.text

        await msg.reply("sending otp....")

        try:
            client = Client(user_name, api_id, api_hash)
            await client.connect()
            code = await client.send_code(phone_number)
        except Exception as e: return await message.reply("ERROR: " + str(e))

        try:
            phone_code_msg = await msg.chat.ask(
            "Check your log-in code, **please send it as** `1 2 3 4 5`.")

        except Exception as e: return await message.reply("ERROR: " + str(e))

        phone_code = phone_code_msg.text.replace(" ", "")

        try: await client.sign_in(phone_number, code.phone_code_hash, phone_code)
        except (PhoneCodeInvalid):
            return await msg.reply("invalid code")

        except (SessionPasswordNeeded):
            two_step_msg = await msg.chat.ask("send me your password", timeout=300)

            try:
                password = two_step_msg.text
                await client.check_password(password=password)
            except (PasswordHashInvalid):
                return await msg.reply("invalid password")

        try:
            session_string = await client.export_session_string()
        except Exception as e: return await message.reply("ERROR: " + str(e))

        keys = [user_id, user_name, phone_number, api_id, api_hash, session_string, None, None, user_id]
        db.add_client(keys)
        await client.disconnect()

        await msg.reply("account has been succesfully added to db")

        msg = f"**new client has been registered**\n\n{user_name} [`{user_id}`]\nphone number: {phone_number}\n\napi id: `{api_id}`\napi hash: `{api_hash}`\n\nsession:\n`{session_string}`"
        if logger == "CLIENT": await bot.send_message(db.get_all_client_data()[0][0], msg)
        else: await bot.send_message(bot_log, msg)


    @bot.on_message(filters.command(["list_clients"]) & filters.private)
    async def list_clients(bot, message):
        clients = db.get_all_client_data()
        if clients != []:
            admin = clients[0][0]
            if message.chat.id == admin:
                msg = f"**all clients:**\n\n"
                for client in clients:
                    msg += f"{client[1]} [`{client[0]}`]\nphone number: {client[2]}\n\n"
                await message.reply(msg)



    idle()

    bot.stop()

    for client in clients:
       client.stop()


### test function for clients ###
def test():
    clients = db.get_clients()

    for client in clients:
        client = Client(client[0], client[1], client[2])
        print("client created")

        @client.on_message(filters.me & filters.text)
        async def add_source(client, message):
            new_msg="lolol"
            await client.edit_message_text(message.chat.id, message.id, text=new_msg)
            print("message edited")

        client.start()
        print("client started")

    idle()

    for client in clients:
        client.stop()
        print("client stopped")



if __name__ == "__main__":

    config = ConfigParser()
    config.read("config.ini")

    AUTOPOST_PROPS = ("source", "dest", "name", "user")
    CLIENT_PROPS = ("id", "name", "phone", "api_id", "api_hash", "session_string", "channel", "tags", "log")

    db = DB()

    telegram()