import sys, os
sys.path.insert(0, os.getcwd())
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import klayout.lay as lay
import klayout.db as kdb
import kfactory as kf
import gdsfactory as gf
from gdsfactory.pdk import get_layer_views
from gdsfactory.config import GDSDIR_TEMP
import ltoi300

def render(c, box=None, w=900, h=900):
    c.insert_vinsts()
    lyp = GDSDIR_TEMP / "lp.lyp"
    get_layer_views().to_lyp(filepath=lyp)
    v = lay.LayoutView()
    i = v.create_layout(True); v.active_cellview_index = i
    cv = v.cellview(i); lo = cv.layout(); lo.assign(kf.kcl.layout)
    cv.cell = lo.cell(c.name)
    v.max_hier(); v.load_layer_props(str(lyp)); v.add_missing_layers()
    v.zoom_fit() if box is None else v.zoom_box(kdb.DBox(*box))
    v.set_config("text-visible", "false")
    v.set_config("grid-show-ruler", "true")
    v.set_config("background-color", "#ffffff")
    return plt.imread(BytesIO(
        v.get_pixels_with_options(width=w, height=h, oversampling=2,
                                  linewidth=1, resolution=0.5).to_png_data()))

c = gf.get_component("ring_resonator_single_mode_point_coupler_oband")
full = render(c, None, 900, 900)
zoom = render(c, (197.6, -3.4, 204.4, 3.4), 900, 900)

# analytic all-pass response from the PDK waveguide parameters
R, ng, neff, loss, lam0 = 200.0, 2.2, 1.75, 0.5, 1.31
L = 2*np.pi*R
a = 10**(-loss*L*1e-4/20.0)
lam = np.linspace(lam0-0.0016, lam0+0.0016, 40001)
neff_l = neff - (ng-neff)*(lam-lam0)/lam0
phi = 2*np.pi*neff_l*L/lam
def thru(k2):
    t = np.sqrt(1-k2)
    return np.abs((t - a*np.exp(1j*phi))/(1 - t*a*np.exp(1j*phi)))**2
T_crit = thru(1-a**2)
T_wip = thru(0.05)

fig = plt.figure(figsize=(14.5, 5.4))
gs = fig.add_gridspec(1, 3, width_ratios=[1, 1, 1.35], wspace=0.18)
for k, (im, t) in enumerate([(full, "Full cell, 414 x 413 um"),
                             (zoom, "Coupling region, 6.8 um wide")]):
    ax = fig.add_subplot(gs[0, k]); ax.imshow(im); ax.axis("off")
    ax.set_title(t, fontsize=10)
ax = fig.add_subplot(gs[0, 2])
x = (lam-lam0)*1e3
ax.plot(x, 10*np.log10(T_wip), lw=1.0, color="tab:blue",
        label=r"$\kappa^2$ = 5 %, the PDK draft model")
ax.plot(x, 10*np.log10(T_crit), lw=1.0, color="tab:orange",
        label=r"$\kappa^2$ = 1.44 %, critical coupling")
ax.set_xlabel(r"$\lambda - 1310$ nm  [nm]"); ax.set_ylabel("through-port transmission [dB]")
ax.set_ylim(-40, 3); ax.set_xlim(-1.3, 1.3)
ax.grid(alpha=0.3, lw=0.5); ax.legend(fontsize=8, loc="lower left")
ax.set_title("Computed response, 0.5 dB/cm, $n_g$ = 2.2", fontsize=10)
ax.annotate("", xy=(-0.18, 1.2), xytext=(0.44, 1.2),
            arrowprops=dict(arrowstyle="<->", lw=0.8))
ax.text(0.13, -2.6, "FSR 0.62 nm", ha="center", fontsize=8)
# inset on one resonance
i0 = int(np.argmin(T_crit))
axi = ax.inset_axes([0.52, 0.30, 0.45, 0.42])
axi.plot((lam-lam[i0])*1e6, 10*np.log10(T_wip), lw=0.9, color="tab:blue")
axi.plot((lam-lam[i0])*1e6, 10*np.log10(T_crit), lw=0.9, color="tab:orange")
axi.set_xlim(-15, 15); axi.set_ylim(-40, 3)
axi.tick_params(labelsize=7)
axi.set_xlabel("detuning [pm]", fontsize=7); axi.grid(alpha=0.3, lw=0.4)
axi.set_title("one resonance", fontsize=7)
fig.suptitle("ltoi300  ring_resonator_single_mode_point_coupler_oband   "
             "R = 200 um, ring width 0.7 um, gap 1.05 um", fontsize=11)
out = sys.argv[1]
fig.savefig(out, dpi=140, bbox_inches="tight")
print("wrote", out)
print("FSR nm", lam0**2/(ng*L)*1e3)
