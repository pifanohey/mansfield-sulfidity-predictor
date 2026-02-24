"""
Unit tests for fiberline BL generation and evaporator modules.

Tests cover:
  - Fiberline BL output (compound mass tracking, element conservation)
  - WBL mixer (stream addition, CTO brine)
  - Evaporator (solids conservation, water removal)
"""

import pytest
from app.engine.constants import MW, CONV, DEFAULTS
from app.engine.fiberline import (
    calculate_fiberline_bl, mix_wbl_streams,
    FiberlineBLOutput, MixedWBLOutput,
)
from app.engine.evaporator import calculate_evaporator, EvaporatorOutput


# ── Test data: typical WL species from slaker (g Na2O/L) ──
WL_NA2S = 32.0     # g Na2O/L
WL_NAOH = 65.0     # g Na2O/L
WL_NA2CO3 = 20.0   # g Na2O/L


class TestFiberlineBLOutput:
    """Test single fiberline BL generation."""

    @pytest.fixture
    def pine_bl(self):
        return calculate_fiberline_bl(
            production_bdt_day=1250.69,
            yield_pct=0.5694,
            wl_flow_gpm=500.0,
            wl_na2s_g_L=WL_NA2S,
            wl_naoh_g_L=WL_NAOH,
            wl_na2co3_g_L=WL_NA2CO3,
            wood_moisture_pct=0.523,
            s_loss_digester_pct=0.02,
        )

    def test_positive_outputs(self, pine_bl):
        """All outputs should be positive for valid inputs."""
        assert pine_bl.wbl_flow_lb_hr > 0
        assert pine_bl.wbl_tds_pct > 0
        assert pine_bl.wbl_na_pct_ds > 0
        assert pine_bl.wbl_s_pct_ds > 0
        assert pine_bl.na_element_lb_hr > 0
        assert pine_bl.s_element_lb_hr > 0
        assert pine_bl.inorganic_solids_lb_hr > 0
        assert pine_bl.organics_lb_hr > 0
        assert pine_bl.water_lb_hr > 0

    def test_total_solids_sum(self, pine_bl):
        """Total solids = inorganic + organics."""
        assert pine_bl.total_solids_lb_hr == pytest.approx(
            pine_bl.inorganic_solids_lb_hr + pine_bl.organics_lb_hr, rel=1e-6
        )

    def test_total_flow_sum(self, pine_bl):
        """Total flow = solids + water."""
        assert pine_bl.wbl_flow_lb_hr == pytest.approx(
            pine_bl.total_solids_lb_hr + pine_bl.water_lb_hr, rel=1e-6
        )

    def test_tds_pct_calculation(self, pine_bl):
        """TDS% = solids / total_flow × 100."""
        expected_tds = pine_bl.total_solids_lb_hr / pine_bl.wbl_flow_lb_hr * 100
        assert pine_bl.wbl_tds_pct == pytest.approx(expected_tds, rel=1e-6)

    def test_na_pct_ds(self, pine_bl):
        """Na% d.s. = Na_element / total_solids × 100."""
        expected = pine_bl.na_element_lb_hr / pine_bl.total_solids_lb_hr * 100
        assert pine_bl.wbl_na_pct_ds == pytest.approx(expected, rel=1e-6)

    def test_s_pct_ds(self, pine_bl):
        """S% d.s. = S_element / total_solids × 100."""
        expected = pine_bl.s_element_lb_hr / pine_bl.total_solids_lb_hr * 100
        assert pine_bl.wbl_s_pct_ds == pytest.approx(expected, rel=1e-6)

    def test_compound_mass_exceeds_element_mass(self, pine_bl):
        """Compound mass (incl. oxygen) must exceed Na+S element mass."""
        na_plus_s = pine_bl.na_element_lb_hr + pine_bl.s_element_lb_hr
        assert pine_bl.inorganic_solids_lb_hr > na_plus_s

    def test_s_conserved_through_fiberline(self):
        """S from WL Na2S should pass through to BL without double-counting NCG.

        NCG losses are tracked in the unified loss table for NaSH sizing,
        NOT subtracted in the fiberline. The WL Na2S already reflects
        steady-state losses from the cycle.
        """
        bl = calculate_fiberline_bl(
            production_bdt_day=1000, yield_pct=0.57, wl_flow_gpm=400,
            wl_na2s_g_L=30, wl_naoh_g_L=60, wl_na2co3_g_L=20,
        )
        # S element should equal S from Na2S compound (no subtraction)
        from app.engine.constants import MW, CONV
        expected_na2s = 30 * 400 * CONV['GPM_GL_TO_LB_HR'] * CONV['Na2S_to_compound']
        expected_s = expected_na2s * (MW['S'] / MW['Na2S'])
        assert abs(bl.s_element_lb_hr - expected_s) / expected_s < 0.001

    def test_zero_production_returns_zeros(self):
        """Zero production should return zero outputs."""
        bl = calculate_fiberline_bl(
            production_bdt_day=0, yield_pct=0.57, wl_flow_gpm=400,
            wl_na2s_g_L=30, wl_naoh_g_L=60, wl_na2co3_g_L=20,
        )
        assert bl.wbl_flow_lb_hr == 0
        assert bl.total_solids_lb_hr == 0

    def test_wbl_tds_in_reasonable_range(self, pine_bl):
        """WBL TDS% should be in weak black liquor range (10-40%).

        Higher values (>25%) occur with low-yield pulping (pine kraft at ~57%)
        where dissolved wood organics are a large fraction of total solids.
        """
        assert 5 < pine_bl.wbl_tds_pct < 40


class TestWBLMixer:
    """Test WBL stream mixing with CTO brine."""

    @pytest.fixture
    def mixed(self):
        pine = calculate_fiberline_bl(
            production_bdt_day=1250.69, yield_pct=0.5694, wl_flow_gpm=500,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        semichem = calculate_fiberline_bl(
            production_bdt_day=636.854, yield_pct=0.7019, wl_flow_gpm=100,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        return mix_wbl_streams(
            pine_bl=pine, semichem_bl=semichem,
            cto_na_lb_hr=100.0, cto_s_lb_hr=50.0, cto_water_lb_hr=500.0,
        )

    def test_na_conservation(self, mixed):
        """Na in mixed = sum of all Na sources."""
        pine = calculate_fiberline_bl(
            production_bdt_day=1250.69, yield_pct=0.5694, wl_flow_gpm=500,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        semichem = calculate_fiberline_bl(
            production_bdt_day=636.854, yield_pct=0.7019, wl_flow_gpm=100,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        expected_na = pine.na_element_lb_hr + semichem.na_element_lb_hr + 100.0
        assert mixed.na_element_lb_hr == pytest.approx(expected_na, rel=1e-6)

    def test_s_conservation(self, mixed):
        """S in mixed = sum of all S sources."""
        pine = calculate_fiberline_bl(
            production_bdt_day=1250.69, yield_pct=0.5694, wl_flow_gpm=500,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        semichem = calculate_fiberline_bl(
            production_bdt_day=636.854, yield_pct=0.7019, wl_flow_gpm=100,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        expected_s = pine.s_element_lb_hr + semichem.s_element_lb_hr + 50.0
        assert mixed.s_element_lb_hr == pytest.approx(expected_s, rel=1e-6)

    def test_positive_tds(self, mixed):
        """Mixed stream should have positive TDS%."""
        assert mixed.tds_pct > 0

    def test_cto_adds_s(self):
        """Adding CTO S should increase S% d.s."""
        pine = calculate_fiberline_bl(
            production_bdt_day=1000, yield_pct=0.57, wl_flow_gpm=400,
            wl_na2s_g_L=30, wl_naoh_g_L=60, wl_na2co3_g_L=20,
        )
        semichem = calculate_fiberline_bl(
            production_bdt_day=600, yield_pct=0.70, wl_flow_gpm=80,
            wl_na2s_g_L=30, wl_naoh_g_L=60, wl_na2co3_g_L=20,
        )
        mixed_no_cto = mix_wbl_streams(pine, semichem)
        mixed_with_cto = mix_wbl_streams(pine, semichem, cto_s_lb_hr=200.0, cto_na_lb_hr=150.0)
        assert mixed_with_cto.s_pct_ds > mixed_no_cto.s_pct_ds


class TestEvaporator:
    """Test evaporator solids conservation and water removal."""

    @pytest.fixture
    def wbl(self):
        pine = calculate_fiberline_bl(
            production_bdt_day=1250.69, yield_pct=0.5694, wl_flow_gpm=500,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        semichem = calculate_fiberline_bl(
            production_bdt_day=636.854, yield_pct=0.7019, wl_flow_gpm=100,
            wl_na2s_g_L=WL_NA2S, wl_naoh_g_L=WL_NAOH, wl_na2co3_g_L=WL_NA2CO3,
        )
        return mix_wbl_streams(pine, semichem)

    def test_na_conservation(self, wbl):
        """Na must be exactly conserved through evaporation."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.na_element_lb_hr == pytest.approx(wbl.na_element_lb_hr, rel=1e-10)

    def test_s_conservation(self, wbl):
        """S must be exactly conserved through evaporation."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.s_element_lb_hr == pytest.approx(wbl.s_element_lb_hr, rel=1e-10)

    def test_solids_conservation(self, wbl):
        """Total solids must be exactly conserved through evaporation."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.total_solids_lb_hr == pytest.approx(wbl.total_solids_lb_hr, rel=1e-10)

    def test_na_pct_invariant(self, wbl):
        """Na% d.s. must be unchanged through evaporation."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.sbl_na_pct_ds == pytest.approx(wbl.na_pct_ds, rel=1e-10)

    def test_s_pct_invariant(self, wbl):
        """S% d.s. must be unchanged through evaporation."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.sbl_s_pct_ds == pytest.approx(wbl.s_pct_ds, rel=1e-10)

    def test_target_tds_achieved(self, wbl):
        """SBL TDS% should match target."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.sbl_tds_pct == pytest.approx(69.1, rel=1e-6)

    def test_water_removed_positive(self, wbl):
        """Water removed should be positive (concentrating)."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.water_removed_lb_hr > 0

    def test_sbl_flow_less_than_wbl(self, wbl):
        """SBL flow should be less than WBL flow (water removed)."""
        sbl = calculate_evaporator(wbl, target_tds_pct=69.1)
        assert sbl.sbl_flow_lb_hr < wbl.total_flow_lb_hr

    def test_different_tds_targets(self, wbl):
        """Higher target TDS → more water removed, less SBL flow."""
        sbl_65 = calculate_evaporator(wbl, target_tds_pct=65.0)
        sbl_75 = calculate_evaporator(wbl, target_tds_pct=75.0)
        assert sbl_75.water_removed_lb_hr > sbl_65.water_removed_lb_hr
        assert sbl_75.sbl_flow_lb_hr < sbl_65.sbl_flow_lb_hr


class TestCompoundMassAccounting:
    """Test that compound masses correctly account for oxygen weight."""

    def test_na2s_compound_heavier_than_elements(self):
        """Na2S (78.05) weighs more than 2×Na + S (78.03). Nearly equal for Na2S."""
        assert MW['Na2S'] > 2 * MW['Na'] + MW['S'] - 0.1  # Within rounding
        # But with oxygen compounds it's very different:
        assert MW['Na2SO4'] > 2 * MW['Na'] + MW['S']  # 142.04 >> 78.03

    def test_inorganic_solids_include_oxygen(self):
        """Inorganic solids from NaOH include O and H weight."""
        bl = calculate_fiberline_bl(
            production_bdt_day=1000, yield_pct=0.57, wl_flow_gpm=400,
            wl_na2s_g_L=0.0, wl_naoh_g_L=100.0, wl_na2co3_g_L=0.0,
            s_loss_digester_pct=0.0,
        )
        # NaOH has MW=40, Na has MW=22.98 — so compound is 40/22.98 = 1.74× element
        # Inorganic solids should be > Na element mass
        assert bl.inorganic_solids_lb_hr > bl.na_element_lb_hr * 1.5

    def test_na2co3_compound_much_heavier(self):
        """Na2CO3 (106) is much heavier than just 2×Na (45.96)."""
        bl = calculate_fiberline_bl(
            production_bdt_day=1000, yield_pct=0.57, wl_flow_gpm=400,
            wl_na2s_g_L=0.0, wl_naoh_g_L=0.0, wl_na2co3_g_L=100.0,
            s_loss_digester_pct=0.0,
        )
        # Na2CO3: MW=106, 2×Na=45.96 → compound/Na = 2.31×
        assert bl.inorganic_solids_lb_hr > bl.na_element_lb_hr * 2.0


class TestWBLMixerList:
    """Test mix_wbl_streams with list of BL outputs (V2 API)."""

    @pytest.fixture
    def bl_outputs(self):
        pine = calculate_fiberline_bl(
            production_bdt_day=1250.69, yield_pct=0.5694,
            wl_flow_gpm=245.0, wl_na2s_g_L=34.0,
            wl_naoh_g_L=51.0, wl_na2co3_g_L=16.0,
        )
        semichem = calculate_fiberline_bl(
            production_bdt_day=636.854, yield_pct=0.7019,
            wl_flow_gpm=98.0, wl_na2s_g_L=34.0,
            wl_naoh_g_L=51.0, wl_na2co3_g_L=16.0,
        )
        return [pine, semichem]

    def test_list_na_conservation(self, bl_outputs):
        mixed = mix_wbl_streams(bl_outputs=bl_outputs)
        expected_na = sum(bl.na_element_lb_hr for bl in bl_outputs)
        assert abs(mixed.na_element_lb_hr - expected_na) < 0.01

    def test_list_s_conservation(self, bl_outputs):
        mixed = mix_wbl_streams(bl_outputs=bl_outputs)
        expected_s = sum(bl.s_element_lb_hr for bl in bl_outputs)
        assert abs(mixed.s_element_lb_hr - expected_s) < 0.01

    def test_list_single_fiberline(self):
        single = calculate_fiberline_bl(
            production_bdt_day=1000.0, yield_pct=0.55,
            wl_flow_gpm=200.0, wl_na2s_g_L=34.0,
            wl_naoh_g_L=51.0, wl_na2co3_g_L=16.0,
        )
        mixed = mix_wbl_streams(bl_outputs=[single])
        assert abs(mixed.na_element_lb_hr - single.na_element_lb_hr) < 0.01

    def test_list_three_fiberlines(self):
        lines = [
            calculate_fiberline_bl(
                production_bdt_day=p, yield_pct=y,
                wl_flow_gpm=100.0, wl_na2s_g_L=34.0,
                wl_naoh_g_L=51.0, wl_na2co3_g_L=16.0,
            )
            for p, y in [(800, 0.55), (600, 0.60), (400, 0.70)]
        ]
        mixed = mix_wbl_streams(bl_outputs=lines)
        expected_na = sum(bl.na_element_lb_hr for bl in lines)
        assert abs(mixed.na_element_lb_hr - expected_na) < 0.01

    def test_list_matches_named_params(self, bl_outputs):
        """V2 list API must produce same results as V1 named-param API."""
        mixed_list = mix_wbl_streams(bl_outputs=bl_outputs)
        mixed_named = mix_wbl_streams(pine_bl=bl_outputs[0], semichem_bl=bl_outputs[1])
        assert abs(mixed_list.na_element_lb_hr - mixed_named.na_element_lb_hr) < 0.01
        assert abs(mixed_list.s_element_lb_hr - mixed_named.s_element_lb_hr) < 0.01
        assert abs(mixed_list.tds_pct - mixed_named.tds_pct) < 0.001
