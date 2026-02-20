# Discord wiring

from discord.ext import commands
from bot import commands as bot_commands


class Bot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        """Called when the bot is setting up, before connecting to Discord."""
        # Load all cogs (commands)
        await bot_commands.setup(self)

    async def on_ready(self):
        print(f"Logged in as {self.user}")

    