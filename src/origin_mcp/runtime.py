from __future__ import annotations

import platform
import sys
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PythonRuntimeProfile:
    version: str
    executable: str
    implementation: str
    major: int
    minor: int
    origin_ext_tier: str
    recommended_backend: str
    note: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "executable": self.executable,
            "implementation": self.implementation,
            "major": self.major,
            "minor": self.minor,
            "origin_ext_tier": self.origin_ext_tier,
            "recommended_backend": self.recommended_backend,
            "note": self.note,
        }


def python_runtime_profile() -> PythonRuntimeProfile:
    major = sys.version_info.major
    minor = sys.version_info.minor
    if major != 3:
        tier = "unsupported"
        backend = "none"
        note = "OriginExt/originpro external automation expects CPython 3."
    elif 10 <= minor <= 12:
        tier = "preferred"
        backend = "origin_embedded_bridge"
        note = (
            "This Python version is compatible with external Origin automation, "
            "but the preferred origin-mcp route is the bridge running inside "
            "Origin's embedded Python session."
        )
    elif minor == 13:
        tier = "experimental"
        backend = "origin_embedded_bridge"
        note = (
            "Python 3.13 is newer than the commonly validated OriginExt range; prefer "
            "starting the bridge inside Origin's embedded Python."
        )
    else:
        tier = "unsupported_external"
        backend = "origin_embedded_bridge"
        note = (
            "Python 3.14+ is not a safe external OriginExt automation target here. "
            "Start the bridge inside Origin's embedded Python session."
        )
    return PythonRuntimeProfile(
        version=platform.python_version(),
        executable=sys.executable,
        implementation=platform.python_implementation(),
        major=major,
        minor=minor,
        origin_ext_tier=tier,
        recommended_backend=backend,
        note=note,
    )
