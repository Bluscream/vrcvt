"""
VRCVideoTester (vrcvt) - Command Line Interface (CLI) Entrypoint
"""

import sys
import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional

from .config import Config
from .discovery import ProtonDiscovery
from .runner import VRCTestRunner, parse_cmd_string
from .suite import VRCBenchmarkSuite
from .launcher import VRCLauncher
from .logger import logger

def main() -> None:
    parser = argparse.ArgumentParser(
        description="VRCVideoTester (vrcvt) - VRChat Video Player Compatibility Tester",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--single",
        action="store_true",
        help="Run a single stream compatibility test instead of the full benchmark matrix"
    )
    parser.add_argument(
        "--tool",
        type=str,
        help="Specify or filter Proton compatibility tools (e.g. 'GE-Proton9-25', 'Proton-GE RTSP Latest')"
    )
    parser.add_argument(
        "--runtime",
        "--env",
        dest="runtime",
        type=str,
        help="Specify or filter Steam Linux Runtime container environment (e.g. 'SteamLinuxRuntime_4', 'SteamLinuxRuntime_sniper', 'HostNative')"
    )
    parser.add_argument(
        "--harness",
        type=str,
        default="unity",
        choices=["unity", "wmf"],
        help="Select video test harness backend binary: 'unity' (VRChatVideoTester.exe, default) or 'wmf' (wmf_test.exe)"
    )
    parser.add_argument(
        "--cmd",
        type=str,
        help="Specify or filter Steam launch command line (e.g. 'WINEDLLOVERRIDES=\"iyuv_32=\" %%command%% --enable-hw-video-decoding')"
    )
    parser.add_argument(
        "--try",
        nargs="?",
        const=1,
        type=int,
        metavar="RANK",
        help="Launch VRChat in 4:3 Desktop Debug mode using specified target rank from results.json (default: 1)"
    )
    parser.add_argument(
        "--no-tests",
        action="store_true",
        help="Skip benchmark matrix tests and launch VRChat directly in Desktop Debug mode"
    )
    parser.add_argument(
        "--url",
        type=str,
        help="Benchmark or filter target video stream URL"
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results for automated tooling"
    )

    args = parser.parse_args()

    # --no-tests mode: Bypass benchmark suite and launch VRChat directly
    try_val = getattr(args, "try")
    if args.no_tests:
        target_rank = try_val if try_val is not None else 1
        VRCLauncher.launch(Config.DEFAULT_TEST_WORLD_ID, target_rank=target_rank)
        sys.exit(0)

    # --single mode: Run a single stream test with custom tool, container runtime, cmd string, and URL
    if args.single:
        proton_tools = ProtonDiscovery.find_proton_tools()
        prefix_dir = ProtonDiscovery.find_vrchat_prefix()
        container_runtimes = ProtonDiscovery.find_all_container_runtimes()

        selected_proton_bin: Optional[Path] = None
        selected_tool_name = "Default System Proton"

        if args.tool:
            for tool in proton_tools:
                if args.tool.lower() in tool.name.lower() or args.tool == str(tool.path) or args.tool == str(tool.bin_path):
                    selected_proton_bin = tool.bin_path
                    selected_tool_name = tool.name
                    break
            if not selected_proton_bin and Path(args.tool).is_file():
                selected_proton_bin = Path(args.tool)
                selected_tool_name = selected_proton_bin.name

        if not selected_proton_bin and proton_tools:
            selected_tool_name = proton_tools[0].name
            selected_proton_bin = proton_tools[0].bin_path

        selected_runtime: Optional[Path | str] = None
        selected_runtime_name = "Auto-detected Container"
        if args.runtime:
            for r in container_runtimes:
                if args.runtime.lower() in r.name.lower():
                    selected_runtime = r.run_path if r.name != "HostNative" else "HostNative"
                    selected_runtime_name = r.name
                    break

        env_vars, cmd_args = parse_cmd_string(args.cmd)
        test_url = args.url or "https://media.w3.org/2010/05/sintel/trailer.mp4"
        harness_bin = Config.get_harness_exe(args.harness)

        runner = VRCTestRunner(
            proton_bin=selected_proton_bin,
            prefix_dir=prefix_dir,
            env_vars=env_vars,
            cmd_args=cmd_args,
            wmf_exe=harness_bin,
            container_runner=selected_runtime
        )
        result = runner.run_test(test_url, timeout=20, retries=1)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            logger.info("\n========================================================================")
            logger.info(" VRCVideoTester (vrcvt) - Single Test Execution Result")
            logger.info("========================================================================")
            logger.info(f" Proton Tool : {selected_tool_name}")
            logger.info(f" Runtime     : {selected_runtime_name}")
            logger.info(f" Harness     : {args.harness} ({harness_bin.name})")
            logger.info(f" Target URL  : {test_url}")
            logger.info(f" Env Vars    : {env_vars}")
            logger.info(f" Cmd Args    : {cmd_args}")
            if result.success:
                logger.success(f"Result      : PASS (Latency: {result.elapsed_ms:.1f}ms | HRESULT: {result.hresult})")
            else:
                logger.error(f"Result      : FAIL (Latency: {result.elapsed_ms:.1f}ms | HRESULT: {result.hresult})")
                logger.error(f" Error Type  : {result.error_type}")
                logger.error(f" Solution    : {result.solution}")
            logger.info("")

        sys.exit(0 if result.success else 1)

    # Multi-layered / filtered benchmark matrix execution
    suite = VRCBenchmarkSuite(custom_url=args.url)
    auto_try = try_val is not None
    target_rank = try_val if try_val is not None else 1

    suite.run_suite(
        auto_try=auto_try,
        target_rank=target_rank,
        tool_filter=args.tool,
        env_filter=args.runtime,
        cmd_filter=args.cmd,
        url_filter=args.url
    )

if __name__ == "__main__":
    main()
