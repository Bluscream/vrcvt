"""
VRCVideoTester (vrcvt) - VRChat Desktop Mode Launcher & Process Manager
"""

import sys
import json
import subprocess
import atexit
from pathlib import Path
from typing import Optional
from .config import Config
from .models import RankedCombination
from .discovery import ProtonDiscovery
from .logger import logger

class VRCLauncher:
    """Manages VRChat desktop mode launching and process cleanup."""

    @staticmethod
    def cleanup_artifacts_and_zombies() -> None:
        """Clean up temporary files and kill lingering Wine/Proton zombie processes."""
        prefix_dir = ProtonDiscovery.find_vrchat_prefix()
        drive_c = prefix_dir / "pfx/drive_c"

        temp_files = [
            drive_c / "vrcvt_wmf_test.exe",
            drive_c / "vrcvt_out.txt",
            drive_c / "vrcvt_out.json",
            drive_c / "sample.mp4",
            Path("/tmp/ytdlp_out.txt"),
            Path("/tmp/wmf_run.txt")
        ]

        for f in temp_files:
            if f.exists():
                try:
                    f.unlink()
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

    @classmethod
    def launch(
        cls,
        world_id: Optional[str] = None,
        target_rank: int = 1,
        best_config: Optional[RankedCombination] = None
    ) -> bool:
        """Launch VRChat in 4:3 desktop mode using target ranking from results.json."""
        target_world_id = world_id or Config.DEFAULT_TEST_WORLD_ID
        vrc_launch_uri = f"vrchat://launch?id={target_world_id}"

        selected_config: Optional[Dict] = best_config.to_dict() if best_config else None
        if not selected_config and Config.RESULTS_JSON.is_file():
            try:
                data = json.loads(Config.RESULTS_JSON.read_text(encoding="utf-8"))
                for r in data.get("rankings", []):
                    if r.get("rank") == target_rank:
                        selected_config = r
                        break
            except Exception:
                pass

        # Kill lingering reaper/VRChat processes
        try:
            subprocess.run(["pkill", "-f", "reaper SteamLaunch AppId=438100"], capture_output=True)
            subprocess.run(["pkill", "-f", "VRChat.exe"], capture_output=True)
        except Exception:
            pass

        logger.info("\n========================================================================")
        logger.info(f" [--try #{target_rank}] Launching VRChat in Desktop Mode for Debug Log Scraping")
        logger.info("========================================================================")
        logger.info(f" Target World ID : {target_world_id}")
        logger.info(f" Selected Rank   : #{target_rank}")
        if selected_config:
            logger.info(f" Proton Tool     : {selected_config.get('proton_name', 'Default')}")
            logger.info(f" Env Config      : {selected_config.get('env_str', 'Default')}")
            logger.info(f" Launch Command  : {selected_config.get('launch_cmd', '')}")
        logger.info(f" Debug Args      : {' '.join(Config.VRCHAT_DEBUG_ARGS)}\n")

        # Launch via bazzite-steam applaunch or steam:// protocol
        try:
            cmd = ["bazzite-steam", "-applaunch", "438100", "--desktop", f"--watch-world={target_world_id}"]
            subprocess.run(cmd, check=True)
            logger.success("Triggered VRChat desktop launch via bazzite-steam -applaunch.")
            return True
        except Exception:
            try:
                cmd = ["steam", f"steam://rungameid/438100//{vrc_launch_uri}"]
                subprocess.run(cmd, check=True)
                logger.success("Triggered VRChat desktop launch via steam:// protocol.")
                return True
            except Exception as e:
                logger.error(f"Failed to launch VRChat via Steam: {e}")
                return False

atexit.register(VRCLauncher.cleanup_artifacts_and_zombies)
