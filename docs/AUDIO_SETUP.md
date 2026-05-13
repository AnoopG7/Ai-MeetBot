# Audio Setup Guide (TTS & STT)

## Overview

This project uses **Text-to-Speech (TTS)** and **Speech-to-Text (STT)** for voice interactions. This guide explains the setup requirements and troubleshooting steps.

## Required Dependencies

### FFmpeg (Required for TTS)

FFmpeg is **required** to synthesize audio using EdgeTTS. It converts audio formats from edge-tts to PCM format compatible with LiveKit.

#### Installation

**macOS:**
```bash
brew install ffmpeg
```

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y ffmpeg
```

**Linux (Fedora/RHEL):**
```bash
sudo dnf install ffmpeg
```

**Windows:**
Download from: https://ffmpeg.org/download.html or use:
```bash
choco install ffmpeg  # if using Chocolatey
```

**Verify Installation:**
```bash
ffmpeg -version
```

## Configuration

### Environment Variables

Set these in your `.env` file or environment:

#### TTS Configuration
```bash
# TTS Provider (options: "edge-tts", "cartesia", "elevenlabs")
# Default: "edge-tts" (free, requires ffmpeg)
TTS_PROVIDER=edge-tts

# Only needed if using Cartesia (paid)
# CARTESIA_API_KEY=your_api_key_here
# CARTESIA_VOICE_ID=6f6a6c6c-6b6a-4e6f-8e6a-6c6c6b6a4e6f
```

#### STT Configuration
```bash
# STT Provider (options: "faster-whisper", "deepgram", "whisper")
# Default: "faster-whisper" (free, local)
STT_PROVIDER=faster-whisper

# Only needed if using Deepgram (paid)
# DEEPGRAM_API_KEY=your_api_key_here

# Only needed if using Groq Whisper (free tier available)
# GROQ_API_KEY=your_api_key_here
# GROQ_BASE_URL=https://api.groq.com/openai/v1
```

## Troubleshooting

### Issue: "TTS synthesis failed" or No Audio Output

**Causes:**
1. FFmpeg not installed
2. FFmpeg not in PATH
3. EdgeTTS API rate limit or network issue
4. Incorrect TTS provider configuration

**Solutions:**

1. **Check FFmpeg Installation:**
   ```bash
   which ffmpeg  # macOS/Linux
   # or
   where ffmpeg  # Windows
   ```
   
   If not found, install using commands above.

2. **Verify FFmpeg Works:**
   ```bash
   echo "test" | ffmpeg -i pipe:0 -f s16le -ar 24000 -ac 1 pipe:1 > /dev/null 2>&1 && echo "OK" || echo "FAILED"
   ```

3. **Check TTS Configuration:**
   ```bash
   # Look for log messages:
   # - "using EdgeTTS" = correct provider set
   # - "ffmpeg not found in system PATH" = install ffmpeg
   # - "CARTESIA_API_KEY not set" = API key missing (if using Cartesia)
   ```

4. **Enable Debug Logging:**
   ```bash
   LOG_LEVEL=DEBUG  # in .env or environment
   ```

5. **Test TTS Directly:**
   Create a test file `test_tts.py`:
   ```python
   import asyncio
   from advisor.agent.tts_edge import EdgeTTS
   
   async def test():
       tts = EdgeTTS()
       stream = tts.synthesize("Hello, this is a test")
       async for _ in stream:
           pass
   
   asyncio.run(test())
   ```

### Issue: "No STT available" or Transcription Not Working

**Causes:**
1. No STT provider configured
2. API key missing for paid providers
3. Faster-Whisper model not downloaded

**Solutions:**

1. **For Faster-Whisper (local, free):**
   - First run will download the model (~141MB for base)
   - Check internet connection and disk space
   - Models are cached in `~/.cache/huggingface/`

2. **For Deepgram (paid):**
   ```bash
   DEEPGRAM_API_KEY=your_key_here STT_PROVIDER=deepgram
   ```

3. **Check STT Status:**
   Look for logs on startup:
   - "using faster-whisper STT" = Correct
   - "no STT available" = Configuration issue

### Issue: Docker Build Fails with Audio Errors

FFmpeg is already included in the Docker image (`Dockerfile`). If issues persist:

1. Rebuild the image:
   ```bash
   make docker-build
   ```

2. Check the Dockerfile has FFmpeg:
   ```dockerfile
   RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg
   ```

## Providers Comparison

| Provider | Type | Cost | Setup | Performance |
|----------|------|------|-------|-------------|
| **EdgeTTS** | TTS | Free | Local (needs ffmpeg) | Fast, good quality |
| **Cartesia** | TTS | Paid | API key | Excellent quality, streaming |
| **Faster-Whisper** | STT | Free | Local (first run downloads model) | Fast, accurate |
| **Deepgram** | STT | Paid | API key | Very accurate, streaming |
| **Groq Whisper** | STT | Free tier | API key | Good accuracy, free tier available |

## Development Setup (Complete)

```bash
# 1. Clone and setup
git clone <repo>
cd AI-MeetBot

# 2. Install FFmpeg
brew install ffmpeg  # macOS
# or
sudo apt-get install ffmpeg  # Linux

# 3. Setup backend
cd backend
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e .

# 4. Create .env with defaults
cp .env.example .env  # if exists
# or manually add:
# TTS_PROVIDER=edge-tts
# STT_PROVIDER=faster-whisper
# LLM_PROVIDER=groq
# GROQ_API_KEY=your_key  # get from https://console.groq.com

# 5. Start services
cd ..
make docker-up

# 6. Run agent (in new terminal)
make dev-agent

# 7. Run API (in new terminal)
make dev-api
```

## Performance Tips

1. **TTS:** EdgeTTS is free and fast but requires ffmpeg. For high-volume production, consider Cartesia.
2. **STT:** Faster-Whisper runs locally. For streaming use cases, consider Deepgram.
3. **LLM:** Groq free tier is fast. For production, use OpenAI or self-hosted Ollama.

## Logging

Enable detailed logs to diagnose audio issues:

```bash
# Terminal
LOG_LEVEL=DEBUG make dev-agent

# or in .env
LOG_LEVEL=DEBUG
```

Look for log messages containing:
- `edge-tts streaming complete`
- `tts synthesis complete`
- `faster-whisper model loaded`
- `synthesizing speech`

## References

- [EdgeTTS Documentation](https://github.com/rany2/edge-tts)
- [Faster-Whisper](https://github.com/SYSTRAN/faster-whisper)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [LiveKit Agents](https://docs.livekit.io/agents/)
