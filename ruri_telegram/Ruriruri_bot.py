from telegram import Update
from telegram.ext import CommandHandler, CallbackContext, Filters, MessageHandler, Updater
import logging
import time
import os
import json
import random
import sys
import re
from subprocess import call

CONFIGFILE = "config.json"
RESOURCE_FILE = "resources.json"
# -@otakutto

CLOSED = 0
OPEN = 1
REPORTED = 2
STATE = "open"
REPORT = "report"

MSG_OPEN = "OPENED"
MSG_CLOSED = "CLOSED"
MSG_NO_REPORT = "NO_REPORT"
MSG_NOT_OPEN = "NOT_OPEN"
MSG_NOT_OPEN_ERROR = "NOT_OPEN_ERROR"
MSG_REPORT = "REPORT"
MSG_ALERT = "ALERT"
MSG_OTHER = "OTHER"
MSG_IDENTITY = "IDENTITY"
MSG_IDIOTS = "STUPIDITY"

SOUND_OK = "SOUND_OK"
SOUND_ALERT = "SOUND_ALERT"

CHECK_INTERVAL = 10


# Load configuration and resources.
try:
    resources = json.load(open(RESOURCE_FILE, "rb"))
    config = json.load(open(CONFIGFILE, "rb"))
    TOKEN = config["token"]
    ACTFILEPATH = config["actfile"]
    CHAT_ID = config["chat_id"]
    USE_PIC = config["use_pic_type"]
    NAUGHTY_RE = re.compile("|".join(resources["NAUGHTY_REGEX"]), re.IGNORECASE)
    IDENTITY_RE = re.compile(resources["IDENTITY_REGEX"], re.IGNORECASE)
    
except FileNotFoundError:
    sys.exit("resources.json or config.json missing, quitting.")



def get_resource(resource: str):
"""Returns a random resource/response of given type from the resources.json"""

    i = random.randint(0, len(resources[resource]) - 1)
    return resources[resource][i]


def send_text_message(context: CallbackContext, msg: str):

    context.bot.send_message(chat_id=CHAT_ID, text=msg)


def send_photo_message(context: CallbackContext, image_path: str, msg: str) -> int:

    try:
        context.bot.send_photo(chat_id=CHAT_ID, photo=open(image_path, 'rb'), caption=msg)
        return 1
    except FileNotFoundError:
        send_text(context, msg)
        return 0


def send_message(context: CallbackContext, msg: str, msg_type: str):
"""Send either photo or ordinary message based on config"""

    try:
        if not msg:
            msg = get_resource(msg_type)
        if USE_PIC[msg_type] != "":
            send_photo_message(context, get_resource(USE_PIC[msg_type]), msg)
        else:
            send_text_message(context, msg)
    except KeyError:
        error = "\n**** Resource configuration error: " + msg_type + " image type missing or resource name mismatch"
        logging.getLogger().log(35, error)


def get_bot_data(context: CallbackContext, key: str) -> int:
"""Return the state of the space from the context where it is stored"""

    try:
        return context.bot_data[key]
    except KeyError:
        set_bot_data(context, key, "")
        return 0


def set_bot_data(context: CallbackContext, key: str, value: int):
"""Store the given state to the bot context."""

    try:
        context.bot_data[key] = value
    except KeyError:
        pass


def verify_chat_id(update: Update):

    return str(update.effective_chat.id) == CHAT_ID


def play(sound):
"""Play given sound. This is intended for audible alerts, notifications, etc."""

    logging.getLogger().log(35, "***** playing sound: " + sound + " *****")
    call(["aplay", "--buffer-size=4096",  sound]) 


def identity(update: Update, context: CallbackContext ):
"""Respond to identity command"""

    if verify_chat_id(update):
        send_message(context, "", MSG_IDENTITY)


def respond_to_idiots(update: Update, context: CallbackContext ):
"""Respond to silly requests. 
Named so due to the tendencies of the bot's namesake
"""

    if verify_chat_id(update):
        msg = "@" + update.message.from_user.username + " "
        msg = msg + get_resource(MSG_STUPIDITY)
        send_message(context, msg, MSG_STUPIDITY)


    
def process_report(update: Update, context: CallbackContext ):
"""Process and react to given user activity report"""

    if verify_chat_id(update):
        msg = " ".join(context.args)
        if get_bot_data(context) != CLOSED :
        
            set_bot_data(context, REPORT, msg)
            set_bot_data(context, STATE, REPORTED)
            send_message(context, "Understood, activity set: " + msg, MSG_REPORT)
            play(get_resource(SOUND_OK))
            logging.getLogger().log(35, "New report: " + msg)
            
        else:
            send_message(context, "", MSG_NOT_OPEN)
        if NAUGHTY_RE.match(msg):
            respond_to_idiots(update, context)
            

def give_report(update: Update, context: CallbackContext ):
"""Respond to status request messages. 
Read return the stored user activity report.
"""

    if verify_chat_id(update):
        state = get_bot_data(context, STATE)
        if  state == REPORTED:
            msg = get_bot_data(context, REPORT)
            send_message(context, "Currently: " + msg, MSG_REPORT)
        elif state == OPEN:
            send_message(context, "", MSG_NO_REPORT)
        else:
            send_message(context, "", MSG_NOT_OPEN_ERROR)


def send_alert(update: Update, context: CallbackContext):
"""React to audible alert command from user.
Checks that message was from correct chat, that the space is open and
then plays sound.
"""
    
    if verify_chat_id(update):
        state = get_bot_data(context)
        if  state != CLOSED:
            send_message(context, "", MSG_ALERT)
            play(get_resource(SOUND_ALERT))
        else:
            send_message(context, "", MSG_NOT_OPEN_ERROR)
    

def activity_check(context: CallbackContext):
"""Function executed by the watchdog.
Checks if there is a change in the monitored file and thus in state of the space.
Acts accordingly depending on the change, if any.
"""

    if os.path.exists(ACTFILEPATH):
        if get_bot_data(context) == CLOSED:
            set_bot_data(context, STATE, OPEN)
            send_message(context, "", MSG_OPEN)
            logging.getLogger().log(35, "Open")
    else:
        if get_bot_data(context) != CLOSED:
            set_bot_data(context, STATE, CLOSED)
            set_bot_data(context, REPORT, "")
            send_message(context, "", MSG_CLOSED)
            logging.getLogger().log(35, "Closed")


def main():
"""Main function.
Sets up the bot and handlers for different bot commands.
Registers the said handlers to the bot's dispatcher and runs the bot.
"""
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)

    updater = Updater(token=TOKEN)
    dispatcher = updater.dispatcher
    
  
  
    identity_handler = CommandHandler(['who'], identity)
    alert_handler = CommandHandler(['alert', 'notify'], send_alert)
    report_handler = CommandHandler(['Ruriruri', 'reporting'], process_report)
    status_handler = CommandHandler(['status', 'report'], give_report)
    pervert_and_idiot_handler = MessageHandler(Filters.regex(IDENTITY_RE) & Filters.regex(NAUGHTY_RE), respond_to_idiots)
    
    
    dispatcher.add_handler(identity_handler)
    dispatcher.add_handler(alert_handler)
    dispatcher.add_handler(report_handler)
    dispatcher.add_handler(status_handler)
    dispatcher.add_handler(pervert_and_idiot_handler)
    
    updater.job_queue.run_repeating(activity_check, interval=CHECK_INTERVAL, first=0)
    
    
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
