"""
VRCVideoTester (vrcvt) - Matrix Benchmark Suite & Dynamic Ranking Engine
"""

import os
import sys
import time
import json
from collections import defaultdict
from .config import (
    COLOR_RESET, COLOR_BOLD, COLOR_RED, COLOR_GREEN, COLOR_YELLOW,
    COLOR_CYAN, COLOR_GRAY, DEFAULT_URLS, DEFAULT_TEST_WORLD_ID
)
from .discovery import find_proton_tools, check_and_unlock_h264, find_vrchat_prefix
from .runner import VRCTestRunner, resolve_url_ytdlp

class VRCBenchmarkSuite:
    """Executes full diagnostic matrix across Proton versions, stream URLs, and environment variables."""

    def __init__(self, custom_url=None):
        self.custom_url = custom_url
        self.prefix_dir = find_vrchat_prefix()
        self.proton_tools = find_proton_tools()

    def run_suite(self, auto_try=False, target_rank=1):
        """Execute full matrix benchmark, rank combinations, save results.json, and launch VRChat if valid combination passes."""
        start_time_iso = time.strftime("%Y-%m-%d %H:%M:%S")
        suite_start_t = time.time()
        
        check_and_unlock_h264()
        
        print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN} VRCVideoTester (vrcvt) - Full Diagnostic Matrix & Compatibility Benchmark{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
        print(f" [{time.strftime('%H:%M:%S')}] Benchmark Start Time  : {start_time_iso}")
        print(f" Discovered Proton Tools : {len(self.proton_tools)}")
        print(f" Target VRChat Prefix    : {self.prefix_dir}")

        package_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(package_dir)
        wmf_exe = os.path.join(project_root, "assets/wmf_test.exe")
        sample_mp4 = os.path.join(project_root, "assets/sample.mp4")

        print(f" WMF Harness Binary      : {wmf_exe}")
        print(f" Bundled Local Asset     : {sample_mp4}\n")
        
        test_urls = DEFAULT_URLS.copy()
        if self.custom_url:
            test_urls["Custom CLI URL"] = self.custom_url
            
        resolved_urls = {}
        total_ytdlp_time = 0.0
        
        print(f" [{time.strftime('%H:%M:%S')}] Pre-resolving stream URLs via yt-dlp...")
        dummy_proton = self.proton_tools[0][2] if self.proton_tools else "proton"
        
        for name, orig_url in test_urls.items():
            if orig_url == "ASSET_LOCAL":
                resolved_urls[name] = (sample_mp4, 0.0)
            else:
                res_url, y_time, _, _, _ = resolve_url_ytdlp(dummy_proton, self.prefix_dir, orig_url)
                resolved_urls[name] = (res_url, y_time)
                total_ytdlp_time += y_time
                
        print(f" [{time.strftime('%H:%M:%S')}] All stream URLs resolved successfully.\n")

        env_matrix = [
            ("Default (Unset)", {}),
            ("WINEDLLOVERRIDES=iyuv_32=", {"WINEDLLOVERRIDES": "iyuv_32="}),
            ("G_TLS_GNUTLS_PRIORITY=NORMAL", {"G_TLS_GNUTLS_PRIORITY": "NORMAL"}),
            ("WINEDLLOVERRIDES=iyuv_32= + GnuTLS", {"WINEDLLOVERRIDES": "iyuv_32=", "G_TLS_GNUTLS_PRIORITY": "NORMAL"})
        ]

        results = defaultdict(dict)
        combination_scores = {}
        tool_runtimes = defaultdict(lambda: {"wmf_ms": 0.0, "count": 0})
        
        total_wmf_time = 0.0
        total_subtests_executed = 0

        for p_name, p_dir, p_bin in self.proton_tools:
            print(f"{COLOR_BOLD}{COLOR_YELLOW}[{time.strftime('%H:%M:%S')}] -> Testing Compatibility Tool: {p_name}{COLOR_RESET}")
            tool_start_t = time.time()
            
            for env_label, env_vars in env_matrix:
                combo_key = (p_name, env_label)
                pass_count = 0
                total_ms_sum = 0.0
                
                runner = VRCTestRunner(proton_bin=p_bin, prefix_dir=self.prefix_dir, env_vars=env_vars, wmf_exe=wmf_exe)
                
                for stream_name, (res_url, y_time) in resolved_urls.items():
                    res = runner.run_test(res_url, timeout=10, retries=1)
                    
                    results[combo_key][stream_name] = res
                    total_ms_sum += res['elapsed_ms']
                    total_wmf_time += res['elapsed_ms']
                    total_subtests_executed += 1
                    
                    tool_runtimes[p_name]["wmf_ms"] += res['elapsed_ms']
                    tool_runtimes[p_name]["count"] += 1
                    
                    if res['success']:
                        pass_count += 1
                        
                avg_ms = total_ms_sum / max(1, len(resolved_urls))
                combination_scores[combo_key] = {
                    "pass_count": pass_count,
                    "avg_ms": avg_ms,
                    "total_tests": len(resolved_urls),
                    "proton_name": p_name,
                    "env_label": env_label,
                    "env_vars": env_vars
                }

        suite_total_time = time.time() - suite_start_t

        print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN} BENCHMARK SUITE TIMING BREAKDOWN & PERFORMANCE METRICS{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
        print(f" Total Benchmark Suite Runtime : {int(suite_total_time // 60)}m {suite_total_time % 60:.1f}s ({suite_total_time:.1f}s total)")
        print(f" Total Sub-Tests Executed      : {total_subtests_executed} sub-tests")
        print(f" Total yt-dlp Resolution Time  : {total_ytdlp_time/1000.0:.1f}s ({(total_ytdlp_time/1000.0/suite_total_time)*100:.1f}% of total runtime)")
        print(f" Total WMF Harness Execution   : {total_wmf_time/1000.0:.1f}s ({(total_wmf_time/1000.0/suite_total_time)*100:.1f}% of total runtime)")
        print(f" Average Sub-Test Latency      : {total_wmf_time / max(1, total_subtests_executed):.0f}ms / sub-test")
        print(f"\n PER-TOOL RUNTIME BREAKDOWN:")

        for p_name, _p_dir, _p_bin in self.proton_tools:
            t_data = tool_runtimes[p_name]
            avg_wmf = t_data["wmf_ms"] / max(1, t_data["count"])
            print(f"   • {p_name:<26} : Avg WMF Decode = {avg_wmf:.0f}ms")

        # Sort combinations dynamically from BEST to WORST
        ranked_combos = sorted(
            combination_scores.values(),
            key=lambda x: (-x['pass_count'], x['avg_ms'])
        )

        results_json_data = {
            "start_time": start_time_iso,
            "suite_runtime_seconds": round(suite_total_time, 2),
            "rankings": []
        }

        print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN} DYNAMIC RANKED RECOMMENDATIONS (BEST TO WORST BY PASS RATE & TIMING){COLOR_RESET}")
        print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
        
        for idx, item in enumerate(ranked_combos, 1):
            env_str = " ".join([f"{k}={v}" for k, v in item['env_vars'].items()])
            launch_cmd = f"{env_str} %command% --enable-avpro-in-proton --disable-hw-video-decoding".strip()
            item['rank'] = idx
            item['env_str'] = env_str
            item['launch_cmd'] = launch_cmd

            results_json_data["rankings"].append({
                "rank": idx,
                "pass_rate": f"{item['pass_count']}/{item['total_tests']}",
                "avg_ms": round(item['avg_ms'], 1),
                "proton_name": item['proton_name'],
                "env_vars": item['env_vars'],
                "env_str": env_str,
                "launch_cmd": launch_cmd
            })

            status_str = f"{COLOR_GREEN}PASS{COLOR_RESET}" if item['pass_count'] == item['total_tests'] else f"{COLOR_RED}FAIL{COLOR_RESET}"
            rank_label = f"#1 BEST: {status_str}" if idx == 1 else f"#{idx}: {status_str}"
            
            print(f" {COLOR_BOLD}{rank_label}")
            print(f"     Pass Rate : {item['pass_count']}/{item['total_tests']} Passed ({item['avg_ms']:.0f}ms avg)")
            print(f"     Proton    : {item['proton_name']}")
            print(f"     Launch Cmd: {launch_cmd}\n")

        results_file = os.path.join(project_root, "results.json")
        try:
            with open(results_file, "w") as f:
                json.dump(results_json_data, f, indent=2)
            print(f"{COLOR_GREEN}[✓] Saved benchmark rankings to {results_file}{COLOR_RESET}\n")
        except Exception as e:
            print(f"{COLOR_RED}[!] Failed to save results.json: {e}{COLOR_RESET}\n")

        best_config = ranked_combos[0] if ranked_combos else None

        # Check user directive: If NO combinations pass, do NOT launch VRChat and exit with error
        if not best_config or best_config['pass_count'] == 0:
            print(f"{COLOR_BOLD}{COLOR_RED}========================================================================{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_RED} [!] ERROR: None of the tested compatibility combinations passed (0/6 passed).{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_RED} Aborting VRChat launch because no working Proton/env setup was found.{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_RED}========================================================================{COLOR_RESET}")
            sys.exit(1)

        if auto_try:
            from .launcher import launch_vrchat_in_desktop_test_mode
            launch_vrchat_in_desktop_test_mode(DEFAULT_TEST_WORLD_ID, target_rank=target_rank, best_config=best_config)

        return results, ranked_combos
