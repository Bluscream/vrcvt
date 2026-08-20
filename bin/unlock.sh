#!/usr/bin/env bash
# unlock.sh - Unlock VRChat Tools folder and binaries with read/write permissions

set -e

TOOLS_DIRS=(
    "$HOME/.local/share/Steam/steamapps/compatdata/438100/pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat/Tools"
    "/run/media/system/Data/Games/Steam/steamapps/compatdata/438100/pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat/Tools"
)

TOOLS_DIR=""
for DIR in "${TOOLS_DIRS[@]}"; do
    if [ -d "$DIR" ]; then TOOLS_DIR="$DIR"; break; fi
done

if [ -z "$TOOLS_DIR" ]; then
    echo "⚠️  VRChat Tools directory not found."
    exit 1
fi

TARGET_YTDLP=false
TARGET_DENO=false
TARGET_FFMPEG=false

if [ $# -eq 0 ]; then
    TARGET_YTDLP=true
    TARGET_DENO=true
    TARGET_FFMPEG=true
else
    for arg in "$@"; do
        case "$arg" in
            --yt-dlp) TARGET_YTDLP=true ;;
            --deno) TARGET_DENO=true ;;
            --ffmpeg) TARGET_FFMPEG=true ;;
            *) echo "Unknown option: $arg"; exit 1 ;;
        esac
    done
fi

chmod 755 "$TOOLS_DIR"

if $TARGET_YTDLP && [ -f "$TOOLS_DIR/yt-dlp.exe" ]; then
    chmod 755 "$TOOLS_DIR/yt-dlp.exe"
    echo "🔓 Unlocked yt-dlp.exe (read/write)"
fi

if $TARGET_DENO && [ -f "$TOOLS_DIR/deno.exe" ]; then
    chmod 755 "$TOOLS_DIR/deno.exe"
    echo "🔓 Unlocked deno.exe (read/write)"
fi

if $TARGET_FFMPEG && [ -f "$TOOLS_DIR/ffmpeg.exe" ]; then
    chmod 755 "$TOOLS_DIR/ffmpeg.exe"
    echo "🔓 Unlocked ffmpeg.exe (read/write)"
fi
