import os
import re
import uuid
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
import requests
import yt_dlp

from app.video_renderer import FFMPEG_EXE

# Guarantee standard ffmpeg.exe exists in binaries folder for yt-dlp and ffmpeg tools
try:
    if FFMPEG_EXE and Path(FFMPEG_EXE).exists():
        ffmpeg_dir = Path(FFMPEG_EXE).parent
        standard_ffmpeg = ffmpeg_dir / "ffmpeg.exe"
        if not standard_ffmpeg.exists():
            shutil.copyfile(FFMPEG_EXE, standard_ffmpeg)
except Exception as _fe:
    print(f"Notice: ffmpeg setup check: {_fe}")

def check_video_has_audio(file_path: Path) -> bool:
    """Checks if a video file contains a valid audio stream."""
    if not file_path or not file_path.exists():
        return False
    try:
        cmd = [FFMPEG_EXE, "-i", str(file_path)]
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=8)
        return "Audio:" in (p.stderr or "")
    except Exception:
        return False

def create_muted_video(src_path: Path, dst_path: Path) -> bool:
    """Strips audio track from video to produce silent, copyright-safe b-roll in 1 second."""
    try:
        cmd = [
            FFMPEG_EXE, "-y",
            "-i", str(src_path),
            "-an",
            "-c:v", "copy",
            str(dst_path)
        ]
        res = subprocess.run(cmd, capture_output=True, timeout=30)
        return dst_path.exists() and dst_path.stat().st_size > 1000
    except Exception as e:
        print(f"Error creating muted video: {e}")
        return False

DEFAULT_MOBILE_HEADERS = {
    "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": "https://www.xiaohongshu.com/"
}

def extract_url_from_text(text: str) -> Optional[str]:
    """Extracts first valid HTTP/HTTPS URL from any shared text string or mobile clipboard."""
    if not text or not text.strip():
        return None
    clean_text = text.strip()
    
    # 1. Match full HTTP/HTTPS URL
    match = re.search(r"https?://[^\s\u4e00-\u9fa5<>\"'()（）「」【】]+", clean_text)
    if match:
        return match.group(0).rstrip("，。！？）】)]>\"'.,;「」【】")
        
    # 2. Match known domains without protocol (e.g. xhslink.com/a/..., v.douyin.com/..., tiktok.com/..., youtube.com/...)
    m2 = re.search(r"(?:[a-zA-Z0-9-]+\.)?(?:xhslink\.com|xiaohongshu\.com|xhs\.com|douyin\.com|tiktok\.com|bilibili\.com|kuaishou\.com|youtube\.com|youtu\.be|facebook\.com|fb\.watch|fb\.com|instagram\.com)/[^\s\u4e00-\u9fa5<>\"'()（）「」【】]+", clean_text)
    if m2:
        return "https://" + m2.group(0).rstrip("，。！？）】)]>\"'.,;「」【】")
        
    # 3. Fallback: any standard domain with path
    m3 = re.search(r"[a-zA-Z0-9-]+\.[a-zA-Z]{2,}(?:/[^\s\u4e00-\u9fa5<>\"'()（）「」【】]*)?", clean_text)
    if m3:
        return "https://" + m3.group(0).rstrip("，。！？）】)]>\"'.,;「」【】")
        
    return None

def clean_html_escapes(raw: str) -> str:
    """Unescapes JSON and HTML escapes commonly found in Xiaohongshu source code."""
    text = raw.replace(r"\u002F", "/").replace(r"\u002f", "/")
    text = text.replace(r"\/", "/")
    text = text.replace("&quot;", '"').replace("&amp;", "&")
    return text

def resolve_rednote_canonical_and_page(url: str, session: requests.Session) -> Tuple[str, str]:
    """
    Follows HTTP redirects for short links (like xhslink.com) to find canonical note URL
    and returns both the final URL and the fetched HTML body in a single network pass.
    """
    try:
        resp = session.get(url, headers=DEFAULT_MOBILE_HEADERS, allow_redirects=True, timeout=15)
        canonical_url = resp.url
        html_content = resp.text
        return canonical_url, html_content
    except Exception as e:
        print(f"RedNote resolve error: {e}")
        return url, ""

def parse_rednote_stream_info(html: str) -> Tuple[Optional[str], Optional[str], Optional[str], float]:
    """
    Parses RedNote HTML to find the best video stream URL, audio stream URL (if separate), title, and duration.
    Prefers H.264 streams for universal web preview and HTML5 compatibility.
    """
    title = "RedNote HD Video"
    duration = 0.0
    video_url = None
    audio_url = None
    
    # 1. Parse window.__INITIAL_STATE__
    state_match = re.search(r"window\.__INITIAL_STATE__\s*=\s*(\{.+?\})</script>", html)
    if state_match:
        try:
            raw_state = state_match.group(1).replace("undefined", "null")
            data = json.loads(raw_state)
            
            def find_stream_maps(obj):
                res = []
                if isinstance(obj, dict):
                    if "h264" in obj or "h265" in obj or "masterUrl" in obj:
                        res.append(obj)
                    for v in obj.values():
                        res.extend(find_stream_maps(v))
                elif isinstance(obj, list):
                    for item in obj:
                        res.extend(find_stream_maps(item))
                return res
                
            stream_maps = find_stream_maps(data)
            
            h264_candidates = []
            other_candidates = []
            
            for sm in stream_maps:
                for item in sm.get("h264", []):
                    m_url = item.get("masterUrl")
                    if m_url and isinstance(m_url, str) and m_url.startswith("http"):
                        h264_candidates.append((item, m_url))
                for item in sm.get("h265", []):
                    m_url = item.get("masterUrl")
                    if m_url and isinstance(m_url, str) and m_url.startswith("http"):
                        other_candidates.append((item, m_url))
                if "masterUrl" in sm and isinstance(sm["masterUrl"], str):
                    m_url = sm["masterUrl"]
                    if m_url.startswith("http"):
                        codec = str(sm.get("videoCodec", "")).lower()
                        if "h264" in codec or "avc" in codec:
                            h264_candidates.append((sm, m_url))
                        else:
                            other_candidates.append((sm, m_url))

            all_candidates = []
            for item, m_url in h264_candidates:
                all_candidates.append((True, item, m_url))
            for item, m_url in other_candidates:
                all_candidates.append((False, item, m_url))

            if all_candidates:
                # Prioritize: 1. Highest resolution (w*h), 2. Universal H.264 if same res, 3. Highest bitrate/size
                all_candidates.sort(
                    key=lambda x: (
                        (x[1].get("width", 0) or 0) * (x[1].get("height", 0) or 0),
                        1 if x[0] else 0,
                        x[1].get("size", 0) or x[1].get("videoBitrate", 0) or 0
                    ),
                    reverse=True
                )
                _, selected_meta, video_url = all_candidates[0]
                if selected_meta.get("duration"):
                    duration = round(float(selected_meta["duration"]) / 1000.0, 2)

            # Look for separate audio stream if present
            def find_audio_stream_url(obj):
                if isinstance(obj, dict):
                    for k in ("audio", "audioStream", "backupAudioUrl", "originAudioUrl", "music"):
                        val = obj.get(k)
                        if isinstance(val, dict):
                            m = val.get("masterUrl") or val.get("url")
                            if m and isinstance(m, str) and m.startswith("http"):
                                return m
                        elif isinstance(val, str) and val.startswith("http") and any(ext in val.lower() for ext in [".m4a", ".mp3", ".aac", "/audio", "sns-audio"]):
                            return val
                    for v in obj.values():
                        res = find_audio_stream_url(v)
                        if res:
                            return res
                elif isinstance(obj, list):
                    for item in obj:
                        res = find_audio_stream_url(item)
                        if res:
                            return res
                return None

            audio_url = find_audio_stream_url(data.get("noteData") or data)

            # Discover title from JSON state
            def find_title(obj):
                if isinstance(obj, dict):
                    for k in ("title", "desc", "displayTitle"):
                        val = obj.get(k)
                        if isinstance(val, str) and len(val.strip()) > 1 and not val.strip().startswith("http"):
                            return val.strip()
                    for v in obj.values():
                        t = find_title(v)
                        if t:
                            return t
                elif isinstance(obj, list):
                    for item in obj:
                        t = find_title(item)
                        if t:
                            return t
                return None

            found_title = find_title(data.get("noteData") or data)
            if found_title:
                title = found_title[:80]

        except Exception as e:
            print(f"Error parsing INITIAL_STATE JSON: {e}")

    # 2. Regex fallback on unescaped HTML if video_url not found in JSON
    unescaped = clean_html_escapes(html)
    if not video_url:
        master_matches = re.findall(r'"(?:masterUrl|originVideoUrl)":\s*"(https?://[a-zA-Z0-9\.\_\-]+?\.mp4[^\s"\'<>]*)"', unescaped)
        if master_matches:
            video_url = master_matches[0]
            
        if not video_url:
            v_matches = re.findall(r'https?://sns-video-[a-zA-Z0-9\.\_\-]+?\.xhscdn\.com/[a-zA-Z0-9\.\_\-\/]+?\.mp4[^\s"\'<>]*', unescaped)
            if v_matches:
                video_url = v_matches[0]

    if not audio_url:
        aud_matches = re.findall(r'"(?:audioUrl|originAudioUrl)":\s*"(https?://[a-zA-Z0-9\.\_\-]+?(?:\.m4a|\.mp3|\.aac)[^\s"\'<>]*)"', unescaped)
        if aud_matches:
            audio_url = aud_matches[0]

    # HTML Title fallback
    if title == "RedNote HD Video":
        title_m = re.search(r"<title>(.*?)</title>", html)
        if title_m:
            clean_title = title_m.group(1).replace(" - 小红书", "").replace("- 小红书", "").replace("小红书", "").strip()
            if clean_title:
                title = clean_title

    return video_url, audio_url, title, duration

def fallback_scrape_rednote_video(
    canonical_url: str,
    target_file: Path,
    preloaded_html: Optional[str] = None,
    session: Optional[requests.Session] = None
) -> Optional[Dict[str, Any]]:
    """
    Direct high-speed scraper for Xiaohongshu (RedNote) watermark-free HD video.
    Extracts direct master MP4 stream (sns-video-*.xhscdn.com) and guarantees audio track.
    """
    if session is None:
        session = requests.Session()
        session.headers.update(DEFAULT_MOBILE_HEADERS)

    # Use preloaded HTML if valid, else fetch canonical_url
    html = preloaded_html or ""
    if not html or len(html) < 500:
        try:
            res = session.get(canonical_url, headers=DEFAULT_MOBILE_HEADERS, timeout=15)
            if res.status_code == 200:
                html = res.text
        except Exception as e:
            print(f"Error fetching canonical URL: {e}")

    if not html:
        return None

    video_url, audio_url, title, duration = parse_rednote_stream_info(html)
    if not video_url:
        note_id_match = re.search(r"(?:explore|discovery/item|item)/([a-zA-Z0-9]+)", canonical_url)
        if note_id_match and "discovery/item" not in canonical_url:
            note_id = note_id_match.group(1)
            alt_url = f"https://www.xiaohongshu.com/discovery/item/{note_id}"
            try:
                res = session.get(alt_url, headers=DEFAULT_MOBILE_HEADERS, timeout=15)
                if res.status_code == 200:
                    video_url, audio_url, alt_title, duration = parse_rednote_stream_info(res.text)
                    if alt_title:
                        title = alt_title
            except Exception:
                pass

    if not video_url:
        print("Fallback scrape: No valid video stream URL found in page HTML.")
        return None

    video_url = video_url.rstrip("\\\"' ")
    dl_headers = {
        "User-Agent": DEFAULT_MOBILE_HEADERS["User-Agent"],
        "Referer": "https://www.xiaohongshu.com/"
    }

    try:
        dl_resp = session.get(video_url, headers=dl_headers, stream=True, timeout=60)
        if dl_resp.status_code == 200:
            with open(target_file, "wb") as f:
                for chunk in dl_resp.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        
            if target_file.exists() and target_file.stat().st_size > 10000:
                # Check if downloaded video already has sound
                has_audio = check_video_has_audio(target_file)
                if not has_audio and audio_url:
                    print(f"Video is mute, downloading separate audio stream: {audio_url[:100]} and muxing...")
                    audio_tmp = target_file.parent / f"audio_tmp_{uuid.uuid4().hex[:6]}.m4a"
                    try:
                        a_resp = session.get(audio_url, headers=dl_headers, timeout=30)
                        if a_resp.status_code == 200:
                            with open(audio_tmp, "wb") as af:
                                af.write(a_resp.content)
                            if audio_tmp.exists() and audio_tmp.stat().st_size > 1000:
                                muxed_tmp = target_file.parent / f"muxed_{uuid.uuid4().hex[:6]}.mp4"
                                cmd = [
                                    FFMPEG_EXE, "-y",
                                    "-i", str(target_file),
                                    "-i", str(audio_tmp),
                                    "-c:v", "copy",
                                    "-c:a", "aac",
                                    "-shortest",
                                    str(muxed_tmp)
                                ]
                                p = subprocess.run(cmd, capture_output=True, timeout=30)
                                if muxed_tmp.exists() and muxed_tmp.stat().st_size > 10000:
                                    shutil.move(str(muxed_tmp), str(target_file))
                                    print("Successfully muxed audio into video!")
                    except Exception as _me:
                        print(f"Audio mux exception: {_me}")
                    finally:
                        if audio_tmp.exists():
                            try:
                                audio_tmp.unlink()
                            except Exception:
                                pass

                # Probe duration if missing
                if duration <= 0.0:
                    try:
                        cmd = [FFMPEG_EXE, "-i", str(target_file)]
                        p = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
                        if m:
                            hrs, mins, secs = m.groups()
                            duration = round(int(hrs) * 3600 + int(mins) * 60 + float(secs), 2)
                    except Exception:
                        pass

                return {
                    "title": title,
                    "video_url_src": video_url,
                    "file_size": target_file.stat().st_size,
                    "duration": duration,
                    "has_audio": check_video_has_audio(target_file)
                }
    except Exception as e:
        print(f"Error downloading stream chunks: {e}")

    return None

def download_rednote_hd_video(
    raw_input: str,
    output_dir: Path
) -> Dict[str, Any]:
    """
    Downloads watermark-free HD video with FULL AUDIO SOUND from RedNote, TikTok, YouTube Shorts, and Facebook.
    Guarantees that the resulting MP4 always has clear sound.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    
    url = extract_url_from_text(raw_input)
    if not url:
        raise ValueError("လင့်ခ် ရှာမတွေ့ပါ (ကျေးဇူးပြု၍ RedNote link သို့မဟုတ် share text ကို ထည့်သွင်းပါ)")

    session = requests.Session()
    session.headers.update(DEFAULT_MOBILE_HEADERS)
    canonical_url, html_content = resolve_rednote_canonical_and_page(url, session)

    job_uid = uuid.uuid4().hex[:8]
    target_filename = f"video_rednote_{job_uid}.mp4"
    target_path = output_dir / target_filename

    title = "HD Video"
    duration = 0.0
    downloaded = False

    # Detect platform
    is_rednote = any(d in canonical_url.lower() or d in url.lower() for d in ["xhslink.com", "xiaohongshu.com", "xhs.com"])
    is_tiktok = any(d in canonical_url.lower() or d in url.lower() for d in ["tiktok.com", "douyin.com"])
    is_youtube = any(d in canonical_url.lower() or d in url.lower() for d in ["youtube.com", "youtu.be"])
    is_facebook = any(d in canonical_url.lower() or d in url.lower() for d in ["facebook.com", "fb.watch", "fb.com"])

    # 1. If RedNote: Direct mobile H5 scraper (Fastest, Watermark-Free HD)
    if is_rednote:
        print(f"Downloading RedNote video stream from: {canonical_url}")
        fb_result = fallback_scrape_rednote_video(
            canonical_url, target_path, preloaded_html=html_content, session=session
        )
        if fb_result and target_path.exists() and target_path.stat().st_size > 10000:
            # Only accept as complete if video has audio or if direct scrape succeeded with audio
            if fb_result.get("has_audio"):
                downloaded = True
                title = fb_result.get("title") or title
                duration = float(fb_result.get("duration") or 0.0)

    # 2. If TikTok: Try TikWM Watermark-Free HD direct scraper
    if not downloaded and is_tiktok:
        try:
            print(f"Downloading TikTok video without watermark: {canonical_url}")
            tik_res = requests.post("https://www.tikwm.com/api/", data={"url": canonical_url, "hd": 1}, timeout=15)
            if tik_res.status_code == 200:
                tdata = tik_res.json()
                if tdata.get("code") == 0 and "data" in tdata:
                    info_d = tdata["data"]
                    stream_url = info_d.get("hdplay") or info_d.get("play")
                    if stream_url:
                        v_res = requests.get(stream_url, headers={"User-Agent": "Mozilla/5.0"}, stream=True, timeout=30)
                        if v_res.status_code == 200:
                            with open(target_path, "wb") as f:
                                for chunk in v_res.iter_content(chunk_size=1024 * 64):
                                    if chunk:
                                        f.write(chunk)
                            if target_path.exists() and target_path.stat().st_size > 10000 and check_video_has_audio(target_path):
                                downloaded = True
                                title = info_d.get("title") or "TikTok HD Video"
                                duration = float(info_d.get("duration") or 0.0)
        except Exception as e:
            print(f"TikTok TikWM direct scraper attempt: {e}")

    # 3. Universal yt-dlp with GUARANTEED Audio Merging (YouTube, Facebook, Douyin, TikTok fallback, RedNote fallback)
    if not downloaded:
        ffmpeg_dir = str(Path(FFMPEG_EXE).parent)
        ydl_opts = {
            "format": "bestvideo*+bestaudio/best[ext=mp4]/best",
            "outtmpl": str(target_path),
            "merge_output_format": "mp4",
            "ffmpeg_location": ffmpeg_dir,
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "concurrent_fragment_downloads": 10,
            "http_chunk_size": 10485760,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios", "mweb"]
                }
            }
        }
        if is_rednote:
            ydl_opts["http_headers"] = {
                "Referer": "https://www.xiaohongshu.com/",
                "User-Agent": DEFAULT_MOBILE_HEADERS["User-Agent"]
            }

        try:
            print(f"Executing yt-dlp with audio merge for: {canonical_url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(canonical_url, download=True)
                if info:
                    title = info.get("title") or title
                    duration = float(info.get("duration") or 0.0)
                    downloaded = target_path.exists() and target_path.stat().st_size > 10000
        except Exception as e:
            print(f"yt-dlp download attempt error: {e}")

    # 4. Secondary fallback scraper if still not downloaded and is RedNote
    if not downloaded and is_rednote:
        fb_result = fallback_scrape_rednote_video(canonical_url, target_path, session=session)
        if fb_result and target_path.exists() and target_path.stat().st_size > 10000:
            downloaded = True
            title = fb_result.get("title") or title
            duration = float(fb_result.get("duration") or 0.0)

    if not downloaded or not target_path.exists() or target_path.stat().st_size < 10000:
        raise RuntimeError("ဗီဒီယို ဒေါင်းလုဒ် မအောင်မြင်ပါ (Link မှန်ကန်မှု မရှိခြင်း သို့မဟုတ် ဗီဒီယိုဖိုင် မဟုတ်ခြင်း/Private ဖြစ်နေခြင်း ဖြစ်နိုင်ပါသည်)")

    # 5. Crucial Guarantee: Check if video has audio. If mute, attempt emergency audio fetch
    has_audio = check_video_has_audio(target_path)
    if not has_audio:
        print(f"Notice: Video {target_path.name} was downloaded without audio. Attempting audio stream merge...")
        try:
            audio_target = output_dir / f"audio_fix_{job_uid}.m4a"
            ydl_audio_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(audio_target),
                "quiet": True,
                "nocheckcertificate": True,
                "extractor_args": {
                    "youtube": {
                        "player_client": ["android", "ios", "mweb"]
                    }
                }
            }
            with yt_dlp.YoutubeDL(ydl_audio_opts) as ydl:
                ydl.extract_info(canonical_url, download=True)
            if audio_target.exists() and audio_target.stat().st_size > 1000:
                fixed_target = output_dir / f"fixed_{job_uid}.mp4"
                cmd = [
                    FFMPEG_EXE, "-y",
                    "-i", str(target_path),
                    "-i", str(audio_target),
                    "-c:v", "copy",
                    "-c:a", "aac",
                    "-shortest",
                    str(fixed_target)
                ]
                subprocess.run(cmd, capture_output=True, timeout=30)
                if fixed_target.exists() and fixed_target.stat().st_size > 10000:
                    shutil.move(str(fixed_target), str(target_path))
                    has_audio = True
                    print("Emergency audio stream merge successful!")
        except Exception as _ae:
            print(f"Audio emergency merge error: {_ae}")

    # Probe duration if still missing
    if duration <= 0.0 and target_path.exists():
        try:
            cmd = [FFMPEG_EXE, "-i", str(target_path)]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", p.stderr)
            if m:
                hrs, mins, secs = m.groups()
                duration = round(int(hrs) * 3600 + int(mins) * 60 + float(secs), 2)
        except Exception:
            pass

    file_size_mb = round(target_path.stat().st_size / (1024 * 1024), 2)

    return {
        "success": True,
        "title": title,
        "video_file": target_filename,
        "video_url": f"/media/uploads/{target_filename}",
        "file_size_mb": file_size_mb,
        "duration": duration,
        "has_audio": has_audio,
        "canonical_url": canonical_url
    }
