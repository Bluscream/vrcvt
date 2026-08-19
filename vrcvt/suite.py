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
from .models import ProtonTool, BenchmarkResult, RankedCombination
from .discovery import ProtonDiscovery
from .runner import VRCTestRunner, URLResolver
from .launcher import VRCLauncher
from .logger import logger

class VRCBenchmarkSuite:
    """Executes full diagnostic matrix across Proton versions, stream URLs, and environment variables."""

    def __init__(self, custom_url: Optional[str] = None):
        self.custom_url = custom_url
        self.prefix_dir: Path = ProtonDiscovery.find_vrchat_prefix()
        self.proton_tools: List[ProtonTool] = ProtonDiscovery.find_proton_tools()

    def run_suite(self, auto_try: bool = False, target_rank: int = 1) -> Tuple[Dict[Any, Any], List[RankedCombination]]:
        """Execute full matrix benchmark, rank combinations, save results.json, and launch VRChat if valid combination passes."""
        start_time_iso = time.strftime("%Y-%m-%d %H:%M:%S")
        suite_start_t = time.time()

        ProtonDiscovery.check_and_unlock_h264()

        logger.info("\n========================================================================")
        logger.info(" VRCVideoTester (vrcvt) - Full Diagnostic Matrix & Compatibility Benchmark")
        logger.info("========================================================================")
        logger.info(f" [{time.strftime('%H:%M:%S')}] Benchmark Start Time  : {start_time_iso}")
        logger.info(f" Discovered Proton Tools : {len(self.proton_tools)}")
        logger.info(f" Target VRChat Prefix    : {self.prefix_dir}")
        logger.info(f" WMF Harness Binary      : {Config.WMF_EXE}")
        logger.info(f" Bundled Local Asset     : {Config.SAMPLE_MP4}\n")

        test_urls = Config.DEFAULT_URLS.copy()
        if self.custom_url:
            test_urls["Custom CLI URL"] = self.custom_url

        resolved_urls: Dict[str, Tuple[str, float]] = {}
        total_ytdlp_time = 0.0

        logger.info(f" [{time.strftime('%H:%M:%S')}] Pre-resolving stream URLs via yt-dlp...")
        dummy_proton = self.proton_tools[0].bin_path if self.proton_tools else Path("proton")

        for name, orig_url in test_urls.items():
            if orig_url == "ASSET_LOCAL":
                resolved_urls[name] = (str(Config.SAMPLE_MP4), 0.0)
            else:
                res_url, y_time, _ = URLResolver.resolve_url(dummy_proton, self.prefix_dir, orig_url)
                resolved_urls[name] = (res_url, y_time)
                total_ytdlp_time += y_time

        logger.info(f" [{time.strftime('%H:%M:%S')}] All stream URLs resolved successfully.\n")

        env_matrix = [
            ("Default (Unset)", {}),
            ("WINEDLLOVERRIDES=iyuv_32=", {"WINEDLLOVERRIDES": "iyuv_32="}),
            ("G_TLS_GNUTLS_PRIORITY=NORMAL", {"G_TLS_GNUTLS_PRIORITY": "NORMAL"}),
            ("WINEDLLOVERRIDES=iyuv_32= + GnuTLS", {"WINEDLLOVERRIDES": "iyuv_32=", "G_TLS_GNUTLS_PRIORITY": "NORMAL"}),
            ("Full VRChat Video Comp (iyuv_32 + GnuTLS + OpenXR)", {
                "WINEDLLOVERRIDES": "iyuv_32=",
                "G_TLS_GNUTLS_PRIORITY": "NORMAL",
                "PRESSURE_VESSEL_IMPORT_OPENXR_1_RUNTIMES": "1",
                "PRESSURE_VESSEL_FILESYSTEMS_RW": "/var/lib/flatpak/app/io.github.wivrn.wivrn"
            })
        ]

        results = defaultdict(dict)
        combination_scores: Dict[Tuple[str, str], RankedCombination] = {}
        tool_runtimes = defaultdict(lambda: {"wmf_ms": 0.0, "count": 0})

        total_wmf_time = 0.0
        total_subtests_executed = 0

        for tool in self.proton_tools:
            logger.info(f"[{time.strftime('%H:%M:%S')}] -> Testing Compatibility Tool: {tool.name}")
            tool_start_t = time.time()

            for env_label, env_vars in env_matrix:
                combo_key = (tool.name, env_label)
                pass_count = 0
                total_ms_sum = 0.0

                runner = VRCTestRunner(proton_bin=tool.bin_path, prefix_dir=self.prefix_dir, env_vars=env_vars, wmf_exe=Config.WMF_EXE)

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
                combination_scores[combo_key] = RankedCombination(
                    rank=0,
                    proton_name=tool.name,
                    env_vars=env_vars,
                    env_str=" ".join([f"{k}={v}" for k, v in env_vars.items()]),
                    pass_count=pass_count,
                    total_tests=len(resolved_urls),
                    avg_ms=avg_ms,
                    launch_cmd=""
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

        for tool in self.proton_tools:
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
            launch_cmd = f"{item.env_str} %command% --enable-avpro-in-proton --disable-hw-video-decoding".strip()
            item.launch_cmd = launch_cmd

            results_json_data["rankings"].append(item.to_dict())

            status_str = "PASS" if item.pass_count == item.total_tests else "FAIL"
            rank_label = f"#{idx} BEST: {status_str}" if idx == 1 else f"#{idx}: {status_str}"

            logger.info(f" {rank_label}")
            logger.info(f"     Pass Rate : {item.pass_count}/{item.total_tests} Passed ({item.avg_ms:.0f}ms avg)")
            logger.info(f"     Proton    : {item.proton_name}")
            logger.info(f"     Launch Cmd: {launch_cmd}\n")

        try:
            Config.RESULTS_JSON.write_text(json.dumps(results_json_data, indent=2), encoding="utf-8")
            logger.success(f"Saved benchmark rankings to {Config.RESULTS_JSON}")
        except Exception as e:
            logger.error(f"Failed to save results.json: {e}")

        best_config = ranked_combos[0] if ranked_combos else None

        # Check user directive: If NO combinations pass, do NOT launch VRChat and exit with error
        if not best_config or best_config.pass_count == 0:
            logger.error("========================================================================")
            logger.error(" [!] ERROR: None of the tested compatibility combinations passed (0/6 passed).")
            logger.error(" Aborting VRChat launch because no working Proton/env setup was found.")
            logger.error("========================================================================")
            sys.exit(1)

        if auto_try and best_config:
            VRCLauncher.launch(Config.DEFAULT_TEST_WORLD_ID, target_rank=target_rank, best_config=best_config)

        return results, ranked_combos
