"""
VRCVideoTester (vrcvt) - Command Line Interface (CLI) Entrypoint
"""

import sys
import os
import argparse
from .config import DEFAULT_TEST_WORLD_ID
from .suite import VRCBenchmarkSuite
from .launcher import launch_vrchat_in_desktop_test_mode

def main():
    parser = argparse.ArgumentParser(
        description="VRCVideoTester (vrcvt) - VRChat Video Player Compatibility Tester",
        formatter_class=argparse.RawTextHelpFormatter
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

    # Standard / --try benchmark matrix execution
    suite = VRCBenchmarkSuite(custom_url=args.url)
    auto_try = try_val is not None
    target_rank = try_val if try_val is not None else 1
    
    suite.run_suite(auto_try=auto_try, target_rank=target_rank)

if __name__ == "__main__":
    main()
