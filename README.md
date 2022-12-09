Ruriruri bot code repository. 
This contains both Telegram and Discord bots that both monitor a file which indicates the status of the monitored space. 

In the actual use environment, this file is created and removed by separate monitoring script. The upside of this is that this bot is universal as long as there exists something to create/remove the monitored file. Downside is that you still need to figure out how to do the actual monitoring.
The bot relies on python telegram library.
