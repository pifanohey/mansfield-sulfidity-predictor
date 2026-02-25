# Sulfidity Predictor V2 — Multi-Mill Architecture

## What This Is
A web-based chemical engineering tool for Kraft pulp mills that predicts white liquor sulfidity and calculates makeup chemical requirements. V2 extends V1 with **configurable N-fiberline support** and **multiple makeup chemical types**, enabling deployment to any mill via JSON config files.

**V2 vs V1:** V1 hardcoded Pine Hill's 2-fiberline setup. V2 loops over a configurable list of fiberlines loaded from JSON. The core solver math is identical — V2 only changes the parameterization layer.

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
cd backend && python3 -m pytest tests/ -v    # 215 tests, ALL passing
```

---

## Project Structure
```
/sulfidity_predictor_v2/
├── mill_configs/                   # ★ V2: JSON config per mill
│   ├── pine_hill.json              #   2 fiberlines, NaSH makeup
│   ├── three_line_chemical.json    #   3 fiberlines, saltcake makeup
│   └── two_batch.json              #   2 batch lines, NaOH makeup
├── backend/
│   ├── app/
│   │   ├── engine/                 # 19 calculation modules
│   │   │   ├── orchestrator.py     #   Master solver, triple-loop
│   │   │   ├── mill_profile.py     #   ★ V2: FiberlineConfig/MillConfig loader
│   │   │   ├── makeup_chemicals.py #   ★ V2: 4 chemical type configs
│   │   │   ├── chemical_charge.py  #   Fiberline WL demand (loops over configs)
│   │   │   ├── fiberline.py        #   BL composition (list-based mixer)
│   │   │   ├── recovery_boiler.py  #   RB chemistry, alkali formation
│   │   │   ├── dissolving_tank.py  #   Smelt dissolution, WW flow solve
│   │   │   ├── slaker_model.py     #   Energy/water/mass balance
│   │   │   ├── makeup.py           #   NaSH/NaOH sizing (Secant method)
│   │   │   ├── s_retention.py      #   Unified loss table, S retention
│   │   │   ├── evaporator.py       #   WBL → SBL concentration
│   │   │   ├── constants.py        #   MW, CONV, DEFAULTS (includes fiberlines)
│   │   │   ├── density.py          #   BL/GL/WL density correlations
│   │   │   ├── mill_config.py      #   Tank geometry (13 tanks)
│   │   │   ├── inventory.py        #   Tank volumes from lab
│   │   │   ├── predictor.py        #   FOPDT sulfidity forecasting
│   │   │   ├── guidance.py         #   Rule-based recommendations
│   │   │   └── sensitivity.py      #   Auto-perturbation analysis
│   │   ├── api/
│   │   │   ├── schemas.py          #   Pydantic models (FiberlineInput, etc.)
│   │   │   └── routes/calculate.py #   REST endpoints + GET /api/mill-config
│   │   ├── reports/                #   PDF & Excel export
│   │   └── main.py                 #   FastAPI entry point
│   └── tests/                      #   215 tests (10 test files)
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
      "id": "pine",
      "name": "Pine",
      "type": "continuous",
      "cooking_type": "chemical",
      "uses_gl_charge": false,
      "defaults": {
        "production_bdt_day": 1250.69,
        "yield_pct": 0.5694,
        "ea_pct": 0.122,
        "wood_moisture": 0.523
      }
    },
    {
      "id": "semichem",
      "name": "Semichem",
      "type": "batch",
      "cooking_type": "semichem",
      "uses_gl_charge": true,
      "defaults": {
        "production_bdt_day": 636.854,
        "yield_pct": 0.7019,
        "ea_pct": 0.0365,
        "gl_ea_pct": 0.017,
        "wood_moisture": 0.461
      }
    }
  ],
  "tanks": [...],
  "defaults": {...}
}
```

### Key Dataclasses (`mill_profile.py`)
- **`FiberlineConfig`**: `id, name, type, cooking_type, uses_gl_charge, defaults`
- **`MillConfig`**: `mill_name, makeup_chemical, fiberlines, tanks, defaults`
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

## Engine Flow (How Fiberlines Are Processed)

### Orchestrator Loop
```
run_calculations(inputs):
  fiberline_configs = inputs['fiberlines']   # List[FiberlineConfig]
  total_prod = sum(fl.production_bdt_day for fl in fiberline_configs)

  OUTER LOOP (BL convergence):
    SECANT LOOP (NaSH targeting):
      INNER LOOP (GL flow convergence):
        dissolving_tank → slaker → WLC Stage 1
        → chemical_charge(fiberlines=fiberline_configs, ...)
        → Na loss factor → WLC Stage 2
        → GL convergence check

    FORWARD LEG:
      for fl in fiberline_configs:
        bl_outputs[fl.id] = calculate_fiberline_bl(fl.production, fl.yield, ...)
        if fl.uses_gl_charge:
          add GL to fiberline inputs

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

The orchestrator produces per-fiberline result keys:
```python
results['fiberline_ids'] = ['pine', 'semichem']   # list of IDs processed
results['pine_wl_demand_gpm'] = 342.5
results['semichem_wl_demand_gpm'] = 93.2
results['pine_bl_organics_lb_hr'] = 5200.0
results['semichem_bl_organics_lb_hr'] = 2100.0
```

---

# API ENDPOINTS

## V2-Specific Endpoints

### `GET /api/mill-config`
Returns the active mill configuration (fiberlines, tanks, defaults, makeup_chemical).

### `POST /api/calculate`
**V2 request body** includes `fiberlines` array:
```json
{
  "fiberlines": [
    {"id": "pine", "production_bdt_day": 1250.69, "yield_pct": 0.5694, "ea_pct": 0.122},
    {"id": "semichem", "production_bdt_day": 636.854, "yield_pct": 0.7019, "ea_pct": 0.0365, "gl_ea_pct": 0.017}
  ],
  "cooking_wl_sulfidity": 0.283,
  "bl_na_pct": 19.39,
  ...
}
```

Backend schema: `FiberlineInput(id, production_bdt_day, yield_pct, ea_pct, gl_ea_pct?)`

### Other Endpoints (unchanged from V1)
- `POST /api/calculate/what-if` — scenario comparison
- `POST /api/calculate/sensitivity` — perturbation analysis
- `POST /api/trends` — save trend point
- `GET /api/trends` — list trend points
- `GET/POST /api/snapshots` — save/load calculations
- `POST /api/export/excel`, `POST /api/export/pdf` — reports

---

# FRONTEND (V2 Changes)

## Config-Driven Fiberline Inputs

The frontend loads mill config via `GET /api/mill-config` and dynamically renders fiberline inputs.

### Key Hook: `useMillConfig`
```typescript
const { config, loading, error } = useMillConfig();
// config: MillConfig | null
// Fetches GET /api/mill-config on mount
```

### State Management (`useAppState`)
```typescript
// New V2 state:
millConfig: MillConfig | null
fiberlineInputs: Record<string, FiberlineInputState>  // keyed by fiberline id
updateFiberlineField(fiberlineId, key, value)
setMillConfig(config)

// runCalculation builds fiberlines array from config + user overrides:
const fiberlines = millConfig.fiberlines.map(fl => ({
  id: fl.id,
  production_bdt_day: fiberlineInputs[fl.id]?.production_bdt_day ?? fl.defaults.production_bdt_day,
  ...
}));
```

### ProductionSection (config-driven loop)
```tsx
{fiberlines.map(fl => (
  <div key={fl.id}>
    <h4>{fl.name} ({fl.type} / {fl.cooking_type})</h4>
    <InputField label="Production" value={...} />
    <InputField label="Yield" value={...} />
    <InputField label="EA Charge" value={...} />
    {fl.uses_gl_charge && <InputField label="GL EA" value={...} />}
  </div>
))}
```

### TypeScript Types
```typescript
interface FiberlineConfig { id, name, type, cooking_type, uses_gl_charge, defaults }
interface FiberlineInputState { production_bdt_day?, yield_pct?, ea_pct?, gl_ea_pct? }
interface MillConfig { mill_name, makeup_chemical, fiberlines[], tanks[], defaults }
```

### Default Inputs (`defaults.ts`)
Uses `fiberlines` array (not flat fields):
```typescript
fiberlines: [
  { id: "pine", production_bdt_day: 1250.69, yield_pct: 0.5694, ea_pct: 0.122 },
  { id: "semichem", production_bdt_day: 636.854, yield_pct: 0.7019, ea_pct: 0.0365, gl_ea_pct: 0.017 },
]
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

---

# TESTING

## Test Coverage (215 tests)
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

1. Create `mill_configs/your_mill.json` with fiberlines, tanks, defaults
2. Set `MILL_CONFIG=your_mill` env var
3. Deploy — the frontend auto-loads config from `GET /api/mill-config`
4. Non-fiberline parameters (BL, RB, DT, losses, etc.) come from JSON `defaults` or fall back to `constants.py` DEFAULTS

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

---

*Sulfidity Predictor v2.0 — Multi-Mill Architecture*
