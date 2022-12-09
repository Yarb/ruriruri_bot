import discord
from discord.ext import commands
from discord.ext import tasks
from os.path import exists
from os.path import getmtime
import json
import re
import random

CLOSED = "closed!"
RESOURCE_FILE = "resources.json"
CONFIGFILE = "config.json"

MSG_OPEN = "OPENED"
MSG_CLOSED = "CLOSED"
MSG_NO_REPORT = "NO_REPORT"
MSG_REPORT = "REPORT"
MSG_ALERT = "ALERT"
MSG_OTHER = "OTHER"
MSG_IDENTITY = "IDENTITY"
MSG_IDIOTS = "STUPIDITY"


class WatchCog(commands.Cog):
    """Watchdog functions
    Namely adds the timed watchdog for monitoring the status file changes
    """
    
    def __init__(self, bot, activity_file):
        self.bot = bot
        self.target = activity_file
        self.activity = ""
        self.modified = 0
        self.sender = self.bot.get_cog('Messaging')
        self.watchdog.start()

    def cog_unload(self):
        self.watchdog.cancel()
        
    @tasks.loop(seconds=10.0)
    async def watchdog(self):
        if exists(self.target):
            try:
                modified = getmtime(self.target)
            except FileNotFoundError:
                return
                
            if  modified != self.modified:
                try:
                    with open(self.target, "r", encoding="utf-8") as f:
                        new_activity = f.readline()
                except FileNotFoundError:
                    return
                self.activity = new_activity
                self.modified = modified
                if self.activity == "":
                    await self.sender.send_msg("", MSG_OPEN)
                else:
                    await self.sender.send_msg(self.activity, MSG_REPORT)
                
        elif self.activity != "":
            self.activity = ""
            await self.sender.send_msg("", MSG_CLOSED)
 

class Messaging(commands.Cog):
    """Messaging cog additions. Basically functions to send messages"""
    
    def __init__(self, bot, channel, resources):
        self.bot = bot
        self.channel = channel
        self.resources = resources

        
    async def post_image_message(self, pic, message):
        try:
            await self.channel.send(file=discord.File(pic), content=message)
        except FileNotFoundError:
            print("File missing: " + pic)
    
    
    async def send_msg(self, msg, type):
        try:
            if not msg:
                msg = self.get_resource(type)
            if USE_PIC[type] != "":
                await self.post_image_message(self.get_resource(USE_PIC[type]), msg)
            else:
                await self.channel.send(msg)
                
        except KeyError:
            print(f"\n**** Resource configuration error: {type} image type missing or resource name mismatch")

            
    def get_resource(self, resource):
        """Randomizes an given resource type from the resource file. 
        These are basically images and replies for the bot to make it more varied.
        """
        i = random.randint(0, len(self.resources[resource]) - 1)
        return self.resources[resource][i]



try:
    with open(RESOURCE_FILE, "rb") as f:
        resources = json.load(f)
    with open(CONFIGFILE, "rb") as f:
        config = json.load(f)
except FileNotFoundError:
    sys.exit("resources.json or config.json missing, quitting.")

TOKEN = config["token"]
ACTIVITY_FILE = config["actfile"]
CHANNEL = config["channel"]
GUILD = config["guild"]

USE_PIC = config["use_pic_type"]
NAUGHTY_RE = re.compile("|".join(resources["NAUGHTY_REGEX"]), re.IGNORECASE)
IDENTITY_RE = re.compile(resources["IDENTITY_REGEX"], re.IGNORECASE)


#Initialize the bot
bot = commands.Bot("$$$$", None, None)

@bot.event
async def on_ready():
    """When bot activates, set up the guild/channel and register cogs."""
    
    print('We have logged in as {0.user}'.format(bot))
    guild = discord.utils.get(bot.guilds, name=GUILD)
    channel = discord.utils.get(guild.text_channels, name=CHANNEL)
    if channel:
        bot.add_cog(Messaging(bot, channel, resources))
        bot.add_cog(WatchCog(bot, ACTIVITY_FILE))

#Start the bot
bot.run(TOKEN)


