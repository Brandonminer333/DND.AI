import os
import logging

import discord
from dotenv import load_dotenv

from bot.client import Bot as DiscordBot


# Load environment variables
load_dotenv()
token = os.getenv("DISCORD_TOKEN")


# Logging
handler = logging.FileHandler(
    filename="discord.log", encoding="utf-8", mode="w")
logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# Bot permissions
intents = discord.Intents.default()
intents.message_content = True


bot = DiscordBot(command_prefix="/", intents=intents)
bot.run(token, log_handler=handler, log_level=logging.DEBUG)
