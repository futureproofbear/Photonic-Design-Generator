import numpy as np, matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt

from matplotlib.colors import LogNorm



# --- inputs from run 20260903-075632-ltoi300_ring_oband_ltpro, being the

# --- cross-section solved on the LT-PRO design manual dispersion

neff, ng, n_clad, lam, R = 1.748261, 2.189394, 1.446804, 1.31, 200.0

L = 2*np.pi*R

k0 = 2*np.pi/lam

gam = np.sqrt((neff*k0)**2 - (n_clad*k0)**2)     # cladding field decay, 1/um

Leff = np.sqrt(2*np.pi*R/gam)

g0 = 1.05

K2_FDTD = 0.009063       # meep, 2D effective index, resolution 50

GAM2 = 7.251            # d(ln kappa^2)/dgap from the three-gap sweep, 1/um

print(f"gamma {gam:.3f} /um, Leff {Leff:.1f} um, FSR {lam**2/(ng*L)*1e3:.4f} nm")



loss = np.logspace(np.log10(0.02), np.log10(3.0), 400)      # dB/cm

k2 = np.logspace(np.log10(2e-4), np.log10(0.08), 400)       # power coupling

LL, KK = np.meshgrid(loss, k2)

a = 10**(-LL*(L*1e-4)/20.0)

t = np.sqrt(1-KK)

ER = 10*np.log10(np.clip(((t-a)/(1-t*a))**2, 1e-12, None))

F = np.pi*np.sqrt(t*a)/(1-t*a)

FSR_nm = lam**2/(ng*L)*1e3

QL = lam*1e3/(FSR_nm/F)



fig, axs = plt.subplots(1, 3, figsize=(16.5, 5.2))



def frame(ax, label=True):

    ax.set_xscale("log"); ax.set_yscale("log")

    ax.set_xlabel("propagation loss [dB/cm]")

    ax.set_ylabel(r"power coupling $\kappa^2$ [%]")

    ax.axvspan(0.436, 1.798, color="tab:purple", alpha=0.10)
    if label:
        ax.text(1.90, 6.2, "Wang et al. transferred to this cross-section",
                fontsize=7, color="tab:purple", rotation=90, va="top")
    for x, lab in ((0.056, "0.056, as published on a\n2 um guide, 500 nm etch"),
                   (0.5, "0.5, the PDK\ncompact model")):
        ax.axvline(x, color="k", ls=":", lw=0.9)

        ax.text(x*1.06, 6.2, lab, fontsize=7, rotation=90, va="top")

    ax.plot(loss, 100*(1-10**(-loss*(L*1e-4)/10)), color="k", lw=1.6,

            label="critical coupling")

    ax.axhline(100*K2_FDTD, color="tab:orange", lw=1.6,

               label=r"measured $\kappa^2$, gap 1.05 um")

    if label:

        ax.text(0.023, 100*K2_FDTD*1.15, "FDTD, 0.906 % at the drawn gap",

                fontsize=7.5, color="tab:orange", va="bottom")



ax = axs[0]

cs = ax.contourf(100*loss/loss, 100*k2, ER, levels=np.arange(-40, 1, 2.5),

                 cmap="viridis")   # placeholder, replaced below

ax.clear()

cs = ax.contourf(LL, 100*KK, ER, levels=np.arange(-40, 1, 2.5), cmap="magma")

cl = ax.contour(LL, 100*KK, ER, levels=[-20, -10, -6, -3], colors="w", linewidths=0.8)

ax.clabel(cl, fmt="%d dB", fontsize=7)

frame(ax); ax.set_title("Through-port extinction [dB]", fontsize=10)

fig.colorbar(cs, ax=ax, pad=0.02)

ax.legend(fontsize=7, loc="lower right")



ax = axs[1]

cs = ax.contourf(LL, 100*KK, QL, levels=np.logspace(4, 7.2, 33), norm=LogNorm(),

                 cmap="viridis", extend="both")

cl = ax.contour(LL, 100*KK, QL, levels=[1e5, 3e5, 1e6, 3e6], colors="w", linewidths=0.8)

ax.clabel(cl, fmt="%.0e", fontsize=7)

frame(ax, label=False); ax.set_title("Loaded Q", fontsize=10)

fig.colorbar(cs, ax=ax, pad=0.02, ticks=[1e4,1e5,1e6,1e7])



# gap that reaches critical coupling, relative to the drawn 1.05 um

ax = axs[2]

k2_crit = 1-10**(-loss*(L*1e-4)/10)

dg = np.log(K2_FDTD/k2_crit)/GAM2               # um to add to the drawn gap

ax.plot(loss, 1e3*dg, color="tab:orange", lw=1.6,

        label=r"from the measured $\kappa^2$ and $2\gamma$ = 7.25 /um")

for lo in (0.436, 0.5, 1.798):

    d = 1e3*np.log(K2_FDTD/(1-10**(-lo*(L*1e-4)/10)))/GAM2

    ax.plot([lo], [d], "o", ms=5, color="k")

    ax.annotate(f"{1050+d:.0f} nm", (lo, d), textcoords="offset points",

                xytext=(6, -11), fontsize=7.5)

ax.axhline(0, color="k", lw=0.8)

ax.set_xscale("log"); ax.set_xlabel("propagation loss [dB/cm]")

ax.set_ylabel("gap change needed for critical coupling [nm]")

ax.axvspan(0.436, 1.798, color="tab:purple", alpha=0.10)
ax.set_title("How far the drawn gap is from critical", fontsize=10)

ax.grid(alpha=0.3, lw=0.5); ax.legend(fontsize=7.5, loc="upper right")

for x in (0.436, 0.5, 1.798):

    ax.axvline(x, color="k", ls=":", lw=0.9)



fig.suptitle("ltoi300 O-band ring, R = 200 um:  what the coupling and the loss decide.  "

             r"$n_g$ = 2.189 and $n_{eff}$ = 1.748 on the LT-PRO dispersion, FSR = 0.624 nm", fontsize=11)

fig.tight_layout()

out = __import__("sys").argv[1]

fig.savefig(out, dpi=140, bbox_inches="tight")

print("wrote", out)



# a few printed points

for lo in (0.056, 0.171, 0.5, 1.0):

    aa = 10**(-lo*(L*1e-4)/20)

    print(f"loss {lo:5.3f} dB/cm -> critical kappa^2 {100*(1-aa**2):.3f} %, "

          f"intrinsic Q {2*np.pi*ng/(lam*1e-6*lo/4.343*100):.2e}")

