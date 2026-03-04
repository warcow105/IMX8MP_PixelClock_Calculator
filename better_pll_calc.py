import sys
import fractions
import math

def calculate_hdmi_phy_registers_final(target_pixclk):
    F_REF = 24000000
    tclk5x = target_pixclk * 5
    
    # FIX 1: Map S strictly to the Linux driver's REG21 configuration bands
    S = 1
    if 22250000 <= target_pixclk <= 33750000: S = 16
    elif 35000000 <= target_pixclk <= 40000000: S = 12
    elif 43200000 <= target_pixclk <= 47500000: S = 10
    elif 50349650 <= target_pixclk <= 63500000: S = 8
    elif 67500000 <= target_pixclk <= 90000000: S = 6
    elif 94000000 <= target_pixclk <= 148500000: S = 4
    elif 154000000 <= target_pixclk <= 297000000: S = 2
    
    vco_target = tclk5x * S
    M_float = vco_target / F_REF
    M = int(M_float)
    frac = M_float - M
    
    # FIX 2: Float precision tolerance to avoid false fractional modes
    sdm_k_en = 1 if frac > 1e-9 else 0
    K, LC = 0, 0
    
    s_options = {1: 0x0, 2: 0x1, 4: 0x3, 6: 0x5, 8: 0x7, 10: 0x9, 12: 0xb, 16: 0xf}
    N_reg_map = {4: 0b000, 5: 0b001, 6: 0b010, 7: 0b100, 8: 0b101, 9: 0b110}
    N_int = 1
    Ksub, LCsub = 0, 0
    
    if sdm_k_en:
        main_frac = fractions.Fraction(frac).limit_denominator(127)
        K, LC = main_frac.numerator, main_frac.denominator
        
        # Force SDC target ~384 MHz
        N_eff = M / 16.0
        N_int = math.ceil(N_eff)
        sub_frac_val = N_int - N_eff
        
        # FIX 3: Safely zero out LCsub when the sub-fraction is exactly 0
        if sub_frac_val > 1e-9:
            sub_frac = fractions.Fraction(sub_frac_val).limit_denominator(63)
            Ksub, LCsub = sub_frac.numerator, sub_frac.denominator
        else:
            Ksub, LCsub = 0, 0

    # Register Formatting
    reg2 = M & 0xFF 
    reg3 = (s_options.get(S, 0) << 4) | N_reg_map.get(N_int, 0)
    reg4 = (sdm_k_en << 7) | (LC & 0x7F)
    reg5 = K & 0x7F
    reg6 = (1 << 7) | (LCsub & 0x3F) if sdm_k_en else 0x80
    reg7 = (sdm_k_en << 6) | (Ksub & 0x3F)

    print({"Target_PixClk": target_pixclk, "VCO": vco_target, "M": M, "S": S})
    return [reg2, reg3, reg4, reg5, reg6, reg7]

if __name__ == "__main__":
    print("--- i.MX8MP Samsung HDMI PHY PLL Calculator ---")
    
    if len(sys.argv) > 1:
        try:
            pclk = float(sys.argv[1])
        except ValueError:
            print("Usage: python3 hdmi_pll_calc.py [pixel_clock_in_mhz]")
            sys.exit(1)
    else:
        try:
            pclk = float(input("Enter Target Pixel Clock in MHz (e.g. 69.76): "))
        except ValueError:
            print("Invalid input.")
            sys.exit(1)

    regs = calculate_hdmi_phy_registers_final(int(pclk * 1000000))
    hex_regs = [f"0x{r:02x}" for r in regs]
    
    print(f"\nTarget Pixel Clock : {pclk} MHz")
    print(f"Calculated C Array : {{ {', '.join(hex_regs)} }}")
    print(f"\nKernel Struct Entry:")
    print("\t{")
    print(f"\t\t.pixclk = {int(pclk * 1000000)},")
    print(f"\t\t.pll_div_regs = {{ {', '.join(hex_regs)} }},")
    print("\t},")
