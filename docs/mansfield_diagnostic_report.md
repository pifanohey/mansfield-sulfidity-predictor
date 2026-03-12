# Mansfield Diagnostic Report

## WinGEMS Targets
| Parameter | WinGEMS | Model (before fix) | Model (after CTO fix) | Gap |
|---|---|---|---|---|
| NaSH dry (lb/hr) | 1,762 | 2,226 (+26.3%) | 2,054 (+16.6%) | +292 |
| NaOH dry (lb/hr) | 4,634 | 7,108 (+53.4%) | 6,285 (+35.6%) | +1,651 |

## Bug Fixed: CTO NaOH Na Return Not Subtracted from Na Deficit

**Root cause:** The CTO tall oil acidulation adds NaOH (193 lb/ton CTO × 117.5 TPD). This Na returns to the system via brine in the WBL mixer. But the Na deficit calculation for NaOH sizing did not subtract this Na input.

**Impact:**
- CTO NaOH = 945 lb NaOH/hr → 543 lb element Na/hr → 732 lb Na₂O/hr
- This was causing a 732 lb Na₂O/hr surplus in the Na balance
- NaOH was oversized by ~823 lb/hr (from 7,108 to 6,285)
- NaSH also reduced by ~172 lb/hr (coupled effect: less NaOH → lower TTA → higher sulfidity → less NaSH)

**Fix:** `orchestrator.py` lines 398-404: Added `cto_na_as_na2o` subtraction in Na deficit:
```python
cto_na_as_na2o = cto_na_lb_hr * CONV['Na_to_Na2O']
na_deficit = max(0, adjusted_na_losses - saltcake_na - na_from_nash - cto_na_as_na2o)
```

## Remaining Gap Analysis: Loss Table Na Values

NaOH is driven by the **losses constraint** (6,285 lb/hr) not EA demand (1,700 lb/hr).

| Metric | Our Model | WinGEMS Implied |
|---|---|---|
| Total Na₂O losses | 61.34 lb/BDT | 48.62 lb/BDT |
| Na₂O losses (lb/hr) | 6,683 | 5,298 |
| Excess | +12.72 lb Na₂O/BDT (+20.7%) | — |

### Largest Na Loss Sources (Mansfield)
| Source | Na₂O (lb/BDT) | % of Total | Notes |
|---|---|---|---|
| Pulp washable soda | 29.16 | 47.5% | Brownstock wash loss — largest single source |
| RB ash (ESP) | 8.07 | 13.2% | ESP dust losses |
| Pulp bound soda | 7.07 | 11.5% | Chemically bound Na in fiber |
| RB dump tank | 5.37 | 8.8% | — |
| Recaust spill | 4.25 | 6.9% | Recausticizing area spills |
| Grits | 3.09 | 5.0% | Slaker grits discharge |
| All others | 4.33 | 7.1% | — |

### Possible Explanations for Excess
1. **Loss table values may be too high** — the data came from the Mansfield Input Collection spreadsheet, but WinGEMS may compute losses dynamically rather than using static lb/BDT values
2. **Pulp washable soda (29.16)** is 58% higher than Pine Hill (18.5) — this is the single biggest contributor to the gap
3. **RB ash + dump tank (13.44)** together are larger than Pine Hill's RB ash (2.8) — Mansfield's NORAM sodium recovery system may handle ash differently

### To Close the NaOH Gap
Need to reduce Na₂O losses by ~12.72 lb/BDT. Most likely adjustment: reduce `pulp_washable_soda_na` from 29.16 to ~16.44 lb Na₂O/BDT (or distribute reduction across multiple sources).

## Spreadsheet vs Config Verification

All Mansfield Input Collection spreadsheet values match mansfield.json config. Minor corrections applied:
- `causticity_pct`: 77.7 → 77.72 (matches spreadsheet exactly)

## Mansfield vs Pine Hill Configuration Comparison

```
                    PINE HILL (V1)              MANSFIELD (V2)
                    ═══════════════             ═══════════════
FIBERLINES          2 lines                     3 lines
  Pine              1251 BDT/d, 56.94% yield    Kraft #1: 1421 BDT/d, 56.72% yield
  Semichem          637 BDT/d, 70.19% yield     Kraft #2: 411 BDT/d, 57.77% yield
                                                Semichem: 783 BDT/d, 72.00% yield
  Total             1,888 BDT/day               2,615 BDT/day (+38.5%)

RECOVERY BOILERS    1 RB                        2 RBs
  RB1               340.5 gpm, 95.0% RE         243.6 gpm, 83.7% RE
  RB2               —                           243.6 gpm, 81.4% RE
  Total BL flow     340.5 gpm                   487.2 gpm (+43%)

DISSOLVING TANKS    1 DT                        2 DTs
  DT1               625 gpm WW                  387 gpm WW
  DT2               —                           387 gpm WW
  Total WW          625 gpm                     774 gpm (+24%)

BLACK LIQUOR        Na 19.39%, S 4.01%          Na 19.80%, S 4.84%
                    TDS 69.1%                   TDS 72.0%

MAKEUP CHEMICAL     NaSH + saltcake(2227 lb/hr) NaSH only (no saltcake)

CTO                 26.7 TPD, 360 lb H₂SO₄/ton 117.5 TPD, 391 lb H₂SO₄/ton
                    No NaOH return              193 lb NaOH/ton (Na return!)

RECAUSTICIZING      CE 81%, lime 1100°F         CE 77.72%, lime 520°F
                    Grits 1.0%                  Grits 4.5%

WL ANALYSIS         TTA 117.4, EA 86.0 g/L     TTA 133.1, EA 95.3 g/L

GL ANALYSIS         TTA 117.5, EA 27.7 g/L     TTA 132.9, EA 26.9 g/L

TARGET SULFIDITY    29.4%                       25.8%

LOSS TABLE          S=16.6, Na=42.8 lb/BDT      S=15.9, Na=61.3 lb/BDT
```
