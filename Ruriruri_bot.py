from telegram import Update
from telegram.ext import Updater
from telegram.ext import CommandHandler, CallbackContext
import logging, time, os, json, random, sys

TOKEN = ""
ACTFILEPATH = "c:\coding\Ruriruri_bot\open"
CHAT_ID = ""
# -@otakutto

CLOSED = 0
OPEN = 1
REPORTED = 2

CHECK_INTERVAL = 10

MESSAGE_FILE = "messages.json"
IDX_IMG_BAKA = 0
IDX_IMG_RURI = 1
IDX_MSG_NOW_OPEN = 2
IDX_MSG_NO_REPORT = 3
IDX_MSG_NOW_CLOSED = 4
IDX_MSG_NOT_OPEN = 5
IDX_MSG_ALERT = 6

try:
    messages = json.load(open(MESSAGE_FILE, "rb"))
except FileNotFoundError:
    sys.exit("messages.json missing, quitting.")


def get_random_msg(index):
    i = random.randint(0, len(messages[index]) - 1)
    return messages[index][i]


def send_photo(context: CallbackContext, image_path, msg):
    try:
        context.bot.send_photo(chat_id=CHAT_ID, photo=open(image_path, 'rb'), caption=msg)
        return 1
    except FileNotFoundError:
        return 0


def send_message(context: CallbackContext, msg):
    context.bot.send_message(chat_id=CHAT_ID, text=msg)


def get_state(context: CallbackContext) -> int:
    try:
        return context.bot_data["open"]
    except KeyError:
        set_state(context, CLOSED)
        return CLOSED


def set_state(context: CallbackContext, state):
    try:
        context.bot_data["open"] = state
    except KeyError:
        pass


def verify_chat_id(update: Update):
    return update.effective_chat.id == CHAT_ID


def identity(update: Update, context: CallbackContext ):
    if verify_chat_id:
        send_photo(context, get_random_msg(IDX_IMG_RURI), "I'm Ruri Hoshino, part time club room monitor.")

    
def process_report(update: Update, context: CallbackContext ):
    if verify_chat_id:
        if get_state(context) != CLOSED :
            msg = " ".join(context.args)
            context.bot_data["status"] = msg
            set_state(context, REPORTED)
            send_message(context, "Understood, activity set: " + msg)
        else:
            if not send_photo(context, get_random_msg(IDX_IMG_BAKA), get_random_msg(IDX_MSG_NOT_OPEN)):
                send_message(context, get_random_msg(IDX_MSG_NOT_OPEN))
            

def give_report(update: Update, context: CallbackContext ):
    if verify_chat_id:
        state = get_state(context)
        if  state == REPORTED:
            msg = context.bot_data["status"]
            send_message(context, "Currently: " + msg)
        elif state == OPEN:
            send_message(context, get_random_msg(IDX_MSG_NO_REPORT))
        else:
            send_photo(context, get_random_msg(IDX_IMG_BAKA), get_random_msg(IDX_MSG_NOT_OPEN))


def activity_check(context: CallbackContext):
    
    if os.path.exists(ACTFILEPATH):
        if get_state(context) == CLOSED:
            set_state(context, OPEN)
            send_photo(context, get_random_msg(IDX_IMG_RURI), get_random_msg(IDX_MSG_NOW_OPEN))
    else:
        if get_state(context) != CLOSED:
            context.bot_data["open"] = CLOSED
            send_message(context, get_random_msg(IDX_MSG_NOW_CLOSED))            


def main():

    updater = Updater(token=TOKEN)
    dispatcher = updater.dispatcher
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                        level=logging.INFO)
                        
    identity_handler = CommandHandler(['who'], identity)
    report_handler = CommandHandler(['Ruriruri', 'reporting'], process_report)
    status_handler = CommandHandler(['status', 'report'], give_report)
    
    dispatcher.add_handler(identity_handler)
    dispatcher.add_handler(report_handler)
    dispatcher.add_handler(status_handler)
    
    updater.job_queue.run_repeating(activity_check, interval=CHECK_INTERVAL, first=0)
    
    updater.start_polling()
    while(updater.running):
        time.sleep(10)


if __name__ == "__main__":
    main()
