This is an autopost script that resend media from source to destination.
You can define infinity autopost groups with their own sources and destinations
and change them while the program is running thx to the sqlite3 database.



You can execute the commands in every chat.


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

.listgroups     #list all groups and supergroups

.listprivate    #list all users and bots
```
