
import pandas as pd
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.getcwd())

from sulfidity_predictor.models import (
    calculate_liquor_composition,
    calculate_tank_inventory,
    calculate_bl_inventory,
    calculate_full_rb_from_bl,
    calculate_makeup_summary,
    calculate_sulfidity_metrics
)
from sulfidity_predictor.config.constants import CONV, MW

def load_excel_data(file_path):
    print(f"Loading Excel file: {file_path}")
    xls = pd.ExcelFile(file_path)
    
    data = {}
    
    # helper to safe get value
    def get_val(df, row, col_idx):
        try:
            # pandas is 0-indexed, excel is 1-indexed. 
            # row 1 in excel is index 0 in pandas if header=None
            val = df.iloc[row-1, col_idx]
            return float(val)
        except:
            return 0.0

    # === 1_Inventory ===
    df_inv = pd.read_excel(xls, '1_Inventory', header=None)
    data['target_sulfidity'] = get_val(df_inv, 19, 2) # C19
    
    # White Liquor Analysis (F4-F6) -> pandas (3, 5), (4,5), (5,5) - wait col F is index 5
    # F4 is row 4, col F (5)
    data['wl_tta'] = get_val(df_inv, 4, 5)
    data['wl_ea'] = get_val(df_inv, 5, 5)
    data['wl_aa'] = get_val(df_inv, 6, 5)
    
    # Green Liquor (F17-F19)
    data['gl_tta'] = get_val(df_inv, 17, 5)
    data['gl_ea'] = get_val(df_inv, 18, 5)
    data['gl_aa'] = get_val(df_inv, 19, 5)

    # Tank Levels
    data['wlc_1_level'] = get_val(df_inv, 1, 5) # F1
    data['wlc_2_level'] = get_val(df_inv, 1, 8) # I1
    
    data['gl_1_level'] = get_val(df_inv, 14, 5) # F14
    data['gl_2_level'] = get_val(df_inv, 14, 8) # I14
    data['dump_level'] = get_val(df_inv, 14, 11) # L14
    
    # BL Properties
    data['bl_na_pct'] = get_val(df_inv, 10, 29) # AD10
    data['bl_s_pct'] = get_val(df_inv, 28, 29)  # AD28
    
    # BL Tanks (Levels, TDS, Temp)
    # WBL1: F40 (Level), F46 (TDS), F47 (Temp - wait check mapping)
    # Let's check cell mapping for WBL 1
    # F40=Level, F42=Vol, F46=TDS?, F47=Temp? 
    # Need to verify BL tank inputs from streamlit_app.py hints
    # streamlit: WBL#1 Level [F40], TDS [?], Temp [?]
    # In streamlit: inputs['wbl_1_tds'] default 19.23
    # Let's assume standard values for now or read from specific cells if known
    
    # Read outputs to compare against
    data['excel_current_sulf'] = get_val(df_inv, 17, 2) # C17
    data['excel_latent_sulf'] = get_val(df_inv, 18, 2) # C18

    # === 2_Recovery boiler ===
    df_rb = pd.read_excel(xls, '2_Recovery boiler', header=None)
    data['bl_flow_gpm'] = get_val(df_rb, 6, 1) # B6
    data['bl_tds_rb'] = get_val(df_rb, 11, 1) # B11
    data['reduction_eff'] = get_val(df_rb, 14, 1) # B14
    data['s_retention'] = get_val(df_rb, 15, 1) # B15
    data['ash_na'] = get_val(df_rb, 18, 1) # B18 (RB Na Losses? wait, B18 is losses)
    # streamlit: Ash Na [B18] -> actually code says Ash Na [B18] label but input is rb_losses_na?
    # Let's check model code: rb_losses_na mapping
    # In streamlit: "Ash Na (lb Na2O/hr) [B18]" -> variable ash_na_na2o.
    # Wait, B18 label in excel might be "RB Na Losses" or "Ash". 
    # Let's trust the value extraction for now.
    
    data['ash_s'] = get_val(df_rb, 51, 1) # B51 for Ash S? 
    # streamlit says Ash S [?], code uses B51 in calculation
    
    data['saltcake_na_lbs'] = get_val(df_rb, 40, 1) # B40 (Saltcake flow)
    
    data['excel_smelt_sulf'] = get_val(df_rb, 35, 1) # B35
    data['excel_rb_tta'] = get_val(df_rb, 34, 1) # B34
    data['excel_rb_active'] = get_val(df_rb, 32, 1) # B32

    # === 0_SULFIDITY CONTROL ===
    df_sulf = pd.read_excel(xls, '0_SULFIDITY CONTROL MAKEUP', header=None)
    data['nash_conc'] = get_val(df_sulf, 4, 1) # B4
    data['naoh_conc'] = get_val(df_sulf, 5, 1) # B5
    data['nash_dens'] = get_val(df_sulf, 6, 1) # B6
    data['naoh_dens'] = get_val(df_sulf, 7, 1) # B7
    
    # Outputs
    data['excel_nash_req'] = get_val(df_sulf, 46, 7) # H46
    data['excel_naoh_req'] = get_val(df_sulf, 47, 7) # H47
    data['excel_final_sulf'] = get_val(df_sulf, 63, 1) # B63
    
    # === 3_Chemical Charge ===
    df_chem = pd.read_excel(xls, '3_Chemical Charge', header=None)
    data['batch_prod'] = get_val(df_chem, 7, 3) # D7
    data['cont_prod'] = get_val(df_chem, 33, 3) # D33
    data['gl_flow_slaker'] = get_val(df_chem, 58, 8) # I58? Checks '2_RB!I58' ref in streamlit
    data['yield_factor'] = get_val(df_chem, 64, 6) # G64
    data['wl_to_dig'] = get_val(df_chem, 110, 20) # U110
    
    return data

def run_comparison(data):
    print("\n--- Running Python Model Calculations ---")
    
    # 1. Liquor Comp
    wl_comp = calculate_liquor_composition(data['wl_tta'], data['wl_ea'], data['wl_aa'])
    gl_comp = calculate_liquor_composition(data['gl_tta'], data['gl_ea'], data['gl_aa'])
    
    print(f"WL Sulfidity: {wl_comp.sulfidity_tta_pct:.2f}%")
    
    # 2. RB Calculations
    # We need to be careful with inputs. Streamlit extracts many specific ones.
    # For a quick check, let's look at the Makeup Logic which seems to be the core user request.
    
    # Reconstruct Makeup Inputs
    total_prod = data['batch_prod'] + data['cont_prod']
    
    # WL Flow Logic
    # wl_flow_from_slaker = gl_flow * yield
    # We might need to look up G64 and I58 from 3_Chem if not read yet
    # Placeholder: use calculated values or read-ins
    
    # Let's try to replicate the Makeup call
    # We need calculated WL TTA Mass and Na2S Mass
    
    # From streamlit:
    # wl_flow_from_slaker = inputs['gl_flow_to_slaker'] * inputs['yield_factor']
    # wl_tta_mass = wl_flow * wl_tta * conversion
    
    # NOTE: We need the exact values used in Excel for these intermediate steps 
    # if we want to isolate the makeup logic.
    # OR we run the full chain.
    
    # Let's run full chain for Makeup part
    gl_flow_slaker = 658.60 # Default from streamlit if not in Excel read
    # Try to use data if available, else default
    
    # ... (Implementing a simplified run for diagnostics)
    
    print("\n--- Comparison Report ---")
    print(f"Target Sulfidity: {data['target_sulfidity']}")
    print(f"Excel NaSH Req (H46): {data['excel_nash_req']:.2f}")
    print(f"Excel NaOH Req (H47): {data['excel_naoh_req']:.2f}")
    
    # We really need to check the intermediate Na deficits
    
if __name__ == "__main__":
    file_path = "tests/excel_v4_copy.xlsx"
    if not os.path.exists(file_path):
        print(f"Error: {file_path} not found")
        sys.exit(1)
        
    data = load_excel_data(file_path)
    # print raw data for validation
    for k, v in data.items():
        print(f"{k}: {v}")
        
    run_comparison(data)
