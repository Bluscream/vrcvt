"""
VRCVideoTester (vrcvt) - Strongly Typed Dataclasses and Models
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

@dataclass
class ProtonTool:
    """Represents an installed Proton compatibility tool instance."""
    name: str
    path: Path
    bin_path: Path

@dataclass
class BenchmarkResult:
    """Represents the execution result of a single MediaFoundation stream test."""
    success: bool
    elapsed_ms: float
    hresult: str
    error_type: Optional[str] = None
    solution: Optional[str] = None
    attempts: int = 1
    stderr_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "elapsed_ms": self.elapsed_ms,
            "hresult": self.hresult,
            "error_type": self.error_type,
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
