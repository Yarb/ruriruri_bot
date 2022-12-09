Ruriruri bot code repository. 
This code is of telegram bot used to monitor club room and report changes in the space. More exactly, the script monitors changes in a file (or rather existence or lack of said file) and acts based on these changes to telegram. 

In the actual use environment, this file is created and removed by separate monitoring script. The upside of this is that this bot is universal as long as there exists something to create/remove the monitored file. Downside is that you still need to figure out how to do the actual monitoring.
The bot relies on python telegram library.
