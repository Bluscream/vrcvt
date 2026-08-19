"""
VRCVideoTester (vrcvt) - Command Line Interface (CLI) Entrypoint
"""

import sys
import os
import argparse
import json
from .config import DEFAULT_TEST_WORLD_ID, COLOR_RESET, COLOR_BOLD, COLOR_GREEN, COLOR_YELLOW, COLOR_RED, COLOR_CYAN
from .discovery import find_proton_tools, find_vrchat_prefix
from .runner import VRCTestRunner
from .suite import VRCBenchmarkSuite
from .launcher import launch_vrchat_in_desktop_test_mode

def parse_env_args(env_list):
    """Parse list of KEY=VAL environment variable strings into a dict."""
    env_vars = {}
    if not env_list:
        return env_vars
    for item in env_list:
        for pair in item.split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                env_vars[k.strip()] = v.strip()
    return env_vars

def parse_cmd_args(args_list):
    """Parse list of command line argument strings into a list of flags."""
    cmd_args = []
    if not args_list:
        return cmd_args
    for item in args_list:
        for token in item.split():
            if token.strip():
                cmd_args.append(token.strip())
    return cmd_args

def main():
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
        launch_vrchat_in_desktop_test_mode(DEFAULT_TEST_WORLD_ID, target_rank=target_rank)
        sys.exit(0)

    # --single mode: Run a single stream test with custom tool, env, and URL
    if args.single:
        proton_tools = find_proton_tools()
        prefix_dir = find_vrchat_prefix()

        selected_proton_bin = None
        selected_tool_name = "Default System Proton"

        if args.tool:
            for name, path, bin_path in proton_tools:
                if args.tool.lower() in name.lower() or args.tool == path or args.tool == bin_path:
                    selected_proton_bin = bin_path
                    selected_tool_name = name
                    break
            if not selected_proton_bin and os.path.isfile(args.tool):
                selected_proton_bin = args.tool
                selected_tool_name = os.path.basename(args.tool)

        if not selected_proton_bin and proton_tools:
            selected_tool_name, _, selected_proton_bin = proton_tools[0]

        env_vars = parse_env_args(args.env)
        cmd_args = parse_cmd_args(args.args)
        test_url = args.url or "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4"

        runner = VRCTestRunner(proton_bin=selected_proton_bin, prefix_dir=prefix_dir, env_vars=env_vars, cmd_args=cmd_args)
        result = runner.run_test(test_url, timeout=10, retries=1)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"\n{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_CYAN} VRCVideoTester (vrcvt) - Single Test Execution Result{COLOR_RESET}")
            print(f"{COLOR_BOLD}{COLOR_CYAN}========================================================================{COLOR_RESET}")
            print(f" Proton Tool : {COLOR_YELLOW}{selected_tool_name}{COLOR_RESET}")
            print(f" Target URL  : {test_url}")
            print(f" Env Vars    : {env_vars}")
            print(f" Cmd Args    : {cmd_args}")
            status_str = f"{COLOR_GREEN}PASS{COLOR_RESET}" if result['success'] else f"{COLOR_RED}FAIL{COLOR_RESET}"
            print(f" Result      : {status_str} (Latency: {result['elapsed_ms']:.1f}ms | HRESULT: {result['hresult']})")
            if not result['success']:
                print(f" Error Type  : {result.get('error_type')}")
                print(f" Solution    : {result.get('solution')}")
            print()

        sys.exit(0 if result['success'] else 1)

    # Standard / --try benchmark matrix execution
    suite = VRCBenchmarkSuite(custom_url=args.url)
    auto_try = try_val is not None
    target_rank = try_val if try_val is not None else 1
    
    suite.run_suite(auto_try=auto_try, target_rank=target_rank)

if __name__ == "__main__":
    main()
