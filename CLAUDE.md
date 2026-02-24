# Sulfidity Predictor - Project Memory & Technical Documentation

## What This Is
A web-based chemical engineering tool for Kraft pulp mills (Pine Hill Mill) that replicates and extends `SULFIDITY_MODEL_CORRECTED_FINAL v5.xlsx`. It predicts white liquor sulfidity and calculates NaSH/NaOH makeup chemical requirements using a **dual-loop iterative solver** that closes the mass balance around the entire circuit.

---

## How to Run the App
```bash
# One command (recommended) — starts both backend and frontend:
./start.sh
# Backend  → http://localhost:8005
# Frontend → http://localhost:3005

# Or manually in two terminals:
# Terminal 1 — Backend
cd backend
python3 -m uvicorn app.main:app --reload --port 8005

# Terminal 2 — Frontend
cd frontend
npm run dev          # pinned to port 3005
```

## Project Structure
```
/sulfidity_predictor/
├── backend/                    # FastAPI + Python calculation engine
│   ├── app/
│   │   ├── engine/             # 17 calculation modules (core math)
│   │   ├── api/routes/         # 4 REST endpoints (calculate, snapshots, mills, export)
│   │   ├── reports/            # PDF & Excel report generators (openpyxl, reportlab)
│   │   ├── db/                 # SQLAlchemy models + SQLite
│   │   └── main.py             # FastAPI entry point (port 8005)
│   ├── tests/
│   │   ├── test_validation_vs_excel.py   # 48 cell-by-cell validation tests
│   │   ├── test_mass_balance_closure.py  # 34 mass balance + convergence tests
│   │   ├── test_forward_leg.py           # Forward leg tracking tests
│   │   └── reference_data/excel_v4_values.json
│   ├── pyproject.toml
│   └── requirements.txt
├── frontend/                   # Next.js 15 + React 18 + TypeScript
│   └── src/
│       ├── app/                # Pages: inputs, results, scenarios
│       ├── components/         # Input sections + result displays
│       └── lib/                # types.ts, defaults.ts, api.ts
├── docs/                       # All documentation (PRD, technical docs, guides)
└── *.xlsx                      # Excel reference models (v3, v4, v5)
```

## Running Tests
```bash
cd backend
python -m pytest tests/ -v          # 126 tests, all passing
```

---

# EXECUTIVE SUMMARY

**Key Capabilities:**
- Predicts final WL sulfidity from first principles
- Calculates NaSH and NaOH makeup requirements
- Tracks Na and S through 11 unit operations
- Supports what-if scenario analysis
- Provides sensitivity analysis on key parameters

**Current Calibration (Default Inputs):**
| Metric | Value |
|--------|-------|
| Final Sulfidity | 29.40% (hits target via Secant method) |
| Smelt Sulfidity | 28.15% |
| NaSH Dry | 1,358 lb/hr |
| NaOH Dry | 2,120 lb/hr |
| Outer Loop | 2 iterations, converged |
| BL Na% | 19.36% computed (lab 19.39%, gap 0.03) |
| BL S% | 4.03% computed (lab 4.01%, gap 0.02) |
| Net S Balance | +105 lb/hr |
| NaOH Constraint | losses (at CE ≥ 81%) |

---

# 1. ARCHITECTURE OVERVIEW

## 1.1 Technology Stack

```
┌─────────────────────────────────────────────────────────────┐
│                      FRONTEND (Next.js 15)                   │
│   React 18 + TypeScript + Tailwind CSS + shadcn/ui          │
│   Pages: Inputs, Results, Scenarios                          │
│   Deployed on: Vercel (https://sulfidity-predictor.vercel.app)│
└───────────────────────────┬─────────────────────────────────┘
                            │ REST API (proxied via Next.js rewrites)
┌───────────────────────────┴─────────────────────────────────┐
│                      BACKEND (FastAPI)                       │
│   Python 3.11 + Pydantic + SQLAlchemy                       │
│   Endpoints: /calculate, /what-if, /sensitivity             │
│   Deployed on: Render (https://sulfidity-predictor.onrender.com)│
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┴─────────────────────────────────┐
│                   CALCULATION ENGINE                         │
│   17 Python modules in /backend/app/engine/                 │
│   Orchestrator → 16 specialized calculation modules          │
└─────────────────────────────────────────────────────────────┘
```

## 1.2 Engine Module Structure

| Module | Purpose | Excel Reference |
|--------|---------|-----------------|
| `orchestrator.py` | Master solver, dual-loop convergence | All sheets |
| `recovery_boiler.py` | BL properties, smelt composition, TTA, sulfidity | 2_RB B21-B35 |
| `dissolving_tank.py` | GL flow calculation (circular variable I58) | 2_RB I43-I75 |
| `slaker_model.py` | Energy/water/mass balance, yield factor, first-principles causticizing | Slaker Model |
| `chemical_charge.py` | Fiberline WL demand, semichem GL, WLC | 3_Chem |
| `makeup.py` | NaSH (Secant method), NaOH (dual-constraint: losses + EA demand) | 0_SULF H44-H63 |
| `s_retention.py` | Unified loss table, S retention factors | 2_RB |
| `fiberline.py` | BL composition from digesters | Forward leg |
| `evaporator.py` | WBL → SBL concentration | Forward leg |
| `constants.py` | MW, conversion factors, 80+ default parameters | All sheets |
| `inventory.py` | Tank volumes, liquor composition from lab | 1_Inv |
| `density.py` | BL/GL/WL density correlations | Various |
| `mill_config.py` | Tank geometry (13 tanks, volume vs. level) | 1_Inv |
| `predictor.py` | FOPDT sulfidity forecasting (4/8/12/24hr predictions) | N/A |
| `guidance.py` | Rule-based operational recommendations | N/A |
| `sensitivity.py` | Auto-perturbation analysis (8 scenarios) | N/A |

---

# 2. CALCULATION FLOW

## 2.1 High-Level Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              INPUT PARAMETERS                                │
│   BL Flow (340.5 gpm), TDS (69.1%), Production (1887.5 BDT/day)            │
│   Lab WL/GL Analysis, Loss Table (13 sources), Target Sulfidity (29.4%)     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         OUTER LOOP (BL Convergence)                          │
│   Converges on BL Na% and S% from forward leg calculation                   │
│   Tolerance: 0.01%, Max iterations: 20, Typical: 2 iterations               │
│                                                                              │
│   ┌───────────────────────────────────────────────────────────────────────┐ │
│   │                    INNER LOOP (GL Flow Convergence)                   │ │
│   │   Converges on GL_flow_to_slaker (circular variable I58)              │ │
│   │   Tolerance: 0.001 gpm, Max iterations: 100, Typical: 5-10            │ │
│   │                                                                        │ │
│   │   Dissolving Tank → Slaker → WLC Stage 1 → Chemical Charge            │ │
│   │        → Na Loss Factor → WLC Stage 2 → Check GL Convergence          │ │
│   └───────────────────────────────────────────────────────────────────────┘ │
│                                      │                                       │
│                                      ▼                                       │
│   Forward Leg: WL → Digesters → WBL → Evaporator → SBL → Check BL Conv     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              OUTPUT RESULTS                                  │
│   Final Sulfidity, NaSH/NaOH Requirements, Mass Balance, Inventories        │
│   Unit Operations Tracking, Guidance Recommendations                         │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 2.2 Triple-Loop Solver Architecture

### Outer Loop: BL Composition Convergence

**Purpose:** Closes the mass balance by computing BL Na%/S% from the forward leg instead of using fixed lab values.

**Status:** ENABLED by default (`enable_outer_loop=True`). Converges in 2 iterations. Computed Na%/S% match lab within 0.03 pts.

**Process:**
1. Recovery Boiler receives BL composition (initially from lab, then from computed values)
2. Middle loop (Secant) runs to convergence
3. Forward leg computes: WL → Digesters → WBL → Evaporator → SBL
4. New BL Na%/S% extracted from forward leg
5. Compare with previous iteration; if |ΔNa%| < 0.01% AND |ΔS%| < 0.01%, converged

**Key Design Decision — NO NCG subtraction in fiberline:**
The fiberline does NOT subtract NCG S losses because the WL Na₂S concentration already reflects steady-state NCG losses from the full cycle. Subtracting again would double-count. NCG losses are tracked only in the unified loss table for NaSH/NaOH sizing.

**Key Design Decision — Outer loop skipped when NaSH is overridden:**
When `nash_dry_override_lb_hr` is set (Sulfidity Predictor mode), the outer loop is skipped after the first iteration. Without the Secant solver adjusting NaSH to compensate, the outer loop creates a runaway positive feedback: lower RE → less Na₂S in smelt → less S in WL → lower BL S% → even lower smelt sulfidity → repeat. This amplified sensitivity 3.5x (0.86%/pt vs correct 0.24%/pt). Skipping the outer loop uses fixed BL composition, giving the physically correct short-term what-if response.

### Middle Loop: Secant Method for Sulfidity Targeting

**Purpose:** Iteratively adjusts NaSH to hit target sulfidity exactly.

**Process:**
```
Target: final_sulfidity = target_sulfidity_pct (e.g., 29.4%)

Secant iteration:
  1. Initial guess: NaSH from S deficit
  2. Run inner loop → get final_sulfidity
  3. If |final - target| > 0.01%, iterate:
     NaSH_next = NaSH_curr - f(NaSH_curr) × (NaSH_curr - NaSH_prev) / (f_curr - f_prev)
     where f(NaSH) = final_sulfidity - target_sulfidity
  4. Converges in 3-5 iterations typically
```

### Inner Loop: GL Flow Convergence

**Purpose:** Solves the circular reference on GL_flow_to_slaker (Excel cell I58)

**Circular Path:**
```
GL flow (I58) → GL composition → Slaker → WL composition
    → Chemical Charge → WL demand → Semichem GL (G5) → back to GL flow
```

**Two-Stage WLC Approach:**
- **Stage 1:** NaSH only → captures final EA for WL demand calculation
- **Stage 2:** NaSH + NaOH → final WL composition

---

# 3. UNIT OPERATIONS FLOW

## 3.1 Complete Circuit Map

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FORWARD LEG                                     │
│                                                                              │
│  WL Storage ──→ Pine Fiberline ──→ Pine WBL ──┐                             │
│      │              (1251 BDT/day)             │                             │
│      │                                          │                             │
│      └──→ Semichem Fiberline ←── GL (93 gpm)   │                             │
│                (637 BDT/day)                    │                             │
│                    │                            │                             │
│              Semichem WBL ─────────────────────→├──→ WBL Mixer ──→ Evaporator│
│                                                 │         + CTO              │
│                                                 │             │              │
│                                                 │          SBL ──→ RB        │
└─────────────────────────────────────────────────────────────────────────────┘
                                                                    │
                                                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           RECOVERY BOILER                                    │
│                                                                              │
│  SBL (Na 19.46%, S 3.85%) + Saltcake (2227 lb/hr) + Ash Recycle (7%)       │
│                                    │                                         │
│                                    ▼                                         │
│  Dry Solids: 191,500 lb/hr  →  Reduction (95%)  →  Smelt                    │
│                                                                              │
│  Smelt Output: TTA 34,800 lb/hr, Active S 9,360 lb/hr, Sulfidity 26.89%    │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          DISSOLVING TANK                                     │
│                                                                              │
│  Inputs:                              Outputs:                               │
│    Smelt: 81 gpm                        GL to Clarifier: 766 gpm            │
│    Weak Wash: ~753 gpm (solved for TTA target)                               │
│    Shower: 60 gpm                                                            │
│    Dregs Filtrate: ~20 gpm (returned)                                        │
│    ─────────────────                                                         │
│    Total: ~766 gpm (after dregs return)                                      │
│                                                                              │
│  GL Composition: TTA 117 g/L, Na₂S 31.5 g/L, Sulfidity 26.9%               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          GL CLARIFIER                                        │
│                                                                              │
│  Subtractions:                                                               │
│    Dregs underflow: 13 gpm                                                   │
│    Grits underflow: 1.7 gpm                                                  │
│    Semichem GL: 93 gpm (to semichem digester)                               │
│    ─────────────────────                                                     │
│    Total removed: 108 gpm                                                    │
│                                                                              │
│  GL to Slaker: 659 gpm                                                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SLAKER                                          │
│                                                                              │
│  Inputs:                              Process:                               │
│    GL: 659 gpm                          Ca(OH)₂ + Na₂CO₃ → 2NaOH + CaCO₃    │
│    Lime: ~X lb/hr                       Causticity: 81%                      │
│                                                                              │
│  Energy Balance:                                                             │
│    Heat from slaking → Steam generated                                       │
│    Water consumed by reaction                                                │
│                                                                              │
│  Outputs:                                                                    │
│    WL: 683 gpm (yield factor 1.033)                                         │
│    Lime mud: ~Y lb/hr (CaCO₃ + excess Ca(OH)₂ + inerts)                    │
│    Grits: 1% of lime feed                                                    │
│                                                                              │
│  WL from Slaker: TTA 121 g/L, Na₂S 32.5 g/L, Sulfidity 26.9%               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      WHITE LIQUOR CLARIFIER                                  │
│                                                                              │
│  Inputs:                              Makeup Additions:                      │
│    WL from Slaker: 683 gpm              NaSH: 1349 lb/hr dry (40% soln)     │
│    Intrusion water: 28 gpm              NaOH: 2267 lb/hr dry (50% soln)     │
│    Dilution water: 24 gpm                                                    │
│                                                                              │
│  Separation:                                                                 │
│    Underflow (lime mud): to lime kiln                                        │
│    Overflow (clarified WL): to storage                                       │
│                                                                              │
│  Final WL: TTA 117 g/L, Na₂S 33.5 g/L, Sulfidity 28.6%, Flow 587 gpm       │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
                               WL Storage → (loops back to Fiberlines)
```

## 3.2 Unit Operations Data Table

| Stage | Na (lb/hr) | S (lb/hr) | TTA (ton/hr) | Flow (gpm) |
|-------|-----------|----------|--------------|------------|
| WL to Digesters | 24,300 | 5,100 | 19.1 | 587 |
| Pine BL | 9,800 | 2,100 | - | - |
| Semichem BL | 4,200 | 900 | - | - |
| Mixed WBL | 14,500 | 3,200 | - | - |
| Evaporator (SBL) | 14,500 | 3,200 | - | - |
| Recovery Boiler (Smelt) | 23,800 | 5,700 | 17.4 | - |
| Dissolving Tank | 25,100 | 6,000 | 18.9 | 766 |
| Green Liquor (to slaker) | 21,600 | 5,200 | 16.3 | 659 |
| Slaker | 21,600 | 5,200 | 16.3 | 659 |
| WL (from slaker) | 22,300 | 5,200 | 16.8 | 683 |

---

# 4. KEY CALCULATIONS

## 4.1 Recovery Boiler Formulas

### Dry Solids & Composition
```
Dry Solids (lb/hr) = BL_flow × BL_density × TDS% × 10 × 0.06
                   = 340.53 × 10.28 × 0.691 × 10 × 0.06
                   = 191,500 lb/hr

Mixed Na% = (Virgin_Na% × Virgin_solids + Ash_Na) / (Virgin + Ash) × 100

Mixed S% = (Virgin_S% × Virgin_solids + Ash_S) / (Virgin + Ash) × 100
```

### Alkali Formation (as Na₂O basis)
```
Potential Na (lb Na₂O/hr) = Na_lbs × 1.3490    [Na → Na₂O]
Potential K (lb Na₂O/hr) = K_lbs × 0.7928      [K → Na₂O equivalent]
Potential S (lb Na₂O/hr) = S_lbs × 1.9335      [S as Na₂S → Na₂O]

Active Sulfide = Potential_S × RE × S_retention - Ash_S_Na₂O
Dead Load = Potential_S × (1 - RE)

TTA = Potential_Na + Potential_K - Dead_Load - RB_Losses - Ash_Na

Smelt Sulfidity (%) = (Active_Sulfide / TTA) × 100
                    = (9,360 / 34,800) × 100 = 26.89%
```

## 4.2 NaSH Sizing (Secant Method for Sulfidity Targeting)

NaSH is sized using a **Secant iterative method** to hit target sulfidity exactly.

### Initial Guess (S Deficit Approach)
```
S Deficit (lb S/hr) = Total_S_Losses - Saltcake_S - CTO_S
                    = 1313 - 503 - 0 = 810 lb/hr

Na₂S Deficit = (Target_Sulfidity × Adjusted_TTA) - WL_Na₂S_from_slaker

NaSH_initial = Na₂S_Deficit × 2000 / 1.106
```

### Secant Iteration
```
f(NaSH) = final_sulfidity(NaSH) - target_sulfidity

Iteration:
  NaSH_{n+1} = NaSH_n - f(NaSH_n) × (NaSH_n - NaSH_{n-1}) / (f_n - f_{n-1})

Convergence: |f(NaSH)| < 0.01% (absolute sulfidity)
Typical iterations: 3-5
```

### Result
Final sulfidity converges to within **0.5%** of target (e.g., 29.4% ± 0.15%).

## 4.3 NaOH Sizing (Dual-Constraint Model)

NaOH must satisfy **TWO constraints** — the binding constraint is the maximum:

### Constraint 1: Na Losses (Mass Balance)
```
At steady state: Na_in = Na_out

Total_Na_losses = 42.8 lb Na₂O/BDT × Production / 24 = 3,366 lb Na₂O/hr
Saltcake_Na = 2227 × 0.4366 = 972 lb Na₂O/hr
NaSH_Na = NaSH_dry × 0.5529

Na_deficit = Total_Na_losses - Saltcake_Na - NaSH_Na
NaOH_for_losses = Na_deficit / 0.775
```

### Constraint 2: EA Demand (Digester Requirement)
```
Digesters need a specific EA charge (% on OD wood).
If CE drops below baseline (81%), EA concentration drops.
NaOH compensates to maintain EA without increasing WL flow.

BASELINE_CE = 0.81
EA_at_baseline = 0.81 × AA + 0.5 × Na₂S
EA_at_actual = CE × AA + 0.5 × Na₂S

EA_deficit = max(0, EA_at_baseline - EA_at_actual) × WL_flow × 0.5007
NaOH_for_EA = EA_deficit / 0.775
```

### Final NaOH
```
NaOH_dry = max(NaOH_for_losses, NaOH_for_EA)

naoh_constraint = 'EA_demand' if NaOH_for_EA > NaOH_for_losses else 'losses'
```

### CE Impact on NaOH
Two mechanisms link CE to NaOH:
1. **Flow-dependent washable soda losses** (75-87% CE): Lower CE → lower WL EA → higher WL demand → more Na washed out → higher Na losses → more NaOH. Sensitivity ~5-6 lb NaOH/hr per 1% CE.
2. **EA demand constraint** (<74% CE): EA deficit exceeds Na losses, NaOH jumps dramatically.

| CE | Constraint | NaOH (lb/hr) | CE adj (lb/hr) | WL demand (gpm) | Reason |
|----|------------|--------------|----------------|-----------------|--------|
| 87% | losses | ~2,198 | -41 | 551 | Flow-dep: less washing → less NaOH |
| 84% | losses | ~2,212 | -21 | 566 | Flow-dep: less washing |
| 81% | losses | ~2,228 | 0 | 581 | **Baseline** |
| 78% | losses | ~2,245 | +22 | 598 | Flow-dep: more washing → more NaOH |
| 75% | losses | ~2,263 | +46 | 615 | Flow-dep: even more washing |
| 74% | EA_demand | ~2,314 | +55 | 620 | Crossover — EA barely exceeds losses |
| 72% | EA_demand | ~2,983 | +72 | 622 | EA demand kicks in hard |
| 70% | EA_demand | ~3,657 | +90 | 624 | EA demand dominates |
| 65% | EA_demand | ~5,360 | +138 | 629 | EA demand >> losses |

## 4.4 Slaker Model (First-Principles Causticizing)

### Yield Factor
```
Yield Factor = WL_volume / GL_volume

Where:
  GL_volume = GL_flow × 60 × 3.785 (L/hr)
  WL_mass = GL_mass + Lime - Steam - Grits_loss
  WL_volume = WL_mass × 907.185 / WL_density (1.135 kg/L)

Typical yield factor = 1.033 (WL flow > GL flow due to lime addition)
```

### First-Principles Causticizing

**Reaction:** Na₂CO₃ + Ca(OH)₂ → 2NaOH + CaCO₃

**GL Na₂CO₃ (dead load to be causticized):**
```
GL_Na₂CO₃ (g Na₂O/L) = GL_TTA - GL_AA
GL_Na₂CO₃ (lb/hr) = GL_Na₂CO₃ × (106/62) × GL_flow × 0.5007
```

**Conversion fraction from target CE:**
```
CE = NaOH / (NaOH + Na₂CO₃)

Let x = fraction of Na₂CO₃ converted:
  CE = 2x / (1 + x)

Solving for x:
  x = CE / (2 - CE)

Examples:
  CE 75%: x = 0.600 (60.0% converted)
  CE 81%: x = 0.681 (68.1% converted)
  CE 85%: x = 0.739 (73.9% converted)
```

**Lime requirement:**
```
Stoichiometry: 1 mol CaO per mol Na₂CO₃ converted

Lime_required (lb CaO/hr) = x × GL_Na₂CO₃ (lb/hr) × (56.08 / 106)
Lime_feed (lb/hr) = Lime_required / CaO_purity
```

**WL composition from slaker:**
```
WL_NaOH = CE × (TTA - Na₂S)           ← Increases with CE
WL_Na₂CO₃ = TTA - Na₂S - WL_NaOH      ← Decreases with CE
WL_Na₂S = GL_Na₂S (unchanged)
WL_AA = WL_NaOH + WL_Na₂S             ← Increases with CE
WL_EA = WL_NaOH + 0.5 × WL_Na₂S       ← Increases with CE
WL_TTA = WL_NaOH + WL_Na₂CO₃ + WL_Na₂S (conserved)
```

### CE Impact on WL Quality
| CE | NaOH (g/L) | Na₂CO₃ (g/L) | AA (g/L) | EA (g/L) |
|----|------------|--------------|----------|----------|
| 81% | 66.2 | 15.5 | 97.5 | 81.9 |
| 85% | 69.5 | 12.2 | 100.8 | 85.1 |
| Δ | +3.3 | -3.3 | +3.3 | +3.3 |


## 4.5 Na Inventory Tracking

At steady state, Na entering = Na leaving. The model tracks accumulation:

```
Na_in (lb/hr) = Saltcake_Na + NaSH_Na + NaOH_Na
              = (Saltcake × 2×22.98/142.04) + (NaSH × 22.98/56.06) + (NaOH × 22.98/40)

Na_out (lb/hr) = Total_Na_losses × (2×22.98/62)
              = 3,366 × 0.7416 = 2,496 lb Na/hr

Na_accumulation = Na_in - Na_out
```

**Status indicators:**
| Status | Condition | Meaning |
|--------|-----------|---------|
| `steady_state` | \|accumulation\| < 50 lb/hr | Balanced operation |
| `building_inventory` | accumulation > 50 lb/hr | Adding Na faster than losing |
| `depleting_inventory` | accumulation < -50 lb/hr | Losing Na faster than adding |

**Interpretation:**
- At `losses` constraint with steady_state: Normal operation
- At `EA_demand` constraint with building_inventory: CE too low, fix causticizing

---

# 5. UNIFIED LOSS TABLE

## 5.1 Loss Sources (13 Categories)

| Source | S (lb/BDT) | Na₂O (lb/BDT) | Unit Operation |
|--------|-----------|---------------|----------------|
| Pulp Washable Soda | 3.0 | 18.5 | Fiberline |
| Pulp Bound Soda | 0.0 | 7.4 | Fiberline |
| Pulp Mill Spills | 0.0 | 0.3 | Fiberline |
| Evaps Spill | 2.4 | 5.2 | Evaporator |
| RB Ash | 1.3 | 2.8 | Recovery Boiler |
| RB Stack | 0.3 | 0.8 | Recovery Boiler |
| Dregs Filter | 0.4 | 2.4 | Recausticizing |
| Grits | 0.2 | 1.5 | Recausticizing |
| Weak Wash Overflow | 0.1 | 0.7 | Recausticizing |
| NCG | 8.5 | 1.0 | NCG System |
| Recaust Spill | 0.4 | 2.2 | Recausticizing |
| Truck Out GL | 0.0 | 0.0 | Other |
| Unaccounted | 0.0 | 0.0 | Other |
| **TOTALS** | **16.7** | **42.8** | |

Loss table key format in constants.py: `loss_{source}_{s|na}` (e.g., `loss_ncg_s`, `loss_ncg_na`).

## 5.2 Conversion to Flow Rates

```
Production = 1887.5 BDT/day

Total S Losses (lb/hr) = 16.7 × 1887.5 / 24 = 1,313 lb/hr
Total Na Losses (lb/hr) = 42.8 × 1887.5 / 24 = 3,365 lb Na₂O/hr
```

## 5.3 S Retention Factors

```
S Throughput (lb S/BDT) = (Dry_Solids × BL_S%) / Production

S Retention (weak) = 1 - (Total_S_Losses / S_Throughput) ≈ 90.5%

S Retention (strong) = 1 - (RB_S_Losses / S_Throughput) ≈ 98.6%
```

---

# 6. KEY CONVERSION FACTORS

## 6.1 Molecular Weights

| Compound | MW (g/mol) |
|----------|------------|
| Na | 22.98 |
| S | 32.065 |
| K | 39.1 |
| Na₂O | 62.0 |
| Na₂S | 78.05 |
| NaOH | 40.0 |
| NaSH | 56.06 |
| Na₂CO₃ | 106.0 |
| Na₂SO₄ | 142.04 |
| CaO | 56.08 |
| CaCO₃ | 100.09 |

## 6.2 Critical Conversion Factors

| Conversion | Factor | Formula | Usage |
|-----------|--------|---------|-------|
| Na → Na₂O | 1.3490 | 62/(2×22.98) | Na mass balance |
| S → Na₂O | 1.9335 | 62/32.065 | S as Na₂S equiv |
| K → Na₂O | 0.7928 | 62/(2×39.1) | K alkali equiv |
| NaSH → Na₂O (Na added) | 0.5529 | 62/(2×56.06) | **Na mass balance, display** |
| NaSH → Na₂S (as Na₂O) | 1.1060 | 62/56.06 | **Sulfidity calc ONLY** |
| S in NaSH | 0.5720 | 32.065/56.06 | NaSH sizing from S deficit |
| NaOH → Na₂O | 0.775 | 62/(2×40) | Na mass balance, display |
| Na₂SO₄ → Na₂O | 0.4366 | 62/142.04 | Saltcake Na₂O equiv |
| gpm × g/L → lb/hr | 0.5007 | (3.785×60)/453.6 | Unit conversion |

**CRITICAL**: NaSH has **1 Na atom**. For "lb Na₂O added" (mass balance), use 0.5529.
The 1.1060 factor is ONLY for Na₂S sulfidity tracking (NaSH+NaOH→Na₂S equilibrium).
NaOH also has 1 Na → uses 62/(2×MW) pattern. Na₂SO₄ has 2 Na → uses 62/MW directly.

---

# 7. DEFAULT PARAMETERS (Pine Hill Mill)

## 7.1 BL Properties
- Flow: 340.53 gpm
- TDS: 69.1%
- Temperature: 253.5°F
- Na% (virgin): 19.39%
- S% (virgin): 4.01%
- K%: 1.58%

## 7.2 Production
- Semichem: 636.9 BDT/day (yield 70.19%)
- Pine: 1250.7 BDT/day (yield 56.94%)
- **Total: 1887.5 BDT/day**

## 7.3 Recovery Boiler
- Reduction Efficiency: 95%
- Ash Recycled: 7%
- Saltcake: 2227 lb/hr Na₂SO₄

## 7.4 Makeup Chemicals
- NaSH: 40% concentration, SG 1.29
- NaOH: 50% concentration, SG 1.52

## 7.5 Slaker/Recausticizing
- Causticity: 81%
- Lime: CaO 87.53%, CaCO₃ 1.96%, Inerts 9.46%
- Grits loss: 1% of lime feed

## 7.6 Dissolving Tank
- Weak Wash: ~753 gpm (solved analytically for GL TTA target)
- Shower: 60 gpm
- GL Target TTA: 7.4 lb/ft³
- Smelt Density: 110 lb/ft³

---

# 8. API ENDPOINTS

- `POST /api/calculate` - main calculation, pure (no side effects — trend logging removed)
- `POST /api/calculate/what-if` - what-if scenario comparison (Sulfidity Predictor uses this with override fields)
- `POST /api/calculate/sensitivity` - perturbation analysis
- `POST /api/trends` - explicitly save a trend point (from Sulfidity Predictor "Save to Trend" button)
- `GET /api/trends` - list trend points (hours filter)
- `PATCH /api/trends/{id}` - update lab sulfidity / notes on a trend point
- `DELETE /api/trends/{id}` - delete a trend point
- `GET/POST /api/snapshots` - save/load historical calculations
- `GET/POST /api/mills` - mill configuration management
- `POST /api/export/excel` - generate Excel report (.xlsx) from inputs+results
- `POST /api/export/pdf` - generate PDF report from inputs+results

## 8.1 Key Result Fields

### Causticizing (First-Principles)
| Field | Description |
|-------|-------------|
| `gl_na2co3_g_L` | Na₂CO₃ in GL (g Na₂O/L) — dead load to be causticized |
| `gl_na2co3_lb_hr` | Na₂CO₃ mass flow in GL (lb/hr) |
| `wl_naoh_slaker_g_L` | NaOH from slaker (g Na₂O/L) |
| `wl_na2co3_slaker_g_L` | Na₂CO₃ remaining after slaker (g Na₂O/L) |
| `final_wl_naoh_g_L` | Final WL NaOH after makeup (g Na₂O/L) |
| `final_wl_na2co3_g_L` | Final WL Na₂CO₃ after makeup (g Na₂O/L) |
| `causticizing_conversion_fraction` | x = CE / (2 - CE) |
| `lime_required_lb_hr` | Lime required for target CE (lb CaO/hr) |
| `lime_feed_lb_hr` | Actual lime feed (lb/hr) |
| `achieved_ce_pct` | Causticity achieved (should match input) |

### Dual-Constraint NaOH
| Field | Description |
|-------|-------------|
| `naoh_for_losses_lb_hr` | NaOH to cover Na losses (mass balance) |
| `naoh_for_ea_demand_lb_hr` | NaOH to cover EA deficit (if CE < 81%) |
| `naoh_constraint` | `'losses'` or `'EA_demand'` — which is binding |
| `ea_required_lb_hr` | Total EA required by digesters |
| `ea_from_slaker_lb_hr` | EA provided by slaker |
| `ea_deficit_lb_hr` | EA shortfall (if CE < baseline) |

### Na Inventory Tracking
| Field | Description |
|-------|-------------|
| `na_in_lb_hr` | Total Na entering (Saltcake + NaSH + NaOH) |
| `na_out_lb_hr` | Total Na leaving (losses) |
| `na_accumulation_lb_hr` | Na_in - Na_out |
| `na_balance_status` | `'steady_state'`, `'building_inventory'`, or `'depleting_inventory'` |

---

# 9. FRONTEND FEATURES

## 9.1 Input Pages
- Lab Data: WL/GL TTA, EA, AA (in **lb/ft³** — DCS units; converted to g/L before engine)
- BL Properties: Flow, TDS, temperature
- Production: Semichem/Pine rates
- Loss Table: 13 sources × S + Na₂O (editable)
- DCS Readings: Real-time values

## 9.2 Results Pages
- **Sulfidity Tab**: Current, latent, final, smelt sulfidity gauges
- **WL Quality Tab**: TTA, EA, AA, Na₂S concentrations (**lb/ft³ primary**, g/L secondary) + **Recausticizing Flow Diagram** (full circuit SVG: CTO/BL Feed → Smelt → DT → GL Clarifier → Slaker → WLC → Final WL, with volume balance check and WL produced-vs-demanded bar chart)
- **Makeup Tab**: NaSH/NaOH requirements in multiple units
- **Recovery Boiler Tab**: Alkali formation, BL composition tracking
- **Mass Balance Tab**: Na/S in/out tracking
- **Circuit Map Tab**: Visual flow diagram with all unit operations
- **Sensitivity Tab**: 8-scenario perturbation analysis
- **Export**: PDF and Excel export buttons in Results header (all 11 sections)

## 9.3 Scenarios Page (Tabbed)

### Tab 1: What-If (ScenarioBuilder)
What-if analysis with sliders for:
- Reduction Efficiency (85-99%)
- Target Sulfidity (25-35%)
- BL S% / BL Na%
- NCG S Loss, Washable S Loss, Washable Na Loss
- Causticity (70-90%)

### Tab 2: Sulfidity Predictor (SulfidityPredictor)
Sulfidity as **dependent variable** with 8 independent variable sliders:
- Reduction Efficiency, Causticity, Pine/Semichem Production, CTO, Saltcake
- NaSH (dry) and NaOH (dry) — **fixed values that bypass Secant solver and dual-constraint NaOH**
- NaSH/NaOH sliders initialize from base computed values (e.g., ~1358 / ~2120 lb/hr)
- "Predict" button runs what-if with `nash_dry_override_lb_hr` / `naoh_dry_override_lb_hr`
- Large sulfidity display (green/yellow/red vs target) + comparison table
- **"Save to Trend" button**: Explicitly saves prediction to trend history (`POST /api/trends`). No auto-logging — user controls when to save.
- **Trend chart** (`SulfidityTrend`): Rendered below tornado chart, shows all saved predictor points with model-vs-lab comparison. Click a point to enter lab sulfidity.
- **Tornado chart**: ±10% perturbation of each variable → sorted horizontal bars showing sulfidity sensitivity
  - 17 parallel API calls (1 main + 16 perturbations)
  - Blue bars = sulfidity decrease, Orange bars = sulfidity increase

## 9.4 Unit Convention: lb/ft³ Inputs, g/L Engine
- **Frontend inputs** (WL/GL TTA, EA, AA) are in **lb/ft³** (DCS units)
- `api.ts` → `convertInputsForApi()` multiplies by `16.01846` (lb/ft³ → g/L) before every engine API call
- **Engine** is entirely in **g/L** internally — zero backend changes needed
- **WL Quality results**: lb/ft³ primary column, g/L secondary (dimmed)
- Conversion: `g/L = lb/ft³ × 16.01846` | `lb/ft³ = g/L ÷ 16.01846`

## Frontend Key Types (lib/types.ts)
- `LossTable`: 13 sources, each with `{ s_lb_bdt, na_lb_bdt }`
- `LossDetailRow`: `{ source, s_lb_hr, s_lb_bdt, na2o_lb_hr, na2o_lb_bdt }`
- `WLQualityOutput`: TTA/AA/EA/Na2S (lb/ft³ primary, g/L secondary), sulfidity, WL flow, WL demand
- `UnitOperationRow`: stage-level Na/S tracking with tta_na2o_ton_hr, na2s_na2o_ton_hr, flow_gpm

---

# 10. MODEL VALIDATION

## 10.1 Test Coverage
- **126 total tests**, all passing
- 33 cell-by-cell validation tests vs Excel v4
- 17 Na/S mass balance tests (RE/CE correlation, loss table sensitivity, CTO sensitivity)
- 26 forward leg tests (fiberline, WBL mixer, evaporator, compound accounting)
- 23 mass balance closure tests (outer loop convergence, evaporator conservation, CTO, backward compat)
- 27 dissolving tank tests (WW flow solve, dregs filter, energy balance)

## 10.2 Validation Tolerances
| Metric | Tolerance |
|--------|-----------|
| Density | ±0.01 lb/gal |
| Sulfidity | ±0.001 (absolute) |
| Mass flows | ±10-200 lb/hr |
| BL Composition (outer loop) | <0.01% absolute |
| BL Na%/S% vs Lab | <0.05 pts absolute |
| DT TTA balance | <0.5% error |

## 10.3 Sulfidity Targeting Accuracy

With the **Secant method**, final sulfidity converges to within **0.5%** of target.

```
Target: 29.4%
Result: 29.4% ± 0.15% (typical)
Iterations: 3-5
```

No workaround needed — set target sulfidity directly.

---

# 11. DESIGN PRINCIPLES

1. **Exact Stoichiometry**: Uses exact MW constants, not rounded values
2. **Dual-Loop Convergence**: Outer loop closes mass balance, inner loop solves circular reference
3. **Immutable Results**: Dataclass results throughout for testability
4. **No Global State**: All state passed explicitly between functions
5. **Excel Traceability**: Cell references in code comments
6. **Unified Loss Table**: Single 13×2 table replaces 3 disconnected mechanisms
7. **Forward Leg Closure**: WL → Digesters → WBL → Evap → SBL → RB

---

# 12. FILES REFERENCE

## Backend Engine (`/backend/app/engine/`)
| File | Lines | Purpose |
|------|-------|---------|
| orchestrator.py | 1148 | Master solver, dual-loop convergence |
| recovery_boiler.py | 230 | RB chemistry, alkali formation |
| slaker_model.py | 350+ | Energy/water/mass balance |
| chemical_charge.py | 320 | Fiberline demand, WLC |
| dissolving_tank.py | 250+ | Smelt dissolution, WW flow solve, DT energy balance |
| dregs_filter.py | 80+ | Dregs filter mass balance, filtrate return to WW tank |
| makeup.py | 145 | NaSH/NaOH sizing |
| s_retention.py | 176 | Loss table, retention factors |
| fiberline.py | 230 | BL generation |
| evaporator.py | 75 | Water removal |
| constants.py | 280 | MW, CONV, DEFAULTS |

## Tests (`/backend/tests/`)
| File | Tests | Purpose |
|------|-------|---------|
| test_validation_vs_excel.py | 33 | Cell-by-cell Excel validation |
| test_mass_balance_closure.py | 23 | Outer loop convergence, evaporator conservation, CTO, backward compat |
| test_forward_leg.py | 26 | Fiberline, WBL mixer, evaporator, compound accounting |
| test_na_s_mass_balance.py | 17 | Na/S balance, RE/CE correlation, loss table sensitivity, CTO sensitivity |
| test_dissolving_tank.py | 27 | WW flow solve, dregs filter, DT energy balance |

---

# 13. DEPLOYMENT

## 13.1 Production (Cloud)

| Component | Platform | URL |
|-----------|----------|-----|
| Frontend | Vercel (free) | https://sulfidity-predictor.vercel.app |
| Backend | Render (Starter, $7/mo) | https://sulfidity-predictor.onrender.com |
| Source Code | GitHub (private) | https://github.com/pifanohey/sulfidity-predictor |

- **Auto-deploy**: Push to `main` branch → both services redeploy automatically
- **Frontend** proxies API calls to backend via `next.config.js` rewrites (`API_URL` env var in Vercel)
- **Backend** health check: `GET /api/health`
- **Database**: SQLite (ephemeral on Render — resets on deploy)

## 13.2 Local Development

```bash
./start.sh                    # Backend :8005, Frontend :3005
# Or manually:
cd backend && python3 -m uvicorn app.main:app --reload --port 8005
cd frontend && npm run dev    # pinned to port 3005
```

## 13.3 Tests

```bash
cd backend && python3 -m pytest tests/ -v    # 126 tests, all passing
```

---

# 14. COMPLETED FIXES (V1 Final State)

All fixes below are implemented and verified in the current codebase:

| Fix | Impact |
|-----|--------|
| DT mass balance closure | TTA error: 17.8% → 0.2% (WW flow solved analytically) |
| NaSH Na₂O display | Corrected to `0.5529` (1 Na atom, not 2) |
| Fiberline TDS | Removed `/ 3.785` unit bug (WBL TDS: 33% → 20.6%) |
| NCG double-count | Removed NCG S subtraction from fiberline (BL Na% gap: 0.03 pts, S% gap: 0.02 pts) |
| Net S balance | Includes NaSH S input, correct sign convention (+105 lb/hr, near steady state) |
| Outer loop skip (NaSH override) | Prevents runaway BL S% feedback in Sulfidity Predictor mode |
| Grits relocation | Moved from GL clarifier to slaker (correct process location) |
| WLC NaOH mass tracking | WL EA gap: 2.34 → 0.03 g/L |
| EA deficit formula | Uses `CE × (TTA - Na₂S)` not `CE × AA` |
| CE flow-dependent washable soda | ~5.5 lb NaOH/hr per 1% CE (75-87% range) |
| CTO delta fix | CTO slider now correctly affects sulfidity in Predictor/What-If modes |
| Latent sulfidity fix | Strong BL uses `s_ret_strong` not `s_ret_weak` |
| Outer loop enabled | Converges in 2 iterations (tolerance 0.01%), matches lab within 0.03 pts |

---

# 15. DOCUMENTATION MAP

| File | Audience | Purpose |
|------|----------|---------|
| `CLAUDE.md` (root) | AI agents / developers | Master technical reference (this file) |
| `docs/ENGINE_REFERENCE.md` | AI agents / developers | Engine module details, gotchas, debugging |
| `docs/MODEL_DOCUMENTATION.md` | Process engineers | User guide, chemistry, solver architecture |
| `docs/PRD_SULFIDITY_PREDICTOR.md` | Stakeholders | Product requirements document |
| `docs/SULFIDITY_MODEL_TECHNICAL_DOCUMENTATION.md` | Management | Technical overview |
| `docs/Deployment_Options_for_IT.md` | IT | Cloud/on-prem deployment options |
| `docs/MILL_ONBOARDING_GUIDE.md` | Implementation | Multi-mill deployment guide |
| `docs/RE_SENSITIVITY_AUDIT_REPORT.md` | Engineering | RB sensitivity audit trail |
| `docs/DEPLOYMENT_README.md` | End users | How to access the deployed app |

---

*Sulfidity Predictor v1.0 - Pine Hill Mill*
