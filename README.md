## Pixel clock and DRM mode calculators for the NXP IMX8MP
The DRM mode calculator requires cvt to be installed and in the path.  It will output an entry to be added to `drm_edid.c` in the linux-imx kernel.
### You will probably want to add a printk in the function `imx8mp_hdmi_check_clk_rate` from `dw_hdmi-imx.c` to be sure what pixel clock it is requesting since apparently if the screen reports a frequency, your drm mode might be ignored.

```
static bool imx8mp_hdmi_check_clk_rate(struct imx_hdmi *hdmi, int rate_khz)
{
  struct clk *clk_pix;
  int rate = rate_khz * 1000;
  
  clk_pix = devm_clk_get(hdmi->dev, "pix");

  /* skip check rate if no pix clk got */
	if (IS_ERR(clk_pix))
		return true;

  /* THIS IS THE SECTION I MODIFIED FOR DEBUG */
	/* Check hdmi phy pixel clock support rate */
	long actual_rate = clk_round_rate(clk_pix, rate);
	if (rate != actual_rate)
	{
		printk("MIKE:DW_HDMI_IMX:CHK_CLK:NO_MATCH= req: %lu act: %lu\n", rate, actual_rate);
		return false;
	}
	return true;
}
```
Use the PLL calculator to generate the entry to add to `phy_pll_cfg` in `phy-fsl-samsung-hdmi.c`

## Example for my weird screen
```
python ./drm_mode_calc.py 1920 540 60 -r
--- 1. Original CVT Output ---
# 1920x540 59.56 Hz (CVT) hsync: 33.29 kHz; pclk: 69.25 MHz
Modeline "1920x540R"   69.25  1920 1968 2000 2080  540 543 553 559 +hsync -vsync

--- 2. Corrected DRM_MODE Entry ---
	{ DRM_MODE("1920x540", DRM_MODE_TYPE_DRIVER | DRM_MODE_TYPE_PREFERRED, 69763,
		   1920, 1968, 2000, 2080, 0,
		   540, 543, 553, 559, 0,
		   DRM_MODE_FLAG_PHSYNC | DRM_MODE_FLAG_NVSYNC) },

--- 3. Target Pixel Clock (For PHY PLL Script) ---
69.763 MHz
```
### But my screen actually wants 69.76 according to debug, so I will add both as a fallback.
```
python imx8_hdmi_pll_calc.py 69.763
--- i.MX8MP Samsung HDMI PHY PLL Calculator ---

Target Pixel Clock : 69.763 MHz
Calculated C Array : { 0x57, 0x58, 0xb6, 0x0b, 0x80, 0x40 }

Kernel Struct Entry:
	{
		.pixclk = 69763000,
		.pll_div_regs = { 0x57, 0x58, 0xb6, 0x0b, 0x80, 0x40 },
	},
```
```
python imx8_hdmi_pll_calc.py 69.76
--- i.MX8MP Samsung HDMI PHY PLL Calculator ---

Target Pixel Clock : 69.76 MHz
Calculated C Array : { 0x57, 0x58, 0x85, 0x01, 0x80, 0x40 }

Kernel Struct Entry:
	{
		.pixclk = 69760000,
		.pll_div_regs = { 0x57, 0x58, 0x85, 0x01, 0x80, 0x40 },
	},
```
