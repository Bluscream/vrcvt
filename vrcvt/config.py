"""
VRCVideoTester (vrcvt) - Global Configuration & Path Definitions
"""

from pathlib import Path
from typing import Dict, List

class Config:
    """Project-wide paths, constants, and VRChat flags."""

    # Project Directories
    PACKAGE_DIR: Path = Path(__file__).resolve().parent
    PROJECT_ROOT: Path = PACKAGE_DIR.parent
    ASSETS_DIR: Path = PROJECT_ROOT / "assets"
    
    # Binary Artifact Paths
    WMF_EXE: Path = ASSETS_DIR / "wmf_test.exe"
    SAMPLE_MP4: Path = ASSETS_DIR / "sample.mp4"
    RESULTS_JSON: Path = PROJECT_ROOT / "results.json"
    LOG_FILE: Path = PROJECT_ROOT / "vrcvt.log"

    # Default Sample Video Test URLs
    DEFAULT_URLS: Dict[str, str] = {
        "Local MP4": "ASSET_LOCAL",
        "YouTube Video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "YouTube Music": "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
        "VRCDN RTSP": "rtspt://stream.vrcdn.live/live/wlk",
        "Eurofurence HLS": "https://stream.eurofurence.org/hls/test_hd.m3u8?streamkey=becoeZKyrxtPUDFVbsc8xaJoJ9B80e2J",
        "HTTPS Direct MP4": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
    }

    # VRChat yt-dlp Standard Parameters
    VRCHAT_USER_AGENT: str = "VRChat/2024.3.2"
    YTDLP_VRCHAT_ARGS: List[str] = [
        "--user-agent", VRCHAT_USER_AGENT,
        "--no-cache-dir",
        "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
    ]

    # Standard VRChat 4:3 Windowed Desktop Debug Launch Arguments
    VRCHAT_DEBUG_ARGS: List[str] = [
        "--desktop",
        "-screen-width", "1024",
        "-screen-height", "768",
        "-screen-fullscreen", "0",
        "--enable-debug-gui",
        "--enable-sdk-log-levels",
        "--enable-udon-debug-logging",
        "--enable-avpro-in-proton",
        "--disable-hw-video-decoding"
    ]

    # Default Video Test World ID (Eurofurence EF30)
    DEFAULT_TEST_WORLD_ID: str = "wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1"
