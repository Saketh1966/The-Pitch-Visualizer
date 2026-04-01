# 🎬 Pitch Visualizer

**From words to storyboard — instantly.**

Pitch Visualizer ingests a block of narrative text, uses Claude AI to craft richly detailed visual prompts for each scene, and generates a cinematic multi-panel storyboard using DALL-E 3. The result is a beautiful, scrollable storyboard presented live in your browser as each panel renders.

---

## Features

- **Intelligent Narrative Segmentation** — Splits your text into logical scenes using punctuation-aware sentence parsing
- **LLM-Powered Prompt Engineering** — Claude (claude-sonnet-4) transforms each plain sentence into a richly atmospheric, cinematically composed image prompt
- **DALL-E 3 Image Generation** — Each enhanced prompt produces a 1792×1024 image for widescreen storyboard panels
- **Live Streaming UI** — Panels appear one by one as they generate, with real-time status updates
- **6 Visual Styles** — Choose from Cinematic, Concept Art, Editorial, Watercolor, Noir, or Sci-Fi
- **Prompt Transparency** — Each panel shows both the original narrative segment and the AI-engineered visual prompt

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Python 3.11+ |
| LLM (Prompt Engineering) | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Image Generation | OpenAI DALL-E 3 |
| Streaming | NDJSON via `StreamingResponse` |
| Frontend | Vanilla HTML/CSS/JS (zero dependencies) |
| Fonts | Cormorant Garamond + DM Mono (Google Fonts) |

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/pitch-visualizer.git
cd pitch-visualizer
```

### 2. Create a virtual environment

```bash
python -m venv venv
source venv/bin/activate        # macOS/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set API Keys

You need two API keys:

| Key | Where to get it |
|---|---|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |

**macOS / Linux:**
```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
```

**Windows (PowerShell):**
```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."
$env:OPENAI_API_KEY = "sk-..."
```

Alternatively, create a `.env` file and load it (requires `python-dotenv`):
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

### 5. Run the server

```bash
python main.py
```

Open your browser at: **http://localhost:8000**

---

## Usage

1. Paste a narrative (3–8 sentences) into the text area — a customer story, product pitch, or success story works great
2. Select a visual style
3. Click **Generate Storyboard** (or press `Ctrl+Enter`)
4. Watch as each panel renders live — prompt engineering then image generation happens sequentially per panel

### Example Input

> Our client was drowning in manual data entry, spending 40 hours a week on tasks that added no value. They implemented our AI automation platform in just two weeks. Within a month, their team had reclaimed those hours for strategic work. Revenue grew 23% as a result. Today they consider us their most critical technology partner.

---

## Design Choices

### Narrative Segmentation
Text is split on sentence boundaries (`.`, `!`, `?`) with a buffer mechanism that merges very short fragments (< 8 words) into the preceding sentence for more coherent scene units. Output is capped at 8 panels to keep generation time reasonable.

### Prompt Engineering Strategy
Each segment is sent to Claude with:
- **Context**: Panel index and total count (so Claude understands narrative arc)
- **Style**: The user-selected visual style appended as genre/aesthetic keywords  
- **Instructions**: Directives for visual composition, lighting, mood, and specificity

Claude transforms e.g. *"They implemented our platform in two weeks"* into something like:
> *"A focused team in a glass-walled conference room, laptops open, pointing at deployment dashboards on a large monitor. Warm overhead lighting. Digital concept art, vibrant colors, highly detailed illustration."*

### Streaming Architecture
The backend uses FastAPI's `StreamingResponse` with NDJSON (newline-delimited JSON). Each panel emits 3 events: `status` → `prompt_ready` → `panel_ready`. This allows the frontend to show all panel placeholders upfront and fill them in progressively, giving a satisfying live-render experience.

### Visual Consistency
All prompts in a session append the same style string (e.g., *"cinematic photorealism, 35mm film, dramatic lighting"*) to anchor visual coherence across panels.

---

## API Reference

### `POST /generate`

**Request body:**
```json
{
  "text": "Your narrative here...",
  "style": "cinematic photorealism, 35mm film, dramatic lighting"
}
```

**Response:** NDJSON stream of events:

| Event type | Fields |
|---|---|
| `status` | `panel`, `total`, `message` |
| `prompt_ready` | `panel`, `segment`, `enhanced_prompt` |
| `panel_ready` | `panel`, `total`, `segment`, `enhanced_prompt`, `image` (data URL) |
| `error` | `panel`, `message` |
| `done` | `total` |

---

## Cost Estimate

Per storyboard (5 panels):
- Claude API: ~5 × 200 tokens out ≈ $0.015
- DALL-E 3 (1792×1024): ~5 × $0.08 = **$0.40**

Total: ~**$0.42 per storyboard**

---

## License

MIT
