# Audio Receiving Guide for D&D.AI Bot

## Implementation

The bot now uses `discord-ext-voice-recv` to receive audio from Discord voice channels. This library provides a clean API similar to discord.py's audio sending functionality.

### Key Components

1. **VoiceRecvClient**: Custom voice client class that enables audio receiving
2. **DnDAudioSink**: Custom audio sink that processes incoming audio data
3. **Commands**: `start-recording` and `stop-recording` to control audio capture

### Usage

```discord
# Join voice channel (automatically uses VoiceRecvClient)
/join-vc

# Start recording audio
/start-recording

# Stop recording audio
/stop-recording

# Leave voice channel
/leave-vc
```

## Alternative Methods for Audio Receiving

### 1. **discord-ext-voice-recv** (Current Implementation) ✅

**Source**: https://github.com/imayhaveborkedit/discord-ext-voice-recv

**Pros:**

- Clean API mirroring discord.py's AudioSource pattern
- No monkey patching required
- Built-in sinks for common tasks (WAV, FFmpeg, etc.)
- Active development
- Good documentation

**Cons:**

- Still in development (may have breaking changes)
- Requires Python 3.8+

**Best for**: Projects using discord.py that need voice receiving

---

### 2. **Pycord** (discord.py fork)

**Source**: https://guide.pycord.dev/voice/receiving

**Pros:**

- Built-in voice receiving support (no extension needed)
- Similar API to discord.py
- Active community
- Well-documented

**Cons:**

- Requires switching from discord.py to Pycord
- Different library = potential migration issues
- May have different API patterns

**Best for**: New projects or projects willing to migrate from discord.py

**Example**:

```python
# Pycord has built-in voice receiving
voice_client = await channel.connect()
sink = discord.sinks.WaveSink()
voice_client.start_recording(sink)
```

---

### 3. **Interactions.py**

**Source**: https://interactions-py.github.io/interactions.py/Guides/23%20Voice/

**Pros:**

- Modern async/await API
- Built-in voice recording support
- Customizable encoding formats (mp3, wav, etc.)
- Good for slash commands

**Cons:**

- Completely different library from discord.py
- Would require full rewrite
- Smaller community than discord.py

**Best for**: New projects using slash commands primarily

---

### 4. **Manual RTCP Packet Handling** (Advanced)

**Source**: Discord Voice Protocol Documentation

**Pros:**

- Full control over audio processing
- No external dependencies
- Can optimize for specific use cases

**Cons:**

- Very complex implementation
- Requires deep understanding of Discord's voice protocol
- High maintenance burden
- Not recommended unless absolutely necessary

**Best for**: Advanced users needing custom voice protocol handling

---

## Audio Transcription Options

### 1. **Deepgram API** (Real-time)

**Source**: 

- https://developers.deepgram.com/docs/python-sdk-streaming-transcription
- https://deepgram.com/learn/live-transcription-quart

**Pros:**

- Real-time streaming transcription
- High accuracy
- Speaker identification
- Python SDK available

**Cons:**

- Paid service (has free tier)
- Requires API key
- External dependency

**Best for**: Real-time transcription needs

### 2. **SpeechRecognition Library** (via discord-ext-voice-recv extras)

**Source**: Included in discord-ext-voice-recv extras

**Pros:**

- Integrated with discord-ext-voice-recv
- Multiple backend support (Google, Azure, etc.)
- Easy to use

**Cons:**

- Quality varies by backend
- May require API keys for best results
- Not real-time (processes chunks)

**Best for**: Simple transcription needs

**Install**: `pip install discord-ext-voice-recv[extras_speech]`

### 3. **External Services** (ScreenApp, etc.)

**Source**: https://screenapp.io/transcription/discord-voice-chat

**Pros:**

- High accuracy (99% claimed)
- Multi-speaker identification
- No coding required

**Cons:**

- Manual upload process
- Not integrated into bot workflow
- External service dependency

**Best for**: One-off transcriptions or post-session analysis

---

## Recommendation

**For your D&D.AI bot**: **discord-ext-voice-recv** is the best choice because:

1. ✅ Works with your existing discord.py codebase
2. ✅ Clean, familiar API (mirrors AudioSource pattern)
3. ✅ Easy to integrate (just change `connect()` call)
4. ✅ Extensible (can add transcription sinks later)
5. ✅ Active development and community support

**Future Enhancement**: Consider adding the `SpeechRecognitionSink` from the extras for real-time transcription of D&D sessions.

---

## Installation

```bash
pip install discord-ext-voice-recv
# Or with speech recognition extras:
pip install discord-ext-voice-recv[extras_speech]
```

## References

1. **discord-ext-voice-recv**: https://github.com/imayhaveborkedit/discord-ext-voice-recv
2. **Pycord Voice Guide**: https://guide.pycord.dev/voice/receiving
3. **Interactions.py Voice**: https://interactions-py.github.io/interactions.py/Guides/23%20Voice/
4. **Deepgram Streaming**: https://developers.deepgram.com/docs/python-sdk-streaming-transcription
5. **Discord Voice Protocol**: Discord Developer Documentation
