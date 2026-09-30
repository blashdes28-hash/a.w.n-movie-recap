import asyncio
import edge_tts
import io
import re
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Any

VOICES = [
    {
        "id": "my-MM-ThihaNeural",
        "name": "Thiha (သီဟ)",
        "gender": "Male",
        "locale": "my-MM",
        "description": "Burmese Male - Crisp, dramatic narration voice popular for movie recaps",
        "is_default": True
    },
    {
        "id": "my-MM-NilarNeural",
        "name": "Nilar (နီလာ)",
        "gender": "Female",
        "locale": "my-MM",
        "description": "Burmese Female - Warm, engaging storytelling voice",
        "is_default": False
    },
    {
        "id": "en-US-ChristopherNeural",
        "name": "Christopher (US Male)",
        "gender": "Male",
        "locale": "en-US",
        "description": "Deep cinematic movie recap voice (English)",
        "is_default": False
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny (US Female)",
        "gender": "Female",
        "locale": "en-US",
        "description": "Clear documentary & recap style (English)",
        "is_default": False
    }
]

def format_srt_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d},{millis:03d}"

def format_vtt_time(seconds: float) -> str:
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        millis = 999
    return f"{hrs:02d}:{mins:02d}:{secs:02d}.{millis:03d}"

def split_into_recap_lines(text: str) -> List[str]:
    """
    Split text into natural storytelling lines for movie recap subtitles.
    Preserves Burmese sentence structures and punctuation.
    """
    lines = []
    # If text already has newlines from the script writer, use them
    raw_lines = [l.strip() for l in text.split("\n") if l.strip()]
    for raw in raw_lines:
        # Split by Burmese fullstop '။' if line is too long (> 60 chars)
        if len(raw) > 60 and "။" in raw:
            parts = [p.strip() for p in raw.split("။") if p.strip()]
            for p in parts:
                lines.append(p + "။")
        else:
            lines.append(raw)
            
    # Fallback if no lines produced
    if not lines and text.strip():
        lines = [text.strip()]
    return lines

async def generate_narration(
    text: str,
    voice: str = "my-MM-ThihaNeural",
    rate: str = "+0%",
    pitch: str = "+0Hz",
    output_dir: Path = None
) -> Dict[str, Any]:
    """
    Generate audio and synchronized subtitles from text using Edge TTS.
    """
    if not voice:
        voice = "my-MM-ThihaNeural"
        
    script_lines = split_into_recap_lines(text)
    combined_audio = io.BytesIO()
    subtitles = []
    current_time = 0.0
    
    for idx, line in enumerate(script_lines, start=1):
        if not line:
            continue
        try:
            comm = edge_tts.Communicate(line, voice, rate=rate, pitch=pitch)
            line_audio = io.BytesIO()
            line_duration_ticks = 0
            
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    line_audio.write(chunk["data"])
                elif chunk["type"] == "SentenceBoundary":
                    line_duration_ticks = max(line_duration_ticks, chunk["offset"] + chunk["duration"])
            
            chunk_data = line_audio.getvalue()
            if not chunk_data:
                continue
                
            combined_audio.write(chunk_data)
            
            # Duration in seconds (1 tick = 100ns = 1e-7s)
            # If tick is available, calculate from it; otherwise estimate from mp3 byte size (approx 32KB/sec for 128kbps)
            if line_duration_ticks > 0:
                duration_sec = line_duration_ticks / 10000000.0
            else:
                duration_sec = max(0.8, len(chunk_data) / 32000.0)
                
            start_time = current_time
            end_time = current_time + duration_sec
            current_time = end_time + 0.15  # Natural short breathing pause between recap scenes
            
            subtitles.append({
                "index": idx,
                "start": start_time,
                "end": end_time,
                "start_str": format_srt_time(start_time),
                "end_str": format_srt_time(end_time),
                "vtt_start": format_vtt_time(start_time),
                "vtt_end": format_vtt_time(end_time),
                "text": line
            })
        except Exception as e:
            print(f"Error synthesizing line {idx}: {e}")
            
    audio_bytes = combined_audio.getvalue()
    total_duration = current_time
    
    # Generate SRT and VTT representations
    srt_lines = []
    vtt_lines = ["WEBVTT\n"]
    for s in subtitles:
        srt_lines.append(f"{s['index']}\n{s['start_str']} --> {s['end_str']}\n{s['text']}\n")
        vtt_lines.append(f"{s['index']}\n{s['vtt_start']} --> {s['vtt_end']}\n{s['text']}\n")
        
    srt_content = "\n".join(srt_lines)
    vtt_content = "\n".join(vtt_lines)
    
    # Save files if output_dir is provided
    audio_filename = None
    srt_filename = None
    vtt_filename = None
    
    if output_dir:
        uid = uuid.uuid4().hex[:10]
        audio_filename = f"narration_{uid}.mp3"
        srt_filename = f"subtitles_{uid}.srt"
        vtt_filename = f"subtitles_{uid}.vtt"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_dir / audio_filename, "wb") as f:
            f.write(audio_bytes)
        with open(output_dir / srt_filename, "w", encoding="utf-8") as f:
            f.write(srt_content)
        with open(output_dir / vtt_filename, "w", encoding="utf-8") as f:
            f.write(vtt_content)
            
    return {
        "audio_bytes": audio_bytes,
        "audio_size": len(audio_bytes),
        "total_duration": total_duration,
        "duration_formatted": f"{int(total_duration // 60):02d}:{int(total_duration % 60):02d}",
        "subtitles": subtitles,
        "srt_content": srt_content,
        "vtt_content": vtt_content,
        "audio_file": audio_filename,
        "srt_file": srt_filename,
        "vtt_file": vtt_filename
    }

async def generate_quick_sample(text: str, voice: str = "my-MM-ThihaNeural") -> bytes:
    """Generate quick speech sample for audio test/audition."""
    comm = edge_tts.Communicate(text, voice)
    audio = bytearray()
    async for chunk in comm.stream():
        if chunk["type"] == "audio":
            audio.extend(chunk["data"])
    return bytes(audio)
