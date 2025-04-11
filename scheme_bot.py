import logging

from telegram import ForceReply, Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters


import random
import string

import os
import anthropic
from pinecone import Pinecone
from dotenv import load_dotenv
import telegramify_markdown
import telegramify_markdown.customize as customize

customize.strict_markdown = False

# Load environment variables from .env file
load_dotenv()

# Initialize Anthropic client
client = anthropic.Anthropic(
    api_key=os.getenv('ANTHROPIC_API_KEY')
)
# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)



def get_ctx(query):
    pc = Pinecone(api_key=os.getenv('PINECONE_API_KEY'))

    # To get the unique host for an index, 
    # see https://docs.pinecone.io/guides/data/target-an-index
    index_name="dense-index"
    dense_index = pc.Index(name=index_name)

    results = dense_index.search(
        namespace="govt_schemes", 
        query={
            "inputs": {"text": query}, 
            "top_k": 3
        },
        fields=[ "chunk_text"]
    )

    # print(results)
    final_ctx=""
    for x in results.result.hits:
        final_ctx+=x['fields']['chunk_text']
    return final_ctx

# msg ="Hi can you get me the name of the scheme  about health insurance in andhra pradesh "
def call_claude(msg):    
    ctx=get_ctx(msg)
    user_input=f"Query: {msg} \n Context: {ctx}"
    message = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=20000,
                temperature=1,
                system="You are Automated bot to help users get information about government schemes in India , you can make use of the context provided by the user to answer the queries. Any information you provide might or might not be accurate, always provide a further reference links ",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": user_input
                            }
                        ]
                    }
                ]
            )
    return message
        




# Define a few command handlers. These usually take the two arguments update and
# context.
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    user = update.effective_user
    await update.message.reply_html(
        rf"Hi {user.mention_html()}!",
        reply_markup=ForceReply(selective=True),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /help is issued."""
    await update.message.reply_text("Help!")


async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Echo the user message."""
    logger.info("Message incoming: %s",str(update.message))

    await process_message(update.message.text,update.message)
    # await update.message.reply_text(update.message.text)




async def process_message(_msg,handler):
    # bot.send_chat_action(chat_id=chat_id, action=telegram.ChatAction.TYPING)


    
    
    response=call_claude(_msg)

    
        
    if response.stop_reason=="end_turn":
        for item in response.content:
            if item.type == "text":
                logger.info(item.text)
                conv_text = telegramify_markdown.markdownify(item.text)
                await handler.reply_text(conv_text,parse_mode="MarkdownV2")
    if response.stop_reason=="max_tokens":        
        await handler.reply_text("Sorry this is too big of a message to process")
        
        
    
    
        
                
    

# "create a sample ui webspage using html and jquery to say hello world on click of a button and host the files in cloud"


def get_random_str(N):    
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=N))

def main() -> None:
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv('tg_token')).build()

    # on different commands - answer in Telegram
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))

    # on non command i.e message - echo the message on Telegram
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
