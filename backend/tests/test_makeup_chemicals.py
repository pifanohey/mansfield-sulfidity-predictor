"""Tests for makeup chemical abstraction.

Validates that all 4 makeup chemical configurations have correct
molecular weight factors, required keys, and consistent stoichiometry.
"""
import pytest
from app.engine.makeup_chemicals import MAKEUP_CHEMICALS, get_makeup_config


# ---------------------------------------------------------------------------
# Individual chemical config tests
# ---------------------------------------------------------------------------

def test_nash_config():
    c = get_makeup_config("nash")
    assert c["adds_s"] is True
    assert c["adds_na"] is True
    assert abs(c["s_factor"] - 0.5714) < 0.01
    assert abs(c["na2o_factor"] - 0.5529) < 0.01
    assert abs(c["na2o_per_unit"] - 1.1060) < 0.01


def test_saltcake_config():
    c = get_makeup_config("saltcake")
    assert c["adds_s"] is True
    assert c["adds_na"] is True
    assert abs(c["mw"] - 142.04) < 0.1
    assert abs(c["s_factor"] - 0.2254) < 0.01


def test_emulsified_sulfur_config():
    c = get_makeup_config("emulsified_sulfur")
    assert c["adds_s"] is True
    assert c["adds_na"] is False
    assert abs(c["s_factor"] - 1.0) < 0.01
    assert c["na_factor"] == 0.0
    assert c["na2o_factor"] == 0.0


def test_naoh_config():
    c = get_makeup_config("naoh")
    assert c["adds_s"] is False
    assert c["adds_na"] is True
    assert abs(c["na_factor"] - 0.5748) < 0.01
    assert c["s_factor"] == 0.0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------

def test_invalid_chemical_raises():
    with pytest.raises(KeyError):
        get_makeup_config("unknown_chemical")


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------

def test_all_chemicals_have_required_keys():
    required = {"name", "formula", "mw", "na2o_factor", "na2o_per_unit",
                "s_factor", "na_factor", "adds_na", "adds_s"}
    for chem_id, config in MAKEUP_CHEMICALS.items():
        for key in required:
            assert key in config, f"{chem_id} missing {key}"


# ---------------------------------------------------------------------------
# Molecular weight consistency checks
# ---------------------------------------------------------------------------

def test_nash_molecular_weight_consistency():
    """Verify NaSH factors are consistent with MW constants."""
    c = get_makeup_config("nash")
    # S_factor = MW_S / MW_NaSH = 32.065 / 56.06
    assert abs(c["s_factor"] - 32.065 / 56.06) < 0.001
    # na2o_factor = MW_Na2O / (2 * MW_NaSH) = 62.0 / 112.12
    assert abs(c["na2o_factor"] - 62.0 / (2 * 56.06)) < 0.001


def test_saltcake_molecular_weight_consistency():
    """Verify saltcake factors are consistent with MW constants."""
    c = get_makeup_config("saltcake")
    assert abs(c["s_factor"] - 32.065 / 142.04) < 0.001
    assert abs(c["na2o_factor"] - 62.0 / 142.04) < 0.001


def test_naoh_molecular_weight_consistency():
    """Verify NaOH factors are consistent with MW constants."""
    c = get_makeup_config("naoh")
    assert abs(c["na2o_factor"] - 62.0 / (2 * 40.0)) < 0.001
    assert abs(c["na_factor"] - 22.98 / 40.0) < 0.001


def test_emulsified_sulfur_is_pure():
    """Emulsified sulfur should be 100% S with zero Na contribution."""
    c = get_makeup_config("emulsified_sulfur")
    assert c["s_factor"] == 1.0
    assert c["na2o_factor"] == 0.0
    assert c["na2o_per_unit"] == 0.0
    assert c["na_factor"] == 0.0
    assert c["mw"] == 32.065


# ---------------------------------------------------------------------------
# Cross-check with existing CONV constants
# ---------------------------------------------------------------------------

def test_nash_matches_conv_constants():
    """NaSH config factors must match the existing CONV dict values."""
    from app.engine.constants import CONV
    c = get_makeup_config("nash")
    assert abs(c["na2o_factor"] - CONV['NaSH_to_Na2O']) < 1e-6
    assert abs(c["na2o_per_unit"] - CONV['Na2O_per_NaSH']) < 1e-6
    assert abs(c["s_factor"] - CONV['S_in_NaSH']) < 1e-6
    assert abs(c["na_factor"] - CONV['Na_in_NaSH']) < 1e-6


def test_saltcake_matches_conv_constants():
    """Saltcake config factors must match the existing CONV dict values."""
    from app.engine.constants import CONV
    c = get_makeup_config("saltcake")
    assert abs(c["na2o_factor"] - CONV['Na2SO4_to_Na2O']) < 1e-6
    assert abs(c["s_factor"] - CONV['S_in_Na2SO4']) < 1e-6
