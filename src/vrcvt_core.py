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

# Default Video Test World Instance (Eurofurence EF30 Public/Private Instance)
DEFAULT_TEST_WORLD_LOCATION = "wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1:19431~group(grp_3b67b24d-6ae2-484b-a0b6-c26255232370)~groupAccessType(public)~region(eu)"

def find_proton_tools(filter_name=None):
    """Discover installed Proton versions on the system."""
    proton_dirs = set()
    search_paths = [
        os.path.expanduser("~/.local/share/Steam/compatibilitytools.d/*"),
        os.path.expanduser("~/.steam/steam/compatibilitytools.d/*"),
        os.path.expanduser("~/.var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/*"),
        os.path.expanduser("~/.local/share/Steam/steamapps/common/Proton*"),
        "/run/media/system/Data/Games/Steam/steamapps/common/Proton*"
    ]
    
    for path_glob in search_paths:
        for entry in glob.glob(path_glob):
            proton_bin = os.path.join(entry, "proton")
            if os.path.isfile(proton_bin) and os.access(proton_bin, os.X_OK):
                tool_name = os.path.basename(entry)
                if filter_name and filter_name.lower() not in tool_name.lower():
                    continue
                proton_dirs.add((tool_name, entry, proton_bin))
                
    return sorted(list(proton_dirs), key=lambda x: x[0])

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
    """Run wmf_test.exe inside Proton prefix and capture timing, HRESULTs, and diagnostic errors."""
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
    env["STEAM_COMPAT_DATA_PATH"] = prefix_dir
    env.update(env_vars)

    c_wmf = os.path.join(prefix_dir, "pfx/drive_c/vrcvt_wmf_test.exe")
    try:
        shutil.copy2(wmf_exe, c_wmf)
    except Exception:
        pass

    for attempt in range(1, retries + 1):
        start_t = time.time()
        try:
            out_json_path = os.path.join(prefix_dir, "pfx/drive_c/vrcvt_out.json")
            if os.path.exists(out_json_path):
                os.remove(out_json_path)

            cmd = [proton_bin, "run", "cmd.exe", "/c", f"C:\\vrcvt_wmf_test.exe \"{url}\" --json > C:\\vrcvt_out.json 2>&1"]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12, env=env)
            elapsed_ms = (time.time() - start_t) * 1000.0
            
            stdout = ""
            if os.path.exists(out_json_path):
                with open(out_json_path, "r", errors="ignore") as f:
                    stdout = f.read()

            stderr = res.stderr + "\n" + stdout
            
            json_data = None
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

def launch_vrchat_in_desktop_test_mode(world_location=None):
    """Launch VRChat in desktop mode with full debug/logging command line flags and join video test world."""
    target_instance = world_location or DEFAULT_TEST_WORLD_LOCATION
    vrc_launch_uri = f"vrchat://launch?id={target_instance}"
    steam_rungame_uri = f"steam://rungameid/438100//{vrc_launch_uri}"

    print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} [--try Mode] Launching VRChat in Desktop Mode for Debug Log Scraping{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f" Target Instance : {target_instance}")
    print(f" Debug Args      : {' '.join(VRCHAT_DEBUG_ARGS)}")
    print()

    # Launch directly via Steam URI protocol / bazzite-steam applaunch
    try:
        cmd = ["steam", steam_rungame_uri]
        subprocess.run(cmd, check=True)
        print(f"{COLOR_GREEN}[✓] Triggered VRChat launch via Steam URI protocol.{COLOR_RESET}")
    except Exception:
        try:
            cmd = ["bazzite-steam", "-applaunch", "438100", vrc_launch_uri]
            subprocess.run(cmd, check=True)
            print(f"{COLOR_GREEN}[✓] Triggered VRChat launch via bazzite-steam applaunch.{COLOR_RESET}")
        except Exception as e:
            print(f"{COLOR_RED}[!] Failed to launch VRChat: {e}{COLOR_RESET}")

def run_matrix_test(quick_mode=False, custom_url=None, tool_filter=None, try_launch=False):
    """Run diagnostic matrix tests across Proton versions and configuration flags."""
    proton_list = find_proton_tools(filter_name=tool_filter)
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

    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} VRCVideoTester (vrcvt) - Diagnostic Matrix & Compatibility Benchmark{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
    print(f" Discovered Proton Tools : {len(proton_list)}")
    print(f" Target VRChat Prefix    : {prefix_dir}")
    print(f" WMF Harness Binary      : {wmf_exe}")
    print(f" Bundled Local Asset     : {local_mp4}")
    print()

    if not proton_list:
        print(f"{COLOR_RED}[!] No Proton compatibility tools matching filter '{tool_filter}'.{COLOR_RESET}")
        return

    # Select URLs to test (Full testing is default)
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

    results = []

    for p_name, p_dir, p_bin in proton_list:
        print(f"{COLOR_BOLD}-> Testing Compatibility Tool: {COLOR_YELLOW}{p_name}{COLOR_RESET}")
        
        for url_label, raw_url in urls_to_test.items():
            url_target = "C:\\sample.mp4" if raw_url == "ASSET_LOCAL" else raw_url
            
            res_url, ytdlp_ms, ytdlp_attempts, ytdlp_err, ssl_bypass_used = resolve_url_ytdlp(p_bin, prefix_dir, url_target)
            
            for env_label, env_vars in env_configs:
                test_result = run_wmf_test(p_bin, prefix_dir, wmf_exe, res_url, env_vars)
                test_result["proton_name"] = p_name
                test_result["url_label"] = url_label
                test_result["env_label"] = env_label
                test_result["ytdlp_ms"] = ytdlp_ms
                test_result["ytdlp_err"] = ytdlp_err
                test_result["ssl_bypass_used"] = ssl_bypass_used
                results.append(test_result)

    # Print Summary Matrix Table
    print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN} DIAGNOSTIC MATRIX SUMMARY RESULTS{COLOR_RESET}")
    print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================================================{COLOR_RESET}")
    print(f"{'PROTON TOOL':<22} | {'STREAM TYPE':<16} | {'ENV CONFIG':<18} | {'STATUS':<8} | {'TIME(ms)':<8} | {'HRESULT':<10} | {'PRIMARY SOLUTION'}")
    print("-" * 115)

    for r in results:
        status_str = f"{COLOR_GREEN}PASS{COLOR_RESET}" if r["success"] else f"{COLOR_RED}FAIL{COLOR_RESET}"
        time_str = f"{r['elapsed_ms']:.0f}ms"
        hres_str = r.get("hresult", "N/A")
        sol_str = r["solution"][:40]

        if r.get("ssl_bypass_used"):
            sol_str = f"[SSL Fix: --no-check-certificates] {sol_str}"

        print(f"{r['proton_name'][:22]:<22} | {r['url_label'][:16]:<16} | {r['env_label'][:18]:<18} | {status_str:<17} | {time_str:<8} | {hres_str:<10} | {sol_str}")

    print("-" * 115)
    print(f"{COLOR_BOLD}Recommended Launch Options for VRChat:{COLOR_RESET}")
    print(f"  WINEDLLOVERRIDES=\"iyuv_32=\" G_TLS_GNUTLS_PRIORITY=NORMAL %command% --enable-avpro-in-proton --disable-hw-video-decoding")
    print()

    if try_launch:
        launch_vrchat_in_desktop_test_mode()

    cleanup_artifacts_and_zombies()

def main():
    parser = argparse.ArgumentParser(description="VRCVideoTester (vrcvt) - VRChat Video Player Compatibility Tester")
    parser.add_argument("--quick", action="store_true", help="Run quick diagnostic test on primary Proton tool")
    parser.add_argument("--all", action="store_true", help="Run comprehensive matrix test suite across all Proton versions")
    parser.add_argument("--tool", type=str, help="Filter test to specific Proton tool name (e.g. RTSP)")
    parser.add_argument("--url", type=str, help="Test a specific video or stream URL")
    parser.add_argument("--try", dest="try_launch", action="store_true", help="Launch VRChat in Desktop mode with full debug flags into video test world after benchmarking")
    parser.add_argument("--json", action="store_true", help="Output raw JSON results for automated tools")
    args = parser.parse_args()

    run_matrix_test(quick_mode=args.quick or (not args.all and not args.tool), custom_url=args.url, tool_filter=args.tool, try_launch=args.try_launch)

if __name__ == "__main__":
    main()
