"""
VRCVideoTester (vrcvt) - Global Configuration & Constants
"""

# ANSI Terminal Formatting Colors
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_CYAN = "\033[36m"
COLOR_GRAY = "\033[90m"

# Default Sample Video Test URLs
DEFAULT_URLS = {
    "Local MP4": "ASSET_LOCAL",
    "YouTube Video": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "YouTube Music": "https://music.youtube.com/watch?v=dQw4w9WgXcQ",
    "VRCDN RTSP": "rtspt://stream.vrcdn.live/live/wlk",
    "Eurofurence HLS": "https://stream.eurofurence.org/hls/test_hd.m3u8?streamkey=becoeZKyrxtPUDFVbsc8xaJoJ9B80e2J",
    "HTTPS Direct MP4": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"
}

# VRChat yt-dlp Standard Parameters
VRCHAT_USER_AGENT = "VRChat/2024.3.2"
YTDLP_VRCHAT_ARGS_DEFAULT = [
    "--user-agent", VRCHAT_USER_AGENT,
    "--no-cache-dir",
    "--format", "bestvideo[height<=1080]+bestaudio/best[height<=1080]/best"
]

# Standard VRChat 4:3 Windowed Desktop Debug Launch Arguments
VRCHAT_DEBUG_ARGS = [
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
DEFAULT_TEST_WORLD_ID = "wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1"
