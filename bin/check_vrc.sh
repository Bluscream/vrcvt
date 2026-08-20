#!/usr/bin/env bash
# check_vrc.sh - Diagnostic utility to inspect running VRChat process args, environment, compare against Steam VDF configuration, and parse latest log details

set -e

# Helper function to extract exact version strings (v2.2.3, vN-126217, 2026.08.19)
get_file_version() {
    local file=$1
    if [ ! -f "$file" ]; then echo ""; return; fi
    local ver
    ver=$(python3 -c '
import sys, re
try:
    with open(sys.argv[1], "rb") as f:
        data = f.read(140000000)
    
    # FFmpeg version
    m = re.search(rb"FFmpeg version ([a-zA-Z0-9\.\-]+)", data)
    if m:
        full = m.group(1).decode("ascii")
        parts = full.split("-")
        short = parts[0] + ("-" + parts[1] if len(parts) > 1 else "")
        print("v" + short); sys.exit(0)

    # PE Version (Deno, etc.)
    for key in (b"P\x00r\x00o\x00d\x00u\x00c\x00t\x00V\x00e\x00r\x00s\x00i\x00o\x00n\x00", b"F\x00i\x00l\x00e\x00V\x00e\x00r\x00s\x00i\x00o\x00n\x00"):
        pos = data.find(key)
        if pos != -1:
            match = re.search(r"([0-9]+(?:\.[0-9]+)+)", data[pos+len(key):pos+len(key)+80].decode("utf-16le", errors="ignore"))
            if match and match.group(1) not in ("1.0.0", "1.0.0.0"):
                print("v" + match.group(1)); sys.exit(0)

    # yt-dlp date format e.g. 2026.08.19
    match = re.search(rb"(202[0-9]\.[0-9]{2}\.[0-9]{2})", data)
    if match: print(match.group(1).decode("ascii")); sys.exit(0)
except Exception: pass
' "$file" 2>/dev/null || true)

    if [ -n "$ver" ]; then
        echo "$ver"
    else
        # Fallback to date
        stat -c '%y' "$file" 2>/dev/null | cut -d' ' -f1
    fi
}

# Locate latest log file quickly at top for async background yt-dlp check
LOG_DIRS=(
    "$HOME/.local/share/Steam/steamapps/compatdata/438100/pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat"
    "/run/media/system/Data/Games/Steam/steamapps/compatdata/438100/pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat"
)

LATEST_LOG=""
for DIR in "${LOG_DIRS[@]}"; do
    if [ -d "$DIR" ]; then
        FOUND=$(ls -t "$DIR"/output_log_*.txt 2>/dev/null | head -n 1 || true)
        if [ -n "$FOUND" ]; then LATEST_LOG="$FOUND"; break; fi
    fi
done

ORIGINAL_REQ_URL=""
if [ -n "$LATEST_LOG" ] && [ -f "$LATEST_LOG" ]; then
    ORIGINAL_REQ_URL=$(grep -E -i "Attempting to resolve URL" "$LATEST_LOG" 2>/dev/null | tail -n 1 | sed -E "s/.*Attempting to resolve URL '//; s/'\s*$//" || true)
fi

# Clean temp files
rm -f /tmp/check_vrc_ytdlp_test.txt /tmp/check_vrc_ytdlp_tag.txt /tmp/check_vrc_deno_tag.txt /tmp/check_vrc_ffmpeg_tag.txt

# Start background async tasks with nohup so bash does not block early script execution
if [ -n "$ORIGINAL_REQ_URL" ] && [ "$ORIGINAL_REQ_URL" != "None recorded" ]; then
    nohup yt-dlp --no-cache-dir --no-playlist --socket-timeout 3 -g "$ORIGINAL_REQ_URL" > /tmp/check_vrc_ytdlp_test.txt 2>&1 &
fi
nohup bash -c 'curl -s --max-time 2 "https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest" 2>/dev/null | grep '"'"'"tag_name"'"'"' | sed -E '"'"'s/.*"tag_name"\s*:\s*"([^"]+)".*/\1/'"'"' > /tmp/check_vrc_ytdlp_tag.txt' >/dev/null 2>&1 &
nohup bash -c 'curl -s --max-time 2 "https://api.github.com/repos/denoland/deno/releases/latest" 2>/dev/null | grep '"'"'"tag_name"'"'"' | sed -E '"'"'s/.*"tag_name"\s*:\s*"v?([^"]+)".*/\1/'"'"' > /tmp/check_vrc_deno_tag.txt' >/dev/null 2>&1 &
nohup bash -c 'curl -s --max-time 2 "https://api.github.com/repos/BtbN/FFmpeg-Builds/releases/latest" 2>/dev/null | grep '"'"'"tag_name"'"'"' | sed -E '"'"'s/.*"tag_name"\s*:\s*"([^"]+)".*/\1/'"'"' > /tmp/check_vrc_ffmpeg_tag.txt' >/dev/null 2>&1 &

echo "========================================================================"
echo " VRChat Diagnostic Inspector & Steam Comparison Tool (check_vrc.sh)"
echo "========================================================================"

# Helper function to format relative time ago
format_relative_time() {
    local target_epoch=$1
    local now_epoch=$(date +%s)
    local diff=$((now_epoch - target_epoch))

    if [ $diff -lt 0 ]; then diff=0; fi

    if [ $diff -lt 60 ]; then
        echo "${diff}s ago"
    elif [ $diff -lt 3600 ]; then
        local mins=$((diff / 60))
        echo "${mins}m ago"
    elif [ $diff -lt 86400 ]; then
        local hours=$((diff / 3600))
        local mins=$(((diff % 3600) / 60))
        echo "${hours}h ${mins}m ago"
    else
        local days=$((diff / 86400))
        local hours=$(((diff % 86400) / 3600))
        echo "${days}d ${hours}h ago"
    fi
}

# 1. READ CONFIGURATION STORED IN STEAM VDF FILES
CONFIG_VDF=$(find "$HOME/.local/share/Steam/config" "$HOME/.steam/steam/config" /run/media/system/Data/Games/Steam/config -name "config.vdf" 2>/dev/null | head -n 1 || true)
LOCALCONFIG_VDF=$(find "$HOME/.local/share/Steam/userdata" "$HOME/.steam/steam/userdata" /run/media/system/Data/Games/Steam/userdata -name "localconfig.vdf" 2>/dev/null | head -n 1 || true)

CONFIGURED_TOOL="None / Default"
CONFIGURED_CMD="None / Unset"
CONFIGURED_RUNTIME_APPID=""
CONFIGURED_RUNTIME_NAME="None / Default"

if [ -f "$CONFIG_VDF" ]; then
    VAL=$(grep -A 10 '"438100"' "$CONFIG_VDF" 2>/dev/null | grep '"name"' | head -n 1 | sed -E 's/.*"name"\s+"([^"]+)".*/\1/' || true)
    if [ -n "$VAL" ]; then CONFIGURED_TOOL="$VAL"; fi
fi

if [ -f "$LOCALCONFIG_VDF" ]; then
    VAL=$(grep -A 15 '"438100"' "$LOCALCONFIG_VDF" 2>/dev/null | grep '"LaunchOptions"' | head -n 1 | sed -E 's/.*"LaunchOptions"\s+"([^"]+)".*/\1/' | sed 's/\\"/"/g' || true)
    if [ -n "$VAL" ]; then CONFIGURED_CMD="$VAL"; fi
fi

# Locate toolmanifest.vdf for the configured Proton tool to read required Steam Linux Runtime
TOOL_DIRS=(
    "$HOME/.local/share/Steam/compatibilitytools.d/$CONFIGURED_TOOL"
    "$HOME/.steam/steam/compatibilitytools.d/$CONFIGURED_TOOL"
    "/run/media/system/Data/Games/Steam/compatibilitytools.d/$CONFIGURED_TOOL"
)

for TDIR in "${TOOL_DIRS[@]}"; do
    MANIFEST="$TDIR/toolmanifest.vdf"
    if [ -f "$MANIFEST" ]; then
        CONFIGURED_RUNTIME_APPID=$(grep '"require_tool_appid"' "$MANIFEST" | head -n 1 | sed -E 's/.*"require_tool_appid"\s+"([^"]+)".*/\1/' || true)
        case "$CONFIGURED_RUNTIME_APPID" in
            "4183110") CONFIGURED_RUNTIME_NAME="SteamLinuxRuntime_4 (AppID 4183110)" ;;
            "1391110") CONFIGURED_RUNTIME_NAME="SteamLinuxRuntime_sniper (AppID 1391110)" ;;
            "1070560") CONFIGURED_RUNTIME_NAME="SteamLinuxRuntime_soldier (AppID 1070560)" ;;
            "1628350") CONFIGURED_RUNTIME_NAME="SteamLinuxRuntime_medic (AppID 1628350)" ;;
            "") CONFIGURED_RUNTIME_NAME="None / Direct Host Execution" ;;
            *) CONFIGURED_RUNTIME_NAME="SteamLinuxRuntime (AppID $CONFIGURED_RUNTIME_APPID)" ;;
        esac
        break
    fi
done

echo -e "\n📌 STEAM VDF CONFIGURATION (Stored on Disk):"
echo "  Proton Tool          : $CONFIGURED_TOOL"
echo "  Required SLR Runtime : $CONFIGURED_RUNTIME_NAME"
echo "  Launch Options       : $CONFIGURED_CMD"

# 2. FIND RUNNING VRCHAT PROCESSES & COMPARE
VRCHAT_PIDS=$(pgrep -f "VRChat.exe" || true)

TOOL_MATCH_STR="❌ NO PROCESS"
SLR_MATCH_STR="❌ NO PROCESS"
LAUNCH_MATCH_STR="❌ NO PROCESS"

if [ -z "$VRCHAT_PIDS" ]; then
    echo -e "\n⚠️  No active VRChat.exe process found."
    echo ""
    echo "Checking related Steam / Proton wrapper processes:"
    ps aux | grep -i "vrchat" | grep -v "grep" | grep -v "check_vrc.sh" || echo "No VRChat processes running."
else
    for PID in $VRCHAT_PIDS; do
        echo ""
        echo "========================================================================"
        echo " 🕹️  ACTIVE VRCHAT PROCESS INSPECTION (PID: $PID)"
        echo "========================================================================"

        # Active Proton Tool Detection & Env Data Load
        ENV_DATA=$(tr '\0' '\n' < "/proc/$PID/environ" 2>/dev/null || true)
        ACTIVE_TOOL_PATH=$(echo "$ENV_DATA" | grep "^STEAM_COMPAT_TOOL_PATHS=" | cut -d'=' -f2 || true)
        ACTIVE_TOOL=$(basename "$(echo "$ACTIVE_TOOL_PATH" | cut -d':' -f1)" 2>/dev/null || echo "Unknown")

        # Active Steam Linux Runtime Detection
        ACTIVE_RUNTIME_BASE=$(echo "$ENV_DATA" | grep "^PRESSURE_VESSEL_RUNTIME_BASE=" | cut -d'=' -f2 || true)
        ACTIVE_RUNTIME_VER=$(echo "$ENV_DATA" | grep "^PRESSURE_VESSEL_RUNTIME=" | cut -d'=' -f2 || true)
        ACTIVE_RUNTIME_NAME=$(basename "$ACTIVE_RUNTIME_BASE" 2>/dev/null || echo "Unknown")

        # Active Command Line
        ACTIVE_CMD=$(tr '\0' ' ' < "/proc/$PID/cmdline" 2>/dev/null || true)

        # Tool Comparison
        if [[ "$ACTIVE_TOOL_PATH" == *"$CONFIGURED_TOOL"* ]] || [[ "$CONFIGURED_TOOL" == "$ACTIVE_TOOL" ]]; then
            TOOL_MATCH_STR="✅ MATCH ($ACTIVE_TOOL)"
        else
            TOOL_MATCH_STR="⚠️ MISMATCH (Steam: $CONFIGURED_TOOL | Active: $ACTIVE_TOOL)"
        fi

        # Steam Linux Runtime Comparison
        if [ -n "$CONFIGURED_RUNTIME_APPID" ]; then
            if [[ "$ACTIVE_RUNTIME_BASE" == *"$CONFIGURED_RUNTIME_APPID"* ]] || [[ "$CONFIGURED_RUNTIME_NAME" == *"$ACTIVE_RUNTIME_NAME"* ]]; then
                SLR_MATCH_STR="✅ MATCH ($ACTIVE_RUNTIME_NAME | $ACTIVE_RUNTIME_VER)"
            else
                SLR_MATCH_STR="⚠️ MISMATCH (Required: $CONFIGURED_RUNTIME_NAME | Active: $ACTIVE_RUNTIME_NAME)"
            fi
        else
            SLR_MATCH_STR="ℹ️ ACTIVE ($ACTIVE_RUNTIME_NAME | $ACTIVE_RUNTIME_VER)"
        fi

        # Fast In-Memory Command Line & Launch Option Comparison
        CMD_DIFF=0
        if [ "$CONFIGURED_CMD" != "None / Unset" ]; then
            for TOKEN in $CONFIGURED_CMD; do
                if [ "$TOKEN" == "%command%" ]; then continue; fi
                if [[ "$TOKEN" == *"="* ]]; then
                    KEY="${TOKEN%%=*}"
                    if [[ "$ENV_DATA" != *"$KEY"* ]] && [[ "$ACTIVE_CMD" != *"$KEY"* ]]; then
                        CMD_DIFF=1
                    fi
                elif [[ "$TOKEN" == "--"* ]]; then
                    if [[ "$ACTIVE_CMD" != *"$TOKEN"* ]]; then
                        CMD_DIFF=1
                    fi
                fi
            done
        fi

        if [ $CMD_DIFF -eq 0 ]; then
            LAUNCH_MATCH_STR="✅ MATCH (All flags and env vars active in process)"
        else
            LAUNCH_MATCH_STR="⚠️ DIFFERENCES DETECTED"
        fi

        echo -e "\n📋 PROCESS COMMAND LINE ARGUMENTS:"
        xargs -0 -n 1 < "/proc/$PID/cmdline" | grep -v "^\s*$" | sed 's/^/  /'

        echo -e "\n🌐 PROCESS ENVIRONMENT VARIABLES (Blacklist Filtered):"
        echo "$ENV_DATA" \
            | grep "=" \
            | grep -v -E "0x[0-9a-fA-F]{4}/0x[0-9a-fA-F]{4}" \
            | grep -v -E "^(PATH|PWD|HOME|USER|LOGNAME|SHELL|LANG|LC_|TERM|SHLVL|_|OLDPWD|XDG_|DBUS_|DESKTOP_SESSION|QT_|KDE_|GTK_|LS_COLORS|LESS|COLORTERM|WINDOWPATH|VTE_VERSION|GS_LIB|EDITOR|HIST|HOSTNAME|ICEAUTHORITY|INVOCATION_ID|JOURNAL_STREAM|MAIL|MANAGERPID|SUDO_|SYSTEMD_|TEXTDOMAIN|TZDIR|XAUTHORITY|XCURSOR_|XKB_|APPDIR|APPIMAGE|ARGV0|CARGO_|DEBUGINFOD_|AT_SPI_|GDK_|JAVA_|SDL_|Steam|32f5h290g|HASS_|MQTT_|MYSQL_|PULSE_|LIBAACS_|LIBBDPLUS_|ESPEAK_|GBM_|GIT_|BREAKPAD_|EAC_|MEMORY_|MESA_|ENABLE_|__GL_|__EGL_|DISPLAY|EGL_|GNUTLS_|LD_LIBRARY_PATH|LESSOPEN|LIBGL_|LIBVA_|ORIG_|OWD|SRT_|SSH_|VK_DRIVER_|VK_ICD_|VK_IMPLICIT_|VKD3D_|WINEDEBUG|WINEESYNC|WINEFSYNC|WINELOADER|WINE_MONO|WINE_LARGE|WINEPREFIX|WINE_CRASH|WINE_GST|XALIA_|container|SESSION_|UNITY_|.*TOKEN.*)=" \
            | grep -v "^\s*$" \
            | sort -u | sed 's/^/  /'
    done
fi

if [ -n "$LATEST_LOG" ] && [ -f "$LATEST_LOG" ]; then
    echo ""
    echo "========================================================================"
    echo " 📜 LAST 15 LOG LINES"
    echo "========================================================================"
    tail -n 15 "$LATEST_LOG" | sed 's/^/  /'

    echo ""
    echo "========================================================================"
    echo " 📄 SUMMARY"
    echo "========================================================================"

    # Timestamps & Relative Time
    CREATED_TIME=$(stat -c '%w' "$LATEST_LOG" 2>/dev/null || stat -c '%z' "$LATEST_LOG")
    CREATED_EPOCH=$(stat -c '%W' "$LATEST_LOG" 2>/dev/null || stat -c '%Z' "$LATEST_LOG")
    if [ "$CREATED_EPOCH" == "0" ] || [ -z "$CREATED_EPOCH" ]; then CREATED_EPOCH=$(stat -c '%Z' "$LATEST_LOG"); fi
    CREATED_AGO=$(format_relative_time "$CREATED_EPOCH")

    MODIFIED_TIME=$(stat -c '%y' "$LATEST_LOG")
    MODIFIED_EPOCH=$(stat -c '%Y' "$LATEST_LOG")
    MODIFIED_AGO=$(format_relative_time "$MODIFIED_EPOCH")

    # Extract VRChat Build & GPU Hardware
    VRC_BUILD=$(grep -E -i "VRChat Build:" "$LATEST_LOG" 2>/dev/null | head -n 1 | sed -E 's/.*VRChat Build:\s*//' || echo "Unknown")
    GPU_NAME=$(grep -E -i "Graphics Device Name:" "$LATEST_LOG" 2>/dev/null | head -n 1 | sed -E 's/.*Graphics Device Name:\s*//' || echo "Unknown")
    
    # Read background async GitHub release tags
    LATEST_YTDLP=$(cat /tmp/check_vrc_ytdlp_tag.txt 2>/dev/null || echo "")
    LATEST_DENO=$(cat /tmp/check_vrc_deno_tag.txt 2>/dev/null || echo "")
    LATEST_FFMPEG=$(cat /tmp/check_vrc_ffmpeg_tag.txt 2>/dev/null || echo "")

    # Extract VRChat Tools Status & Version (yt-dlp.exe, deno.exe, ffmpeg.exe)
    YTDLP_STATUS="❌ MISSING"
    DENO_STATUS="❌ MISSING"
    FFMPEG_STATUS="❌ MISSING"
    
    VRC_TOOLS_DIR="$(dirname "$LATEST_LOG")/Tools"
    if [ -d "$VRC_TOOLS_DIR" ]; then
        if [ -f "$VRC_TOOLS_DIR/yt-dlp.exe" ]; then
            YTDLP_VER=$(get_file_version "$VRC_TOOLS_DIR/yt-dlp.exe")
            if [ -n "$LATEST_YTDLP" ] && [[ "$YTDLP_VER" == *"${LATEST_YTDLP#v}"* ]]; then
                YTDLP_STATUS="✅ LATEST ($YTDLP_VER)"
            elif [ -n "$YTDLP_VER" ]; then
                YTDLP_STATUS="✅ LATEST ($YTDLP_VER)"
            else
                YTDLP_STATUS="⚠️ EXISTS"
            fi
        fi
        if [ -f "$VRC_TOOLS_DIR/deno.exe" ]; then
            DENO_VER=$(get_file_version "$VRC_TOOLS_DIR/deno.exe")
            if [ -n "$LATEST_DENO" ] && [[ "$DENO_VER" == *"${LATEST_DENO#v}"* ]]; then
                DENO_STATUS="✅ LATEST ($DENO_VER)"
            elif [ -n "$DENO_VER" ]; then
                DENO_STATUS="✅ LATEST ($DENO_VER)"
            else
                DENO_STATUS="⚠️ EXISTS"
            fi
        fi
        if [ -f "$VRC_TOOLS_DIR/ffmpeg.exe" ]; then
            FFMPEG_VER=$(get_file_version "$VRC_TOOLS_DIR/ffmpeg.exe")
            if [ -n "$FFMPEG_VER" ]; then
                FFMPEG_STATUS="✅ LATEST ($FFMPEG_VER)"
            else
                FFMPEG_STATUS="⚠️ EXISTS"
            fi
        fi
    fi

    # Extract Last Room Name & Instance Location
    LAST_ROOM_NAME=$(grep -E -i "\[Behaviour\] Entering Room:" "$LATEST_LOG" 2>/dev/null | tail -n 1 | sed -E 's/.*Entering Room:\s*//' || echo "Unknown")
    LAST_WORLD_ID=$(grep -E -i "\[Behaviour\] Joining wrld_" "$LATEST_LOG" 2>/dev/null | tail -n 1 | sed -E 's/.*Joining //; s/.*Joining world //' || echo "Unknown")
    
    # Extract Last Generic Warning and Error
    LAST_WARN=$(grep " Warning " "$LATEST_LOG" 2>/dev/null | tail -n 1 | sed -E 's/^[0-9.]+\s+[0-9:]+\s+Warning\s+-\s+//' || echo "None")
    LAST_ERR=$(grep " Error " "$LATEST_LOG" 2>/dev/null | tail -n 1 | sed -E 's/^[0-9.]+\s+[0-9:]+\s+Error\s+-\s+//' || echo "None")

    # Extract Video Details
    LAST_OPEN_LINE=$(grep -n "\[AVProVideo\] Opening\|resolved to" "$LATEST_LOG" 2>/dev/null | tail -n 1 || true)
    
    RESOLVED_STREAM_URL="None"
    VIDEO_STATUS="None"
    PIPELINE=""
    ERR_DETAILS=""

    if [ -n "$LAST_OPEN_LINE" ]; then
        line_num=$(echo "$LAST_OPEN_LINE" | cut -d':' -f1)
        RESOLVED_STREAM_URL=$(echo "$LAST_OPEN_LINE" | sed -E "s/.*resolved to '//; s/.*Opening //; s/'\s*$//; s/\s+\(offset 0\).*//")
        
        SUB_LOG=$(sed -n "${line_num},$((line_num+10))p" "$LATEST_LOG" 2>/dev/null)
        SUCCESS=$(echo "$SUB_LOG" | grep "Using playback path:" | head -n 1 | sed -E 's/.*Using playback path:\s*//')
        FAILURE=$(echo "$SUB_LOG" | grep "Error: Loading failed" | head -n 1 | sed -E 's/.*Error:\s*//')
        
        if [ -n "$SUCCESS" ]; then
            VIDEO_STATUS="✅ SUCCESS"
            PIPELINE="$SUCCESS"
        elif [ -n "$FAILURE" ]; then
            VIDEO_STATUS="⚠️ FAILED"
            ERR_DETAILS="$FAILURE"
        else
            VIDEO_STATUS="ℹ️ OPENED"
        fi
    fi

    # Wait specifically before outputting the single yt-dlp Live Check line
    YTDLP_VERIFICATION="None"
    if [ -n "$ORIGINAL_REQ_URL" ] && [ "$ORIGINAL_REQ_URL" != "None recorded" ]; then
        for i in {1..35}; do
            if [ -s /tmp/check_vrc_ytdlp_test.txt ]; then break; fi
            sleep 0.1
        done

        if [ -s /tmp/check_vrc_ytdlp_test.txt ]; then
            YTDLP_OUT=$(cat /tmp/check_vrc_ytdlp_test.txt)
            if [[ "$YTDLP_OUT" == *"http"* ]]; then
                YTDLP_VERIFICATION="✅ VALID (Stream Resolved)"
            else
                CLEAN_ERR=$(echo "$YTDLP_OUT" | grep -E "^ERROR:" | head -n 1 | sed 's/.*ERROR:\s*//')
                if [ -z "$CLEAN_ERR" ]; then CLEAN_ERR=$(echo "$YTDLP_OUT" | grep -v "No supported JavaScript" | head -n 1); fi
                YTDLP_VERIFICATION="⚠️ FAILED: $CLEAN_ERR"
            fi
        else
            YTDLP_VERIFICATION="⚠️ TIMED OUT"
        fi
    fi

    echo "📂 Log File Path       : $LATEST_LOG"
    echo "📏 Log File Size       : $(du -h "$LATEST_LOG" | cut -f1)"
    echo "🐣 Log File Created    : $CREATED_TIME ($CREATED_AGO)"
    echo "🕒 Log File Modified   : $MODIFIED_TIME ($MODIFIED_AGO)"
    echo "🎮 VRChat Build        : $VRC_BUILD"
    echo "🖥️  GPU Device          : $GPU_NAME"
    echo "🍷 Proton Tool          : $TOOL_MATCH_STR"
    echo "🐧 Steam Linux Runtime  : $SLR_MATCH_STR"
    echo "🚀 Launch Options       : $LAUNCH_MATCH_STR"
    echo "🛠️  VRChat yt-dlp.exe   : $YTDLP_STATUS"
    echo "🦕 VRChat deno.exe     : $DENO_STATUS"
    echo "🎞️  VRChat ffmpeg.exe   : $FFMPEG_STATUS"
    echo "🏷️  World Room Name     : $LAST_ROOM_NAME"
    echo "🌍 Location / World ID : $LAST_WORLD_ID"
    echo "⚠️  Last Warning        : $LAST_WARN"
    echo "❌ Last Error          : $LAST_ERR"
    echo "🎬 Last Video Status   : $VIDEO_STATUS"
    echo "🔗 Original Input URL  : $ORIGINAL_REQ_URL"
    echo "📡 Resolved Stream URL : $RESOLVED_STREAM_URL"
    if [ -n "$PIPELINE" ]; then echo "⚙️  Playback Pipeline   : $PIPELINE"; fi
    if [ -n "$ERR_DETAILS" ]; then echo "💥 Video Error Details : $ERR_DETAILS"; fi
    echo "🧪 yt-dlp Live Check   : $YTDLP_VERIFICATION"
else
    echo "⚠️  No output_log_*.txt file found in VRChat AppData directory."
fi

echo "========================================================================"
