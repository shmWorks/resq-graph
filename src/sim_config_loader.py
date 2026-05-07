"""
sim_config_loader.py – Sprint 7 (US-027)

Loads sim_config.yaml and optionally merges a named profile on top of the
base values.  The returned dict is the single source of truth for all
runtime parameters; it supersedes the hard-coded values in config.py so
that both can coexist during the migration.

Usage
-----
    from src.sim_config_loader import load_sim_config

    cfg = load_sim_config("sim_config.yaml", profile="headless")
    print(cfg["TARGET_FPS"])   # 0

Profile merge semantics
-----------------------
The base-level keys form the defaults.  A profile's key-value pairs are
shallow-merged on top (``base.update(profile_overrides)``).  The special
``profiles:`` key itself is stripped from the returned dict.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ── Optional YAML backend ──────────────────────────────────────────────────────

try:
    import yaml as _yaml                  # PyYAML
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def _parse_yaml(path: str) -> dict:
    """Parse a YAML file using PyYAML if available, else a minimal fallback."""
    if _HAS_YAML:
        with open(path, "r", encoding="utf-8") as fh:
            return _yaml.safe_load(fh) or {}
    return _minimal_yaml_parse(path)


def _minimal_yaml_parse(path: str) -> dict:
    """
    Minimal key: value / key: {sub-key: value} YAML parser for environments
    without PyYAML installed.  Supports scalar values and a single level of
    nested mapping (used for the ``profiles:`` block).
    """
    result: dict[str, Any] = {}
    current_profile: str | None = None
    in_profiles = False

    def _cast(v: str) -> Any:
        v = v.strip()
        if v.lower() == "true":
            return True
        if v.lower() == "false":
            return False
        if v.lower() == "null":
            return None
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v.strip('"').strip("'")

    with open(path, "r", encoding="utf-8") as fh:
        for raw_line in fh:
            line = raw_line.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue

            indent = len(line) - len(line.lstrip())

            if indent == 0:
                in_profiles = False
                current_profile = None

            if ":" not in line:
                continue

            key, _, value = line.partition(":")
            key   = key.strip()
            value = value.strip()

            if indent == 0 and key == "profiles":
                in_profiles = True
                result["profiles"] = {}
                continue

            if in_profiles and indent == 2:
                # profile name
                current_profile = key
                result["profiles"][current_profile] = {}
                continue

            if in_profiles and indent == 4 and current_profile is not None:
                result["profiles"][current_profile][key] = _cast(value)
                continue

            if indent == 0 and not in_profiles:
                result[key] = _cast(value)

    return result


# ── Public API ────────────────────────────────────────────────────────────────

_DEFAULT_CONFIG_PATH = str(
    Path(__file__).parent.parent / "sim_config.yaml"
)


def load_sim_config(
    path: str = _DEFAULT_CONFIG_PATH,
    profile: str | None = None,
) -> dict[str, Any]:
    """Load the YAML config and apply *profile* overrides.

    Parameters
    ----------
    path:
        Filesystem path to ``sim_config.yaml``.  Defaults to the project root.
    profile:
        Name of the profile to merge (e.g. ``"headless"``).  ``None`` means
        use the raw base values with no overrides.

    Returns
    -------
    dict
        Merged configuration dict with the ``profiles`` key removed.

    Raises
    ------
    FileNotFoundError
        If *path* does not exist.
    KeyError
        If *profile* is specified but does not exist in the YAML.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Config file not found: {path!r}")

    raw = _parse_yaml(path)

    # Extract and remove the profiles meta-section before returning
    profiles: dict[str, dict] = raw.pop("profiles", {})

    if profile is not None:
        if profile not in profiles:
            raise KeyError(
                f"Profile {profile!r} not found in {path!r}. "
                f"Available: {list(profiles.keys())}"
            )
        overrides = profiles.get(profile) or {}
        raw.update(overrides)
        logger.info("Loaded config profile %r from %s", profile, path)
    else:
        logger.info("Loaded base config from %s", path)

    return raw
