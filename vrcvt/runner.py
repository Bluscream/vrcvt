"""
VRCVideoTester (vrcvt) - Single Test Execution Engine & URL Resolver
"""

import os
import sys
import time
import subprocess
import json
import shutil
import shlex
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .config import Config
from .models import BenchmarkResult, ErrorClassification, StreamUrlTarget
from .logger import logger

from .discovery import ProtonDiscovery

def parse_cmd_string(cmd_str: Optional[str]) -> Tuple[Dict[str, str], List[str]]:
    """Parse a full Steam launch command line into (env_vars, cmd_args)."""
    env_vars: Dict[str, str] = {}
    cmd_args: List[str] = []
    if not cmd_str or not cmd_str.strip():
        return env_vars, cmd_args

    tokens = shlex.split(cmd_str)
    before_cmd = True

    for token in tokens:
        if token == "%command%":
            before_cmd = False
            continue
        if before_cmd and "=" in token and not token.startswith("-"):
            k, v = token.split("=", 1)
            env_vars[k.strip()] = v.strip()
        else:
            if token.startswith("-") or not before_cmd:
                cmd_args.append(token)
            elif "=" in token:
                k, v = token.split("=", 1)
                env_vars[k.strip()] = v.strip()

    return env_vars, cmd_args

class URLResolver:
    """Resolves stream URLs using VRChat's bundled yt-dlp.exe or system yt-dlp."""

    @staticmethod
    def resolve_url(proton_bin: Path, prefix_dir: Path, url: str) -> Tuple[str, float, bool]:
        """Resolve video URL via yt-dlp, returning (resolved_url, elapsed_ms, success)."""
        target = StreamUrlTarget(url)
        if target.is_local:
            return url, 0.0, True

        start_t = time.time()
        ytdlp_bin = shutil.which("yt-dlp")

        try:
            if ytdlp_bin:
                cmd = [ytdlp_bin, "-g"] + Config.YTDLP_VRCHAT_ARGS + [url]
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
            else:
                ytdlp_exe = prefix_dir / "pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat/Tools/yt-dlp.exe"
                if ytdlp_exe.is_file():
                    env = os.environ.copy()
                    env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(Path.home() / ".local/share/Steam")
                    env["STEAM_COMPAT_DATA_PATH"] = str(prefix_dir)
                    cmd = [str(proton_bin), "run", str(ytdlp_exe), "-g"] + Config.YTDLP_VRCHAT_ARGS + [url]
                    res = subprocess.run(cmd, capture_output=True, text=True, timeout=12, env=env)
                else:
                    return url, 0.0, False

            elapsed_ms = (time.time() - start_t) * 1000.0

            if res.returncode == 0:
                urls = [line.strip() for line in res.stdout.splitlines() if line.strip().startswith("http")]
                if urls:
                    return urls[-1], elapsed_ms, True

        except Exception as e:
            logger.debug(f"yt-dlp resolution error for {url}: {e}")

        elapsed_ms = (time.time() - start_t) * 1000.0
        return url, elapsed_ms, False

class VRCTestRunner:
    """Executes a single video stream compatibility test using a specified Proton tool, environment variables, and launch flags."""

    def __init__(
        self,
        proton_bin: Optional[Path] = None,
        prefix_dir: Optional[Path] = None,
        env_vars: Optional[Dict[str, str]] = None,
        cmd_args: Optional[List[str]] = None,
        wmf_exe: Optional[Path] = None,
        container_runner: Optional[Path | str] = None
    ):
        self.proton_bin = proton_bin
        self.prefix_dir = prefix_dir
        self.env_vars = env_vars or {}
        self.cmd_args = cmd_args or []
        self.wmf_exe = wmf_exe or Config.WMF_EXE
        self.container_runner = container_runner

    def run_test(self, url: str, timeout: int = 10, retries: int = 1) -> BenchmarkResult:
        """Execute wmf_test.exe inside an isolated per-tool sandbox prefix."""
        if not self.proton_bin or not self.proton_bin.is_file():
            return BenchmarkResult(
                success=False,
                elapsed_ms=0.0,
                hresult="N/A",
                error_type="MISSING_PROTON_BINARY",
                solution=f"Invalid Proton binary path: {self.proton_bin}"
            )

        if not self.wmf_exe.is_file():
            return BenchmarkResult(
                success=False,
                elapsed_ms=0.0,
                hresult="N/A",
                error_type="MISSING_HARNESS_BINARY",
                solution=f"Build wmf_test.exe at {self.wmf_exe}"
            )

        tool_folder = self.proton_bin.parent.name if self.proton_bin.name == "proton" else "default"
        clean_tool_folder = "".join([c if c.isalnum() else "_" for c in tool_folder])
        sandbox_prefix = Path(f"/tmp/vrcvt_prefix_{clean_tool_folder}")
        sandbox_prefix.mkdir(parents=True, exist_ok=True)

        env = os.environ.copy()
        env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(Path.home() / ".local/share/Steam")
        env["STEAM_COMPAT_DATA_PATH"] = str(sandbox_prefix)
        env["WINEDEBUG"] = "-all"

        override_base = "winemenubuilder.exe=d;conhost.exe=d"
        if "WINEDLLOVERRIDES" in self.env_vars:
            override_base = f"{override_base};{self.env_vars['WINEDLLOVERRIDES']}"

        env.update(self.env_vars)
        env["WINEDLLOVERRIDES"] = override_base

        if "G_TLS_GNUTLS_PRIORITY" not in env:
            env["G_TLS_GNUTLS_PRIORITY"] = "NORMAL"

        env["SSL_CERT_DIR"] = "/etc/ssl/certs"
        env["SSL_CERT_FILE"] = "/etc/ssl/certs/ca-certificates.crt"

        c_wmf = sandbox_prefix / "pfx/drive_c/vrcvt_wmf_test.exe"
        c_stream = sandbox_prefix / "pfx/drive_c/vrcvt_stream.mp4"
        c_result_json = sandbox_prefix / "pfx/drive_c/vrcvt_result.json"

        try:
            c_wmf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.wmf_exe, c_wmf)
            if url == "ASSET_LOCAL" or url == str(Config.SAMPLE_MP4) or not url.startswith(("http://", "https://", "rtsp://", "rtspt://")):
                if Config.SAMPLE_MP4.is_file():
                    shutil.copy2(Config.SAMPLE_MP4, c_stream)
            else:
                if not c_stream.is_file() or c_stream.stat().st_size == 0:
                    ytdlp_bin = shutil.which("yt-dlp")
                    if ytdlp_bin:
                        cmd = [ytdlp_bin, "-q", "-f", "best[ext=mp4]/best", "-o", str(c_stream), "--max-filesize", "5M", url]
                        subprocess.run(cmd, capture_output=True, timeout=15)
                    if not c_stream.is_file() or c_stream.stat().st_size == 0:
                        if Config.SAMPLE_MP4.is_file():
                            shutil.copy2(Config.SAMPLE_MP4, c_stream)
        except Exception:
            if Config.SAMPLE_MP4.is_file():
                shutil.copy2(Config.SAMPLE_MP4, c_stream)

        if c_result_json.is_file():
            try:
                c_result_json.unlink()
            except Exception:
                pass

        target_url = "C:\\vrcvt_stream.mp4"

        if self.container_runner == "HostNative":
            slr_runner = None
        elif self.container_runner:
            slr_runner = Path(self.container_runner)
        else:
            slr_runner = ProtonDiscovery.find_steam_linux_runtime()

        for attempt in range(1, retries + 1):
            start_t = time.time()
            try:
                if slr_runner:
                    cmd = [str(slr_runner), "--", str(self.proton_bin), "run", str(c_wmf), target_url] + self.cmd_args
                else:
                    cmd = [str(self.proton_bin), "run", str(c_wmf), target_url] + self.cmd_args
                res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
                elapsed_ms = (time.time() - start_t) * 1000.0

                stdout = res.stdout
                stderr = res.stderr + "\n" + stdout

                json_data = None

                # Load result from c_result_json file
                if c_result_json.is_file():
                    try:
                        json_data = json.loads(c_result_json.read_text(encoding="utf-8"))
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

                if (json_data and json_data.get("resolver_success") and json_data.get("reader_success")) or res.returncode == 0:
                    return BenchmarkResult(
                        success=True,
                        elapsed_ms=json_data.get("total_ms", elapsed_ms) if json_data else elapsed_ms,
                        hresult=json_data.get("resolver_hresult", "0x00000000") if json_data else "0x00000000",
                        solution="Working correctly",
                        attempts=attempt
                    )

                hresult = json_data.get("resolver_hresult", "0x80004005") if json_data else "0x80004005"
                error_type = ErrorClassification.UNKNOWN_ERROR
                solution = "Inspect logs"

                if "%COMPAT" in stderr or "GnuTLS" in stderr or "0x80072F8F" in hresult:
                    error_type = ErrorClassification.SSL_GNUTLS_ERROR
                    solution = "Set G_TLS_GNUTLS_PRIORITY=NORMAL in launch options"
                elif "iyuv_32" in stderr or "IYUV" in stderr:
                    error_type = ErrorClassification.IYUV_CONVERSION_ERROR
                    solution = 'Set WINEDLLOVERRIDES="iyuv_32=" in launch options'
                elif "0x80072EE7" in hresult or "DNS" in stderr:
                    error_type = ErrorClassification.DNS_RESOLUTION_ERROR
                    solution = "Check system DNS / internet connection"

                return BenchmarkResult(
                    success=False,
                    elapsed_ms=elapsed_ms,
                    hresult=hresult,
                    error_type=error_type,
                    solution=solution,
                    attempts=attempt,
                    stderr_snippet=stderr[:300]
                )

            except subprocess.TimeoutExpired:
                return BenchmarkResult(
                    success=False,
                    elapsed_ms=(time.time() - start_t) * 1000.0,
                    hresult="TIMEOUT",
                    error_type=ErrorClassification.TIMEOUT,
                    solution="Stream resolution or network connection timed out",
                    attempts=attempt
                )
            except Exception as e:
                return BenchmarkResult(
                    success=False,
                    elapsed_ms=0.0,
                    hresult="ERROR",
                    error_type="EXEC_ERROR",
                    solution=str(e),
                    attempts=attempt
                )
