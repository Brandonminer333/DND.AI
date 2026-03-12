# Discord wiring

from discord.ext import commands as cmds

from bot import commands as bot_cmds


class DiscordBot(cmds.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        """Called when the bot is setting up, before connecting to Discord."""
        # Load all cogs (commands)
        await bot_cmds.setup(self)

    async def on_ready(self):
        print(f"Logged in as {self.user}")
