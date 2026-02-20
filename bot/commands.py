# Slash commands

import time

from discord.ext import commands

from mvp import *


class NotInVoiceChannelError(Exception):
    pass
class AlreadyInVoiceChannelError(Exception):
    pass


class CommandsCog(commands.Cog):
    """Bot commands cog."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
    
    
    @commands.command(name="hello")
    async def hello(self, ctx):
        """Says hello. Test command."""
        await ctx.send(f"Hello, {ctx.author.mention}!")

    
    @commands.command(name='join-vc')
    async def join_vc(self, ctx):
        """Join the voice channel the command user is in"""
        try:
            if ctx.author.voice is None:
                raise NotInVoiceChannelError('User not in a voice chat')
            
            channel = ctx.author.voice.channel
            if ctx.voice_client is None:
                await ctx.send(f"Joined {channel.name}!")
            else:
                raise AlreadyInVoiceChannelError('Bot already connected to a voice channel')
    
        except NotInVoiceChannelError as e:
            await ctx.send(f'Failed to join voice chat: {e}')
        except AlreadyInVoiceChannelError as e:
            await ctx.send(f'{e}')

    @commands.command(name='leave-vc')
    async def leave_vc(self, ctx):
        """Leave voice channel"""
        try:
            if ctx.voice_client is None:
                raise NotInVoiceChannelError("Bot not connected to a voice channel")
                        
            # Get channel name before disconnecting
            channel_name = ctx.voice_client.channel.name if ctx.voice_client.channel else "voice channel"
            await ctx.voice_client.disconnect()
            await ctx.send(f"Left {channel_name}")
        
        except NotInVoiceChannelError as e:
            await ctx.send(f"{e}")    

    @commands.command(name='listen')
    async def listen(self, ctx, arg):
        """Start local runtime listening
        Local device must be in voice channel, not the bot"""
        # TODO identify exception types and make one try many excepts
        if arg is None:
            arg = 5
            ctx.send("Not time given, defaulting to 5 seconds")
        try:
            t = int(arg)
            await start_recording(output_file="../data/output.wav")
            time.sleep(time)
            await stop_recording()
            ctx.send(f"Done listening for {t} seconds")

        except (ValueError, TypeError) as e:
            await ctx.send(f"Error: invalid number of seconds {e}")
        except:
            ctx.send("Failed to start listening")




async def setup(bot: commands.Bot):
    """Setup function called when the cog is loaded."""
    await bot.add_cog(CommandsCog(bot))
