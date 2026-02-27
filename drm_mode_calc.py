#!/usr/bin/env python3
import subprocess
import sys
import argparse

def generate_drm_mode(width, height, refresh, reduced_blanking=False):
    # Prepare the cvt command
    cmd = ['cvt', str(width), str(height), str(refresh)]
    if reduced_blanking:
        cmd.append('-r')
    
    # Run standard cvt tool
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        print("Error: 'cvt' command not found. Ensure the xserver-xorg-core package is installed.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(f"Error running cvt: {e}")
        sys.exit(1)

    # Parse the output
    lines = result.stdout.strip().split('\n')
    modeline = ""
    for line in lines:
        if line.strip().startswith("Modeline"):
            modeline = line.strip()
            break
            
    if not modeline:
        print("Failed to parse cvt output.")
        sys.exit(1)

    # Example Modeline format:
    # Modeline "1920x540_60.00"   69.75  1920 1968 2000 2080  540 543 548 559 -hsync +vsync
    parts = modeline.split()
    
    # Extract structural timings
    hdisplay = int(parts[3])
    hsync_start = int(parts[4])
    hsync_end = int(parts[5])
    htotal = int(parts[6])
    
    vdisplay = int(parts[7])
    vsync_start = int(parts[8])
    vsync_end = int(parts[9])
    vtotal = int(parts[10])
    
    # Parse sync flags
    flags_str = parts[11:]
    drm_flags = []
    for f in flags_str:
        if f == "+hsync":
            drm_flags.append("DRM_MODE_FLAG_PHSYNC")
        elif f == "-hsync":
            drm_flags.append("DRM_MODE_FLAG_NHSYNC")
        elif f == "+vsync":
            drm_flags.append("DRM_MODE_FLAG_PVSYNC")
        elif f == "-vsync":
            drm_flags.append("DRM_MODE_FLAG_NVSYNC")
            
    if not drm_flags:
        # Default flags if none provided
        drm_flags = ["DRM_MODE_FLAG_NHSYNC", "DRM_MODE_FLAG_NVSYNC"]
        
    flags_joined = " | ".join(drm_flags)
    
    # --- The Fix: Calculate exact pixel clock ---
    # Standard CVT outputs a slightly rounded pixel clock which fails strict checks. 
    # DRM calculates the target refresh rate exactly based on the blanking totals. 
    # We reverse-engineer the perfect clock to match the requested integer refresh rate.
    exact_pclk_hz = htotal * vtotal * refresh
    pclk_khz = int(exact_pclk_hz / 1000)
    pclk_mhz = exact_pclk_hz / 1000000.0

    # Format the C macro
    mode_name = f"{width}x{height}"
    macro = f"""\t{{ DRM_MODE("{mode_name}", DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED, {pclk_khz},
\t\t   {hdisplay}, {hsync_start}, {hsync_end}, {htotal}, 0,
\t\t   {vdisplay}, {vsync_start}, {vsync_end}, {vtotal}, 0,
\t\t   {flags_joined}) }},"""

    print("--- 1. Original CVT Output ---")
    print(result.stdout.strip())
    
    print("\n--- 2. Corrected DRM_MODE Entry ---")
    print(macro)
    
    print(f"\n--- 3. Target Pixel Clock (For PHY PLL Script) ---")
    print(f"{pclk_mhz:.3f} MHz")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate DRM_MODE macro from cvt")
    parser.add_argument("width", type=int, help="Resolution width")
    parser.add_argument("height", type=int, help="Resolution height")
    parser.add_argument("refresh", type=int, help="Refresh rate (e.g. 60)")
    parser.add_argument("-r", "--reduced", action="store_true", help="Use reduced blanking")
    
    args = parser.parse_args()
    generate_drm_mode(args.width, args.height, args.refresh, args.reduced)
