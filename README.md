# Updates

Voice-to-Readwise capture tool. Record spoken insights while reading or listening, and save them directly to your Readwise library.

## What it does

1. **Record** - Speak your insight ("From Thinking Fast and Slow, the planning fallacy means we underestimate how long things take")
2. **Transcribe** - Audio is transcribed using ElevenLabs
3. **Parse** - Claude extracts the book/podcast title, author, and your insight
4. **Save** - Highlight is submitted to Readwise

Your words are preserved exactly as you said them—only punctuation is added.

## Setup

### 1. Install dependencies

```bash
# Clone the repo
git clone https://github.com/olivernormand/updates.git
cd updates

# Install with uv (recommended)
uv sync
```

### 2. Get API keys

You'll need three API keys:

| Service | Get your key | What it's for |
|---------|--------------|---------------|
| **Readwise** | [readwise.io/access_token](https://readwise.io/access_token) | Saving highlights |
| **ElevenLabs** | [elevenlabs.io](https://elevenlabs.io) → Profile → API Keys | Speech-to-text |
| **Anthropic** | [console.anthropic.com](https://console.anthropic.com) → API Keys | Parsing transcripts |

### 3. Create `.env` file

```bash
cp .env.example .env
```

Edit `.env` with your keys:

```
ELEVENLABS_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
READWISE_ACCESS_TOKEN=your_token_here
```

## Usage

### Interactive mode (recommended)

```bash
uv run updates
```

This starts the server and enters interactive recording mode:

```
Updates - Voice to Readwise

Starting server...
Server ready.

Press [Enter] to start recording, [Enter] again to stop.
Press [Ctrl+C] to exit.

Ready. Press [Enter] to record...
```

Press Enter, speak your insight, press Enter again. Your highlight is transcribed, parsed, and saved to Readwise.

### With context

If you're reading a specific book, set context first:

```bash
uv run updates start -c "Reading: Thinking, Fast and Slow by Daniel Kahneman"
```

This helps the parser when you don't explicitly mention the source.

### Other commands

```bash
uv run updates context "Reading: Atomic Habits"  # Set context
uv run updates context                            # View current context
uv run updates recent                             # See recent submissions
uv run updates health                             # Check API connectivity
uv run updates serve                              # Run server only (foreground)
```

## How it works

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Record    │ ──▶ │ Transcribe  │ ──▶ │    Parse    │ ──▶ │   Submit    │
│   (local)   │     │ (ElevenLabs)│     │  (Claude)   │     │ (Readwise)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
```

The CLI records audio locally, then sends it to a local FastAPI server that orchestrates the pipeline. Your audio is sent to ElevenLabs for transcription, the transcript is parsed by Claude to extract metadata (title, author, category), and the structured highlight is submitted to Readwise.

## Example

**You say:**
> "Update from Thinking Fast and Slow. The planning fallacy means we systematically underestimate how long things take because we focus on the specific case rather than base rates."

**Saved to Readwise:**
- **Title:** Thinking, Fast and Slow
- **Author:** Daniel Kahneman
- **Text:** The planning fallacy means we systematically underestimate how long things take because we focus on the specific case rather than base rates.
- **Category:** books
