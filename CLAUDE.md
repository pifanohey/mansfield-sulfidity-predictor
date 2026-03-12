# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Sulfidity Predictor V2 — Multi-Mill Architecture

## What This Is
A web-based chemical engineering tool for Kraft pulp mills that predicts white liquor sulfidity and calculates makeup chemical requirements. V2 extends V1 with **configurable N-fiberline support**, **multiple recovery boilers/dissolving tanks**, and **multiple makeup chemical types**, enabling deployment to any mill via JSON config files.

**V2 vs V1:** V1 hardcoded Pine Hill's 2-fiberline, single-RB setup. V2 loops over configurable lists of fiberlines, recovery boilers, and dissolving tanks loaded from JSON. The core solver math is identical — V2 only changes the parameterization layer.

---

## How to Run
```bash
./start.sh                    # Backend :8005, Frontend :3005

# Or manually:
cd backend && python3 -m uvicorn app.main:app --reload --port 8005
cd frontend && npm run dev    # port 3005
```

**Use `python3`** (not `python`) — macOS system Python.

## Running Tests
```bash
cd backend && python3 -m pytest tests/ -v                        # All tests (249)
cd backend && python3 -m pytest tests/test_golden_regression.py -v  # Single file
cd backend && python3 -m pytest tests/test_golden_regression.py::TestGoldenRegression::test_final_sulfidity -v  # Single test
```

## Lint & Build
```bash
cd frontend && npm run lint      # ESLint (Next.js config)
cd frontend && npm run build     # Next.js production build (also type-checks)
```

---

## Project Structure
```
/sulfidity_predictor_v2/
├── mill_configs/                   # ★ V2: JSON config per mill
│   ├── pine_hill.json              #   2 fiberlines, 1 RB/DT, NaSH makeup
│   ├── mansfield.json              #   3 fiberlines, 2 RBs/DTs, NaSH makeup
│   ├── three_line_chemical.json    #   3 fiberlines, saltcake makeup
│   └── two_batch.json              #   2 batch lines, NaOH makeup
├── backend/
│   ├── app/
│   │   ├── engine/                 # 19 calculation modules
│   │   │   ├── orchestrator.py     #   Master solver, triple-loop + multi-RB loop
│   │   │   ├── mill_profile.py     #   ★ V2: FiberlineConfig/RB/DT/MillConfig loader
│   │   │   ├── makeup_chemicals.py #   ★ V2: 4 chemical type configs
│   │   │   ├── chemical_charge.py  #   Fiberline WL demand (loops over configs)
│   │   │   ├── fiberline.py        #   BL composition (list-based mixer)
│   │   │   ├── recovery_boiler.py  #   RB chemistry, alkali formation
│   │   │   ├── dissolving_tank.py  #   Smelt dissolution, WW flow solve
│   │   │   ├── slaker_model.py     #   Energy/water/mass balance
│   │   │   ├── makeup.py           #   NaSH/NaOH sizing (Secant method)
│   │   │   ├── s_retention.py      #   Unified loss table (15 sources), S retention
│   │   │   ├── evaporator.py       #   WBL → SBL concentration
│   │   │   ├── constants.py        #   MW, CONV, DEFAULTS (includes fiberlines, RB/DT)
│   │   │   ├── density.py          #   BL/GL/WL density correlations
│   │   │   ├── mill_config.py      #   Tank geometry (13 tanks)
│   │   │   ├── inventory.py        #   Tank volumes from lab
│   │   │   ├── predictor.py        #   FOPDT sulfidity forecasting
│   │   │   ├── guidance.py         #   Rule-based recommendations
│   │   │   └── sensitivity.py      #   Auto-perturbation analysis
│   │   ├── api/
│   │   │   ├── schemas.py          #   Pydantic models (FiberlineInput, RB/DT, etc.)
│   │   │   └── routes/calculate.py #   REST endpoints + GET /api/mill-config
│   │   ├── reports/                #   PDF & Excel export
│   │   └── main.py                 #   FastAPI entry point
│   └── tests/                      #   249 tests (12 test files)
├── frontend/                       #   Next.js 15 + React 18 + TypeScript
│   └── src/
│       ├── app/                    #   Pages: dashboard, inputs, results, scenarios
│       ├── components/             #   44 components (inputs, results, scenarios, ui)
│       ├── hooks/                  #   useAppState, useMillConfig, etc.
│       └── lib/                    #   types.ts, defaults.ts, api.ts
└── docs/                           #   Documentation
```

---

# V2 ARCHITECTURE: MULTI-MILL CONFIG

## Mill Configuration System

Each mill is defined by a JSON file in `mill_configs/`. The active config is selected by the `MILL_CONFIG` env var (default: `"pine_hill"`).

### Config Structure
```json
{
  "mill_name": "Pine Hill",
  "makeup_chemical": "nash",
  "fiberlines": [
    {
      "id": "pine", "name": "Pine", "type": "continuous",
      "cooking_type": "chemical", "uses_gl_charge": false,
      "defaults": { "production_bdt_day": 1250.69, "yield_pct": 0.5694, "ea_pct": 0.122 }
    }
  ],
  "recovery_boilers": [
    {
      "id": "rb1", "name": "Recovery Boiler", "paired_dt_id": "dt1",
      "defaults": {
        "bl_flow_gpm": 340.53, "bl_tds_pct": 69.1, "bl_temp_f": 253.5,
        "reduction_eff_pct": 95.0, "ash_recycled_pct": 0.07, "saltcake_flow_lb_hr": 2227.0
      }
    }
  ],
  "dissolving_tanks": [
    {
      "id": "dt1", "name": "Dissolving Tank", "paired_rb_id": "rb1",
      "defaults": {
        "ww_flow_gpm": 625.0, "ww_tta_lb_ft3": 1.07978, "ww_sulfidity": 0.2550,
        "shower_flow_gpm": 60.0, "smelt_density_lb_ft3": 110.0
      }
    }
  ],
  "tanks": [...],
  "defaults": {...}
}
```

### Key Dataclasses (`mill_profile.py`)
- **`FiberlineConfig`**: `id, name, type, cooking_type, uses_gl_charge, defaults`
- **`RecoveryBoilerConfig`**: `id, name, paired_dt_id, defaults`
- **`DissolvingTankConfig`**: `id, name, paired_rb_id, defaults`
- **`MillConfig`**: `mill_name, makeup_chemical, fiberlines, recovery_boilers, dissolving_tanks, tanks, defaults`
- `load_mill_config(mill_id)` — loads from `mill_configs/{mill_id}.json`
- `get_mill_config()` — reads `MILL_CONFIG` env var

### Fiberline Types
| Type | Cooking | GL Charge | Example |
|------|---------|-----------|---------|
| continuous | chemical | No | Pine kraft line |
| batch | chemical | No | Batch kraft line |
| batch | semichem | Yes | Semichem NSSC line |
| continuous | semichem | Yes | Semichem continuous |

### Makeup Chemical Types (`makeup_chemicals.py`)
| ID | Formula | adds_na | adds_s |
|----|---------|---------|--------|
| `nash` | NaSH | Yes | Yes |
| `saltcake` | Na₂SO₄ | Yes | Yes |
| `emulsified_sulfur` | S | No | Yes |
| `naoh` | NaOH | Yes | No |

---

## Multi-Recovery Boiler / Dissolving Tank Architecture

### How Multi-RB Works
The orchestrator loops over N recovery boilers, each with independent parameters:
```
for rb in rb_configs:
  rb_bl_flow = rb.defaults['bl_flow_gpm']
  rb_re = rb.defaults['reduction_eff_pct']
  flow_fraction = rb_bl_flow / total_bl_flow
  rb_prod = total_prod * flow_fraction
  rb_smelt = calculate_recovery_boiler(rb_prod, rb_bl_flow, rb_re, ...)
  per_rb_results.append(rb_smelt)

combined_rb, combined_smelt = _combine_smelts(per_rb_smelt_list, per_rb_inputs_list)
```

### Key Helpers (`orchestrator.py`)
- **`_combine_smelts(smelt_list, rb_inputs_list)`**: Sums extensive fields (tta, active_sulfide, dry_solids), recomputes intensive (smelt_sulfidity_pct = total_active/total_tta, bl_s_pct_fired weighted by dry_solids). Single-item → identity pass-through.
- **`_combine_dt_inputs(dt_configs, overrides, global_defaults)`**: Sums flows (ww_flow, shower_flow), flow-weighted avg for concentrations (ww_tta, ww_sulfidity, smelt_density). Empty/single → returns global defaults.

### Production Splitting
Each RB gets a proportional share of total production based on BL flow fraction:
```python
flow_fraction = rb_bl_flow / total_bl_flow
rb_prod = total_prod * flow_fraction
```

### Per-RB Results
When multiple RBs are configured, per-RB breakdown is included in results:
```python
results['recovery_boiler_ids'] = ['rb1', 'rb2']
results['rb1_smelt_sulfidity_pct'] = 35.2
results['rb2_smelt_sulfidity_pct'] = 33.8
results['rb1_production_bdt_day'] = 1308.0
results['rb2_production_bdt_day'] = 1307.0
```

### Override Precedence
1. User flat inputs (e.g., `reduction_eff_pct` at request level) → override ALL per-RB config defaults
2. Per-RB config defaults from JSON → used when no flat override
3. `constants.py` DEFAULTS → final fallback

---

## Engine Flow (How Fiberlines Are Processed)

### Orchestrator Loop
```
run_calculations(inputs):
  fiberline_configs = inputs['fiberlines']   # List[FiberlineConfig]
  rb_configs = inputs['recovery_boilers']    # List[RecoveryBoilerConfig]
  dt_configs = inputs['dissolving_tanks']    # List[DissolvingTankConfig]
  total_prod = sum(fl.production_bdt_day for fl in fiberline_configs)

  OUTER LOOP (BL convergence):
    SECANT LOOP (NaSH targeting):
      INNER LOOP (GL flow convergence):
        combine_dt_inputs → dissolving_tank → slaker → WLC Stage 1
        → chemical_charge(fiberlines=fiberline_configs, ...)
        → Na loss factor → WLC Stage 2
        → GL convergence check

      MULTI-RB LOOP:
        for rb in rb_configs:
          calculate_recovery_boiler(rb_prod, rb_params, ...)
        combine_smelts → s_retention

    FORWARD LEG:
      for fl in fiberline_configs:
        bl_outputs[fl.id] = calculate_fiberline_bl(fl.production, fl.yield, ...)

      mixed_wbl = mix_wbl_streams(list(bl_outputs.values()), cto_...)
      evaporator → SBL → BL convergence check
```

### Key Function Signatures (V2)

```python
# fiberline.py
def mix_wbl_streams(
    bl_outputs: List[FiberlineBLOutput],  # any number of fiberlines
    cto_na_lb_hr, cto_s_lb_hr, cto_water_lb_hr,
) -> MixedWBLOutput

# chemical_charge.py
def calculate_chemical_charge(
    fiberlines: List[FiberlineConfig],    # loops over all
    gl_flow_to_slaker_gpm, yield_factor,
    wl_tta_g_L, wl_na2s_g_L, wl_ea_g_L, wl_sulfidity,
    gl_tta_g_L, gl_na2s_g_L, gl_aa_g_L,
    dregs_underflow_gpm,
) -> ChemicalChargeResults

# ChemicalChargeResults
class ChemicalChargeResults:
    fiberline_results: Dict[str, FiberlineResult]  # keyed by fl.id
    gl_charge_gpm: Dict[str, float]                # keyed by fl.id
    total_wl_demand_gpm: float
```

### Dynamic Result Keys

The orchestrator produces per-fiberline and per-RB result keys:
```python
results['fiberline_ids'] = ['pine', 'semichem']
results['pine_wl_demand_gpm'] = 342.5
results['semichem_wl_demand_gpm'] = 93.2

results['recovery_boiler_ids'] = ['rb1', 'rb2']
results['rb1_smelt_sulfidity_pct'] = 35.2
results['rb2_smelt_sulfidity_pct'] = 33.8
```

---

# API ENDPOINTS

## V2-Specific Endpoints

### `GET /api/mill-config`
Returns the active mill configuration (fiberlines, recovery_boilers, dissolving_tanks, tanks, defaults, makeup_chemical).

### `POST /api/calculate`
**V2 request body** includes `fiberlines` array and optional multi-RB/DT:
```json
{
  "fiberlines": [
    {"id": "pine", "production_bdt_day": 1250.69, "yield_pct": 0.5694, "ea_pct": 0.122},
    {"id": "semichem", "production_bdt_day": 636.854, "yield_pct": 0.7019, "ea_pct": 0.0365, "gl_ea_pct": 0.017}
  ],
  "recovery_boilers": [
    {"id": "rb1", "bl_flow_gpm": 243.6},
    {"id": "rb2", "bl_flow_gpm": 243.6}
  ],
  "dissolving_tanks": [
    {"id": "dt1"},
    {"id": "dt2"}
  ],
  "cto_naoh_per_ton": 193.0,
  "cooking_wl_sulfidity": 0.283,
  "bl_na_pct": 19.39,
  ...
}
```

Backend schemas:
- `FiberlineInput(id, production_bdt_day, yield_pct, ea_pct, gl_ea_pct?)`
- `RecoveryBoilerConfigInput(id, bl_flow_gpm?, bl_tds_pct?, bl_temp_f?, reduction_eff_pct?, ash_recycled_pct?, saltcake_flow_lb_hr?)` — Optional fields override mill config defaults
- `DissolvingTankInput(id, ww_flow_gpm?, ww_tta_lb_ft3?, ww_sulfidity?, shower_flow_gpm?, smelt_density_lb_ft3?)` — Optional fields override mill config defaults

### Other Endpoints (unchanged from V1)
- `POST /api/calculate/what-if` — scenario comparison
- `POST /api/calculate/sensitivity` — perturbation analysis
- `POST /api/trends` — save trend point
- `GET /api/trends` — list trend points
- `GET/POST /api/snapshots` — save/load calculations
- `POST /api/export/excel`, `POST /api/export/pdf` — reports

---

# FRONTEND (V2 Changes)

## Config-Driven Inputs

The frontend loads mill config via `GET /api/mill-config` and dynamically renders fiberline, RB, and DT inputs.

### Key Hook: `useMillConfig`
```typescript
const { config, loading, error } = useMillConfig();
// config: MillConfig | null
// Fetches GET /api/mill-config on mount
```

### State Management (`useAppState`)
```typescript
// V2 state:
millConfig: MillConfig | null
fiberlineInputs: Record<string, FiberlineInputState>  // keyed by fiberline id
updateFiberlineField(fiberlineId, key, value)
setMillConfig(config)

// runCalculation builds fiberlines + multi-RB/DT arrays from config:
const fiberlines = millConfig.fiberlines.map(fl => ({
  id: fl.id,
  production_bdt_day: fiberlineInputs[fl.id]?.production_bdt_day ?? fl.defaults.production_bdt_day,
  ...
}));
// Multi-RB/DT: sends per-RB/DT config IDs when mill has >1
if (millConfig.recovery_boilers.length > 1) {
  inp.recovery_boilers = millConfig.recovery_boilers.map(rb => ({ id: rb.id }));
}
```

### TypeScript Types
```typescript
interface FiberlineConfig { id, name, type, cooking_type, uses_gl_charge, defaults }
interface RecoveryBoilerConfig { id, name, paired_dt_id, defaults }
interface DissolvingTankConfig { id, name, paired_rb_id, defaults }
interface MillConfig { mill_name, makeup_chemical, fiberlines[], recovery_boilers[], dissolving_tanks[], tanks[], defaults }
interface RecoveryBoilerConfigInput { id, bl_flow_gpm?, bl_tds_pct?, ... }  // API request per-RB overrides
interface DissolvingTankConfigInput { id, ww_flow_gpm?, ww_tta_lb_ft3?, ... }  // API request per-DT overrides
```

### Multi-RB/DT UI Behavior
- **Single RB/DT (Pine Hill)**: Standard flat input fields, no change from V1
- **Multi-RB/DT (Mansfield)**: Per-RB/DT bordered cards with independently editable fields (BL Flow, TDS, Temp, RE, Ash, Saltcake for RBs; WW Flow, TTA, Sulfidity, Shower, Smelt Density for DTs). State managed via `rbInputs` and `dtInputs` in `useAppState`.

### Dynamic Mill Name
- `TopNav.tsx` and `Sidebar.tsx` read `mill_name` from `useMillConfig()` — no hardcoded mill names
- Initials in top-right avatar derived from mill name

### Loss Table (15 sources)
Frontend `LossTable` type and `LossTableSection` include all 15 loss sources:
```
pulp_washable_soda, pulp_bound_soda, pulp_mill_spills, evap_spill,
rb_ash, rb_stack, dregs_filter, grits, weak_wash_overflow, ncg,
recaust_spill, rb_dump_tank, kiln_scrubber, truck_out_gl, unaccounted
```

---

# SOLVER ARCHITECTURE (Same as V1)

## Triple-Loop Solver

### Outer Loop: BL Composition Convergence
- Converges on BL Na%/S% from forward leg (2 iterations typical)
- Tolerance: 0.01% absolute
- **Skipped when `nash_dry_override` is set** (prevents runaway feedback)

### Middle Loop: Secant Method for Sulfidity Targeting
- Adjusts NaSH to hit `target_sulfidity_pct`
- Converges in 3-5 iterations

### Inner Loop: GL Flow Convergence
- Solves circular reference on GL_flow_to_slaker
- Tolerance: 0.001 gpm, 5-10 iterations

## NaOH Sizing (Dual-Constraint)
```
NaOH = max(NaOH_for_losses, NaOH_for_EA_demand)
```
- **Losses constraint**: Na mass balance (Saltcake_Na + NaSH_Na + NaOH_Na = Total_Na_losses)
- **EA demand constraint**: If CE < 81%, NaOH compensates EA deficit

## CTO NaOH Na Return
Mills that add NaOH in tall oil acidulation return Na to the system via brine:
```python
cto_naoh_per_ton  # lb NaOH/ton CTO (0 for Pine Hill, 193 for Mansfield)
cto_na_return = cto_tpd * cto_naoh_per_ton * NaOH_TO_Na / 24
```
This Na is added to the WBL mixer alongside CTO acid Na.

## Key Design Decisions (unchanged from V1)
- **NO NCG subtraction in fiberline** — WL Na₂S already reflects steady-state losses
- **Outer loop skip on NaSH override** — prevents runaway BL S% feedback
- **Na₂S is INERT through causticizing** — does not react with Ca(OH)₂

---

# CONSTANTS & CONVERSIONS

## Critical Conversion Factors
| Conversion | Factor | Formula |
|-----------|--------|---------|
| NaSH → Na₂O (Na added) | 0.5529 | 62/(2×56.06) |
| NaSH → Na₂S (as Na₂O) | 1.1060 | 62/56.06 |
| NaOH → Na₂O | 0.775 | 62/(2×40) |
| Na₂SO₄ → Na₂O | 0.4366 | 62/142.04 |
| Na → Na₂O | 1.3490 | 62/(2×22.98) |
| S → Na₂O | 1.9335 | 62/32.065 |
| gpm × g/L → lb/hr | 0.5007 | (3.785×60)/453.6 |
| lb/ft³ → g/L | 16.01846 | — |

## Default Parameters (Pine Hill)
| Parameter | Value |
|-----------|-------|
| BL Flow | 340.53 gpm |
| BL TDS | 69.1% |
| Total Production | 1887.5 BDT/day |
| Reduction Efficiency | 95% |
| Causticity | 81% |
| Target Sulfidity | 29.4% |
| Final Sulfidity | 29.40% |
| NaSH Dry | ~1,207 lb/hr |
| NaOH Dry | ~2,228 lb/hr |

## Mansfield Parameters
| Parameter | Value |
|-----------|-------|
| BL Flow | 487.2 gpm (2 × 243.6) |
| BL TDS | 72.0% |
| Total Production | 2,615 BDT/day (3 fiberlines) |
| Fiberlines | kraft_pine1 (1421 BDT), kraft_pine2 (411 BDT), semichem (783 BDT) |
| Recovery Boilers | 2 (RE: 83.7%, 81.4%) |
| Dissolving Tanks | 2 (387 gpm WW each) |
| Causticity | 77.7% |
| Target Sulfidity | 25.8% |
| Expected NaSH Dry | ~1,762 lb/hr (~15.87 lb/BDT) |
| Model NaSH Dry | ~1,631 lb/hr (7.4% gap — loss table needs per-mill calibration) |
| CTO NaOH | 193 lb/ton (Na returns via brine) |
| Semichem GL EA% | 1.61% (gl_ea_pct: 0.0161) |
| Semichem WL EA% | 3.85% (ea_pct: 0.0385) |

---

# TESTING

## Test Coverage (249 tests)
| File | Count | Purpose |
|------|-------|---------|
| `test_validation_vs_excel.py` | 33 | Cell-by-cell Excel v4 validation |
| `test_mass_balance_closure.py` | 23 | Outer loop, mass balance |
| `test_forward_leg.py` | 31 | Forward leg, WBL mixer (list API) |
| `test_dissolving_tank.py` | 27 | DT mass balance, WW flow solve |
| `test_na_s_mass_balance.py` | 17 | Na/S balance, sensitivity |
| `test_golden_regression.py` | 12 | **V2 vs V1 Pine Hill snapshot** |
| `test_mill_profile.py` | 30 | Mill config loading, validation |
| `test_makeup_chemicals.py` | 12 | 4 chemical configs, MW consistency |
| `test_chemical_charge_multi.py` | 14 | Multi-fiberline chemical charge |
| `test_multi_mill_configs.py` | 16 | Integration: 3 mill configs |
| `test_combine_rb_dt.py` | 10 | `_combine_smelts()` + `_combine_dt_inputs()` |
| `test_multi_rb_dt_integration.py` | 20 | **Multi-RB/DT end-to-end** |

### Multi-RB/DT Integration Tests
- **SingleRBBackwardCompat**: Legacy flat inputs ≡ explicit single-item RB/DT config
- **MansfieldMultiRB**: 2 RBs, 2 DTs, 3 fiberlines — converges, per-RB results present
- **HalfCapacityEquivalence**: Two half-capacity RBs ≈ one full-capacity RB
- **AsymmetricRBs**: Different RE values → correct blended smelt sulfidity

## Golden Regression Gate
`test_golden_regression.py` verifies 12 critical output keys against a V1 snapshot (`golden_snapshot_pine_hill.json`):

```
final_sulfidity_pct, nash_dry_lbs_hr, naoh_dry_lbs_hr, smelt_sulfidity_pct,
total_wl_demand_gpm, final_wl_tta_g_L, final_wl_na2s_g_L, final_wl_naoh_g_L,
bl_na_pct_used, bl_s_pct_used, pine_wl_demand_gpm, semichem_wl_demand_gpm
```

Tolerance: 0.01% relative error. **Must pass after every change.**

---

# UNIT CONVENTIONS

- **Frontend inputs** (WL/GL TTA, EA, AA): **lb/ft³** (DCS units)
- **Engine**: entirely **g/L** internally
- `api.ts` converts: `g/L = lb/ft³ × 16.01846` before every API call
- **Results display**: lb/ft³ primary, g/L secondary (dimmed)

---

# ADDING A NEW MILL

## Basic Steps
1. Create `mill_configs/your_mill.json` with fiberlines, recovery_boilers, dissolving_tanks, tanks, defaults
2. Set `MILL_CONFIG=your_mill` env var
3. Deploy — the frontend auto-loads config from `GET /api/mill-config`
4. Non-fiberline parameters (BL, losses, etc.) come from JSON `defaults` or fall back to `constants.py` DEFAULTS
5. For multi-RB mills: define each RB with `paired_dt_id` and each DT with `paired_rb_id`
6. For CTO NaOH return: set `cto_naoh_per_ton` in defaults (0 if no NaOH added in tall oil plant)

## Migration Checklist (Lessons from Mansfield Deployment)

The following issues were discovered deploying Mansfield. **Check every item when adding a new mill.**

### Config Data Validation
- [ ] **Verify gl_ea_pct vs ea_pct for semichem lines** — these are different values. `ea_pct` is WL EA charge (e.g., 3.85%), `gl_ea_pct` is GL EA charge (e.g., 1.61%). Copy-paste errors here cause GL charge to be 2-3× too high.
- [ ] **Verify causticity_pct** — don't assume 81% (Pine Hill default). Each mill has its own value.
- [ ] **Verify cto_naoh_per_ton** — 0 for mills with no NaOH in tall oil acidulation. Non-zero values (e.g., 193 for Mansfield) significantly affect Na/S balance.
- [ ] **Verify per-RB reduction efficiencies** — each RB may have different RE values. Don't use a single global RE for multi-RB mills.
- [ ] **Config key naming**: JSON uses `reduction_efficiency_pct`, engine uses `reduction_eff_pct`. The frontend `applyMillDefaults()` maps between them.

### Frontend — State & Defaults
- [ ] **Mill config loads globally on mount** — `AppStateProvider` fetches config via `useEffect` and gates all pages with `configReady`. If this is broken, the first calculation runs with Pine Hill hardcoded defaults from `defaults.ts`.
- [ ] **`applyMillDefaults()` must map ALL config defaults** — every new config key needs a mapping in this function. Missing keys (like `cto_naoh_per_ton` was) cause the frontend to use Pine Hill fallback values silently.
- [ ] **Loss table mapping** — config uses flat `loss_<source>_s` / `loss_<source>_na` keys; `applyMillDefaults()` converts these to the nested `LossTable` structure.
- [ ] **`resetToDefaults()` must re-apply mill config** — after resetting to `DEFAULT_INPUTS`, it must call `applyMillDefaults(millConfig)` or users get Pine Hill values.
- [ ] **`buildFullRequest()` used for all API calls** — raw `inputs` state is missing fiberlines, multi-RB/DT arrays. The `buildFullRequest()` function in `useAppState` combines inputs + mill config and must be used by Scenarios (what-if, predictor) and any other consumer. Never pass raw `inputs` to API calls.

### Frontend — Dynamic Components
- [ ] **No hardcoded fiberline IDs** — components must loop over `millConfig.fiberlines` or `fiberline_ids` from results. Never reference `'pine'`, `'semichem'`, etc. by name.
- [ ] **Scenario PARAMS built from config** — `ScenarioBuilder` and `SulfidityPredictor` dynamically generate fiberline production sliders from `millConfig.fiberlines`. Slider min/max are derived from each fiberline's default production (±50%/+30%).
- [ ] **Slider ranges must accommodate the mill** — e.g., RE slider min was 85% but Mansfield uses 81.4%. Now set to 75% minimum.
- [ ] **Mill name dynamic everywhere** — TopNav, Sidebar, breadcrumbs read from `useMillConfig()`.
- [ ] **BL composition charts** — must use dynamic fiberline IDs from results, not hardcoded IDs.
- [ ] **GL sulfidity display** — use `gl_sulfidity_pct` (Na₂O-based %) not `gl_sulfidity` (raw fraction).

### Backend — Multi-RB/DT
- [ ] **Flat RB keys skipped for multi-RB** — `to_engine_inputs()` must NOT set flat keys (`reduction_eff_pct`, `bl_flow_gpm`, etc.) when `self.recovery_boilers` is present. Otherwise the orchestrator's override logic (`if 'reduction_eff_pct' in inputs`) forces all RBs to the same value.
- [ ] **What-if endpoint override safety** — the what-if merges `{**base_inputs, **overrides}` directly. Flat overrides like `reduction_eff_pct` will trigger the orchestrator's per-RB override, potentially corrupting multi-RB calculations.
- [ ] **Per-RB production splitting** — each RB gets a proportional share of total production based on BL flow fraction. Verify flow fractions sum to ~100%.

### Deployment
- [ ] **Render free tier spins down after 15min** — causes 30-60s cold starts. Upgrade to Starter ($7/mo) or add a keep-alive ping.
- [ ] **`PYTHON_VERSION=3.11.11`** — Render requires full semver, not just `3.11`.
- [ ] **`MILL_CONFIG` env var set** — without it, defaults to `pine_hill`.
- [ ] **Separate repo/deployment per mill** — Mansfield has its own GitHub repo, Render service, and Vercel project. Pine Hill V1 is completely separate and untouched.

### Validation After Deployment
- [ ] Run base calculation — verify NaSH, NaOH, sulfidity match expected values
- [ ] Test Reset button — should return to mill config defaults, not Pine Hill
- [ ] Test Scenarios what-if — perturb RE, target sulfidity, production; verify directional correctness
- [ ] Test Scenarios predictor — fix NaSH/NaOH, vary parameters; verify sulfidity responds correctly
- [ ] Verify per-RB results (if multi-RB) — each RB should show independent RE and smelt sulfidity
- [ ] Check all pages load correctly without navigating to Inputs first

---

# COMPLETED V1 FIXES (All preserved in V2)

| Fix | Impact |
|-----|--------|
| DT mass balance closure | TTA error: 17.8% → 0.2% |
| NaSH Na₂O display | Corrected to 0.5529 (1 Na atom) |
| Fiberline TDS | Removed `/3.785` unit bug |
| NCG double-count | Removed NCG S subtraction from fiberline |
| Outer loop skip (NaSH override) | Prevents runaway feedback |
| WLC NaOH mass tracking | WL EA gap: 2.34 → 0.03 g/L |
| EA deficit formula | CE × (TTA - Na₂S) not CE × AA |
| CE flow-dependent washable soda | ~5.5 lb NaOH/hr per 1% CE |
| CTO delta fix | Correct sulfidity impact |
| Latent sulfidity fix | Strong BL uses s_ret_strong |

# V2 DEPLOYMENT FIXES

| Fix | Impact |
|-----|--------|
| Mansfield gl_ea_pct | Was 0.0385 (same as ea_pct), corrected to 0.0161 → GL charge 276.8→115.5 gpm |
| Dynamic mill name in nav | TopNav/Sidebar read from useMillConfig() instead of hardcoded "Pine Hill" |
| Dynamic BL composition chart | BLCompositionChart loops fiberline_bl array instead of hardcoded 'pine'/'semichem' IDs |
| Per-RB/DT editable fields | Multi-RB/DT cards with independent inputs (not read-only summaries) |
| GL sulfidity display | Uses gl_sulfidity_pct (Na₂O-based) not gl_sulfidity×100 (raw fraction) |
| Dynamic fiberline WL bars | RecaustFlowDiagram reads fiberline_ids from intermediate dict |
| Mill config defaults | applyMillDefaults() maps JSON defaults to frontend state with g/L→lb/ft³ conversion |
| intermediate dict typing | Changed from Record<string, number> to Record<string, any> for mixed types |
| Global mill config loading | Config was only loaded on Inputs page → moved to AppStateProvider with configReady gating |
| cto_naoh_per_ton mapping | Was missing from applyMillDefaults → NaSH off by ~200 lb/hr for Mansfield |
| Loss table from config | applyMillDefaults now maps flat loss_*_s/loss_*_na keys to LossTable structure |
| Multi-RB flat override conflict | to_engine_inputs() skips flat RB keys when recovery_boilers array is present |
| Reset to mill defaults | resetToDefaults() re-applies mill config after clearing, not just Pine Hill defaults |
| Mansfield causticity | Was 81.0% (Pine Hill default), corrected to 77.7% |
| Scenarios use buildFullRequest | What-if/Predictor now use full request with mill config fiberlines + multi-RB/DT |
| Dynamic scenario params | ScenarioBuilder/SulfidityPredictor build PARAMS from mill config fiberlines |
| Slider ranges widened | RE min 85→75% to accommodate low-RE mills like Mansfield (81.4%) |

---

# DEPLOYMENT

## Mansfield (Independent from Pine Hill V1)
- **GitHub**: `pifanohey/mansfield-sulfidity-predictor`
- **Render**: `mansfield-sulfidity-backend` with `MILL_CONFIG=mansfield`
- **Vercel**: Frontend with `API_URL` pointing to Render backend
- **Pine Hill V1**: Completely separate repo/deployment, untouched

---

*Sulfidity Predictor v2.0 — Multi-Mill, Multi-RB/DT Architecture*
