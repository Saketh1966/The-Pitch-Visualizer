import os
import re
import base64
import httpx
import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import json

app = FastAPI(title="Pitch Visualizer")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


def segment_text(text: str) -> list[str]:
    """Split text into logical scenes (sentence-level segmentation)."""
    # Split on sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    # Filter empty and merge very short ones
    segments = []
    buffer = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if buffer and len(buffer.split()) < 8:
            buffer += " " + s
        else:
            if buffer:
                segments.append(buffer)
            buffer = s
    if buffer:
        segments.append(buffer)
    # Ensure at least 3 segments by splitting longer ones if needed
    if len(segments) < 3 and len(segments) > 0:
        # try to split on commas or semicolons
        expanded = []
        for seg in segments:
            parts = re.split(r'(?<=[,;])\s+', seg)
            expanded.extend([p.strip() for p in parts if p.strip()])
        if len(expanded) >= 3:
            segments = expanded
    return segments[:8]  # cap at 8 panels


async def enhance_prompt_with_claude(segment: str, style: str, panel_index: int, total_panels: int) -> str:
    """Use Claude to generate a rich visual prompt from a text segment."""
    system_prompt = (
        "You are a cinematic art director and visual prompt engineer. "
        "Given a sentence from a narrative, craft a detailed, vivid image generation prompt. "
        "Focus on visual composition, lighting, mood, and specific details. "
        "Your output must be ONLY the prompt text — no explanation, no quotes, no preamble. "
        "Keep it under 120 words. Always end with style keywords appropriate to the requested style."
    )
    user_msg = (
        f"Panel {panel_index+1} of {total_panels}.\n"
        f"Narrative segment: \"{segment}\"\n"
        f"Visual style requested: {style}\n\n"
        "Create a detailed, visually imaginative image generation prompt for this panel. "
        "Make it specific, atmospheric, and cinematically composed."
    )

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 200,
                "system": system_prompt,
                "messages": [{"role": "user", "content": user_msg}],
            }
        )
        data = resp.json()
        enhanced = data["content"][0]["text"].strip()
        return enhanced


async def generate_image(prompt: str) -> str:
    """Generate an image using DALL-E 3 and return base64 data URL."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/images/generations",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "dall-e-3",
                "prompt": prompt,
                "n": 1,
                "size": "1792x1024",
                "response_format": "b64_json",
            }
        )
        data = resp.json()
        if "data" in data and data["data"]:
            b64 = data["data"][0]["b64_json"]
            return f"data:image/png;base64,{b64}"
        raise ValueError(f"Image generation failed: {data.get('error', {}).get('message', 'Unknown error')}")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate_storyboard(request: Request):
    body = await request.json()
    text = body.get("text", "").strip()
    style = body.get("style", "cinematic photorealism")

    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    if not ANTHROPIC_API_KEY:
        return JSONResponse({"error": "ANTHROPIC_API_KEY not set"}, status_code=500)
    if not OPENAI_API_KEY:
        return JSONResponse({"error": "OPENAI_API_KEY not set"}, status_code=500)

    segments = segment_text(text)
    if not segments:
        return JSONResponse({"error": "Could not segment text into scenes"}, status_code=400)

    async def stream_panels():
        for i, segment in enumerate(segments):
            try:
                # Step 1: Enhance prompt
                yield json.dumps({
                    "type": "status",
                    "panel": i,
                    "total": len(segments),
                    "message": f"Crafting visual prompt for panel {i+1}..."
                }) + "\n"

                enhanced_prompt = await enhance_prompt_with_claude(segment, style, i, len(segments))

                yield json.dumps({
                    "type": "prompt_ready",
                    "panel": i,
                    "segment": segment,
                    "enhanced_prompt": enhanced_prompt
                }) + "\n"

                # Step 2: Generate image
                yield json.dumps({
                    "type": "status",
                    "panel": i,
                    "total": len(segments),
                    "message": f"Generating image for panel {i+1}..."
                }) + "\n"

                image_data = await generate_image(enhanced_prompt)

                yield json.dumps({
                    "type": "panel_ready",
                    "panel": i,
                    "total": len(segments),
                    "segment": segment,
                    "enhanced_prompt": enhanced_prompt,
                    "image": image_data
                }) + "\n"

            except Exception as e:
                yield json.dumps({
                    "type": "error",
                    "panel": i,
                    "message": str(e)
                }) + "\n"

        yield json.dumps({"type": "done", "total": len(segments)}) + "\n"

    return StreamingResponse(stream_panels(), media_type="application/x-ndjson")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
