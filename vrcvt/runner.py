"""
VRCVideoTester (vrcvt) - Single Test Execution Engine & URL Resolver
"""

import os
import sys
import time
import subprocess
import json
import shutil
from .config import YTDLP_VRCHAT_ARGS_DEFAULT

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
        
    return url, elapsed_ms, 1, error_msg[:100], False

class VRCTestRunner:
    """Executes a single video stream compatibility test using a specified Proton tool, environment variables, and launch flags."""

    def __init__(self, proton_bin=None, prefix_dir=None, env_vars=None, cmd_args=None, wmf_exe=None):
        self.proton_bin = proton_bin
        self.prefix_dir = prefix_dir
        self.env_vars = env_vars or {}
        self.cmd_args = cmd_args or []

        # Locate project root and wmf_test.exe binary
        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(package_dir)
        self.wmf_exe = wmf_exe or os.path.join(project_root, "assets/wmf_test.exe")

    def run_test(self, url, timeout=10, retries=1):
        """Execute wmf_test.exe inside an isolated per-tool sandbox prefix."""
        if not self.proton_bin or not os.path.isfile(self.proton_bin):
            return {
                "success": False,
                "error_type": "MISSING_PROTON_BINARY",
                "solution": f"Invalid Proton binary path: {self.proton_bin}",
                "elapsed_ms": 0.0,
                "hresult": "N/A"
            }

        if not os.path.isfile(self.wmf_exe):
            return {
                "success": False,
                "error_type": "MISSING_HARNESS_BINARY",
                "solution": f"Build wmf_test.exe at {self.wmf_exe}",
                "elapsed_ms": 0.0,
                "hresult": "N/A"
            }

        tool_folder = os.path.basename(os.path.dirname(self.proton_bin)) if os.path.basename(self.proton_bin) == "proton" else "default"
        clean_tool_folder = "".join([c if c.isalnum() else "_" for c in tool_folder])
        sandbox_prefix = f"/tmp/vrcvt_prefix_{clean_tool_folder}"
        os.makedirs(sandbox_prefix, exist_ok=True)

        env = os.environ.copy()
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = os.path.expanduser("~/.local/share/Steam")
        env["STEAM_COMPAT_DATA_PATH"] = sandbox_prefix
        env["WINEDEBUG"] = "-all"

        override_base = "winemenubuilder.exe=d;conhost.exe=d"
        if "WINEDLLOVERRIDES" in self.env_vars:
            override_base = f"{override_base};{self.env_vars['WINEDLLOVERRIDES']}"

        env.update(self.env_vars)
        env["WINEDLLOVERRIDES"] = override_base

        c_wmf = os.path.join(sandbox_prefix, "pfx/drive_c/vrcvt_wmf_test.exe")
        c_result_json = os.path.join(sandbox_prefix, "pfx/drive_c/vrcvt_result.json")
        try:
            os.makedirs(os.path.dirname(c_wmf), exist_ok=True)
            shutil.copy2(self.wmf_exe, c_wmf)
        except Exception:
            pass

        if os.path.isfile(c_result_json):
            try:
                os.remove(c_result_json)
            except Exception:
                pass

        for attempt in range(1, retries + 1):
            start_t = time.time()
            try:
                cmd = [self.proton_bin, "run", c_wmf, url, "--json"] + self.cmd_args
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
                elapsed_ms = (time.time() - start_t) * 1000.0

                stdout = res.stdout
                stderr = res.stderr + "\n" + stdout

                json_data = None

                # Load result from c_result_json file
                if os.path.isfile(c_result_json):
                    try:
                        with open(c_result_json, "r") as f:
                            json_data = json.load(f)
                    except Exception:
                        pass

                # Fallback to multi-line substring JSON extraction
                if not json_data:
                    first_brace = stdout.find("{")
                    last_brace = stdout.rfind("}")
                    if first_brace != -1 and last_brace > first_brace:
                        try:
                            json_data = json.loads(stdout[first_brace:last_brace+1])
                        except Exception:
                            pass

                # Fallback to line-by-line JSON parsing
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

                if "%COMPAT" in stderr or "GnuTLS" in stderr or "0x80072F8F" in hresult:
                    error_type = "SSL_GNUTLS_ERROR"
                    solution = "Set G_TLS_GNUTLS_PRIORITY=NORMAL in launch options"
                elif "iyuv_32" in stderr or "IYUV" in stderr:
                    error_type = "IYUV_CONVERSION_ERROR"
                    solution = "Set WINEDLLOVERRIDES=\"iyuv_32=\" in launch options"
                elif "0x80072EE7" in hresult or "DNS" in stderr:
                    error_type = "DNS_RESOLUTION_ERROR"
                    solution = "Check system DNS / internet connection"

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
                return {
                    "success": False,
                    "error_type": "TIMEOUT",
                    "solution": "Stream resolution or network connection timed out",
                    "elapsed_ms": (time.time() - start_t) * 1000.0,
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
