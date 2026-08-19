"""
VRCVideoTester (vrcvt) - VRChat Desktop Test Mode Launcher & Process Manager
"""

import os
import sys
import json
import subprocess
import atexit
from .config import (
    COLOR_RESET, COLOR_BOLD, COLOR_GREEN, COLOR_YELLOW, COLOR_CYAN,
    DEFAULT_TEST_WORLD_ID, VRCHAT_DEBUG_ARGS
)
from .discovery import find_vrchat_prefix

def cleanup_artifacts_and_zombies():
    """Clean up temporary files and kill any lingering Wine/Proton zombie processes/windows."""
    prefix_dir = find_vrchat_prefix()
    drive_c = os.path.join(prefix_dir, "pfx/drive_c")
    
    temp_files = [
        os.path.join(drive_c, "vrcvt_wmf_test.exe"),
        os.path.join(drive_c, "vrcvt_out.txt"),
        os.path.join(drive_c, "vrcvt_out.json"),
        os.path.join(drive_c, "sample.mp4"),
        "/tmp/ytdlp_out.txt",
        "/tmp/wmf_run.txt"
    ]
    
    for f in temp_files:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass
                
    target_procs = [
        "vrcvt_wmf_test.exe",
        "wmf_test.exe",
        "wineserver",
        "explorer.exe",
        "services.exe",
        "plugplay.exe",
        "svchost.exe",
        "conhost.exe"
    ]
    for proc in target_procs:
        try:
            subprocess.run(["pkill", "-9", "-f", proc], capture_output=True, timeout=3)
        except Exception:
            pass

atexit.register(cleanup_artifacts_and_zombies)

def launch_vrchat_in_desktop_test_mode(world_id=None, target_rank=1, best_config=None):
    """Launch VRChat in desktop mode using target ranking from results.json."""
    target_world_id = world_id or DEFAULT_TEST_WORLD_ID
    vrc_launch_uri = f"vrchat://launch?id={target_world_id}"

    # Try loading target rank configuration from results.json
    selected_config = best_config
    if not selected_config:
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(package_dir)
        results_file = os.path.join(project_root, "results.json")
        if os.path.isfile(results_file):
            try:
                with open(results_file, "r") as f:
                    data = json.load(f)
                rankings = data.get("rankings", [])
                for r in rankings:
                    if r.get("rank") == target_rank:
                        selected_config = r
                        break
            except Exception:
                pass

    # Kill any lingering zombie/reaper processes from prior runs that lock Steam AppId 438100
    try:
        subprocess.run(["pkill", "-f", "reaper SteamLaunch AppId=438100"], capture_output=True)
        subprocess.run(["pkill", "-f", "VRChat.exe"], capture_output=True)
    except Exception:
        pass

    print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} [--try #{target_rank}] Launching VRChat in Desktop Mode for Debug Log Scraping{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f" Target World ID : {target_world_id}")
    print(f" Selected Rank   : #{target_rank}")
    if selected_config:
        print(f" Proton Tool     : {COLOR_YELLOW}{selected_config.get('proton_name', 'Default')}{COLOR_RESET}")
        print(f" Env Config      : {COLOR_GREEN}{selected_config.get('env_str', 'Default')}{COLOR_RESET}")
        print(f" Launch Command  : {selected_config.get('launch_cmd', '')}")
    print(f" Debug Args      : {' '.join(VRCHAT_DEBUG_ARGS)}")
    print()

    # Launch directly via Steam URI protocol / bazzite-steam applaunch with explicit --desktop flag
    try:
        cmd = ["bazzite-steam", "-applaunch", "438100", "--desktop", f"--watch-world={target_world_id}"]
        subprocess.run(cmd, check=True)
        print(f"{COLOR_GREEN}[✓] Triggered VRChat desktop launch via bazzite-steam -applaunch.{COLOR_RESET}")
    except Exception:
        try:
            cmd = ["steam", f"steam://rungameid/438100//{vrc_launch_uri}"]
            subprocess.run(cmd, check=True)
            print(f"{COLOR_GREEN}[✓] Triggered VRChat desktop launch via steam:// protocol.{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}[!] Failed to launch VRChat via Steam: {e}{COLOR_RESET}")
