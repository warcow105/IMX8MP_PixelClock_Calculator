import sys
import fractions
import math

def calculate_hdmi_phy_registers_final(target_pixclk):
    F_REF = 24000000
    tclk5x = target_pixclk * 5
    
    s_options = {1: 0x0, 2: 0x1, 4: 0x3, 6: 0x5, 8: 0x7, 10: 0x9, 12: 0xb, 16: 0xf}
    
    # NXP's hidden VCO limits
    vco_min = 2000000000
    vco_max = 3000000000
    
    best_S = None
    
    # 1. Pass 1: Hunt for an exact Integer mode match inside the VCO bounds
    for s in s_options.keys():
        vco = tclk5x * s
        if vco_min <= vco <= vco_max:
            if vco % F_REF == 0:
                best_S = s
                break
                
    # 2. Pass 2: If no integer match, just pick the smallest S that puts VCO > 2.0 GHz
    if not best_S:
        for s in s_options.keys():
            vco = tclk5x * s
            if vco_min <= vco <= vco_max:
                best_S = s
                break
                
    # 3. Pass 3: Edge case fallback for extreme pixel clocks (e.g. 162 MHz)
    if not best_S:
        for s in reversed(list(s_options.keys())):
            if (tclk5x * s) <= vco_max:
                best_S = s
                break
    if not best_S:
        best_S = 1

    # Extract chosen values
    S = best_S
    vco_target = tclk5x * S
    M = int(vco_target // F_REF)
    sdm_k_en = 1 if (vco_target % F_REF) != 0 else 0
    K, LC = 0, 0
    
    # SDC Generator Settings (N, Ksub, LCsub)
    N_reg_map = {4: 0b000, 5: 0b001, 6: 0b010, 7: 0b100, 8: 0b101, 9: 0b110}
    N_int = 1
    Ksub, LCsub = 0, 0
    
    if sdm_k_en:
        main_frac = fractions.Fraction((vco_target / F_REF) - M).limit_denominator(127)
        K, LC = main_frac.numerator, main_frac.denominator
        
        # Force SDC target ~384 MHz
        N_eff = M / 16.0
        N_int = math.ceil(N_eff)
        sub_frac = fractions.Fraction(N_int - N_eff).limit_denominator(63)
        Ksub, LCsub = sub_frac.numerator, sub_frac.denominator

    # Register Formatting
    reg2 = M & 0xFF 
    reg3 = (s_options[S] << 4) | N_reg_map.get(N_int, 0)
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
