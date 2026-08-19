"""
VRCVideoTester (vrcvt) - Diagnostic Matrix Benchmark Suite & Scoring Engine
"""

import sys
import time
import json
from pathlib import Path
from collections import defaultdict
from typing import Dict, List, Optional, Tuple, Any

from .config import Config
from .models import ProtonTool, SteamContainerRuntime, BenchmarkResult, RankedCombination
from .discovery import ProtonDiscovery
from .runner import VRCTestRunner, URLResolver, parse_cmd_string
from .launcher import VRCLauncher
from .logger import logger

DEFAULT_CMD_MATRIX = [
    ("Full Video Comp + HW Decode", 'WINEDLLOVERRIDES="iyuv_32=" G_TLS_GNUTLS_PRIORITY=NORMAL PRESSURE_VESSEL_IMPORT_OPENXR_1_RUNTIMES=1 PRESSURE_VESSEL_FILESYSTEMS_RW=/var/lib/flatpak/app/io.github.wivrn.wivrn %command% --enable-hw-video-decoding --enable-avpro-in-proton'),
    ("IYUV + GnuTLS", 'WINEDLLOVERRIDES="iyuv_32=" G_TLS_GNUTLS_PRIORITY=NORMAL %command% --enable-avpro-in-proton --disable-hw-video-decoding'),
    ("IYUV Override", 'WINEDLLOVERRIDES="iyuv_32=" %command% --enable-avpro-in-proton --disable-hw-video-decoding'),
    ("GnuTLS Normal", 'G_TLS_GNUTLS_PRIORITY=NORMAL %command% --enable-avpro-in-proton --disable-hw-video-decoding'),
    ("Default (Unset)", '%command% --enable-avpro-in-proton --disable-hw-video-decoding'),
]

class VRCBenchmarkSuite:
    """Executes full multi-layered diagnostic matrix across Proton versions, Container Runtimes, launch commands, and stream URLs."""

    def __init__(self, custom_url: Optional[str] = None):
        self.custom_url = custom_url
        self.prefix_dir: Path = ProtonDiscovery.find_vrchat_prefix()
        self.proton_tools: List[ProtonTool] = ProtonDiscovery.find_proton_tools()
        self.container_runtimes: List[SteamContainerRuntime] = ProtonDiscovery.find_all_container_runtimes()

    def run_suite(
        self,
        auto_try: bool = False,
        target_rank: int = 1,
        tool_filter: Optional[str] = None,
        env_filter: Optional[str] = None,
        cmd_filter: Optional[str] = None,
        url_filter: Optional[str] = None
    ) -> Tuple[Dict[Any, Any], List[RankedCombination]]:
        """Execute matrix benchmark with optional filters across Proton tools, container runtimes, launch commands, and URLs."""
        start_time_iso = time.strftime("%Y-%m-%d %H:%M:%S")
        suite_start_t = time.time()

        ProtonDiscovery.check_and_unlock_h264()

        # Apply Filters
        filtered_tools = [
            t for t in self.proton_tools
            if not tool_filter or tool_filter.lower() in t.name.lower()
        ]
        filtered_runtimes = [
            r for r in self.container_runtimes
            if not env_filter or env_filter.lower() in r.name.lower()
        ]
        filtered_cmds = [
            (label, cmd) for label, cmd in DEFAULT_CMD_MATRIX
            if not cmd_filter or cmd_filter.lower() in cmd.lower() or cmd_filter.lower() in label.lower()
        ]
        if cmd_filter and not filtered_cmds:
            filtered_cmds = [("Custom Filtered Cmd", cmd_filter)]

        test_urls = Config.DEFAULT_URLS.copy()
        if self.custom_url:
            test_urls["Custom CLI URL"] = self.custom_url

        if url_filter:
            test_urls = {
                k: v for k, v in test_urls.items()
                if url_filter.lower() in k.lower() or url_filter.lower() in v.lower()
            }
            if not test_urls:
                test_urls["Filtered URL"] = url_filter

        logger.info("\n========================================================================")
        logger.info(" VRCVideoTester (vrcvt) - Multi-Layered Compatibility Matrix Benchmark")
        logger.info("========================================================================")
        logger.info(f" [{time.strftime('%H:%M:%S')}] Benchmark Start Time  : {start_time_iso}")
        logger.info(f" Discovered Proton Tools : {len(filtered_tools)} matching / {len(self.proton_tools)} total")
        logger.info(f" Container Runtimes      : {len(filtered_runtimes)} matching / {len(self.container_runtimes)} total")
        logger.info(f" Launch Command Profiles : {len(filtered_cmds)} matching")
        logger.info(f" Target Stream URLs      : {len(test_urls)} matching")
        logger.info(f" Target VRChat Prefix    : {self.prefix_dir}")
        logger.info(f" WMF Harness Binary      : {Config.WMF_EXE}")
        logger.info(f" Bundled Local Asset     : {Config.SAMPLE_MP4}\n")

        if not filtered_tools:
            logger.error("No Proton compatibility tools matched the specified --tool filter.")
            sys.exit(1)
        if not filtered_runtimes:
            logger.error("No Steam container runtimes matched the specified --env filter.")
            sys.exit(1)

        resolved_urls: Dict[str, Tuple[str, float]] = {}
        total_ytdlp_time = 0.0

        logger.info(f" [{time.strftime('%H:%M:%S')}] Pre-resolving stream URLs via yt-dlp...")
        dummy_proton = filtered_tools[0].bin_path

        for name, orig_url in test_urls.items():
            if orig_url == "ASSET_LOCAL":
                resolved_urls[name] = (str(Config.SAMPLE_MP4), 0.0)
            else:
                res_url, y_time, _ = URLResolver.resolve_url(dummy_proton, self.prefix_dir, orig_url)
                resolved_urls[name] = (res_url, y_time)
                total_ytdlp_time += y_time

        logger.info(f" [{time.strftime('%H:%M:%S')}] All stream URLs resolved successfully.\n")

        results = defaultdict(dict)
        combination_scores: Dict[Tuple[str, str, str], RankedCombination] = {}
        tool_runtimes = defaultdict(lambda: {"wmf_ms": 0.0, "count": 0})

        total_wmf_time = 0.0
        total_subtests_executed = 0

        for tool in filtered_tools:
            logger.info(f"[{time.strftime('%H:%M:%S')}] -> Testing Compatibility Tool: {tool.name}")

            for runtime in filtered_runtimes:
                for cmd_label, cmd_str in filtered_cmds:
                    combo_key = (tool.name, runtime.name, cmd_label)
                    env_vars, cmd_args = parse_cmd_string(cmd_str)

                    pass_count = 0
                    total_ms_sum = 0.0

                    runner = VRCTestRunner(
                        proton_bin=tool.bin_path,
                        prefix_dir=self.prefix_dir,
                        env_vars=env_vars,
                        cmd_args=cmd_args,
                        wmf_exe=Config.WMF_EXE,
                        container_runner=runtime.run_path if runtime.name != "HostNative" else "HostNative"
                    )

                    for stream_name, (res_url, _) in resolved_urls.items():
                        res = runner.run_test(res_url, timeout=20, retries=1)

                        results[combo_key][stream_name] = res
                        total_ms_sum += res.elapsed_ms
                        total_wmf_time += res.elapsed_ms
                        total_subtests_executed += 1

                        tool_runtimes[tool.name]["wmf_ms"] += res.elapsed_ms
                        tool_runtimes[tool.name]["count"] += 1

                        if res.success:
                            pass_count += 1

                    avg_ms = total_ms_sum / max(1, len(resolved_urls))
                    env_str = " ".join([f"{k}={v}" for k, v in env_vars.items()])

                    combination_scores[combo_key] = RankedCombination(
                        rank=0,
                        proton_name=tool.name,
                        runtime_name=runtime.name,
                        env_vars=env_vars,
                        env_str=env_str,
                        pass_count=pass_count,
                        total_tests=len(resolved_urls),
                        avg_ms=avg_ms,
                        launch_cmd=cmd_str
                    )

        suite_total_time = time.time() - suite_start_t

        logger.info("\n========================================================================")
        logger.info(" BENCHMARK SUITE TIMING BREAKDOWN & PERFORMANCE METRICS")
        logger.info("========================================================================")
        logger.info(f" Total Benchmark Suite Runtime : {int(suite_total_time // 60)}m {suite_total_time % 60:.1f}s ({suite_total_time:.1f}s total)")
        logger.info(f" Total Sub-Tests Executed      : {total_subtests_executed} sub-tests")
        logger.info(f" Total yt-dlp Resolution Time  : {total_ytdlp_time/1000.0:.1f}s ({(total_ytdlp_time/1000.0/suite_total_time)*100:.1f}% of total runtime)")
        logger.info(f" Total WMF Harness Execution   : {total_wmf_time/1000.0:.1f}s ({(total_wmf_time/1000.0/suite_total_time)*100:.1f}% of total runtime)")
        logger.info(f" Average Sub-Test Latency      : {total_wmf_time / max(1, total_subtests_executed):.0f}ms / sub-test")
        logger.info("\n PER-TOOL RUNTIME BREAKDOWN:")

        for tool in filtered_tools:
            t_data = tool_runtimes[tool.name]
            avg_wmf = t_data["wmf_ms"] / max(1, t_data["count"])
            logger.info(f"   • {tool.name:<26} : Avg WMF Decode = {avg_wmf:.0f}ms")

        # Sort combinations dynamically from BEST to WORST
        ranked_combos = sorted(
            combination_scores.values(),
            key=lambda x: (-x.pass_count, x.avg_ms)
        )

        results_json_data = {
            "generated_at": start_time_iso,
            "suite_runtime_seconds": round(suite_total_time, 2),
            "rankings": []
        }

        logger.info("\n========================================================================")
        logger.info(" DYNAMIC RANKED RECOMMENDATIONS (BEST TO WORST BY PASS RATE & TIMING)")
        logger.info("========================================================================")

        for idx, item in enumerate(ranked_combos, 1):
            item.rank = idx
            results_json_data["rankings"].append(item.to_dict())

            status_str = "PASS" if item.pass_count == item.total_tests else "FAIL"
            rank_label = f"#{idx} BEST: {status_str}" if idx == 1 else f"#{idx}: {status_str}"

            logger.info(f" {rank_label}")
            logger.info(f"     Pass Rate : {item.pass_count}/{item.total_tests} Passed ({item.avg_ms:.0f}ms avg)")
            logger.info(f"     Proton    : {item.proton_name}")
            logger.info(f"     Runtime   : {item.runtime_name}")
            logger.info(f"     Launch Cmd: {item.launch_cmd}\n")

        try:
            Config.RESULTS_JSON.write_text(json.dumps(results_json_data, indent=2), encoding="utf-8")
            logger.success(f"Saved benchmark rankings to {Config.RESULTS_JSON}")
        except Exception as e:
            logger.error(f"Failed to save results.json: {e}")

        best_config = ranked_combos[0] if ranked_combos else None

        if not best_config or best_config.pass_count == 0:
            logger.error("========================================================================")
            logger.error(" [!] ERROR: None of the tested compatibility combinations passed.")
            logger.error("========================================================================")

        if auto_try and best_config and best_config.pass_count > 0:
            VRCLauncher.launch(Config.DEFAULT_TEST_WORLD_ID, target_rank=target_rank, best_config=best_config)

        return results, ranked_combos
