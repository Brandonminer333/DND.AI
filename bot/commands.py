# Slash commands
import os

import discord
from discord.ext import commands
from discord.sinks import WaveSink


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
                raise AlreadyInVoiceChannelError(
                    'Bot already connected to a voice channel')

        except NotInVoiceChannelError as e:
            await ctx.send(f'Failed to join voice chat: {e}')
        except AlreadyInVoiceChannelError as e:
            await ctx.send(f'{e}')

    @commands.command(name='leave-vc')
    async def leave_vc(self, ctx):
        """Leave voice channel"""
        try:
            if ctx.voice_client is None:
                raise NotInVoiceChannelError(
                    "Bot not connected to a voice channel")

            # Get channel name before disconnecting
            channel_name = ctx.voice_client.channel.name if ctx.voice_client.channel else "voice channel"
            await ctx.voice_client.disconnect()
            await ctx.send(f"Left {channel_name}")

        except NotInVoiceChannelError as e:
            await ctx.send(f"{e}")

    # Called when recording finishes
    async def finished_callback(self, sink: WaveSink, channel: discord.TextChannel):
        recorded_users = []
        audio_files = []

        for user_id, audio in sink.audio_data.items():
            filename = f"recordings/{user_id}.wav"
            os.makedirs("recordings", exist_ok=True)

            with open(filename, "wb") as f:
                f.write(audio.file.read())

            user = await self.fetch_user(user_id)
            recorded_users.append(user.mention)
            audio_files.append(discord.File(
                filename, filename=f"{user.name}.wav"))

        await channel.send(
            f"Finished recording: {', '.join(recorded_users)}",
            files=audio_files
        )

    @commands.command(name="record", description="Start recording the voice channel")
    async def record(self, ctx):
        if not ctx.author.voice:
            return await ctx.send("You must be in a voice channel!")

        vc = await ctx.author.voice.channel.connect()
        vc.start_recording(
            WaveSink(),
            self.finished_callback,
            ctx.channel  # text channel to send results to
        )
        await ctx.send("🔴 Recording started!")

    @commands.command(name="stop", description="Stop recording")
    async def stop(self, ctx):
        if not ctx.voice_client:
            return await ctx.send("I'm not recording anything!")

        ctx.voice_client.stop_recording()  # triggers finished_callback
        await ctx.send("⏹️ Recording stopped, processing audio...")


async def setup(bot: commands.Bot):
    """Setup function called when the cog is loaded."""
    await bot.add_cog(CommandsCog(bot))
