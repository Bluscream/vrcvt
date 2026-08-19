"""
VRCVideoTester (vrcvt) - Proton Compatibility Discovery & System Utilities
"""

import os
import glob
import subprocess
from pathlib import Path
from typing import List, Optional
from .models import ProtonTool, SteamContainerRuntime
from .logger import logger

class ProtonDiscovery:
    """Discovers installed Proton compatibility tools and verifies Steam runtime codec payloads."""

    @staticmethod
    def find_proton_tools() -> List[ProtonTool]:
        """Discover installed Proton versions on the system using Path, deduplicating symlinked paths."""
        seen_realpaths = set()
        proton_tools: List[ProtonTool] = []

        search_globs = [
            Path.home() / ".local/share/Steam/compatibilitytools.d/*",
            Path.home() / ".steam/steam/compatibilitytools.d/*",
            Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam/compatibilitytools.d/*",
            Path.home() / ".local/share/Steam/steamapps/common/Proton*",
            Path("/run/media/system/Data/Games/Steam/steamapps/common/Proton*")
        ]

        for path_glob in search_globs:
            for entry_str in glob.glob(str(path_glob)):
                entry_path = Path(entry_str)
                try:
                    real_entry = entry_path.resolve()
                except Exception:
                    continue

                if real_entry in seen_realpaths:
                    continue

                proton_bin = real_entry / "proton"
                if proton_bin.is_file() and os.access(proton_bin, os.X_OK):
                    seen_realpaths.add(real_entry)
                    proton_tools.append(
                        ProtonTool(name=real_entry.name, path=real_entry, bin_path=proton_bin)
                    )

        return sorted(proton_tools, key=lambda x: x.name)

    @staticmethod
    def check_and_unlock_h264() -> bool:
        """Verify if Steam's H.264 codec payload (mfh264enc.dll) is unlocked, auto-triggering unlock if missing."""
        global_pfx_dll = Path.home() / ".local/share/Steam/steamapps/compatdata/0/pfx/drive_c/windows/system32/mfh264enc.dll"
        if not global_pfx_dll.is_file():
            logger.warning("H.264 codec payload (mfh264enc.dll) not found in Steam runtime. Triggering steam://unlockh264/...")
            try:
                subprocess.run(["steam", "steam://unlockh264/"], capture_output=True, timeout=5)
                logger.success("Triggered steam://unlockh264/ payload installation.")
                return True
            except Exception as e:
                logger.error(f"Failed to trigger steam://unlockh264/: {e}")
                return False
        else:
            logger.success("H.264 codec payload (mfh264enc.dll) verified in Steam runtime.")
            return True

    @staticmethod
    def find_vrchat_prefix() -> Path:
        """Locate VRChat compatibility prefix data directory."""
        candidates = [
            Path("/run/media/system/Data/Games/Steam/steamapps/compatdata/438100"),
            Path.home() / ".local/share/Steam/steamapps/compatdata/438100",
            Path.home() / ".steam/steam/steamapps/compatdata/438100",
            Path.home() / ".var/app/com.valvesoftware.Steam/data/Steam/steamapps/compatdata/438100"
        ]
        for candidate in candidates:
            if candidate.is_dir():
                return candidate
        return candidates[0]

    @staticmethod
    def find_steam_linux_runtime() -> Optional[Path]:
        """Locate SteamLinuxRuntime container runner (preferring SteamLinuxRuntime_4 for newest container support)."""
        candidates = [
            Path("/run/media/system/Data/Games/Steam/steamapps/common/SteamLinuxRuntime_4/run"),
            Path.home() / ".local/share/Steam/steamapps/common/SteamLinuxRuntime_4/run",
            Path("/run/media/system/Data/Games/Steam/steamapps/common/SteamLinuxRuntime_sniper/run"),
            Path.home() / ".local/share/Steam/steamapps/common/SteamLinuxRuntime_sniper/run",
            Path("/run/media/system/Data/Games/Steam/steamapps/common/SteamLinuxRuntime_soldier/run"),
            Path.home() / ".local/share/Steam/steamapps/common/SteamLinuxRuntime_soldier/run",
            Path("/run/media/system/Data/Games/Steam/steamapps/common/SteamLinuxRuntime/run"),
            Path.home() / ".local/share/Steam/steamapps/common/SteamLinuxRuntime/run",
        ]
        for c in candidates:
            if c.is_file() and os.access(c, os.X_OK):
                return c
        return None

    @staticmethod
    def find_all_container_runtimes() -> List[SteamContainerRuntime]:
        """Discover all installed Steam Linux Runtime container environments on the system."""
        runtimes: List[SteamContainerRuntime] = []
        seen = set()

        search_dirs = [
            Path("/run/media/system/Data/Games/Steam/steamapps/common"),
            Path.home() / ".local/share/Steam/steamapps/common",
            Path.home() / ".steam/steam/steamapps/common",
        ]

        for base_dir in search_dirs:
            if not base_dir.is_dir():
                continue
            for entry in base_dir.iterdir():
                if entry.name.startswith("SteamLinuxRuntime"):
                    run_bin = entry / "run"
                    if run_bin.is_file() and os.access(run_bin, os.X_OK):
                        if entry.name not in seen:
                            seen.add(entry.name)
                            runtimes.append(SteamContainerRuntime(name=entry.name, run_path=run_bin))

        runtimes.sort(key=lambda r: r.name, reverse=True)
        runtimes.append(SteamContainerRuntime(name="HostNative", run_path=None))
        return runtimes
