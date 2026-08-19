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
from .runner import VRCTestRunner
from .suite import VRCBenchmarkSuite
from .launcher import VRCLauncher
from .logger import logger

def parse_env_args(env_list: Optional[List[str]]) -> Dict[str, str]:
    """Parse list of KEY=VAL environment variable strings into a dict."""
    env_vars: Dict[str, str] = {}
    if not env_list:
        return env_vars
    for item in env_list:
        for pair in item.split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars

def parse_cmd_args(args_list: Optional[List[str]]) -> List[str]:
    """Parse list of command line argument strings into a list of flags."""
    cmd_args: List[str] = []
    if not args_list:
        return cmd_args
    for item in args_list:
        for token in item.split():
            if token.strip():
                cmd_args.append(token.strip())
    return cmd_args

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
        help="Specify a Proton tool name or path (e.g. 'Proton-GE RTSP Latest', 'GE-Proton9-25')"
    )
    parser.add_argument(
        "--env",
        action="append",
        type=str,
        help="Custom environment variable(s) (e.g. --env WINEDLLOVERRIDES=iyuv_32= --env G_TLS_GNUTLS_PRIORITY=NORMAL)"
    )
    parser.add_argument(
        "--args",
        action="append",
        type=str,
        help="Custom command line argument(s) passed to harness / Proton (e.g. --args --enable-avpro-in-proton)"
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
        help="Benchmark a specific custom stream or video URL"
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

    # --single mode: Run a single stream test with custom tool, env, and URL
    if args.single:
        proton_tools = ProtonDiscovery.find_proton_tools()
        prefix_dir = ProtonDiscovery.find_vrchat_prefix()

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

        env_vars = parse_env_args(args.env)
        cmd_args = parse_cmd_args(args.args)
        test_url = args.url or "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

        runner = VRCTestRunner(proton_bin=selected_proton_bin, prefix_dir=prefix_dir, env_vars=env_vars, cmd_args=cmd_args)
        result = runner.run_test(test_url, timeout=10, retries=1)

        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            logger.info("\n========================================================================")
            logger.info(" VRCVideoTester (vrcvt) - Single Test Execution Result")
            logger.info("========================================================================")
            logger.info(f" Proton Tool : {selected_tool_name}")
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

    # Standard / --try benchmark matrix execution
    suite = VRCBenchmarkSuite(custom_url=args.url)
    auto_try = try_val is not None
    target_rank = try_val if try_val is not None else 1
    
    suite.run_suite(auto_try=auto_try, target_rank=target_rank)

if __name__ == "__main__":
    main()
