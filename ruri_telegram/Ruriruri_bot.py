import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackContext, MessageHandler, filters
import random
import time
import os
import json
import sys
import re
from subprocess import call


CONFIGFILE = "config.json"
RESOURCE_FILE = "resources.json"
# -@otakutto

CLOSED = 0
OPEN = 1
REPORTED = 2
STATUS = "status"
REPORT = "report"
USE_STICKER = 0
USE_PIC = 0


MSG_OPEN = "OPENED"
MSG_CLOSED = "CLOSED"
MSG_NO_REPORT = "NO_REPORT"
MSG_NOT_OPEN = "NOT_OPEN"
MSG_NOT_OPEN_ERROR = "NOT_OPEN_ERROR"
MSG_NEED_REPORT = "NEED_REPORT"
MSG_REPORT = "REPORT"
MSG_ALERT = "ALERT"
MSG_OTHER = "OTHER"
MSG_IDENTITY = "IDENTITY"
MSG_IDIOTS = "STUPIDITY"

SOUND_OK = "SOUND_OK"
SOUND_ALERT = "SOUND_ALERT"

CHECK_INTERVAL = 10

TOKEN = "token"
ACTFILE = "activity_file"
REPORT_FILE_ALT = "alt_reportfile"
CHAT_ID = "chat_id"
USE_PIC = "use_pictures"
USE_AUDIO = "use_audio"
PICTURES = "pictures"
USE_STICKER = "use_stickers"
STICKER_PACK = "sticker_pack"
STICKER_SUBSETS = "sticker_subsets"
SPAM_COUNT = "spamcount"
SPAM_LIMIT = "sticker_spam_limit"

HTML_CLOSED = '<link rel="stylesheet" href="report.css"><b id="red">Closed</b>'
HTML_OPEN = '<link rel="stylesheet" href="report.css"><b id="green">Open</b>'


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Load configuration and resources.
try:
    resources = json.load(open(RESOURCE_FILE, "rb"))
    config = json.load(open(CONFIGFILE, "rb"))
        
except FileNotFoundError:
    sys.exit("resources.json or config.json missing, quitting.")


naughty_re = re.compile(r"\b(?:%s)\b" % "|".join(resources["NAUGHTY_REGEX"]), re.IGNORECASE)
identity_re = re.compile(resources["IDENTITY_REGEX"], re.IGNORECASE)



def play(sound):
    """Play given sound. This is intended for audible alerts, notifications, etc."""

    if config[USE_AUDIO]:
        logging.getLogger().log(35, "***** playing sound: " + sound + " *****")
        call(["aplay", "-D", "sysdefault:CARD=Headphones", sound])



def get_state(context: CallbackContext, key: str) -> int:
    """Return the state of the space from the context where it is stored"""

    return context.bot_data.get(key, "")



def set_state(context: CallbackContext, key: str, value: int):
    """Store the given state to the bot context."""

    context.bot_data[key] = value



def get_resource(resource: str):
    """Returns a random resource/response of given type from the resources.json"""

    return random.choice(resources[resource])



def verify_message(update: Update):
    """Verify that the message is from the correct chat and is a new message, not a reaction or other update type."""
    if str(update.effective_chat.id) == config[CHAT_ID]:
        if update.message is None:
            logging.getLogger().log(35, "Ignoring non-message update")
            return False
        return True



async def identity(update: Update, context: CallbackContext ):
    """Respond to identity command"""

    if verify_message(update):
        await send_message(context, "", MSG_IDENTITY)



async def send_alert(update: Update, context: CallbackContext):
    """React to audible alert command from user.
    Checks that message was from correct chat, that the space is open and
    then plays sound.
    """
    
    if verify_message(update):
        
        if  get_state(context, STATUS) != CLOSED:
            await send_message(context, "", MSG_ALERT)
            play(get_resource(SOUND_ALERT))
        else:
            await send_message(context, "", MSG_NOT_OPEN_ERROR)



async def process_report(update: Update, context: CallbackContext ):
    """Process and react to given user activity report"""

    if verify_message(update):
        msg = " ".join(context.args)
        if get_state(context, STATUS) != CLOSED :
            if len(msg) > 0:
                set_state(context, REPORT, msg)
                await send_message(context, "Understood, activity set: " + msg, MSG_REPORT)
                play(get_resource(SOUND_OK))
                
                with open(config[ACTFILE],'w', encoding = 'utf-8') as f:
                    f.write(msg)
                with open(config[REPORT_FILE_ALT],'w', encoding = 'utf-8') as f:
                    f.write(HTML_OPEN)
                    f.write("<b> - " + msg + "</b>")
                logging.getLogger().log(35, "New report: " + msg)
            else:
                await send_message(context, "", MSG_NEED_REPORT)
        else:
            await send_message(context, "", MSG_NOT_OPEN_ERROR)
        if naughty_re.search(msg):
            await respond_to_idiots(update, context)

            

async def give_report(update: Update, context: CallbackContext ):
    """Respond to status request messages. 
    Read return the stored user activity report.
    """

    if verify_message(update):
        if  get_state(context, STATUS) == OPEN:
            msg = get_state(context, REPORT)
            if msg == "":
                await send_message(context, "", MSG_NO_REPORT)
            else:
                await send_message(context, "Currently: " + msg, MSG_REPORT)
        else:
            await send_message(context, "", MSG_NOT_OPEN)

    
    
async def send_sticker(context: ContextTypes.DEFAULT_TYPE, subset: dict):
    sticker_set = await context.bot.get_sticker_set(config[STICKER_PACK])    # Maybe cache the sticker set data?
    sticker = random.choice(sticker_set.stickers[subset["start"]:subset["end"]])
    await context.bot.sendSticker(chat_id=config[CHAT_ID], sticker=sticker.file_id)

    
    
async def send_text_message(context: CallbackContext, msg: str):

    await context.bot.send_message(chat_id=config[CHAT_ID], text=msg)



async def send_photo_message(context: CallbackContext, image_path: str, msg: str) -> int:

    try:
        await context.bot.send_photo(chat_id=config[CHAT_ID], photo=open(image_path, 'rb'), caption=msg)
        return 1
    except FileNotFoundError:
        error = "\n**** Resource configuration error: (" + image_path + ") invalid path."
        await send_text_message(context, msg)
        return 0



async def send_message(context: CallbackContext, msg: str, msg_type: str):
    """Send either photo or ordinary message based on config"""

    try:
        if not msg:
            msg = get_resource(msg_type)
            
        if config[USE_PIC] and config[PICTURES][msg_type] != "":
            await send_photo_message(context, get_resource(config[PICTURES][msg_type]), msg)
        else:
            if config[USE_STICKER] and config[STICKER_SUBSETS][msg_type]:
                await send_sticker(context, config[STICKER_SUBSETS][msg_type])
            await send_text_message(context, msg)
    except KeyError:
        error = "\n**** Resource configuration error: " + msg_type + " image type missing or resource name mismatch"
        logging.getLogger().log(35, error)


async def activity_check(context: CallbackContext):
    """Function executed by the watchdog.
    Checks if there is a change in the monitored file and thus in state of the space.
    Acts accordingly depending on the change, if any.
    """

    if os.path.exists(config[ACTFILE]):
        if get_state(context, STATUS) == CLOSED:
            set_state(context, STATUS, OPEN)
            await send_message(context, "", MSG_OPEN)
            with open(config[REPORT_FILE_ALT],'w', encoding = 'utf-8') as f:
                f.write(HTML_OPEN)
            logging.getLogger().log(35, "Open")
    else:
        if get_state(context, STATUS) != CLOSED:
            set_state(context, STATUS, CLOSED)
            set_state(context, REPORT, "")
            await send_message(context, "", MSG_CLOSED)
            with open(config[REPORT_FILE_ALT],'w', encoding = 'utf-8') as f:
                f.write(HTML_CLOSED)
            logging.getLogger().log(35, "Closed")


async def initialize(context: CallbackContext):
    
    #Init the bot state in context
    set_state(context, SPAM_COUNT, 0)
    set_state(context, STATUS, CLOSED)
    set_state(context, REPORT, "")
    set_state(context, SPAM_LIMIT, config[SPAM_LIMIT])
    
    # clear the report file, just in case we crashed.
    with open(config[REPORT_FILE_ALT],'w', encoding = 'utf-8') as f:
                f.write("")
    


async def respond_to_idiots(update: Update, context: CallbackContext ):
    """Respond to silly requests. 
    Named so due to the tendencies of the bot's namesake
    """

    if verify_message(update):
        msg = ""
        if update.message.from_user:
            msg = "@" + update.message.from_user.username + " "
        msg = msg + get_resource(MSG_IDIOTS)
        await send_message(context, msg, MSG_IDIOTS)



async def sticker_counter(update: Update, context: CallbackContext):
    
    if update.message.sticker and config[USE_STICKER]:
        counter = get_state(context, SPAM_COUNT)
        if counter == get_state(context, SPAM_LIMIT):
            await send_sticker(context, config[STICKER_SUBSETS][MSG_IDIOTS]) 
        counter += 1
        set_state(context, SPAM_COUNT, counter)
    else:
        set_state(context, SPAM_COUNT, 0)
        set_state(context, SPAM_LIMIT, config[SPAM_LIMIT] + random.randint(0,3))
        


if __name__ == '__main__':

    application = ApplicationBuilder().token(config[TOKEN]).build()
    
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)
    
    
    identity_handler = CommandHandler(['who'], identity)
    alert_handler = CommandHandler(['alert', 'notify'], send_alert)
    report_handler = CommandHandler(['Ruriruri', 'reporting'], process_report)
    status_handler = CommandHandler(['status', 'report'], give_report)
    
    counter_handler = MessageHandler(filters.ALL, sticker_counter)
    
    pervert_and_idiot_handler = MessageHandler(filters.Regex(identity_re) & filters.Regex(naughty_re), respond_to_idiots)
    
    application.add_handler(pervert_and_idiot_handler)
    application.add_handler(identity_handler)
    application.add_handler(alert_handler)
    application.add_handler(report_handler)
    application.add_handler(status_handler)
    application.add_handler(counter_handler)
    
    application.job_queue.run_once(callback=initialize, when=0)
    application.job_queue.run_repeating(callback=activity_check,interval=CHECK_INTERVAL)
    
    application.run_polling()
    
    
 #  context.job_queue.run_repeating(callback, interval, first=None, last=None, data=None, name=None, chat_id=None, user_id=None, job_kwargs=None)
 

