/**
 * Liquor concentration unit conversion utilities.
 *
 * Internal state always stores concentrations in lb/ft³.
 * Display converts to the mill's preferred unit (lb/ft³ or lb Na₂O/gal).
 */

export type LiquorUnit = "lb_per_ft3" | "lb_per_gal";

/** 1 ft³ = 7.48052 US gallons */
const FT3_PER_GAL = 7.48052;

/** Display label for the unit. */
export function getLiquorUnitLabel(unit: LiquorUnit): string {
  return unit === "lb_per_gal" ? "lb Na₂O/gal" : "lb/ft³";
}

/** Convert from internal lb/ft³ to display unit. */
export function toDisplay(lbFt3: number, unit: LiquorUnit): number {
  return unit === "lb_per_gal" ? lbFt3 / FT3_PER_GAL : lbFt3;
}

/** Convert from display unit back to internal lb/ft³. */
export function fromDisplay(displayValue: number, unit: LiquorUnit): number {
  return unit === "lb_per_gal" ? displayValue * FT3_PER_GAL : displayValue;
}

/** Convert from g/L to display unit. */
export function gLToDisplay(gL: number, unit: LiquorUnit): number {
  const GL_TO_LB_FT3 = 1 / 16.01846;
  const lbFt3 = gL * GL_TO_LB_FT3;
  return toDisplay(lbFt3, unit);
}
