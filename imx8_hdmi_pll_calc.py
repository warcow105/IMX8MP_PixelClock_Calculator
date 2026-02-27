#!/usr/bin/env python3
import sys
from fractions import Fraction

def calculate_hdmi_pll(pclk_mhz):
    # The reference clock on the i.MX8MP is fixed at 24 MHz
    Fref = 24.0

    # Post-divider ranges mapped to the NXP driver's lookup table bands
    if 22.25 <= pclk_mhz <= 33.75:
        div = 0xf
    elif 35.0 <= pclk_mhz <= 40.0:
        div = 0xb
    elif 43.2 <= pclk_mhz <= 47.5:
        div = 0x9
    elif 50.34965 <= pclk_mhz <= 63.5:
        div = 0x7
    elif 67.5 <= pclk_mhz <= 90.0:
        div = 0x5
    elif 94.0 <= pclk_mhz <= 148.5:
        div = 0x3
    elif 154.0 <= pclk_mhz <= 297.0:
        div = 0x1
    else:
        print(f"Warning: {pclk_mhz} MHz is out of known bounds, defaulting to div=0x1")
        div = 0x1

    # 'S' is the true multiplier derived from the 'div' bitfield
    S = div + 1

    # Calculate the target VCO frequency and the Effective Multiplier
    Fvco = pclk_mhz * 5 * S
    M_eff = Fvco / Fref

    # Separate the integer multiplier (M) and the fractional component
    M = int(M_eff)
    frac = M_eff - M

    # The hardware only supports up to a 7-bit denominator (max 127)
    # We find the closest exact fraction that fits into the registers
    f = Fraction(frac).limit_denominator(127)
    K = f.numerator
    L = f.denominator

    # PHY_REG2: Integer multiplier
    reg2 = M
    
    # PHY_REG3: Post divider (PMS_S) and default SDC clocking
    # Bits [7:4] = div, Bit 3 = 1 (div2), Bits [2:0] = 0 (4/4)
    reg3 = (div << 4) | 0x08
    
    # PHY_REG4 / PHY_REG5: Fractional Logic
    if K > 0:
        reg4 = 0x80 | L  # Bit 7 (0x80) enables the fractional Sigma-Delta Modulator
                         # Bits 6-0 hold the Denominator (L)
        reg5 = K         # Numerator (K)
    else:
        reg4 = 0x00      # Integer mode (Fractional Modulator Disabled)
        reg5 = 0x00
    
    # PHY_REG6 / PHY_REG7: Additional Sigma-Delta Control
    # These are locked to standard defaults for basic video timings
    reg6 = 0x80
    reg7 = 0x40

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
        
    regs = calculate_hdmi_pll(pclk)
    hex_regs = [f"0x{r:02x}" for r in regs]
    
    print(f"\nTarget Pixel Clock : {pclk} MHz")
    print(f"Calculated C Array : {{ {', '.join(hex_regs)} }}")
    print(f"\nKernel Struct Entry:")
    print("\t{")
    print(f"\t\t.pixclk = {int(pclk * 1000000)},")
    print(f"\t\t.pll_div_regs = {{ {', '.join(hex_regs)} }},")
    print("\t},")
