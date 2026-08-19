"""
VRCVideoTester (vrcvt) - Single Test Execution Engine & URL Resolver
"""

import os
import sys
import time
import subprocess
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from .config import Config
from .models import BenchmarkResult
from .logger import logger

class URLResolver:
    """Resolves stream URLs using VRChat's bundled yt-dlp.exe."""

    @staticmethod
    def resolve_url(proton_bin: Path, prefix_dir: Path, url: str) -> Tuple[str, float, bool]:
        """Resolve video URL via yt-dlp.exe, returning (resolved_url, elapsed_ms, success)."""
        if url.startswith("ASSET_LOCAL") or Path(url).is_file() or url.startswith("C:\\"):
            return url, 0.0, True

        ytdlp_exe = prefix_dir / "pfx/drive_c/users/steamuser/AppData/LocalLow/VRChat/VRChat/Tools/yt-dlp.exe"
        start_t = time.time()

        try:
            if ytdlp_exe.is_file():
                env = os.environ.copy()
                env["STEAM_COMPAT_CLIENT_INSTALL_PATH"] = str(Path.home() / ".local/share/Steam")
                env["STEAM_COMPAT_DATA_PATH"] = str(prefix_dir)
                cmd = [str(proton_bin), "run", str(ytdlp_exe), "-g"] + Config.YTDLP_VRCHAT_ARGS + [url]
            else:
                cmd = ["yt-dlp", "-g"] + Config.YTDLP_VRCHAT_ARGS + [url]

            res = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
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
        wmf_exe: Optional[Path] = None
    ):
        self.proton_bin = proton_bin
        self.prefix_dir = prefix_dir
        self.env_vars = env_vars or {}
        self.cmd_args = cmd_args or []
        self.wmf_exe = wmf_exe or Config.WMF_EXE

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

        c_wmf = sandbox_prefix / "pfx/drive_c/vrcvt_wmf_test.exe"
        c_result_json = sandbox_prefix / "pfx/drive_c/vrcvt_result.json"

        try:
            c_wmf.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.wmf_exe, c_wmf)
        except Exception:
            pass

        if c_result_json.is_file():
            try:
                c_result_json.unlink()
            except Exception:
                pass

        for attempt in range(1, retries + 1):
            start_t = time.time()
            try:
                cmd = [str(self.proton_bin), "run", str(c_wmf), url, "--json"] + self.cmd_args
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

                if json_data and json_data.get("resolver_success") and json_data.get("reader_success"):
                    return BenchmarkResult(
                        success=True,
                        elapsed_ms=json_data.get("total_ms", elapsed_ms),
                        hresult=json_data.get("resolver_hresult", "0x00000000"),
                        solution="Working correctly",
                        attempts=attempt
                    )

                hresult = json_data.get("resolver_hresult", "0x80004005") if json_data else "0x80004005"
                error_type = "UNKNOWN_ERROR"
                solution = "Inspect logs"

                if "%COMPAT" in stderr or "GnuTLS" in stderr or "0x80072F8F" in hresult:
                    error_type = "SSL_GNUTLS_ERROR"
                    solution = "Set G_TLS_GNUTLS_PRIORITY=NORMAL in launch options"
                elif "iyuv_32" in stderr or "IYUV" in stderr:
                    error_type = "IYUV_CONVERSION_ERROR"
                    solution = 'Set WINEDLLOVERRIDES="iyuv_32=" in launch options'
                elif "0x80072EE7" in hresult or "DNS" in stderr:
                    error_type = "DNS_RESOLUTION_ERROR"
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
                    error_type="TIMEOUT",
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
