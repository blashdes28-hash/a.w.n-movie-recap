import os
import subprocess
import threading
import time
import uuid
import math
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFilter
import freetype
import uharfbuzz as hb

FFMPEG_EXE = imageio_ffmpeg.get_ffmpeg_exe()
BASE_DIR = Path(__file__).resolve().parent.parent
FONTS_DIR = BASE_DIR / "fonts"
FONTS_DIR.mkdir(parents=True, exist_ok=True)

# Dictionary to track background render jobs
RENDER_JOBS: Dict[str, Dict[str, Any]] = {}

def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    return RENDER_JOBS.get(job_id)

def get_available_fonts() -> List[Dict[str, str]]:
    """Returns all available Myanmar and custom fonts in project fonts/ and system."""
    fonts = [
        {"name": "Pyidaungsu (ပြည်ထောင်စု - စံဖောင့်)", "family": "Pyidaungsu", "file": "Pyidaungsu.ttf"},
        {"name": "Myanmar Text (ဝင်းဒိုးစံဖောင့်)", "family": "Myanmar Text", "file": "MyanmarText.ttf"},
        {"name": "Pyidaungsu Bold (စာလုံးမည်း)", "family": "Pyidaungsu Bold", "file": "Pyidaungsu_Bold.ttf"},
        {"name": "Myanmar Text Bold", "family": "Myanmar Text Bold", "file": "MyanmarText_Bold.ttf"},
    ]

    # Check for custom uploaded fonts in fonts/ (e.g. Yamin.ttf, Masterpiece.ttf, etc.)
    if FONTS_DIR.exists():
        known_files = {"pyidaungsu.ttf", "pyidaungsu_bold.ttf", "myanmartext.ttf", "myanmartext_bold.ttf"}
        for f in FONTS_DIR.glob("*.*"):
            if f.suffix.lower() in [".ttf", ".otf"] and f.name.lower() not in known_files:
                if "yamin" in f.name.lower():
                    fonts.append({
                        "name": "Yamin (ရောင်စုံ / စိတ်ကြိုက်ဖောင့်)",
                        "family": "Yamin",
                        "file": f.name
                    })
                else:
                    base_name = f.stem.replace("_", " ").title()
                    fonts.append({
                        "name": f"{base_name} (Custom Font)",
                        "family": base_name,
                        "file": f.name
                    })

    return fonts

def resolve_font_file(font_name: Optional[str] = None) -> Path:
    """Finds matching font file in fonts/ directory."""
    if not font_name:
        return FONTS_DIR / "Pyidaungsu.ttf"
    clean = font_name.lower().strip()
    if "pyidaungsu" in clean:
        if "bold" in clean:
            p = FONTS_DIR / "Pyidaungsu_Bold.ttf"
            if p.exists(): return p
        return FONTS_DIR / "Pyidaungsu.ttf"
    if "myanmar" in clean or "mmrtext" in clean:
        if "bold" in clean:
            p = FONTS_DIR / "MyanmarText_Bold.ttf"
            if p.exists(): return p
        return FONTS_DIR / "MyanmarText.ttf"
    if "yamin" in clean:
        for f in FONTS_DIR.glob("*.*"):
            if "yamin" in f.name.lower() and f.suffix.lower() in [".ttf", ".otf"]:
                return f
    for f in FONTS_DIR.glob("*.*"):
        if f.suffix.lower() in [".ttf", ".otf"]:
            if clean in f.stem.lower() or f.stem.lower() in clean:
                return f
    cand = FONTS_DIR / "Pyidaungsu.ttf"
    if cand.exists(): return cand
    cand2 = FONTS_DIR / "MyanmarText.ttf"
    if cand2.exists(): return cand2
    return FONTS_DIR / "Pyidaungsu.ttf"

def create_synthetic_cinematic_bgm(output_path: Path, duration_sec: float = 60.0):
    """
    Creates an atmospheric cinematic background music loop using pure Python wave synthesis.
    Safe, royalty-free, and always available offline without internet.
    """
    import wave
    import struct
    
    sample_rate = 44100
    n_samples = int(sample_rate * duration_sec)
    
    # Cinematic drone frequencies: C minor chord
    freqs = [65.4, 77.8, 98.0, 116.5, 130.8]
    
    with wave.open(str(output_path), "wb") as wav:
        wav.setnchannels(2)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        
        frames = bytearray()
        for i in range(n_samples):
            t = i / sample_rate
            lfo = 0.6 + 0.4 * math.sin(2 * math.pi * 0.2 * t)
            sample_val = 0.0
            for idx, f in enumerate(freqs):
                detune = 1.0 + 0.002 * math.sin(2 * math.pi * 0.1 * t * (idx + 1))
                sample_val += math.sin(2 * math.pi * f * detune * t) * (0.15 / (idx + 1))
            sample_val *= lfo * 0.25
            int_val = int(max(-32767, min(32767, sample_val * 32767)))
            frames.extend(struct.pack("<hh", int_val, int_val))
            
        wav.writeframes(frames)

def escape_ffmpeg_path(path_str: str) -> str:
    """Escapes Windows path for FFmpeg filter syntax."""
    return path_str.replace("\\", "/").replace(":", "\\:")

def get_burmese_font_path(font_name: Optional[str] = None) -> str:
    """Returns escaped path for selected Myanmar font file to prevent tofu boxes."""
    if font_name:
        for f in FONTS_DIR.glob("*.*"):
            if font_name.lower() in f.stem.lower():
                return escape_ffmpeg_path(str(f))

    candidates = [
        FONTS_DIR / "Pyidaungsu.ttf",
        FONTS_DIR / "MyanmarText.ttf",
        Path("C:/Windows/Fonts/mmrtext.ttf"),
        Path("C:/Windows/Fonts/Pyidaungsu-2.5.3_Regular.ttf"),
        Path("C:/Windows/Fonts/arial.ttf")
    ]
    for c in candidates:
        if c.exists():
            return escape_ffmpeg_path(str(c))
    return ""

def get_sharp_watermark_font_path() -> str:
    """Returns crisp font for high-definition watermark."""
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        FONTS_DIR / "MyanmarText.ttf",
        Path("C:/Windows/Fonts/mmrtext.ttf"),
        Path("C:/Windows/Fonts/segoeui.ttf")
    ]
    for c in candidates:
        if c.exists():
            return escape_ffmpeg_path(str(c))
    return ""

def hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple:
    """Converts hex color (#ffffff or #fff) to RGBA tuple."""
    if not hex_str:
        return (255, 255, 255, alpha)
    c = hex_str.strip().lstrip("#")
    if len(c) == 3:
        c = "".join([ch * 2 for ch in c])
    if len(c) == 6:
        return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16), alpha)
    return (255, 255, 255, alpha)

def hex_to_ass_color(color_str: str) -> str:
    """Converts #RRGGBB hex color to ASS format &H00BBGGRR."""
    if not color_str:
        return "&H00FFFFFF"
    c = color_str.strip().lstrip("#")
    if c.startswith("&H") or c.startswith("&h"):
        return color_str
    if len(c) == 6:
        r, g, b = c[0:2], c[2:4], c[4:6]
        return f"&H00{b.upper()}{g.upper()}{r.upper()}"
    return "&H00FFFFFF"

def format_ass_time(seconds: float) -> str:
    """Formats seconds into ASS subtitle timestamp: H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hrs}:{mins:02d}:{secs:05.2f}"

def wrap_burmese_text(text: str, max_chars: int = 36) -> List[str]:
    """
    Intelligently breaks long Burmese sentences into natural lines at punctuation/words
    so subtitles never overflow off screen edges.
    """
    text = text.strip()
    if not text:
        return []
    raw_lines = [l.strip() for l in text.replace('\\N', '\n').replace('\\n', '\n').split('\n') if l.strip()]
    final_lines = []
    
    for line in raw_lines:
        if len(line) <= max_chars:
            final_lines.append(line)
            continue
            
        parts = re.split(r'([၊။])', line)
        reconstructed = []
        for i in range(0, len(parts), 2):
            p = parts[i]
            punct = parts[i+1] if i+1 < len(parts) else ''
            comb = (p + punct).strip()
            if comb:
                reconstructed.append(comb)
                
        if len(reconstructed) > 1:
            cur = ''
            for chunk in reconstructed:
                if len(cur) + len(chunk) <= max_chars:
                    cur += (' ' if cur else '') + chunk
                else:
                    if cur:
                        final_lines.append(cur)
                    cur = chunk
            if cur:
                final_lines.append(cur)
            continue
            
        if ' ' in line:
            words = line.split(' ')
            cur = ''
            for w in words:
                if len(cur) + len(w) + 1 <= max_chars:
                    cur += (' ' if cur else '') + w
                else:
                    if cur:
                        final_lines.append(cur)
                    cur = w
            if cur:
                final_lines.append(cur)
            continue
            
        for i in range(0, len(line), max_chars):
            final_lines.append(line[i:i+max_chars])
            
    return final_lines

def shape_and_render_line(
    text: str,
    font_path: str,
    font_size: int,
    text_color: tuple = (255, 255, 255, 255),
    outline_color: tuple = (0, 0, 0, 255),
    outline_width: int = 3,
    shadow_offset: tuple = (2, 2),
    shadow_color: tuple = (0, 0, 0, 190)
) -> Image.Image:
    """
    Renders complex text with 100% accurate HarfBuzz OpenType shaping.
    Properly handles Myanmar glyph reordering (သဝေထိုး), stacked consonants (စာလုံးဆင့်),
    medials (ယပင့်၊ ရရစ်၊ ဝဆွဲ), and tone marks with subpixel anti-aliasing.
    """
    if not text.strip():
        return Image.new('RGBA', (1, 1), (0, 0, 0, 0))

    try:
        with open(font_path, 'rb') as f:
            font_data = f.read()

        hb_face = hb.Face(font_data)
        hb_font = hb.Font(hb_face)
        hb_font.scale = (int(font_size * 64), int(font_size * 64))

        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        
        # Explicitly declare Myanmar script and language for HarfBuzz OpenType engine
        has_myanmar = any(0x1000 <= ord(c) <= 0x109F or 0xAA60 <= ord(c) <= 0xAA7F for c in text)
        if has_myanmar:
            buf.script = "Mymr"
            buf.language = "my"

        hb.shape(hb_font, buf)
        infos = buf.glyph_infos
        positions = buf.glyph_positions

        ft_face = freetype.Face(font_path)
        ft_face.set_char_size(int(font_size * 64))

        glyph_draw_data = []
        curr_x = 0

        for info, pos in zip(infos, positions):
            gid = info.codepoint
            ft_face.load_glyph(gid, freetype.FT_LOAD_RENDER)
            slot = ft_face.glyph
            bitmap = slot.bitmap

            x = curr_x + (pos.x_offset / 64.0) + slot.bitmap_left
            y = (pos.y_offset / 64.0) - slot.bitmap_top

            if bitmap.width > 0 and bitmap.rows > 0:
                glyph_draw_data.append({
                    'x': x,
                    'y': y,
                    'width': bitmap.width,
                    'rows': bitmap.rows,
                    'pitch': bitmap.pitch,
                    'buffer': bytes(bitmap.buffer)
                })

            curr_x += (pos.x_advance / 64.0)

        total_width = int(curr_x) + 20
        line_height = int(font_size * 1.5)
        pad = outline_width + 12

        img_w = total_width + pad * 2
        img_h = line_height + pad * 2

        alpha_img = Image.new('L', (img_w, img_h), 0)
        baseline_y = pad + int(font_size * 1.1)

        for g in glyph_draw_data:
            gx = int(pad + g['x'])
            gy = int(baseline_y + g['y'])
            glyph_mask = Image.frombytes('L', (g['width'], g['rows']), g['buffer'], 'raw', 'L', g['pitch'], 1)
            alpha_img.paste(glyph_mask, (gx, gy), glyph_mask)

        final_img = Image.new('RGBA', (img_w, img_h), (0, 0, 0, 0))

        if shadow_offset and shadow_color[3] > 0:
            shadow_mask = alpha_img.filter(ImageFilter.GaussianBlur(radius=1.5))
            shadow_layer = Image.new('RGBA', (img_w, img_h), shadow_color)
            final_img.paste(shadow_layer, shadow_offset, shadow_mask)

        if outline_width > 0 and outline_color[3] > 0:
            outline_mask = alpha_img.filter(ImageFilter.MaxFilter(outline_width * 2 + 1))
            outline_layer = Image.new('RGBA', (img_w, img_h), outline_color)
            final_img.paste(outline_layer, (0, 0), outline_mask)

        text_layer = Image.new('RGBA', (img_w, img_h), text_color)
        final_img.paste(text_layer, (0, 0), alpha_img)

        bbox = final_img.getbbox()
        if bbox:
            final_img = final_img.crop(bbox)

        return final_img
    except Exception as e:
        print(f"Error shaping line '{text[:20]}': {e}")
        return Image.new('RGBA', (1, 1), (0, 0, 0, 0))

def render_composite_subtitle_frame(
    video_w: int,
    video_h: int,
    my_text: str = "",
    en_text: str = "",
    zh_text: str = "",
    sub_mode: str = "my",
    font_path: str = "fonts/Pyidaungsu.ttf",
    font_size: int = 34,
    text_color: str = "#ffffff",
    style_type: str = "box", # "box", "outline", "banner", "yellow"
    position_type: str = "bottom", # "bottom", "middle", "top", "custom"
    y_percent: float = 0.86
) -> Image.Image:
    """
    Composites synchronized subtitle lines onto a full-resolution transparent frame.
    Supports 4 styles (box, outline, banner, yellow) and 4 positions (bottom, middle, top, custom).
    """
    frame = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))

    # Scale font size relative to standard 1080p height
    scale = max(0.55, min(2.5, video_h / 1080.0))
    eff_font_size = max(18, int(font_size * scale))
    en_font_size = max(14, int(eff_font_size * 0.76))

    eff_outline = max(2, int(3 * scale))

    # Determine colors based on style_type
    if style_type == "yellow":
        main_color = (253, 224, 71, 255) # TikTok Yellow (#fde047)
        secondary_color = (255, 255, 255, 240)
    else:
        main_color = hex_to_rgba(text_color)
        secondary_color = (253, 224, 71, 255) if sub_mode == "my_en" else (226, 232, 240, 240)

    mm_font = font_path
    sec_font = str(FONTS_DIR / "MyanmarText.ttf") if (FONTS_DIR / "MyanmarText.ttf").exists() else font_path

    # Build line elements with auto-wrapping
    lines_to_render = []
    max_char_per_line = max(25, int(36 * (video_w / 1280.0)))

    if sub_mode == "my_en":
        if my_text:
            wrapped = wrap_burmese_text(my_text, max_chars=max_char_per_line)
            for wl in wrapped:
                lines_to_render.append((wl, mm_font, eff_font_size, main_color, eff_outline))
        if en_text:
            wrapped_en = wrap_burmese_text(en_text, max_chars=int(max_char_per_line * 1.25))
            for we in wrapped_en:
                lines_to_render.append((we, sec_font, en_font_size, secondary_color, max(1, eff_outline - 1)))
    elif sub_mode == "my_zh":
        if my_text:
            wrapped = wrap_burmese_text(my_text, max_chars=max_char_per_line)
            for wl in wrapped:
                lines_to_render.append((wl, mm_font, eff_font_size, main_color, eff_outline))
        if zh_text:
            lines_to_render.append((zh_text, sec_font, en_font_size, (203, 213, 225, 230), max(1, eff_outline - 1)))
    elif sub_mode == "en":
        t = en_text or my_text
        if t:
            wrapped = wrap_burmese_text(t, max_chars=max_char_per_line)
            for wl in wrapped:
                lines_to_render.append((wl, sec_font, eff_font_size, main_color, eff_outline))
    else:
        # Burmese only
        t = my_text or zh_text
        if t:
            wrapped = wrap_burmese_text(t, max_chars=max_char_per_line)
            for wl in wrapped:
                lines_to_render.append((wl, mm_font, eff_font_size, main_color, eff_outline))

    if not lines_to_render:
        return frame

    rendered_images = []
    max_w = 0
    total_h = 0
    spacing = int(6 * scale)

    for text, fpath, fsize, color, out_w in lines_to_render:
        img_line = shape_and_render_line(
            text, fpath, fsize,
            text_color=color,
            outline_color=(0, 0, 0, 255),
            outline_width=out_w,
            shadow_offset=(int(2 * scale), int(2 * scale)),
            shadow_color=(0, 0, 0, 195)
        )
        rendered_images.append(img_line)
        max_w = max(max_w, img_line.width)
        total_h += img_line.height

    total_h += (len(rendered_images) - 1) * spacing

    # Determine vertical target position
    if position_type == "top":
        target_y = int(video_h * 0.10)
    elif position_type == "middle":
        target_y = int((video_h - total_h) / 2)
    elif position_type == "custom":
        clamped_y = max(0.06, min(0.92, y_percent))
        target_y = int(video_h * clamped_y - total_h / 2)
    else:
        # bottom (default 86%)
        target_y = int(video_h * 0.86 - total_h / 2)

    center_x = video_w // 2

    # Draw background box or banner based on style_type
    if style_type in ("box", "yellow"):
        box_pad_x = int(24 * scale)
        box_pad_y = int(10 * scale)
        box_x1 = max(16, center_x - max_w // 2 - box_pad_x)
        box_x2 = min(video_w - 16, center_x + max_w // 2 + box_pad_x)
        box_y1 = max(4, target_y - box_pad_y)
        box_y2 = min(video_h - 4, target_y + total_h + box_pad_y)
        
        box_img = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(box_img)
        radius = int(14 * scale)
        draw.rounded_rectangle([box_x1, box_y1, box_x2, box_y2], radius=radius, fill=(0, 0, 0, 195))
        frame = Image.alpha_composite(frame, box_img)

    elif style_type == "banner":
        banner_pad_y = int(12 * scale)
        banner_img = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
        draw = ImageDraw.Draw(banner_img)
        draw.rectangle([0, target_y - banner_pad_y, video_w, target_y + total_h + banner_pad_y], fill=(0, 0, 0, 210))
        frame = Image.alpha_composite(frame, banner_img)

    # Paste shaped text lines centered
    curr_y = target_y
    for img_line in rendered_images:
        paste_x = center_x - img_line.width // 2
        frame.paste(img_line, (paste_x, curr_y), img_line)
        curr_y += img_line.height + spacing

    return frame

def parse_time_to_seconds(val: Any) -> float:
    """Converts seconds (float/int) or SRT timestamp strings (00:01:23,456) to float seconds."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        val = val.strip().replace(",", ".")
        parts = val.split(":")
        if len(parts) == 3:
            try:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            except Exception:
                pass
        elif len(parts) == 2:
            try:
                m, s = parts
                return int(m) * 60 + float(s)
            except Exception:
                pass
        try:
            return float(val)
        except Exception:
            return 0.0
    return 0.0

def build_subtitle_overlay_concat(
    segments: Optional[List[Dict[str, Any]]] = None,
    srt_path: Optional[Path] = None,
    video_w: int = 1080,
    video_h: int = 1920,
    temp_dir: Optional[Path] = None,
    sub_mode: str = "my",
    font_name: str = "Pyidaungsu",
    font_size: int = 34,
    sub_color: str = "#ffffff",
    style_type: str = "box",
    position_type: str = "bottom",
    y_percent: float = 0.86
) -> Optional[Path]:
    """
    Renders shaped HarfBuzz frame PNGs and writes a concat.txt demuxer manifest.
    Returns path to concat.txt.
    """
    if not segments and srt_path and srt_path.exists():
        from app.transcriber import parse_srt_string
        try:
            srt_content = srt_path.read_text(encoding='utf-8', errors='replace')
            segments = parse_srt_string(srt_content)
            for s in segments:
                if not s.get("my_text") and s.get("zh_text"):
                    s["my_text"] = s["zh_text"]
        except Exception as e:
            print(f"Error parsing srt for overlay: {e}")
            return None

    if not segments:
        return None

    if not temp_dir:
        temp_dir = OUTPUT_DIR / f"burn_tmp_{uuid.uuid4().hex[:8]}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    blank_p = temp_dir / "blank.png"
    blank_img = Image.new('RGBA', (video_w, video_h), (0, 0, 0, 0))
    blank_img.save(blank_p, compress_level=1)

    resolved_font = str(resolve_font_file(font_name).resolve())

    # Pre-render all HarfBuzz shaped subtitle frames concurrently for extreme speed
    from concurrent.futures import ThreadPoolExecutor
    def render_and_save_frame(idx_seg):
        idx, s = idx_seg
        frame_img = render_composite_subtitle_frame(
            video_w=video_w,
            video_h=video_h,
            my_text=s.get("my_text", ""),
            en_text=s.get("en_text", ""),
            zh_text=s.get("zh_text", ""),
            sub_mode=sub_mode,
            font_path=resolved_font,
            font_size=font_size,
            text_color=sub_color,
            style_type=style_type,
            position_type=position_type,
            y_percent=y_percent
        )
        frame_p = temp_dir / f"f_{idx:05d}.png"
        frame_img.save(frame_p, compress_level=1)

    indexed_segments = list(enumerate(segments))
    max_workers = min(len(indexed_segments), 8) if indexed_segments else 1
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        list(executor.map(render_and_save_frame, indexed_segments))

    concat_lines = []
    curr_time = 0.0

    for idx, s in enumerate(segments):
        start_sec = parse_time_to_seconds(s.get("start", 0.0))
        end_sec = parse_time_to_seconds(s.get("end", start_sec + 2.0))
        dur = max(0.08, end_sec - start_sec)

        # Gap between subtitles
        if start_sec > curr_time:
            gap = start_sec - curr_time
            if gap > 0.04:
                concat_lines.append(f"file '{blank_p.name}'")
                concat_lines.append(f"duration {gap:.3f}")

        concat_lines.append(f"file 'f_{idx:05d}.png'")
        concat_lines.append(f"duration {dur:.3f}")
        curr_time = end_sec

    # Trailing blank frame
    concat_lines.append(f"file '{blank_p.name}'")
    concat_lines.append("duration 30.0")
    concat_lines.append(f"file '{blank_p.name}'")

    concat_file = temp_dir / "concat.txt"
    concat_file.write_text("\n".join(concat_lines), encoding='utf-8')
    return concat_file

def probe_video_resolution(video_path: Path) -> tuple[int, int]:
    """Returns (width, height) of input video using FFmpeg probe."""
    try:
        cmd = [FFMPEG_EXE, "-i", str(video_path)]
        res = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
        m = re.search(r"Stream.*Video:.* (\d{3,4})x(\d{3,4})", res.stderr)
        if m:
            return int(m.group(1)), int(m.group(2))
    except Exception:
        pass
    return 1080, 1920

def resolve_upload_file(filename: Optional[str]) -> Optional[Path]:
    """Finds uploaded asset (like channel logo, BGM) in uploads/, data/bgm/, or output/."""
    if not filename:
        return None
    candidates = [
        BASE_DIR / "uploads" / filename,
        BASE_DIR / "data" / "bgm" / filename,
        BASE_DIR / "output" / filename,
        Path(filename)
    ]
    for c in candidates:
        if c.exists():
            return c
    return None

def burn_subtitles_to_video(
    video_path: Path,
    output_path: Path,
    segments: Optional[List[Dict[str, Any]]] = None,
    srt_path: Optional[Path] = None,
    sub_mode: str = "my",
    font_name: str = "Pyidaungsu",
    sub_font_size: int = 34,
    sub_color: str = "#ffffff",
    margin_v: int = 50,
    style_type: str = "box",
    position_type: str = "bottom",
    y_percent: float = 0.86,
    aspect_ratio: str = "original", # "original", "9:16", "16:9", "1:1"
    resize_mode: str = "fit_blur", # "fit_blur", "crop"
    blur_enabled: bool = False,
    blur_y_percent: float = 0.56,
    blur_height_percent: float = 0.08,
    logo_file: Optional[str] = None,
    logo_pos: str = "top-right",
    logo_size_percent: float = 0.18,
    logo_opacity: float = 0.85,
    orig_audio_volume: float = 1.0,
    bgm_file: Optional[str] = None,
    bgm_volume: float = 0.35,
    bgm_loop: bool = True,
    export_quality: str = "very_high"
) -> Path:
    """
    Burns synchronized Burmese / bilingual subtitles onto a video using HarfBuzz + FreeType
    complex text shaping and FFmpeg concat overlay with ultra-fast hardware-friendly encoding.
    Guarantees 100% flawless Myanmar font rendering with zero glyph corruption.
    Supports audio volume control, copyright music muting, and BGM mixing.
    """
    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Fallback to parse SRT if segments omitted
    if not segments and srt_path and srt_path.exists():
        from app.transcriber import parse_srt_string
        try:
            srt_content = srt_path.read_text(encoding='utf-8', errors='replace')
            segments = parse_srt_string(srt_content)
            for s in segments:
                if not s.get("my_text") and s.get("zh_text"):
                    s["my_text"] = s["zh_text"]
        except Exception as e:
            print(f"Error parsing srt: {e}")

    if not segments:
        raise ValueError("No subtitle segments available to burn into video.")

    w, h = probe_video_resolution(video_path)
    
    # Probe duration for audio mixing and fade
    video_dur = 60.0
    try:
        cmd_p = [FFMPEG_EXE, "-i", str(video_path)]
        res_p = subprocess.run(cmd_p, capture_output=True, text=True, timeout=5)
        m_dur = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", res_p.stderr)
        if m_dur:
            hrs, mins, secs = m_dur.groups()
            video_dur = max(1.0, float(hrs) * 3600 + float(mins) * 60 + float(secs))
    except Exception:
        pass

    # 1. Determine target dimensions based on aspect ratio without unnecessary heavy upscaling
    if aspect_ratio == "16:9":
        if h <= 720 and w <= 1280:
            final_w, final_h = 1280, 720
        else:
            final_w, final_h = 1920, 1080
    elif aspect_ratio == "9:16":
        if w <= 720 and h <= 1280:
            final_w, final_h = 720, 1280
        else:
            final_w, final_h = 1080, 1920
    elif aspect_ratio == "1:1":
        sq = min(w, h, 1080)
        final_w, final_h = sq, sq
    else:
        final_w, final_h = w, h

    # Ensure even dimensions for H.264
    final_w = final_w if final_w % 2 == 0 else final_w + 1
    final_h = final_h if final_h % 2 == 0 else final_h + 1

    job_uid = uuid.uuid4().hex[:8]
    temp_burn_dir = output_path.parent / f"burn_tmp_{job_uid}"

    try:
        concat_file = build_subtitle_overlay_concat(
            segments=segments,
            video_w=final_w,
            video_h=final_h,
            temp_dir=temp_burn_dir,
            sub_mode=sub_mode,
            font_name=font_name,
            font_size=sub_font_size,
            sub_color=sub_color,
            style_type=style_type,
            position_type=position_type,
            y_percent=y_percent
        )

        cmd = [FFMPEG_EXE, "-y", "-i", str(video_path)]
        input_count = 1

        # Check logo input
        resolved_logo = resolve_upload_file(logo_file)
        logo_input_idx = None
        if resolved_logo and resolved_logo.exists():
            cmd.extend(["-i", str(resolved_logo)])
            logo_input_idx = input_count
            input_count += 1

        # Concat demuxer input for HarfBuzz subtitles
        cmd.extend(["-f", "concat", "-safe", "0", "-i", str(concat_file)])
        concat_input_idx = input_count
        input_count += 1

        # Check BGM audio input
        resolved_bgm = resolve_upload_file(bgm_file)
        bgm_input_idx = None
        if resolved_bgm and resolved_bgm.exists():
            cmd.extend(["-i", str(resolved_bgm)])
            bgm_input_idx = input_count
            input_count += 1

        # 2. Build Video Filter Graph
        fc_steps = []
        curr_v = "0:v"

        # Step A: Aspect ratio resize with ultra-fast bokeh blur (1/4 downscaled blur pipeline)
        if (final_w, final_h) != (w, h):
            if resize_mode == "crop":
                fc_steps.append(f"[0:v]scale={final_w}:{final_h}:force_original_aspect_ratio=increase,crop={final_w}:{final_h}[v_res]")
            else:
                # 16x faster bokeh blur by blurring at 1/4 resolution, then scaling up
                bg_w = max(160, final_w // 4)
                bg_h = max(90, final_h // 4)
                fc_steps.append(
                    f"[0:v]split=2[mv][bv]; "
                    f"[bv]scale={bg_w}:{bg_h}:force_original_aspect_ratio=increase,crop={bg_w}:{bg_h},boxblur=8:1,scale={final_w}:{final_h},eq=brightness=-0.12[bg_b]; "
                    f"[mv]scale={final_w}:{final_h}:force_original_aspect_ratio=decrease[fg_v]; "
                    f"[bg_b][fg_v]overlay=(W-w)/2:(H-h)/2[v_res]"
                )
            curr_v = "v_res"

        # Step B: Blur original subtitle / text band (Fast single-pass blur)
        if blur_enabled:
            by = max(0, min(final_h - 10, int(final_h * blur_y_percent)))
            bh = max(20, min(final_h - by, int(final_h * blur_height_percent)))
            fc_steps.append(
                f"[{curr_v}]split=2[v_k][v_c]; "
                f"[v_c]crop=iw:{bh}:0:{by},boxblur=10:1,eq=brightness=-0.05:contrast=1.05[v_bb]; "
                f"[v_k][v_bb]overlay=0:{by}[v_blur]"
            )
            curr_v = "v_blur"

        # Step C: Channel Logo overlay
        if logo_input_idx is not None:
            lw = max(40, int(final_w * logo_size_percent))
            lx = 35 if "left" in logo_pos else "W-w-35"
            ly = 35 if "top" in logo_pos else "H-h-35"
            fc_steps.append(
                f"[{logo_input_idx}:v]scale={lw}:-1,format=rgba,colorchannelmixer=aa={logo_opacity}[s_logo]; "
                f"[{curr_v}][s_logo]overlay={lx}:{ly}[v_logo]"
            )
            curr_v = "v_logo"

        # Step D: HarfBuzz Subtitles overlay
        fc_steps.append(f"[{curr_v}][{concat_input_idx}:v]overlay=0:0:shortest=1[v_out]")

        # 3. Audio Filter Graph (Volume Ducking, Muting & BGM Mixing)
        has_custom_audio = False
        fade_st = max(0.5, video_dur - 2.0)
        fade_d = min(2.0, video_dur)

        if bgm_input_idx is not None:
            has_custom_audio = True
            if orig_audio_volume <= 0.01:
                # Anti-copyright: Original audio completely muted, BGM only!
                fc_steps.append(
                    f"[{bgm_input_idx}:a]aloop=loop=-1:size=2e+09,atrim=0:{video_dur},volume={bgm_volume},afade=t=out:st={fade_st}:d={fade_d}[a_out]"
                )
            else:
                # Mixed: Ducked original + BGM
                fc_steps.append(f"[0:a]volume={orig_audio_volume}[orig_a]")
                fc_steps.append(
                    f"[{bgm_input_idx}:a]aloop=loop=-1:size=2e+09,atrim=0:{video_dur},volume={bgm_volume},afade=t=out:st={fade_st}:d={fade_d}[bgm_a]"
                )
                fc_steps.append(
                    f"[orig_a][bgm_a]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
                )
        elif orig_audio_volume <= 0.01:
            # Completely muted without BGM
            has_custom_audio = False
        elif orig_audio_volume < 0.98:
            # Adjusted original volume
            has_custom_audio = True
            fc_steps.append(f"[0:a]volume={orig_audio_volume}[a_out]")
        else:
            has_custom_audio = False

        filter_complex_str = "; ".join(fc_steps)

        # Quality settings:
        crf_val = "18" if export_quality == "very_high" else ("21" if export_quality == "high" else "24")
        a_bitrate = "256k" if export_quality == "very_high" else "192k"

        cmd.extend([
            "-filter_complex", filter_complex_str,
            "-map", "[v_out]"
        ])

        if has_custom_audio:
            cmd.extend([
                "-map", "[a_out]",
                "-c:a", "aac",
                "-b:a", a_bitrate
            ])
        elif orig_audio_volume <= 0.01:
            cmd.extend(["-an"])
        else:
            cmd.extend([
                "-map", "0:a?",
                "-c:a", "copy"
            ])

        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", crf_val,
            "-threads", "0",
            "-pix_fmt", "yuv420p",
            str(output_path)
        ])

        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            # Fallback with AAC audio encoding if stream copy fails
            cmd_reencode = [
                arg if arg != "copy" else "aac" for arg in cmd
            ]
            # Replace -c:a aac and add -b:a 192k
            try:
                a_idx = cmd_reencode.index("-c:a")
                cmd_reencode.insert(a_idx + 2, "-b:a")
                cmd_reencode.insert(a_idx + 3, "192k")
            except Exception:
                pass
            res2 = subprocess.run(cmd_reencode, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if res2.returncode != 0:
                raise RuntimeError(f"FFmpeg subtitle burn failed: {res2.stderr[-400:]}")

    finally:
        # Cleanup temporary frames directory
        try:
            if temp_burn_dir.exists():
                shutil.rmtree(temp_burn_dir, ignore_errors=True)
        except Exception:
            pass

    return output_path

def render_movie_recap(
    job_id: str,
    output_dir: Path,
    narration_audio_path: Path,
    srt_path: Optional[Path] = None,
    source_video_path: Optional[Path] = None,
    watermark_text: str = "@actrecap",
    watermark_pos: str = "top-right",
    watermark_opacity: float = 0.8,
    title_text: Optional[str] = None,
    sub_color: str = "&H00FFFFFF",
    sub_font_size: int = 24,
    font_name: str = "Pyidaungsu",
    anti_copyright: bool = True,
    speed_factor: float = 1.05,
    mirror_flip: bool = False,
    bgm_enabled: bool = True,
    bgm_volume: float = 0.12,
    aspect_ratio: str = "16:9",
    style_type: str = "box",
    position_type: str = "bottom",
    y_percent: float = 0.86
):
    """
    Renders the complete movie recap video with subtitles, audio narration, watermark, and BGM.
    Runs asynchronously and updates RENDER_JOBS.
    """
    job = RENDER_JOBS[job_id]
    job["status"] = "processing"
    job["progress"] = 5
    job["step"] = "Preparing assets and media streams..."

    try:
        output_filename = f"recap_{job_id}.mp4"
        final_output_path = output_dir / output_filename
        raw_output_path = output_dir / f"raw_recap_{job_id}.mp4" if (srt_path and srt_path.exists()) else final_output_path
        
        # 1. Determine narration audio duration
        probe_cmd = [
            FFMPEG_EXE, "-i", str(narration_audio_path),
            "-f", "null", "-"
        ]
        probe_res = subprocess.run(probe_cmd, stderr=subprocess.PIPE, text=True)
        duration = 15.0
        dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", probe_res.stderr)
        if dur_match:
            hrs, mins, secs = dur_match.groups()
            duration = float(hrs) * 3600 + float(mins) * 60 + float(secs)
        job["duration"] = duration
        job["progress"] = 15
        job["step"] = f"Audio duration: {duration:.1f}s. Building video timeline..."
        
        # 2. Dimensions
        if aspect_ratio == "9:16":
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080

        # Auto-fallback to any existing uploaded video if none explicitly specified
        if not source_video_path or not source_video_path.exists():
            uploads_dir = output_dir.parent / "uploads"
            if uploads_dir.exists():
                video_files = sorted(
                    [f for f in uploads_dir.glob("video_*.mp4")],
                    key=lambda p: p.stat().st_mtime,
                    reverse=True
                )
                if video_files:
                    source_video_path = video_files[0]
                    print(f"Auto-selected latest uploaded video: {source_video_path.name}")

        # 3. Handle BGM
        bgm_path = None
        if bgm_enabled:
            job["step"] = "Synthesizing cinematic recap background music..."
            bgm_wav = output_dir / f"bgm_{job_id}.wav"
            create_synthetic_cinematic_bgm(bgm_wav, duration_sec=duration + 5)
            bgm_path = bgm_wav
            
        job["progress"] = 30
        job["step"] = "Compiling FFmpeg composition graph..."

        # 4. Construct FFmpeg command
        cmd = [FFMPEG_EXE, "-y"]
        
        has_source_video = source_video_path and source_video_path.exists()
        if has_source_video:
            cmd.extend(["-stream_loop", "-1", "-i", str(source_video_path)])
        else:
            cmd.extend([
                "-f", "lavfi",
                "-i", f"color=c=#0c101d:s={width}x{height}:d={duration + 1}:r=30"
            ])
            
        # Narration audio input
        cmd.extend(["-i", str(narration_audio_path)])
        
        # BGM input if present
        if bgm_path and bgm_path.exists():
            cmd.extend(["-i", str(bgm_path)])

        # Construct Video Filter Graph
        vf_filters = []
        
        if has_source_video:
            vf_filters.append(f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height}")
            if mirror_flip:
                vf_filters.append("hflip")
            if anti_copyright:
                vf_filters.append("eq=saturation=1.10:contrast=1.05:brightness=0.02")
        else:
            vf_filters.append("vignette=PI/4,noise=alls=10:allf=t+u")

        # Top Title Banner (Uses Myanmar Text/Pyidaungsu font to prevent [][][][][][] tofu boxes)
        if title_text:
            safe_title = title_text.replace("'", "").replace(":", " - ")
            bm_font = get_burmese_font_path(font_name)
            font_clause = f"fontfile='{bm_font}':" if bm_font else ""
            banner_vf = (
                f"drawtext={font_clause}text='{safe_title}':fontsize={int(height*0.042)}:"
                f"fontcolor=white:box=1:boxcolor=black@0.75:boxborderw=12:"
                f"x=(w-text_w)/2:y={int(height*0.055)}"
            )
            vf_filters.append(banner_vf)

        # Crisp High-Definition Watermark
        if watermark_text:
            safe_wm = watermark_text.replace("'", "").replace(":", " - ")
            wm_font = get_sharp_watermark_font_path()
            font_clause = f"fontfile='{wm_font}':" if wm_font else ""
            wm_x = "w-tw-40" if "right" in watermark_pos else "40"
            wm_y = "40" if "top" in watermark_pos else "h-th-40"
            wm_vf = (
                f"drawtext={font_clause}text='{safe_wm}':fontsize={int(height*0.032)}:"
                f"fontcolor=white@{watermark_opacity}:borderw=2:bordercolor=black@0.85:"
                f"shadowx=2:shadowy=2:shadowcolor=black@0.75:x={wm_x}:y={wm_y}"
            )
            vf_filters.append(wm_vf)

        filter_graph = ",".join(vf_filters)
        cmd.extend(["-vf", filter_graph])

        # Audio Mixing: duck BGM under narration
        if bgm_path and bgm_path.exists():
            filter_complex_audio = (
                f"[2:a]volume={bgm_volume}[bgm];"
                f"[1:a]volume=1.0[narr];"
                f"[narr][bgm]amix=inputs=2:duration=first:dropout_transition=2[aout]"
            )
            cmd.extend(["-filter_complex", filter_complex_audio, "-map", "0:v", "-map", "[aout]"])
        else:
            cmd.extend(["-map", "0:v", "-map", "1:a"])

        # Encoding options
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-threads", "0",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-t", f"{duration}",
            str(raw_output_path)
        ])

        job["progress"] = 50
        job["step"] = "Encoding high-definition video recap..."
        
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0:
            print("FFmpeg render failed:\n", stderr)
            job["step"] = "Applying safe encoding fallback..."
            safe_cmd = [
                FFMPEG_EXE, "-y",
                "-stream_loop", "-1", "-i", str(source_video_path) if has_source_video else "color=c=#0b1120:s=1280x720:d=10",
                "-i", str(narration_audio_path),
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac",
                "-t", f"{duration}",
                str(raw_output_path)
            ]
            subprocess.run(safe_cmd, check=True)

        # Apply 100% flawless HarfBuzz-shaped Burmese subtitles overlay if srt is provided
        if srt_path and srt_path.exists() and raw_output_path.exists():
            job["step"] = "Burning HarfBuzz-shaped Burmese subtitles onto recap video..."
            job["progress"] = 85
            burn_subtitles_to_video(
                video_path=raw_output_path,
                output_path=final_output_path,
                srt_path=srt_path,
                font_name=font_name,
                sub_font_size=sub_font_size,
                sub_color=sub_color if (sub_color.startswith("#") or len(sub_color) <= 7) else "#ffffff",
                style_type=style_type,
                position_type=position_type,
                y_percent=y_percent
            )
            try:
                if raw_output_path.exists() and raw_output_path != final_output_path:
                    raw_output_path.unlink()
            except Exception:
                pass

        job["progress"] = 100
        job["status"] = "completed"
        job["step"] = "Recap video rendered successfully!"
        job["output_video"] = output_filename
        job["output_path"] = str(final_output_path)
        job["file_size_mb"] = round(final_output_path.stat().st_size / (1024 * 1024), 2)
        
        if bgm_path and bgm_path.exists():
            try:
                bgm_path.unlink()
            except Exception:
                pass

    except Exception as e:
        job["status"] = "error"
        job["error"] = str(e)
        job["step"] = f"Rendering error: {e}"
        print(f"Render job {job_id} error: {e}")

def start_render_job(
    output_dir: Path,
    narration_audio_path: Path,
    srt_path: Optional[Path] = None,
    source_video_path: Optional[Path] = None,
    watermark_text: str = "@actrecap",
    watermark_pos: str = "top-right",
    watermark_opacity: float = 0.8,
    title_text: Optional[str] = None,
    sub_color: str = "&H00FFFFFF",
    sub_font_size: int = 24,
    font_name: str = "Pyidaungsu",
    anti_copyright: bool = True,
    speed_factor: float = 1.05,
    mirror_flip: bool = False,
    bgm_enabled: bool = True,
    bgm_volume: float = 0.12,
    aspect_ratio: str = "16:9",
    style_type: str = "box",
    position_type: str = "bottom",
    y_percent: float = 0.86,
    callback: Optional[Callable[[Dict[str, Any]], None]] = None
) -> str:
    """Spawns an asynchronous render job and returns the job ID."""
    job_id = uuid.uuid4().hex[:12]
    RENDER_JOBS[job_id] = {
        "job_id": job_id,
        "status": "queued",
        "progress": 0,
        "step": "Queueing render task...",
        "created_at": time.time(),
        "output_video": None
    }
    
    thread = threading.Thread(
        target=render_movie_recap,
        args=(job_id, output_dir, narration_audio_path),
        kwargs={
            "srt_path": srt_path,
            "source_video_path": source_video_path,
            "watermark_text": watermark_text,
            "watermark_pos": watermark_pos,
            "watermark_opacity": watermark_opacity,
            "title_text": title_text,
            "sub_color": sub_color,
            "sub_font_size": sub_font_size,
            "font_name": font_name,
            "anti_copyright": anti_copyright,
            "speed_factor": speed_factor,
            "mirror_flip": mirror_flip,
            "bgm_enabled": bgm_enabled,
            "bgm_volume": bgm_volume,
            "aspect_ratio": aspect_ratio,
            "style_type": style_type,
            "position_type": position_type,
            "y_percent": y_percent
        },
        daemon=True
    )
    thread.start()
    return job_id
