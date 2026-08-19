"""
VRCVideoTester (vrcvt) - Modular VRChat Video Player Compatibility Benchmark Package
Repository: https://github.com/Bluscream/vrcvt
"""

__version__ = "1.1.0"
__author__ = "Bluscream"

from .config import Config
from .models import ProtonTool, BenchmarkResult, RankedCombination, ErrorClassification, StreamUrlTarget
from .discovery import ProtonDiscovery
from .runner import VRCTestRunner, URLResolver
from .suite import VRCBenchmarkSuite
from .launcher import VRCLauncher
from .logger import VRCLogger, logger
