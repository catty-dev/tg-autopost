This is an autopost script that resend media from source to destination.
You can define infinity autopost groups with their own sources and destinations
and change them while the program is running thx to the sqlite3 database.
Fill out config.ini like the example.

You can use as much clients as you want. You just need a bot token. Create the client sessions through the bot by feeding him with your api id, api hash, phone number and login code for each account you want to use then restart the script.

All registered clients and the bots are running parallel.

USE AT YOUR OWN RISK


You can execute user commands in every chat.

You can use followed commands:
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
.listgroup     #list all groups and supergroups
.listuser    #list all users
.listbot    #list all bots
```
