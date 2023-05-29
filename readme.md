This is an autopost script that resend media from source to destination.
You can define infinity autopost groups with their own sources and destinations
and change them while the program is running thx to the sqlite3 database.
Fill out config.ini like the example.

You can use as much clients as you want. You just need a bot token. Create the client sessions through the bot by feeding him with your api id, api hash, phone number and login code for each account you want to use then restart the script.

You can define a logger for every client with the command ```.setlog [ID]``` (defult is saved messages of the client) or you can let the bot send logs from all clients to group/channel by setting LOGGER_MODE to BOT or CLIENT.

All registered clients and the bot are running parallel.


USE AT YOUR OWN RISK, TELEGRAM DOESN'T LIKE SCRIPTS LIKE THIS


You can execute client commands in every chat.

Client commands:
```
.asource [ID] [examplegroup]           #add source chat with that ID to your example group
.adest   [ID] [examplegroup]           #add destination chat with that ID to your example group
.dsource [ID] [examplegroup]           #delete source chat with that ID of your example group
.ddest   [ID] [examplegroup]           #delete destination chat with that ID of your example group
```
```
.listdb         #lists all your saved sources and destinantions catigorized in your groups
```

To get the chat IDs needed for the commands you can list all your dialogs with their id and name:
```
.listchannel    #list all channels
.listgroup      #list all groups and supergroups
.listuser       #list all users
.listbot        #list all bots
```


Bot commands:
```
/start          #creating a session for the actual client.
/list_clients   #list all clients in db. Can only be used from the first client in db.
```