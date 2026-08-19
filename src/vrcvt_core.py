#!/usr/bin/env python3
"""
VRCVideoTester (vrcvt) - Comprehensive VRChat Video Player Compatibility Tester
Repository: https://github.com/Bluscream/vrcvt
"""

import sys
import os
import time
import subprocess
import json
import argparse
import glob
import atexit
import shutil
from pathlib import Path
from collections import defaultdict

# ANSI Terminal Formatting
COLOR_RESET = "\033[0m"
COLOR_BOLD = "\033[1m"
COLOR_RED = "\033[31m"
COLOR_GREEN = "\033[32m"
COLOR_YELLOW = "\033[33m"
COLOR_CYAN = "\033[36m"
COLOR_GRAY = "\033[90m"

# Default Sample Test URLs
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

# Standard VRChat Debug & Logging Launch Arguments
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

def resolve_url_ytdlp(proton_bin, prefix_dir, url):
    """Resolve video URL using VRChat's yt-dlp.exe."""
    if url.startswith("ASSET_LOCAL") or os.path.exists(url) or url.startswith("C:\\"):
        return url, 0.0, 1, None, False

    ytdlp_exe = os.path.join(prefix_dir, "pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat/Tools/yt-dlp.exe")
    
    start_t = time.time()
    try:
        if os.path.isfile(ytdlp_exe):
            env = os.environ.copy()
            env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = os.path.expanduser("~/.local/share/Steam")
            env["STEAM_COMPAT_DATA_PATH"] = prefix_dir
            cmd = [proton_bin, "run", ytdlp_exe, "-g"] + YTDLP_VRCHAT_ARGS_DEFAULT + [url]
        else:
            cmd = ["yt-dlp", "-g"] + YTDLP_VRCHAT_ARGS_DEFAULT + [url]
            
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        elapsed_ms = (time.time() - start_t) * 1000.0
        
        if res.returncode == 0:
            urls = [line.strip() for line in res.stdout.splitlines() if line.strip().startswith("http")]
            if urls:
                return urls[-1], elapsed_ms, 1, None, False
                
        error_msg = res.stderr.strip() or f"Exit code {res.returncode}"
    except Exception as e:
        elapsed_ms = (time.time() - start_t) * 1000.0
        error_msg = str(e)

    # SSL Certificate Fallback Retry
    is_ssl_err = "SSL" in error_msg or "CERTIFICATE_VERIFY_FAILED" in error_msg or "certificate" in error_msg.lower()
    if is_ssl_err:
        start_t_retry = time.time()
        try:
            cmd_retry = cmd + ["--no-check-certificates"]
            res_retry = subprocess.run(cmd_retry, capture_output=True, text=True, timeout=12)
            elapsed_ms_retry = (time.time() - start_t_retry) * 1000.0
            
            if res_retry.returncode == 0:
                urls = [line.strip() for line in res_retry.stdout.splitlines() if line.strip().startswith("http")]
                if urls:
                    return urls[-1], elapsed_ms + elapsed_ms_retry, 2, None, True
        except Exception:
            pass

    return url, elapsed_ms, 1, error_msg[:100], False

def run_wmf_test(proton_bin, prefix_dir, wmf_exe, url, env_vars, retries=1):
    """Run wmf_test.exe inside an isolated per-tool sandbox prefix to capture timing and HRESULTs without prefix upgrade delays."""
    tool_folder = os.path.basename(os.path.dirname(proton_bin)) if os.path.basename(proton_bin) == "proton" else "default"
    clean_tool_folder = "".join([c if c.isalnum() else "_" for c in tool_folder])
    sandbox_prefix = f"/tmp/vrcvt_prefix_{clean_tool_folder}"
    os.makedirs(sandbox_prefix, exist_ok=True)

    if not os.path.isfile(wmf_exe):
        return {
            "success": False,
            "error_type": "MISSING_HARNESS_BINARY",
            "solution": f"Build wmf_test.exe at {wmf_exe}",
            "elapsed_ms": 0.0,
            "hresult": "N/A"
        }

    env = os.environ.copy()
    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = os.path.expanduser("~/.local/share/Steam")
    env["STEAM_COMPAT_DATA_PATH"] = sandbox_prefix
    env["WINEDEBUG"] = "-all"
    
    # Merge WINEDLLOVERRIDES to disable conhost and winemenubuilder window creation
    override_base = "winemenubuilder.exe=d;conhost.exe=d"
    if "WINEDLLOVERRIDES" in env_vars:
        override_base = f"{override_base};{env_vars['WINEDLLOVERRIDES']}"
    
    env.update(env_vars)
    env["WINEDLLOVERRIDES"] = override_base

    c_wmf = os.path.join(sandbox_prefix, "pfx/drive_c/vrcvt_wmf_test.exe")
    try:
        os.makedirs(os.path.dirname(c_wmf), exist_ok=True)
        shutil.copy2(wmf_exe, c_wmf)
    except Exception:
        pass

    c_result_json = os.path.join(sandbox_prefix, "pfx/drive_c/vrcvt_result.json")
    if os.path.isfile(c_result_json):
        try:
            os.remove(c_result_json)
        except Exception:
            pass

    for attempt in range(1, retries + 1):
        start_t = time.time()
        try:
            cmd = [proton_bin, "run", c_wmf, url, "--json"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10, env=env)
            elapsed_ms = (time.time() - start_t) * 1000.0
            
            stdout = res.stdout
            stderr = res.stderr + "\n" + stdout
            
            json_data = None

            # First try loading result from c_result_json file
            if os.path.isfile(c_result_json):
                try:
                    with open(c_result_json, "r") as f:
                        json_data = json.load(f)
                except Exception:
                    pass

            if not json_data:
                first_brace = stdout.find("{")
                last_brace = stdout.rfind("}")
                if first_brace != -1 and last_brace > first_brace:
                    try:
                        json_data = json.loads(stdout[first_brace:last_brace+1])
                    except Exception:
                        pass

            if not json_data:
                for line in stdout.splitlines():
                    line = line.strip()
                    if line.startswith("{") and line.endswith("}"):
                        try:
                            json_data = json.loads(line)
                            break
                        except Exception:
                            pass
            
            if json_data and json_data.get("resolver_success") and json_data.get("reader_success"):
                return {
                    "success": True,
                    "error_type": None,
                    "solution": "Working correctly",
                    "elapsed_ms": json_data.get("total_ms", elapsed_ms),
                    "hresult": json_data.get("resolver_hresult", "0x00000000"),
                    "attempts": attempt
                }
                
            hresult = json_data.get("resolver_hresult", "0x80004005") if json_data else "0x80004005"
            
            error_type = "UNKNOWN_ERROR"
            solution = "Inspect logs"
            
            if "libbz2.so.1.0" in stderr or "libavcodec.so.58" in stderr:
                error_type = "MISSING_SHARED_LIBS"
                solution = "Populate libbz2.so.1.0 & libavcodec.so.58 in Proton files/lib/x86_64-linux-gnu/"
            elif "%COMPAT" in stderr or "GnuTLS" in stderr or "GLib-Net" in stderr:
                error_type = "SSL_GNUTLS_ERROR"
                solution = "Set G_TLS_GNUTLS_PRIORITY=NORMAL in launch options"
            elif "No decoder available for type" in stderr:
                error_type = "GSTREAMER_DECODER_MISSING"
                solution = "Pass --disable-hw-video-decoding and use software FFmpeg decode"
            elif "failed to allocate udp ports" in stderr or "rtspsrc" in stderr and "error" in stderr:
                error_type = "RTSP_UDP_BLOCKED"
                solution = "Use rtspt:// (RTSP over TCP) instead of rtsp:// (UDP)"
            elif hresult in ["0x80072EE7", "0x80072EE2"]:
                error_type = "DNS_NETWORK_ERROR"
                solution = "Check system DNS resolver (/etc/resolv.conf) & internet connection"
            elif hresult in ["0x80072F8F", "0x80090327"]:
                error_type = "SSL_CERT_ERROR"
                solution = "Set SSL_CERT_FILE=/etc/pki/tls/certs/ca-bundle.crt"
            elif hresult == "0xC00D36BB":
                error_type = "UNSUPPORTED_BYTESTREAM_OR_DECODER_FAILED"
                solution = "Fix GStreamer libav dependencies or enable --enable-avpro-in-proton"

            return {
                "success": False,
                "error_type": error_type,
                "solution": solution,
                "elapsed_ms": elapsed_ms,
                "hresult": hresult,
                "attempts": attempt,
                "stderr_snippet": stderr[:300]
            }

        except subprocess.TimeoutExpired:
            elapsed_ms = (time.time() - start_t) * 1000.0
            if attempt == retries:
                return {
                    "success": False,
                    "error_type": "TIMEOUT",
                    "solution": "Stream resolution or network connection timed out",
                    "elapsed_ms": elapsed_ms,
                    "hresult": "TIMEOUT",
                    "attempts": attempt
                }
        except Exception as e:
            return {
                "success": False,
                "error_type": "EXEC_ERROR",
                "solution": str(e),
                "elapsed_ms": 0.0,
                "hresult": "ERROR",
                "attempts": attempt
            }

def launch_vrchat_in_desktop_test_mode(world_id=None, target_rank=1, best_config=None):
    """Launch VRChat in desktop mode using target ranking from results.json."""
    target_world_id = world_id or DEFAULT_TEST_WORLD_ID
    vrc_launch_uri = f"vrchat://launch?id={target_world_id}"

    # Try loading target rank configuration from results.json
    selected_config = best_config
    if not selected_config:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir) if os.path.basename(script_dir) == "src" else script_dir
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
            print(f"{COLOR_GREEN}[✓] Triggered VRChat launch via Steam URI protocol.{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}[!] Failed to launch VRChat: {e}{COLOR_RESET}")

def run_matrix_test(custom_url=None, try_launch=False):
    """Run diagnostic matrix tests across Proton versions and configuration flags with high-precision timing."""
    suite_start_t = time.time()
    from datetime import datetime

    check_and_unlock_h264()
    proton_list = find_proton_tools()
    prefix_dir = find_vrchat_prefix()
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir) if os.path.basename(script_dir) == "src" else script_dir
    wmf_exe = os.path.join(project_root, "assets/wmf_test.exe")
    local_mp4 = os.path.join(project_root, "assets/sample.mp4")

    c_sample = os.path.join(prefix_dir, "pfx/drive_c/sample.mp4")
    if os.path.isfile(local_mp4):
        try:
            shutil.copy2(local_mp4, c_sample)
        except Exception:
            pass

    now_str = datetime.now().strftime("[%H:%M:%S]")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} VRCVideoTester (vrcvt) - Full Diagnostic Matrix & Compatibility Benchmark{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f" {now_str} Benchmark Start Time  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f" Discovered Proton Tools : {len(proton_list)}")
    print(f" Target VRChat Prefix    : {prefix_dir}")
    print(f" WMF Harness Binary      : {wmf_exe}")
    print(f" Bundled Local Asset     : {local_mp4}")
    print()

    if not proton_list:
        print(f"{COLOR_RED}[!] No Proton compatibility tools found.{COLOR_RESET}")
        return

    # Select URLs to test (Full testing across all sample streams is mandatory)
    urls_to_test = {}
    if custom_url:
        urls_to_test["Custom URL"] = custom_url
    else:
        urls_to_test = DEFAULT_URLS.copy()
        urls_to_test["Local MP4"] = "C:\\sample.mp4"

    env_configs = [
        ("Full VRChat Env", {"WINEDLLOVERRIDES": "iyuv_32=", "G_TLS_GNUTLS_PRIORITY": "NORMAL"}),
        ("GnuTLS Normal", {"G_TLS_GNUTLS_PRIORITY": "NORMAL"}),
        ("IYUV Override", {"WINEDLLOVERRIDES": "iyuv_32="}),
        ("Default (Unset)", {})
    ]

    # Pre-resolve test URLs upfront (once for the suite) to eliminate redundant yt-dlp invocations across all 11 Proton tools
    primary_p_bin = proton_list[0][2]
    resolved_url_map = {}
    print(f" {now_str} Pre-resolving stream URLs via yt-dlp...")
    for url_label, raw_url in urls_to_test.items():
        url_target = "C:\\sample.mp4" if raw_url == "ASSET_LOCAL" else raw_url
        res_info = resolve_url_ytdlp(primary_p_bin, prefix_dir, url_target)
        resolved_url_map[url_label] = res_info
    print(f" {datetime.now().strftime('[%H:%M:%S]')} All stream URLs resolved successfully.\n")

    results = []

    for p_name, p_dir, p_bin in proton_list:
        p_start_t = time.time()
        p_now = datetime.now().strftime("[%H:%M:%S]")
        print(f"{p_now} {COLOR_BOLD}-> Testing Compatibility Tool: {COLOR_YELLOW}{p_name}{COLOR_RESET}")
        
        for url_label, raw_url in urls_to_test.items():
            res_url, ytdlp_ms, ytdlp_attempts, ytdlp_err, ssl_bypass_used = resolved_url_map[url_label]
            
            for env_label, env_vars in env_configs:
                test_result = run_wmf_test(p_bin, prefix_dir, wmf_exe, res_url, env_vars)
                test_result["proton_name"] = p_name
                test_result["url_label"] = url_label
                test_result["env_label"] = env_label
                test_result["env_vars"] = env_vars
                test_result["ytdlp_ms"] = ytdlp_ms
                test_result["wmf_ms"] = test_result["elapsed_ms"]
                test_result["total_subtest_ms"] = ytdlp_ms + test_result["elapsed_ms"]
                test_result["ytdlp_err"] = ytdlp_err
                test_result["ssl_bypass_used"] = ssl_bypass_used
                results.append(test_result)

        p_elapsed_sec = time.time() - p_start_t
        print(f"    {COLOR_GRAY}[✓ Finished {p_name} in {p_elapsed_sec:.1f}s]{COLOR_RESET}")

    suite_elapsed_sec = time.time() - suite_start_t
    mins = int(suite_elapsed_sec // 60)
    secs = suite_elapsed_sec % 60

    # Print Summary Matrix Table
    print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} DIAGNOSTIC MATRIX SUMMARY RESULTS (Total Runtime: {mins}m {secs:.1f}s / {suite_elapsed_sec:.1f}s){COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f"{'PROTON TOOL':<22} | {'STREAM TYPE':<16} | {'ENV CONFIG':<18} | {'STATUS':<8} | {'WMF(ms)':<8} | {'YTDLP(ms)':<9} | {'PRIMARY SOLUTION'}")
    print("-" * 120)

    for r in results:
        status_str = f"{COLOR_GREEN}PASS{COLOR_RESET}" if r["success"] else f"{COLOR_RED}FAIL{COLOR_RESET}"
        wmf_time_str = f"{r['wmf_ms']:.0f}ms"
        ytdlp_time_str = f"{r['ytdlp_ms']:.0f}ms"
        sol_str = r["solution"][:40]

        if r.get("ssl_bypass_used"):
            sol_str = f"[SSL Fix: --no-check-certificates] {sol_str}"

        print(f"{r['proton_name'][:22]:<22} | {r['url_label'][:16]:<16} | {r['env_label'][:18]:<18} | {status_str:<17} | {wmf_time_str:<8} | {ytdlp_time_str:<9} | {sol_str}")

    print("-" * 120)
    print(f"{COLOR_BOLD}Overall Suite Execution Time: {mins} minutes {secs:.1f} seconds ({suite_elapsed_sec:.1f} seconds total){COLOR_RESET}")
    print()

    # Dynamic Ranking of Combinations (Best to Worst by Pass Count & Timing)
    combo_stats = defaultdict(lambda: {"pass_count": 0, "total_tests": 0, "total_ms": 0.0, "env_vars": {}, "env_label": "", "proton_name": ""})
    tool_timing = defaultdict(lambda: {"total_wmf_ms": 0.0, "total_ytdlp_ms": 0.0, "count": 0, "elapsed_sec": 0.0})
    
    total_ytdlp_ms_all = 0.0
    total_wmf_ms_all = 0.0

    for r in results:
        key = (r["proton_name"], r["env_label"])
        combo = combo_stats[key]
        combo["proton_name"] = r["proton_name"]
        combo["env_label"] = r["env_label"]
        combo["env_vars"] = r["env_vars"]
        combo["total_tests"] += 1
        combo["total_ms"] += r["elapsed_ms"]
        if r["success"]:
            combo["pass_count"] += 1

        tt = tool_timing[r["proton_name"]]
        tt["total_wmf_ms"] += r["wmf_ms"]
        tt["total_ytdlp_ms"] += r["ytdlp_ms"]
        tt["count"] += 1

        total_ytdlp_ms_all += r["ytdlp_ms"]
        total_wmf_ms_all += r["wmf_ms"]

    # Print Detailed Timing & Bottleneck Analysis
    total_ytdlp_sec = total_ytdlp_ms_all / 1000.0
    total_wmf_sec = total_wmf_ms_all / 1000.0
    container_overhead_sec = max(0.0, suite_elapsed_sec - (total_ytdlp_sec + total_wmf_sec))

    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} DETAILED SUITE TIMING & BOTTLENECK ANALYSIS{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f" Total Benchmark Suite Runtime : {COLOR_BOLD}{mins}m {secs:.1f}s ({suite_elapsed_sec:.1f}s total){COLOR_RESET}")
    print(f" Total Sub-Tests Executed      : {len(results)} sub-tests")
    print(f" Total yt-dlp Resolution Time  : {total_ytdlp_sec:.1f}s ({total_ytdlp_sec/suite_elapsed_sec*100:.1f}% of total runtime)")
    print(f" Total WMF Harness Execution   : {total_wmf_sec:.1f}s ({total_wmf_sec/suite_elapsed_sec*100:.1f}% of total runtime)")
    print(f" Container & Process Overhead  : {container_overhead_sec:.1f}s ({container_overhead_sec/suite_elapsed_sec*100:.1f}% of total runtime)")
    print(f" Average Sub-Test Latency      : {(suite_elapsed_sec/max(len(results),1))*1000:.0f}ms / sub-test")
    print()
    print(f" {COLOR_BOLD}PER-TOOL RUNTIME BREAKDOWN:{COLOR_RESET}")
    for p_name, t_info in tool_timing.items():
        avg_wmf = t_info["total_wmf_ms"] / max(t_info["count"], 1)
        avg_ytdlp = t_info["total_ytdlp_ms"] / max(t_info["count"], 1)
        print(f"   • {p_name:<26} : Avg WMF Decode = {avg_wmf:.0f}ms | Avg yt-dlp = {avg_ytdlp:.0f}ms")
    print()

    ranked_combos = []
    for (p_name, e_label), stats in combo_stats.items():
        avg_ms = stats["total_ms"] / max(stats["total_tests"], 1)
        env_str = " ".join([f'{k}="{v}"' if ' ' in v else f'{k}={v}' for k, v in stats["env_vars"].items()])
        ranked_combos.append({
            "proton_name": p_name,
            "env_label": e_label,
            "env_vars": stats["env_vars"],
            "env_str": env_str,
            "pass_count": stats["pass_count"],
            "total_tests": stats["total_tests"],
            "avg_ms": avg_ms
        })

    # Sort: Pass Count (descending), then Avg Execution Time (ascending - fastest first!)
    ranked_combos.sort(key=lambda x: (-x["pass_count"], x["avg_ms"]))

    # Save benchmark rankings to results.json
    results_file = os.path.join(project_root, "results.json")
    try:
        data = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "rankings": []
        }
        for idx, c in enumerate(ranked_combos, 1):
            data["rankings"].append({
                "rank": idx,
                "proton_name": c["proton_name"],
                "env_label": c["env_label"],
                "env_vars": c["env_vars"],
                "env_str": c["env_str"],
                "pass_count": c["pass_count"],
                "total_tests": c["total_tests"],
                "avg_ms": round(c["avg_ms"], 1),
                "launch_cmd": f"{c['env_str']} %command% --enable-avpro-in-proton --disable-hw-video-decoding".strip()
            })
        with open(results_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"{COLOR_GREEN}[✓] Saved benchmark rankings to {results_file}{COLOR_RESET}\n")
    except Exception as e:
        print(f"{COLOR_RED}[!] Failed to save results.json: {e}{COLOR_RESET}")

    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} DYNAMIC RANKED RECOMMENDATIONS (BEST TO WORST BY PASS RATE & TIMING){COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")

    for idx, c in enumerate(ranked_combos, 1):
        status_tag = f"{COLOR_GREEN}PASS{COLOR_RESET}" if c['pass_count'] == c['total_tests'] else (f"{COLOR_YELLOW}PARTIAL{COLOR_RESET}" if c['pass_count'] > 0 else f"{COLOR_RED}FAIL{COLOR_RESET}")
        rank_tag = f"{COLOR_GREEN}#1 BEST{COLOR_RESET}" if idx == 1 else f"#{idx}"
        env_cmd = f"{c['env_str']} %command% --enable-avpro-in-proton --disable-hw-video-decoding".strip()
        print(f" {rank_tag}: {status_tag}")
        print(f"     Pass Rate : {c['pass_count']}/{c['total_tests']} Passed ({c['avg_ms']:.0f}ms avg)")
        print(f"     Proton: {COLOR_YELLOW}{c['proton_name']}{COLOR_RESET}")
        print(f"     Launch Cmd: {COLOR_BOLD}{env_cmd}{COLOR_RESET}")
        print()

    if try_launch:
        rank_num = try_launch if isinstance(try_launch, int) else 1
        launch_vrchat_in_desktop_test_mode(target_rank=rank_num)

    cleanup_artifacts_and_zombies()

def main():
    parser = argparse.ArgumentParser(description="VRCVideoTester (vrcvt) - Dynamic VRChat Video Player Compatibility Benchmark")
    parser.add_argument("--url", type=str, help="Test a specific video or stream URL")
    parser.add_argument("--try", dest="try_rank", nargs="?", const=1, type=int, help="Launch VRChat in Desktop mode using target ranking number (e.g. --try 1, --try 2, --try 3)")
    parser.add_argument("--no-tests", dest="no_tests", action="store_true", help="Skip benchmark testing phase and launch VRChat directly")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results for automated tools")
    args = parser.parse_args()

    if args.no_tests:
        rank_num = args.try_rank if args.try_rank else 1
        launch_vrchat_in_desktop_test_mode(target_rank=rank_num)
    else:
        run_matrix_test(custom_url=args.url, try_launch=args.try_rank)

if __name__ == "__main__":
    main()
