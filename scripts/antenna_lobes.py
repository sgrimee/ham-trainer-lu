"""Generate the 3D radiation-pattern figure of antennes/gain-d-antenne.fr.md:
a dipole's doughnut next to a Yagi's forward lobe, as inline SVG.

    uv run python -m scripts.antenna_lobes > figure.svg   # paste into the lesson

World axes: x = main direction (the Yagi's boom), z = up = the elements and
the dipole wire, both vertical. Each pattern is drawn as field strength
(square root of the power pattern), both scaled to the same total power, so
the Yagi's lobe is longer only where the dipole's is shorter. Surfaces are
flat-shaded quads, depth-sorted, front faces only (painter's algorithm).
"""

import math
import sys

AZ, EL = math.radians(22), math.radians(28)  # camera azimuth / elevation
LIGHT = (-0.45, -0.35, 0.82)  # towards the light, world coords (normalised below)
_l = math.sqrt(sum(c * c for c in LIGHT))
LIGHT = tuple(c / _l for c in LIGHT)


def cam(p):
    """World -> camera (x right, y up, z towards the viewer)."""
    x, y, z = p
    ca, sa = math.cos(AZ), math.sin(AZ)
    x1, y1 = ca * x - sa * y, sa * x + ca * y  # rotate about z
    ce, se = math.cos(EL), math.sin(EL)
    return (x1, ce * z - se * y1, se * z + ce * y1)  # tilt: y1 is depth before tilt


def blend(t):
    lo, hi = (0x5F, 0x82, 0xDE), (0xEE, 0xF2, 0xFF)
    return "#" + "".join(f"{round(a + (b - a) * t):02x}" for a, b in zip(lo, hi, strict=True))


def surface(r, n_th=16, n_ph=24, pole_x=False):
    """Quads of the surface point = r(u) * u, u over the sphere (theta from +z,
    or from +x with `pole_x`, so a lobe along x gets rings around its axis)."""
    if pole_x:
        quads = surface(lambda u: r((u[2], u[0], u[1])), n_th, n_ph)
        return [[(p[2], p[0], p[1]) for p in q] for q in quads]
    pts = [
        [
            (lambda u: tuple(r(u) * c for c in u))(
                (
                    math.sin(math.pi * i / n_th) * math.cos(2 * math.pi * j / n_ph),
                    math.sin(math.pi * i / n_th) * math.sin(2 * math.pi * j / n_ph),
                    math.cos(math.pi * i / n_th),
                )
            )
            for j in range(n_ph)
        ]
        for i in range(n_th + 1)
    ]
    quads = []
    for i in range(n_th):
        for j in range(n_ph):
            q = [pts[i][j], pts[i][(j + 1) % n_ph], pts[i + 1][(j + 1) % n_ph], pts[i + 1][j]]
            quads.append(q)
    return quads


def normal(q):
    a, b, c, d = q
    u = [c[k] - a[k] for k in range(3)]
    v = [d[k] - b[k] for k in range(3)]
    n = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
    ln = math.sqrt(sum(c * c for c in n)) or 1
    return tuple(c / ln for c in n)


def render(quads, ox, oy, s):
    """SVG paths for the world quads that face the camera, back to front."""
    items = []
    for q in quads:
        cq = [cam(p) for p in q]
        n = normal(q)
        # Only faces turned towards the camera; outward normal check by centroid.
        cen = [sum(p[k] for p in q) / 4 for k in range(3)]
        if sum(n[k] * cen[k] for k in range(3)) < 0:
            n = tuple(-c for c in n)
        cn = cam(n)
        if cn[2] <= 0:
            continue
        lam = max(0.0, sum(n[k] * LIGHT[k] for k in range(3)))
        colour = blend(0.25 + 0.75 * lam)
        depth = sum(p[2] for p in cq) / 4
        d = "M" + " L".join(f"{ox + s * p[0]:.0f} {oy - s * p[1]:.0f}" for p in cq) + "Z"
        items.append((depth, f'<path d="{d}" fill="{colour}" stroke="{colour}" stroke-width="0.6"/>'))
    items.sort(key=lambda t: t[0])
    return [t[1] for t in items]


def dipole_r(u):
    return 1 - u[2] ** 2  # power pattern: sin² of the angle to the wire (z)


def yagi_r(u):
    c = u[0]
    fwd = ((1 + c) / 2) ** 6
    return (fwd + 0.10 * ((1 - c) / 2) ** 3) * (1 - u[2] ** 2)


def power(r, n=200):
    """∫ r(u) dΩ, to give both antennas the same total power."""
    tot = 0
    for i in range(n):
        th = math.pi * (i + 0.5) / n
        for j in range(n):
            ph = 2 * math.pi * (j + 0.5) / n
            u = (math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th))
            tot += r(u) * math.sin(th)
    return tot * (math.pi / n) * (2 * math.pi / n)


P_d, P_y = power(dipole_r), power(yagi_r)
k_y = P_d / P_y  # scale the Yagi's power pattern to the dipole's total
print(f"forward ratio (power) = {k_y:.2f}  ≈ {10 * math.log10(k_y):.1f} dBd", file=sys.stderr)

S = 44  # px per unit of field strength
COPPER = "#d9822b"


def pt(p, ox, oy):
    c = cam(p)
    return ox + S * c[0], oy - S * c[1]


def seg(p0, p1, ox, oy, stroke, w):
    (ax, ay), (bx, by) = pt(p0, ox, oy), pt(p1, ox, oy)
    d = f"M{ax:.1f} {ay:.1f} L{bx:.1f} {by:.1f}"
    return f'<path d="{d}" stroke="{stroke}" stroke-width="{w}" stroke-linecap="round"/>'


DX, DY = 76, 96
YX, YY = 190, 96
out = []
out.append(
    '<g font-size="13" font-weight="bold" fill="#1c1f26" text-anchor="middle">'
    '<text x="80" y="16">Dipôle</text><text x="245" y="16">Antenne directive</text></g>'
)
out.append(seg((0, 0, -1.3), (0, 0, 1.3), DX, DY, COPPER, 4))
out.append(
    '<g opacity="0.8">' + "".join(render(surface(lambda u: math.sqrt(dipole_r(u))), DX, DY, S)) + "</g>"
)
els = [(-0.3, 0.5), (0, 0.46)] + [(0.25 * k, 0.4) for k in (1, 2, 3)]
out.append(seg((-0.3, 0, 0), (0.75, 0, 0), YX, YY, "#6b7280", 2))
out += [seg((x, 0, -h), (x, 0, h), YX, YY, COPPER, 3) for x, h in els]
yagi_lobe = surface(lambda u: math.sqrt(k_y * yagi_r(u)), 18, 24, pole_x=True)
out.append('<g opacity="0.8">' + "".join(render(yagi_lobe, YX, YY, S)) + "</g>")
# main-direction arrow along +x, below the lobe
a0, a1 = pt((0.4, 0, -1.3), YX, YY), pt((2.0, 0, -1.3), YX, YY)
ang = math.atan2(a1[1] - a0[1], a1[0] - a0[0])
h1 = (a1[0] - 7 * math.cos(ang - 0.5), a1[1] - 7 * math.sin(ang - 0.5))
h2 = (a1[0] - 7 * math.cos(ang + 0.5), a1[1] - 7 * math.sin(ang + 0.5))
shaft = f"M{a0[0]:.0f} {a0[1]:.0f} L{a1[0]:.0f} {a1[1]:.0f}"
head = f"M{h1[0]:.0f} {h1[1]:.0f} L{a1[0]:.0f} {a1[1]:.0f} L{h2[0]:.0f} {h2[1]:.0f}"
out.append(f'<g stroke="#c0362c" stroke-width="2" fill="none"><path d="{shaft}"/><path d="{head}"/></g>')
out.append(
    f'<text x="{(a0[0] + a1[0]) / 2 - 6:.0f}" y="{(a0[1] + a1[1]) / 2 + 20:.0f}" font-size="12" '
    'fill="#c0362c" text-anchor="middle">direction principale</text>'
)
aria = (
    "Dessin en trois dimensions. À gauche, un dipôle vertical est entouré d'un beignet : il rayonne "
    "autant dans toutes les directions autour de lui, mais rien vers le haut ni vers le bas, dans l'axe "
    "de son fil. À droite, une antenne directive, un rang de tiges verticales sur une barre, est entourée "
    "d'un grand lobe allongé vers la droite, la direction principale, et d'un tout petit lobe vers l'arrière."
)
print(f'<svg viewBox="0 0 340 185" width="340" role="img" aria-label="{aria}">')
print("\n".join(out))
print("</svg>")
