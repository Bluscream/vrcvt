"""
VRCVideoTester (vrcvt) - Modular VRChat Video Player Compatibility Benchmark Package
Repository: https://github.com/Bluscream/vrcvt
"""

__version__ = "1.1.0"
__author__ = "Bluscream"

from .config import DEFAULT_URLS, DEFAULT_TEST_WORLD_ID, VRCHAT_DEBUG_ARGS
from .discovery import find_proton_tools, check_and_unlock_h264, find_vrchat_prefix
from .runner import VRCTestRunner
from .suite import VRCBenchmarkSuite
from .launcher import launch_vrchat_in_desktop_test_mode
