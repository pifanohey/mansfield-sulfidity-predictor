"""Tests for mill configuration loading (mill_profile.py)."""
import pytest

from app.engine.mill_profile import load_mill_config, get_mill_config, FiberlineConfig, MillConfig
from app.engine.constants import DEFAULTS


# ── Loading & structure ──────────────────────────────────────────────────────

class TestLoadMillConfig:
    """Test loading pine_hill.json and inspecting structure."""

    def test_load_pine_hill(self):
        cfg = load_mill_config("pine_hill")
        assert isinstance(cfg, MillConfig)
        assert cfg.mill_name == "Pine Hill"

    def test_fiberline_count(self):
        cfg = load_mill_config("pine_hill")
        assert len(cfg.fiberlines) == 2

    def test_fiberline_ids(self):
        cfg = load_mill_config("pine_hill")
        ids = [fl.id for fl in cfg.fiberlines]
        assert "pine" in ids
        assert "semichem" in ids

    def test_pine_fiberline_type(self):
        cfg = load_mill_config("pine_hill")
        pine = [fl for fl in cfg.fiberlines if fl.id == "pine"][0]
        assert pine.type == "continuous"
        assert pine.cooking_type == "chemical"
        assert pine.uses_gl_charge is False

    def test_semichem_fiberline_type(self):
        cfg = load_mill_config("pine_hill")
        sc = [fl for fl in cfg.fiberlines if fl.id == "semichem"][0]
        assert sc.type == "batch"
        assert sc.cooking_type == "semichem"
        assert sc.uses_gl_charge is True

    def test_makeup_chemical(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.makeup_chemical in ("nash", "naoh", "saltcake")


# ── Fiberline defaults vs constants.py ───────────────────────────────────────

class TestFiberlineDefaults:
    """Verify fiberline default values match constants.py DEFAULTS."""

    def test_pine_production(self):
        cfg = load_mill_config("pine_hill")
        pine = [fl for fl in cfg.fiberlines if fl.id == "pine"][0]
        assert pine.production_bdt_day == pytest.approx(
            DEFAULTS["cont_production_bdt_day"], rel=1e-4
        )

    def test_pine_yield(self):
        cfg = load_mill_config("pine_hill")
        pine = [fl for fl in cfg.fiberlines if fl.id == "pine"][0]
        assert pine.yield_pct == pytest.approx(DEFAULTS["pine_yield_pct"], rel=1e-4)

    def test_pine_ea(self):
        cfg = load_mill_config("pine_hill")
        pine = [fl for fl in cfg.fiberlines if fl.id == "pine"][0]
        assert pine.ea_pct == pytest.approx(DEFAULTS["pine_ea_pct"], rel=1e-4)

    def test_pine_wood_moisture(self):
        cfg = load_mill_config("pine_hill")
        pine = [fl for fl in cfg.fiberlines if fl.id == "pine"][0]
        assert pine.wood_moisture == pytest.approx(
            DEFAULTS["wood_moisture_pine"], rel=1e-4
        )

    def test_pine_no_gl_charge(self):
        cfg = load_mill_config("pine_hill")
        pine = [fl for fl in cfg.fiberlines if fl.id == "pine"][0]
        assert pine.gl_ea_pct == 0.0

    def test_semichem_production(self):
        cfg = load_mill_config("pine_hill")
        sc = [fl for fl in cfg.fiberlines if fl.id == "semichem"][0]
        assert sc.production_bdt_day == pytest.approx(
            DEFAULTS["batch_production_bdt_day"], rel=1e-4
        )

    def test_semichem_yield(self):
        cfg = load_mill_config("pine_hill")
        sc = [fl for fl in cfg.fiberlines if fl.id == "semichem"][0]
        assert sc.yield_pct == pytest.approx(DEFAULTS["semichem_yield_pct"], rel=1e-4)

    def test_semichem_ea(self):
        cfg = load_mill_config("pine_hill")
        sc = [fl for fl in cfg.fiberlines if fl.id == "semichem"][0]
        assert sc.ea_pct == pytest.approx(DEFAULTS["semichem_ea_pct"], rel=1e-4)

    def test_semichem_gl_ea(self):
        cfg = load_mill_config("pine_hill")
        sc = [fl for fl in cfg.fiberlines if fl.id == "semichem"][0]
        assert sc.gl_ea_pct == pytest.approx(
            DEFAULTS["semichem_gl_ea_pct"], rel=1e-4
        )

    def test_semichem_wood_moisture(self):
        cfg = load_mill_config("pine_hill")
        sc = [fl for fl in cfg.fiberlines if fl.id == "semichem"][0]
        assert sc.wood_moisture == pytest.approx(
            DEFAULTS["wood_moisture_semichem"], rel=1e-4
        )


# ── Tank loading ─────────────────────────────────────────────────────────────

class TestTanks:
    """Verify tanks are loaded from the config."""

    def test_tank_count(self):
        cfg = load_mill_config("pine_hill")
        assert len(cfg.tanks) == 12

    def test_tank_ids(self):
        cfg = load_mill_config("pine_hill")
        tank_ids = {t["id"] for t in cfg.tanks}
        expected = {
            "wlc_1", "wlc_2", "gl_1", "gl_2", "dump_tank",
            "wbl_1", "wbl_2", "cssc_weak",
            "tank_50pct", "tank_55pct_1", "tank_55pct_2", "tank_65pct",
        }
        assert tank_ids == expected

    def test_tank_has_required_keys(self):
        cfg = load_mill_config("pine_hill")
        for tank in cfg.tanks:
            assert "id" in tank
            assert "name" in tank
            assert "constant" in tank
            assert "max_level" in tank
            assert "gal_per_ft" in tank
            assert "group" in tank

    def test_tank_gal_per_ft_consistent(self):
        """gal_per_ft should equal constant / max_level."""
        cfg = load_mill_config("pine_hill")
        for tank in cfg.tanks:
            expected = tank["constant"] / tank["max_level"]
            assert tank["gal_per_ft"] == pytest.approx(expected, rel=1e-6), (
                f"Tank {tank['id']}: gal_per_ft {tank['gal_per_ft']} != "
                f"constant/max_level {expected}"
            )


# ── Non-fiberline defaults ───────────────────────────────────────────────────

class TestMillDefaults:
    """Verify mill-level defaults match constants.py."""

    def test_target_sulfidity(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["target_sulfidity_pct"] == DEFAULTS["target_sulfidity_pct"]

    def test_reduction_efficiency(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["reduction_efficiency_pct"] == DEFAULTS["reduction_efficiency_pct"]

    def test_causticity(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["causticity_pct"] == DEFAULTS["causticity_pct"]

    def test_bl_flow(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["bl_flow_gpm"] == DEFAULTS["bl_flow_gpm"]

    def test_saltcake(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["saltcake_flow_lb_hr"] == DEFAULTS["saltcake_flow_lb_hr"]

    def test_loss_table_ncg_s(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["loss_ncg_s"] == DEFAULTS["loss_ncg_s"]

    def test_loss_table_ncg_na(self):
        cfg = load_mill_config("pine_hill")
        assert cfg.defaults["loss_ncg_na"] == DEFAULTS["loss_ncg_na"]


# ── Error handling ───────────────────────────────────────────────────────────

class TestErrorHandling:
    """Test error cases."""

    def test_invalid_mill_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_mill_config("nonexistent_mill_xyz")


# ── get_mill_config env var ──────────────────────────────────────────────────

class TestGetMillConfig:
    """Test the convenience get_mill_config() function."""

    def test_default_loads_pine_hill(self, monkeypatch):
        monkeypatch.delenv("MILL_CONFIG", raising=False)
        cfg = get_mill_config()
        assert cfg.mill_name == "Pine Hill"

    def test_env_var_overrides(self, monkeypatch):
        monkeypatch.setenv("MILL_CONFIG", "nonexistent_mill_xyz")
        with pytest.raises(FileNotFoundError):
            get_mill_config()
