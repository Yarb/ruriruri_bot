from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import logging, time, os, json, random, sys, signal, re
from subprocess import call

CONFIGFILE = "config.json"
RESOURCE_FILE = "resources.json"
# -@otakutto

CLOSED = 0
OPEN = 1
REPORTED = 2

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


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.WARNING)

# Load configuration and resources.
try:
    resources = json.load(open(RESOURCE_FILE, "rb"))
    config = json.load(open(CONFIGFILE, "rb"))
    TOKEN = config["token"]
    ACTFILEPATH = config["actfile"]
    CHAT_ID = config["chat_id"]
    USE_PIC = config["use_pic_type"]
    NAUGHTY_RE = re.compile("|".join(resources["NAUGHTY_REGEX"]))
    IDENTITY_RE = re.compile(resources["IDENTITY_REGEX"])

except FileNotFoundError:
    sys.exit("resources.json or config.json missing, quitting.")


def get_resource(resource: str):

    i = random.randint(0, len(resources[resource]) - 1)
    return resources[resource][i]


async def send_text_message(context: CallbackContext, msg: str):

    await context.bot.send_message(chat_id=CHAT_ID, text=msg)


async def send_photo_message(context: CallbackContext, image_path: str, msg: str) -> int:

    try:
        await context.bot.send_photo(chat_id=CHAT_ID, photo=open(image_path, 'rb'), caption=msg)
        return 1
    except FileNotFoundError:
        await send_text_message(context, msg)
        return 0


# Send either photo or ordinary message based on config
async def send_message(context: CallbackContext, msg: str, type: str):

    try:
        if not msg:
            msg = get_resource(type)
        if USE_PIC[type] != "":
            await send_photo_message(context, get_resource(USE_PIC[type]), msg)
        else:
            await send_text_message(context, msg)
    except KeyError:
        print("\n**** Resource configuration error: " + type + " image type missing or resource name mismatch")


def get_state(context: CallbackContext) -> int:

    try:
        return context.bot_data["open"]
    except KeyError:
        set_state(context, CLOSED)
        return CLOSED


def set_state(context: CallbackContext, state: int):

    try:
        context.bot_data["open"] = state
    except KeyError:
        pass


def verify_chat_id(update: Update):

    return str(update.effective_chat.id) == CHAT_ID


# Sound playing
def play(sound):

#    print("***** playing sound: " + sound + " *****")
    call(["aplay", "--buffer-size=4096",  sound])


# Doorbell
def alert_signal(signum, stack):

    if opened:
        play(get_resource(SOUND_ALERT))

# Doorbell signal (*NIX only)
# signal.signal(signal.SIGUSR2, alert_signal)    



async def identity(update: Update, context: CallbackContext ):

    if verify_chat_id(update):
        await send_message(context, "", MSG_IDENTITY)


async def respond_to_idiots(update: Update, context: CallbackContext ):

    if verify_chat_id(update):
        msg = "@" + update.message.from_user.username + " "
        msg = msg + get_resource(MSG_STUPIDITY)
        await send_message(context, msg, MSG_STUPIDITY)


    
async def process_report(update: Update, context: CallbackContext ):

    if verify_chat_id(update):
        if len(context.args) == 0:
            return
        msg = " ".join(context.args)
        if get_state(context) != CLOSED :
        
            context.bot_data["status"] = msg
            set_state(context, REPORTED)
            await send_message(context, "Understood, activity set: " + msg, MSG_REPORT)
            play(get_resource(SOUND_OK))
            logging.getLogger().log(35, "New report: " + msg)
            with open(ACTFILEPATH,'w', encoding = 'utf-8') as f:
                f.write(msg)
            
        else:
            await send_message(context, "", MSG_NOT_OPEN_ERROR)
        if NAUGHTY_RE.match(msg):
            await respond_to_idiots(update, context)
            

async def give_report(update: Update, context: CallbackContext ):

    if verify_chat_id(update):
        state = get_state(context)
        if  state == REPORTED:
            msg = context.bot_data["status"]
            await send_message(context, "Currently: " + msg, MSG_REPORT)
        elif state == OPEN:
            await send_message(context, "", MSG_NO_REPORT)
        else:
            await send_message(context, "", MSG_NOT_OPEN)


async def send_alert(update: Update, context: CallbackContext):
    
    if verify_chat_id(update):
        state = get_state(context)
        if  state != CLOSED:
            await send_message(context, "", MSG_ALERT)
            play(get_resource(SOUND_ALERT))
        else:
            await send_message(context, "", MSG_NOT_OPEN_ERROR)
    

async def activity_check(context: CallbackContext):

    if os.path.exists(ACTFILEPATH):
        if get_state(context) == CLOSED:
            set_state(context, OPEN)
            await send_message(context, "", MSG_OPEN)
            logging.getLogger().log(35, "Open")
    else:
        if get_state(context) != CLOSED:
            context.bot_data["open"] = CLOSED
            await send_message(context, "", MSG_CLOSED)
            logging.getLogger().log(35, "Closed")


def log( msg: str ):
    print()

def main():

    application = Application.builder().token(TOKEN).build()
  
    identity_handler = CommandHandler(['who'], identity)
    alert_handler = CommandHandler(['alert', 'notify'], send_alert)
    report_handler = CommandHandler(['Ruriruri', 'reporting'], process_report)
    status_handler = CommandHandler(['status', 'report'], give_report)
    pervert_and_idiot_handler = MessageHandler(filters.Regex(IDENTITY_RE) & filters.Regex(NAUGHTY_RE), respond_to_idiots)
    
    
    application.add_handler(identity_handler)
    application.add_handler(alert_handler)
    application.add_handler(report_handler)
    application.add_handler(status_handler)
    application.add_handler(pervert_and_idiot_handler)
    
    job_queue = application.job_queue
    job_queue.run_repeating(activity_check, interval=CHECK_INTERVAL, first=0)
    
    application.run_polling()

if __name__ == "__main__":
    main()
