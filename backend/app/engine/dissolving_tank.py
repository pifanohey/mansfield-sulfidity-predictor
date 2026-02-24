"""
Dissolving tank mass balance — faithful reproduction of Excel I43-I75.

Reference: 2_Recovery boiler sheet, cells I43-I75
Smelt flow is CALCULATED (not an input).
WW flow can be:
  - Fixed INPUT (625 gpm default) - original Excel behavior
  - CALCULATED to hit GL TTA setpoint - new control loop mode
GL flow to slaker participates in the circular reference.

Energy balance: Hot smelt (~1338°F) releases sensible heat into the DT,
warming the weak wash and shower water to DT operating temperature (~212°F).
Excess heat evaporates water as steam, reducing liquid flow to the GL clarifier.
"""

from dataclasses import dataclass

# lb/hr per gpm of water: 8.34 lb/gal × 60 min/hr
LB_PER_GPM_HR = 8.34 * 60  # 500.4


@dataclass
class DTEnergyBalance:
    """Energy balance around the dissolving tank."""
    heat_from_smelt_btu_hr: float      # Sensible heat from smelt cooling
    heat_to_warm_ww_btu_hr: float      # Heat absorbed by WW warming
    heat_to_warm_shower_btu_hr: float  # Heat absorbed by shower warming
    net_heat_btu_hr: float             # Available for steam generation
    steam_evaporated_lb_hr: float      # Water evaporated
    steam_evaporated_gpm: float        # Steam as gpm liquid equivalent


@dataclass
class DissolvingTankResult:
    """Dissolving tank output — all values matching Excel cells."""
    # Smelt
    expansion_factor: float       # B77
    smelt_total_mass_ton_hr: float  # I44
    smelt_tta_mass_ton_hr: float    # I45
    smelt_flow_gpm: float           # I55 — CALCULATED
    # WW
    ww_tta_mass_ton_hr: float       # I46
    ww_s_mass_ton_hr: float         # I62
    # Dissolving
    total_dissolving_flow_gpm: float  # I57
    dissolving_tta_mass_ton_hr: float  # I59
    dissolving_s_mass_ton_hr: float    # I61
    dissolving_sulfidity: float        # I60
    # GL to slaker (circular)
    gl_flow_to_slaker_gpm: float     # I58
    gl_tta_mass_ton_hr: float        # I63
    gl_s_mass_ton_hr: float          # I64
    gl_sulfidity: float              # I65
    gl_tta_lb_ft3: float             # I66
    gl_tta_g_L: float                # I67
    gl_na2s_g_L: float               # I68
    gl_aa_g_L: float                 # I69
    # Energy balance
    steam_evaporated_lb_hr: float = 0.0
    steam_evaporated_gpm: float = 0.0
    heat_from_smelt_btu_hr: float = 0.0
    heat_to_warm_liquor_btu_hr: float = 0.0
    net_heat_for_steam_btu_hr: float = 0.0


def calculate_dt_energy_balance(
    smelt_mass_lb_hr: float,
    ww_flow_gpm: float,
    shower_flow_gpm: float,
    smelt_temp_f: float = 1338.0,
    ww_temp_f: float = 180.0,
    shower_temp_f: float = 140.0,
    dt_temp_f: float = 212.0,
    smelt_cp: float = 0.29,
    latent_heat: float = 970.0,
) -> DTEnergyBalance:
    """
    Energy balance around the dissolving tank.

    Hot smelt releases sensible heat as it cools from smelt_temp to dt_temp.
    This heat warms the weak wash and shower water to DT operating temperature.
    Excess heat evaporates water as steam.

    Cp_smelt typical range: 0.25-0.35 BTU/lb/°F for molten smelt.
    Latent heat at 212°F: 970 BTU/lb.

    Note: Heat of dissolution (Na₂S, Na₂CO₃ dissolving) is small compared
    to sensible heat and is neglected here.
    """
    # Heat from smelt cooling to DT temperature
    heat_smelt = smelt_mass_lb_hr * smelt_cp * (smelt_temp_f - dt_temp_f)

    # Heat absorbed by WW warming to DT temperature
    heat_ww = ww_flow_gpm * LB_PER_GPM_HR * 1.0 * max(0, dt_temp_f - ww_temp_f)

    # Heat absorbed by shower water warming to DT temperature
    heat_shower = shower_flow_gpm * LB_PER_GPM_HR * 1.0 * max(0, dt_temp_f - shower_temp_f)

    # Net heat available for steam generation
    net_heat = heat_smelt - heat_ww - heat_shower

    # Steam evaporated
    steam_lb_hr = max(0.0, net_heat / latent_heat)
    steam_gpm = steam_lb_hr / LB_PER_GPM_HR

    return DTEnergyBalance(
        heat_from_smelt_btu_hr=heat_smelt,
        heat_to_warm_ww_btu_hr=heat_ww,
        heat_to_warm_shower_btu_hr=heat_shower,
        net_heat_btu_hr=net_heat,
        steam_evaporated_lb_hr=steam_lb_hr,
        steam_evaporated_gpm=steam_gpm,
    )


def calculate_dissolving_tank(
    # From RB
    smelt_tta_lbs_hr: float,        # B34
    smelt_active_sulfide: float,    # B32
    smelt_dead_load: float,         # B33
    smelt_sulfidity_pct: float,     # B35*100
    # User inputs
    ww_flow_gpm: float,             # I53 = 625 (INPUT)
    ww_tta_lb_ft3: float,           # I50 = 1.07978
    ww_sulfidity: float,            # I48 = 0.2550
    shower_flow_gpm: float,         # I54 = 60
    smelt_density_lb_ft3: float,    # I56 = 100
    gl_target_tta_lb_ft3: float,    # I49 = 7.325
    gl_causticity: float,           # I75 = 0.1016
    # From iteration (underflows + semichem GL)
    underflow_dregs_gpm: float,     # 3_Chem!B69
    semichem_gl_gpm: float,         # 3_Chem!G5
    # Dregs filter filtrate return (to WW tank → DT)
    filtrate_return_gpm: float = 0.0,
    filtrate_tta_g_L: float = 0.0,
    filtrate_sulfidity: float = 0.0,
    # Energy balance parameters
    smelt_temp_f: float = 1338.0,
    ww_temp_f: float = 180.0,
    shower_temp_f: float = 140.0,
    dt_temp_f: float = 212.0,
    smelt_cp: float = 0.29,
    latent_heat: float = 970.0,
) -> DissolvingTankResult:
    """
    Dissolving tank mass balance based on Excel 2_RB I43-I75.

    Key features:
    - Smelt flow is CALCULATED from smelt mass (not an input)
    - WW flow can be fixed or solved by calculate_ww_flow_for_tta_target
    - GL flow to slaker is part of the circular reference
    - Uses lb/ft3 units (not g/L) matching Excel
    - Expansion factor B77 applied to smelt mass
    - Optional dregs filter filtrate return adds flow and TTA to DT
    - Energy balance computes steam evaporated from hot smelt
    """
    # B77: Expansion factor = 1.7097 - 0.0045 * smelt_sulfidity%
    b77 = 1.7097 - 0.0045 * smelt_sulfidity_pct

    # I45: Smelt TTA mass (ton/hr) = B34 / 2000
    i45 = smelt_tta_lbs_hr / 2000.0

    # I44: Total smelt mass (ton/hr) = I45 * B77 + B33/2000
    i44 = i45 * b77 + smelt_dead_load / 2000.0

    # I55: Smelt flow (gpm) = ((I44 * 33.3333) / smelt_density) * 7.48
    # 33.3333 = 2000 lb/ton / 60 min/hr = converts ton/hr to lb/min
    # / density = ft3/min
    # * 7.48 = gal/ft3 = gpm
    i55 = ((i44 * 33.3333) / smelt_density_lb_ft3) * 7.48

    # I46: WW TTA mass (ton/hr) = ww_flow * ww_tta_lb_ft3 * 16.01 * 0.00025
    # 16.01 converts lb/ft3 to g/L (approximately)
    # 0.00025 is the Excel conversion factor gpm*g/L -> ton/hr
    i46 = ww_flow_gpm * ww_tta_lb_ft3 * 16.01 * 0.00025

    # Dregs filter filtrate TTA mass (returns to WW tank → enters DT)
    filtrate_tta_ton_hr = filtrate_return_gpm * filtrate_tta_g_L * 0.00025 if filtrate_return_gpm > 0 else 0.0
    filtrate_s_ton_hr = filtrate_tta_ton_hr * filtrate_sulfidity

    # ── Energy Balance: steam evaporated by hot smelt ──
    energy = calculate_dt_energy_balance(
        smelt_mass_lb_hr=i44 * 2000,
        ww_flow_gpm=ww_flow_gpm,
        shower_flow_gpm=shower_flow_gpm,
        smelt_temp_f=smelt_temp_f,
        ww_temp_f=ww_temp_f,
        shower_temp_f=shower_temp_f,
        dt_temp_f=dt_temp_f,
        smelt_cp=smelt_cp,
        latent_heat=latent_heat,
    )

    # I57: Total dissolving flow (gpm) = smelt + shower + WW + filtrate - steam
    # Steam removes water as vapor, reducing liquid flow
    i57 = i55 + shower_flow_gpm + ww_flow_gpm + filtrate_return_gpm - energy.steam_evaporated_gpm

    # I58: GL flow to slaker (gpm) = total - dregs underflow - semichem
    # Grits are removed at the slaker, not here at the GL clarifier
    # This is the CIRCULAR variable
    i58 = i57 - underflow_dregs_gpm - semichem_gl_gpm

    # I59: Dissolving TTA mass (ton/hr) = smelt_TTA + WW_TTA + filtrate_TTA
    # TTA mass is CONSERVED — steam removes water only, not dissolved solids
    i59 = i45 + i46 + filtrate_tta_ton_hr

    # I62: WW S mass (ton/hr) = I46 * ww_sulfidity
    i62 = i46 * ww_sulfidity

    # I61: Dissolving S mass (ton/hr) = smelt_active_sulfide/2000 + WW_S + filtrate_S
    i61 = smelt_active_sulfide / 2000.0 + i62 + filtrate_s_ton_hr

    # I60: Dissolving sulfidity = S_mass / TTA_mass
    i60 = i61 / i59 if i59 > 0 else 0.0

    # I66: GL TTA (lb/ft3) — mass-balance concentration (not circular target echo)
    # GL is well-mixed: concentration = TTA_mass_in / GL_total_volume
    gl_factor_per_gpm = 0.1336806 * 60 / 2000  # converts gpm to volume units matching TTA ton/hr
    if i57 > 0:
        i66 = i59 / (gl_factor_per_gpm * i57)  # actual TTA lb/ft3
    else:
        i66 = 0.0

    # I67: GL TTA (g/L) = I66 * 16.01
    i67 = i66 * 16.01

    # I63: GL TTA to slaker mass (ton/hr) — at actual concentration, not target
    i63 = i58 * i66 * 16.01 * 0.00025

    # I64: GL S to slaker mass (ton/hr) = I63 * I60
    i64 = i63 * i60

    # I65: GL sulfidity = dissolving sulfidity
    i65 = i60

    # I68: GL Na2S (g/L) = GL TTA * GL sulfidity
    i68 = i67 * i65

    # I69: GL AA (g/L) = GL TTA * GL causticity + GL Na2S
    i69 = i67 * gl_causticity + i68

    return DissolvingTankResult(
        expansion_factor=b77,
        smelt_total_mass_ton_hr=i44,
        smelt_tta_mass_ton_hr=i45,
        smelt_flow_gpm=i55,
        ww_tta_mass_ton_hr=i46,
        ww_s_mass_ton_hr=i62,
        total_dissolving_flow_gpm=i57,
        dissolving_tta_mass_ton_hr=i59,
        dissolving_s_mass_ton_hr=i61,
        dissolving_sulfidity=i60,
        gl_flow_to_slaker_gpm=i58,
        gl_tta_mass_ton_hr=i63,
        gl_s_mass_ton_hr=i64,
        gl_sulfidity=i65,
        gl_tta_lb_ft3=i66,
        gl_tta_g_L=i67,
        gl_na2s_g_L=i68,
        gl_aa_g_L=i69,
        # Energy balance
        steam_evaporated_lb_hr=energy.steam_evaporated_lb_hr,
        steam_evaporated_gpm=energy.steam_evaporated_gpm,
        heat_from_smelt_btu_hr=energy.heat_from_smelt_btu_hr,
        heat_to_warm_liquor_btu_hr=energy.heat_to_warm_ww_btu_hr + energy.heat_to_warm_shower_btu_hr,
        net_heat_for_steam_btu_hr=energy.net_heat_btu_hr,
    )


def calculate_ww_flow_for_tta_target(
    # From RB
    smelt_tta_lbs_hr: float,        # B34
    smelt_active_sulfide: float,    # B32
    smelt_dead_load: float,         # B33
    smelt_sulfidity_pct: float,     # B35*100
    # User inputs
    ww_tta_lb_ft3: float,           # I50 = 1.07978
    ww_sulfidity: float,            # I48 = 0.2550
    shower_flow_gpm: float,         # I54 = 60
    smelt_density_lb_ft3: float,    # I56 = 100
    gl_target_tta_lb_ft3: float,    # I49 = 7.325 (SETPOINT)
    gl_causticity: float,           # I75 = 0.1016
    # From iteration (underflows + semichem GL)
    underflow_dregs_gpm: float,     # 3_Chem!B69
    semichem_gl_gpm: float,         # 3_Chem!G5
    # Optional: dregs filtrate return
    dregs_filtrate_gpm: float = 0.0,  # Filtrate flow returning to DT (gpm)
    filtrate_tta_g_L: float = 0.0,    # Filtrate TTA concentration (g/L)
    # Energy balance parameters
    smelt_temp_f: float = 1338.0,
    ww_temp_f: float = 180.0,
    shower_temp_f: float = 140.0,
    dt_temp_f: float = 212.0,
    smelt_cp: float = 0.29,
    latent_heat: float = 970.0,
) -> tuple[float, DissolvingTankResult]:
    """
    Calculate the weak wash flow required to hit the GL TTA setpoint.

    This implements a control loop where WW flow is the manipulated variable
    and GL TTA is the controlled variable (setpoint = gl_target_tta_lb_ft3).

    Includes energy balance: steam evaporation from hot smelt reduces GL flow.
    The analytical solution accounts for the WW-steam coupling (more WW absorbs
    more heat, reducing steam, which increases GL flow).

    Returns:
        tuple of (ww_flow_gpm, DissolvingTankResult)

    The math (with energy balance):
        GL_flow = Smelt_flow + WW_flow + Shower - Subtractions - Steam(WW)
        Steam(WW) = steam_base - WW × steam_per_ww  (more WW absorbs more heat)
        GL_flow = (base_flow - steam_base) + WW × (1 + steam_per_ww)
        TTA_mass_in = GL_TTA_target × GL_flow  (mass balance)

    Solving for WW_flow is still linear (analytical solution).
    """
    # B77: Expansion factor = 1.7097 - 0.0045 * smelt_sulfidity%
    b77 = 1.7097 - 0.0045 * smelt_sulfidity_pct

    # I45: Smelt TTA mass (ton/hr) = B34 / 2000
    smelt_tta_ton_hr = smelt_tta_lbs_hr / 2000.0

    # I44: Total smelt mass (ton/hr) = I45 * B77 + B33/2000
    smelt_total_mass = smelt_tta_ton_hr * b77 + smelt_dead_load / 2000.0

    # I55: Smelt flow (gpm)
    smelt_flow_gpm = ((smelt_total_mass * 33.3333) / smelt_density_lb_ft3) * 7.48

    # WW TTA contribution: ww_tta_mass = ww_flow * ww_tta_lb_ft3 * 16.01 * 0.00025
    ww_tta_factor = ww_tta_lb_ft3 * 16.01 * 0.00025  # ton/hr per gpm of WW

    # GL TTA factor
    gl_tta_factor = gl_target_tta_lb_ft3 * 0.1336806 * 60 / 2000  # ton/hr per gpm of GL

    # Total subtractions from GL flow (dregs only — grits removed at slaker)
    total_subtractions = underflow_dregs_gpm + semichem_gl_gpm

    # Filtrate TTA contribution (ton/hr)
    filtrate_tta_ton_hr = dregs_filtrate_gpm * filtrate_tta_g_L * 0.00025 if dregs_filtrate_gpm > 0 else 0.0
    filtrate_sulf = ww_sulfidity  # Approximate: filtrate sulfidity ≈ WW sulfidity

    # ── Energy balance: steam evaporation reduces GL flow ──
    # Steam depends on WW flow (more WW absorbs more heat → less steam).
    # Analytical solution accounts for this coupling.

    smelt_mass_lb = smelt_total_mass * 2000

    # Heat from smelt cooling (constant for given RB outputs)
    heat_smelt = smelt_mass_lb * smelt_cp * (smelt_temp_f - dt_temp_f)

    # Heat absorbed by shower (constant)
    heat_shower = shower_flow_gpm * LB_PER_GPM_HR * max(0, dt_temp_f - shower_temp_f)

    # Steam base: steam if WW = 0 (maximum steam)
    net_heat_base = heat_smelt - heat_shower
    steam_base_lb = max(0, net_heat_base / latent_heat)
    steam_base_gpm = steam_base_lb / LB_PER_GPM_HR

    # Steam reduction per gpm of WW: each gpm of WW absorbs heat → less steam
    # heat_per_ww_gpm = LB_PER_GPM_HR × Cp_water × ΔT_ww
    # steam_per_ww (gpm) = heat_per_ww_gpm / (latent_heat × LB_PER_GPM_HR)
    #                     = ΔT_ww / latent_heat
    dt_ww = max(0, dt_temp_f - ww_temp_f)
    steam_per_ww = dt_ww / latent_heat  # gpm steam reduction per gpm WW

    # ── Adjusted flow balance with energy ──
    # GL_flow = (smelt + shower + filtrate - subtractions - steam_base) + WW × (1 + steam_per_ww)
    # Each gpm of WW contributes (1 + steam_per_ww) gpm to GL flow because
    # WW absorbs heat that would have evaporated (steam_per_ww) gpm of water.
    # DT is well-mixed: all outflows (slaker + dregs + grits + semichem) leave at the SAME
    # concentration. Subtractions happen downstream of the DT and don't affect mixing balance.
    adjusted_base = smelt_flow_gpm + shower_flow_gpm + dregs_filtrate_gpm - steam_base_gpm
    ww_gl_factor = 1 + steam_per_ww  # effective GL flow contribution per gpm WW

    # Mass balance with energy-adjusted flows:
    # smelt_tta + WW × ww_factor + filtrate_tta = gl_factor × (adjusted_base + WW × ww_gl_factor)
    # WW × (ww_factor - gl_factor × ww_gl_factor) = gl_factor × adjusted_base - smelt_tta - filtrate_tta

    numerator = gl_tta_factor * adjusted_base - smelt_tta_ton_hr - filtrate_tta_ton_hr
    denominator = ww_tta_factor - gl_tta_factor * ww_gl_factor

    if abs(denominator) < 1e-10:
        ww_flow_gpm = 625.0  # Fall back to default
    else:
        ww_flow_gpm = numerator / denominator

    # Ensure WW flow is reasonable (non-negative, not absurdly high)
    ww_flow_gpm = max(0.0, min(ww_flow_gpm, 2000.0))

    # Now calculate the full dissolving tank result with this WW flow
    # Pass filtrate and energy params through
    result = calculate_dissolving_tank(
        smelt_tta_lbs_hr=smelt_tta_lbs_hr,
        smelt_active_sulfide=smelt_active_sulfide,
        smelt_dead_load=smelt_dead_load,
        smelt_sulfidity_pct=smelt_sulfidity_pct,
        ww_flow_gpm=ww_flow_gpm,
        ww_tta_lb_ft3=ww_tta_lb_ft3,
        ww_sulfidity=ww_sulfidity,
        shower_flow_gpm=shower_flow_gpm,
        smelt_density_lb_ft3=smelt_density_lb_ft3,
        gl_target_tta_lb_ft3=gl_target_tta_lb_ft3,
        gl_causticity=gl_causticity,
        underflow_dregs_gpm=underflow_dregs_gpm,
        semichem_gl_gpm=semichem_gl_gpm,
        filtrate_return_gpm=dregs_filtrate_gpm,
        filtrate_tta_g_L=filtrate_tta_g_L,
        filtrate_sulfidity=filtrate_sulf,
        smelt_temp_f=smelt_temp_f,
        ww_temp_f=ww_temp_f,
        shower_temp_f=shower_temp_f,
        dt_temp_f=dt_temp_f,
        smelt_cp=smelt_cp,
        latent_heat=latent_heat,
    )

    return ww_flow_gpm, result
