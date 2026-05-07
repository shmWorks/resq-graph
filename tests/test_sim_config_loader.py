"""
test_sim_config_loader.py – Sprint 7 (US-027)

Tests for the YAML simulation config loader.

Acceptance criteria:
- Supports SCREEN_W, SCREEN_H, TARGET_FPS.
- Supports profiles: default, headless, high_stress.
- Headless profile sets TARGET_FPS to 0.
- Unknown profile raises KeyError.
- Missing file raises FileNotFoundError.
"""
import os
import tempfile
import textwrap
import pytest

from src.sim_config_loader import load_sim_config


# ── Helpers ───────────────────────────────────────────────────────────────────

def _write_yaml(content: str) -> str:
    """Write YAML content to a temp file and return its path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False, encoding="utf-8"
    )
    f.write(textwrap.dedent(content))
    f.flush()
    f.close()
    return f.name


# ── Base config loading ────────────────────────────────────────────────────────

class TestBaseConfig:

    def test_loads_screen_dimensions(self):
        path = _write_yaml("""\
            SCREEN_W: 1200
            SCREEN_H: 900
            TARGET_FPS: 30
            profiles:
              default: {}
        """)
        cfg = load_sim_config(path)
        assert cfg["SCREEN_W"]   == 1200
        assert cfg["SCREEN_H"]   == 900
        assert cfg["TARGET_FPS"] == 30
        os.unlink(path)

    def test_loads_boolean_values(self):
        path = _write_yaml("""\
            TRAFFIC_ENABLED: true
            profiles:
              default: {}
        """)
        cfg = load_sim_config(path)
        assert cfg["TRAFFIC_ENABLED"] is True
        os.unlink(path)

    def test_loads_float_values(self):
        path = _write_yaml("""\
            POISSON_LAMBDA: 0.05
            profiles:
              default: {}
        """)
        cfg = load_sim_config(path)
        assert cfg["POISSON_LAMBDA"] == pytest.approx(0.05)
        os.unlink(path)


# ── Profile loading ────────────────────────────────────────────────────────────

class TestProfileLoading:

    def test_headless_profile_sets_target_fps_zero(self):
        path = _write_yaml("""\
            TARGET_FPS: 30
            SCREEN_W: 1200
            profiles:
              headless:
                TARGET_FPS: 0
        """)
        cfg = load_sim_config(path, profile="headless")
        assert cfg["TARGET_FPS"] == 0, (
            "headless profile must set TARGET_FPS to 0 (no render delay)."
        )
        os.unlink(path)

    def test_profile_overrides_only_declared_keys(self):
        path = _write_yaml("""\
            SCREEN_W: 1200
            TARGET_FPS: 30
            profiles:
              custom:
                TARGET_FPS: 60
        """)
        cfg = load_sim_config(path, profile="custom")
        assert cfg["TARGET_FPS"] == 60
        assert cfg["SCREEN_W"]   == 1200   # untouched by profile
        os.unlink(path)

    def test_default_profile_returns_base_values(self):
        path = _write_yaml("""\
            TARGET_FPS: 30
            profiles:
              default: {}
        """)
        cfg = load_sim_config(path, profile="default")
        assert cfg["TARGET_FPS"] == 30
        os.unlink(path)

    def test_no_profile_returns_base_values(self):
        path = _write_yaml("""\
            TARGET_FPS: 30
            profiles:
              default: {}
        """)
        cfg = load_sim_config(path, profile=None)
        assert cfg["TARGET_FPS"] == 30
        os.unlink(path)

    def test_profiles_key_stripped_from_result(self):
        path = _write_yaml("""\
            TARGET_FPS: 30
            profiles:
              default: {}
        """)
        cfg = load_sim_config(path)
        assert "profiles" not in cfg
        os.unlink(path)


# ── Error handling ─────────────────────────────────────────────────────────────

class TestErrorHandling:

    def test_missing_file_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_sim_config("/nonexistent/path/sim_config.yaml")

    def test_unknown_profile_raises_key_error(self):
        path = _write_yaml("""\
            TARGET_FPS: 30
            profiles:
              default: {}
        """)
        with pytest.raises(KeyError, match="unknown_profile"):
            load_sim_config(path, profile="unknown_profile")
        os.unlink(path)


# ── Real file smoke test ───────────────────────────────────────────────────────

class TestRealConfigFile:

    def test_real_sim_config_loads(self):
        """The project's actual sim_config.yaml must load without errors."""
        real_path = os.path.join(
            os.path.dirname(__file__), "..", "sim_config.yaml"
        )
        if not os.path.exists(real_path):
            pytest.skip("sim_config.yaml not found in project root.")
        cfg = load_sim_config(real_path)
        assert "SCREEN_W"   in cfg
        assert "TARGET_FPS" in cfg

    def test_real_headless_profile(self):
        real_path = os.path.join(
            os.path.dirname(__file__), "..", "sim_config.yaml"
        )
        if not os.path.exists(real_path):
            pytest.skip("sim_config.yaml not found in project root.")
        cfg = load_sim_config(real_path, profile="headless")
        assert cfg["TARGET_FPS"] == 0
