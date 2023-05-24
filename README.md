Ruriruri bot code repository. 
This contains both Telegram and Discord bots which both monitor a file indicating the status of the monitored space. 

In our actual use environment, this file is created and removed by separate monitoring script. The upside of this is that this bot is universal as long as there exists something to create/remove the monitored file. Downside is that you still need to figure out how to do the actual monitoring, which is sometimes easier said than done.
