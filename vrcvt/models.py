"""
VRCVideoTester (vrcvt) - Strongly Typed Dataclasses and Models
"""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, ParseResult

class ErrorClassification(str, Enum):
    """Enumeration of known VRChat video stream diagnostic error classifications."""
    NONE = "NONE"
    MISSING_PROTON_BINARY = "MISSING_PROTON_BINARY"
    MISSING_HARNESS_BINARY = "MISSING_HARNESS_BINARY"
    SSL_GNUTLS_ERROR = "SSL_GNUTLS_ERROR"
    IYUV_CONVERSION_ERROR = "IYUV_CONVERSION_ERROR"
    DNS_RESOLUTION_ERROR = "DNS_RESOLUTION_ERROR"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"

@dataclass
class ProtonTool:
    """Represents an installed Proton compatibility tool instance."""
    name: str
    path: Path
    bin_path: Path

@dataclass
class StreamUrlTarget:
    """Represents a target stream URL with structured urllib.parse metadata."""
    raw_url: str

    @property
    def parsed(self) -> ParseResult:
        """Returns parsed URL structure using urllib.parse."""
        return urlparse(self.raw_url)

    @property
    def scheme(self) -> str:
        return self.parsed.scheme

    @property
    def host(self) -> str:
        return self.parsed.netloc or "local"

    @property
    def is_local(self) -> bool:
        return self.raw_url == "ASSET_LOCAL" or self.scheme == "" or Path(self.raw_url).is_file() or self.raw_url.startswith("C:\\")

@dataclass
class BenchmarkResult:
    """Represents the execution result of a single MediaFoundation stream test."""
    success: bool
    elapsed_ms: float
    hresult: str
    error_type: Optional[ErrorClassification | str] = None
    solution: Optional[str] = None
    attempts: int = 1
    stderr_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "elapsed_ms": self.elapsed_ms,
            "hresult": self.hresult,
            "error_type": str(self.error_type) if self.error_type else None,
            "solution": self.solution,
            "attempts": self.attempts,
            "stderr_snippet": self.stderr_snippet
        }

@dataclass
class RankedCombination:
    """Represents a scored (Proton, EnvVars) compatibility combination."""
    rank: int
    proton_name: str
    env_vars: Dict[str, str]
    env_str: str
    pass_count: int
    total_tests: int
    avg_ms: float
    launch_cmd: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rank": self.rank,
            "proton_name": self.proton_name,
            "env_vars": self.env_vars,
            "env_str": self.env_str,
            "pass_rate": f"{self.pass_count}/{self.total_tests}",
            "avg_ms": round(self.avg_ms, 1),
            "launch_cmd": self.launch_cmd
        }
