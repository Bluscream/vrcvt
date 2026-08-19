"""
VRCVideoTester (vrcvt) - System & Proton Compatibility Tool Discovery
"""

import os
import glob
import subprocess
from .config import COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_RESET

def find_proton_tools():
    """Discover installed Proton versions on the system, deduplicating symlinked paths."""
    seen_realpaths = set()
    proton_list = []
    
    search_paths = [
        os.path.expanduser("~/.local/share/Steam/compatibilitytools.d/*"),
        os.path.expanduser("~/.steam/steam/compatibilitytools.d/*"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/*"),
        os.path.expanduser("~/.local/share/Steam/steamapps/common/Proton*"),
        "/run/media/system/Data/Games/Steam/steamapps/common/Proton*"
    ]
    
    for path_glob in search_paths:
        for entry in glob.glob(path_glob):
            real_entry = os.path.realpath(entry)
            if real_entry in seen_realpaths:
                continue
                
            proton_bin = os.path.join(real_entry, "proton")
            if os.path.isfile(proton_bin) and os.access(proton_bin, os.X_OK):
                tool_name = os.path.basename(real_entry)
                seen_realpaths.add(real_entry)
                proton_list.append((tool_name, real_entry, proton_bin))
                
    return sorted(proton_list, key=lambda x: x[0])

def check_and_unlock_h264():
    """Verify if Steam's H.264 codec payload (mfh264enc.dll) is unlocked, and auto-trigger unlock if missing."""
    global_pfx = os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/0/pfx/drive_c/windows/system32/mfh264enc.dll")
    if not os.path.isfile(global_pfx):
        print(f"{COLOR_YELLOW}[!] H.264 codec payload (mfh264enc.dll) not found in Steam runtime. Triggering steam://unlockh264/...{COLOR_RESET}")
        try:
            subprocess.run(["steam", "steam://unlockh264/"], capture_output=True, timeout=5)
            print(f"{COLOR_GREEN}[✓] Triggered steam://unlockh264/ payload installation.{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}[!] Failed to trigger steam://unlockh264/: {e}{COLOR_RESET}")
    else:
        print(f"{COLOR_GREEN}[✓] H.264 codec payload (mfh264enc.dll) verified in Steam runtime.{COLOR_RESET}")

def find_vrchat_prefix():
    """Locate VRChat compatibility prefix data directory."""
    candidates = [
        "/run/media/system/Data/Games/Steam/steamapps/compatdata/438100",
        os.path.expanduser("~/.local/share/Steam/steamapps/compatdata/438100"),
        os.path.expanduser("~/.steam/steam/steamapps/compatdata/438100"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/steamapps/compatdata/438100")
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]
