#!/usr/bin/env python3
"""Touch-up PROPOSALS for Dracula 16-bit (stage 18): variants of the pictures of build_dracula16.py.

Nothing here is wired into the game: `build_dracula16.py <castlevania-md> --variant NAME[,NAME] --out-dir DIR` writes the
variant arrays to DIR (never to the committed sgdk/src/generated/). Every variant keeps the constraints of the MSX layout:
the same 24 cells of 16 x 16 (96 tiles), the same boxes, the same 65 bust composites, the same transfers, the same
palette slots 8 and 14. Only the pixels inside the cells change. research/dracula-touchups.md describes and compares them.

Variants (suffix a / b = proposal A / B of the board of the defect):
  head-a   high collar: the empty hood cell (cells 2 / 6, drawn over the head) holds a cloak collar and a neck under the chin
  head-b   cowl: the hood cell holds a black hood with a red lining behind the face, and a low collar
  cape-a   cape drawn again, same 24-column silhouette: curved pleats, no black strip, notched hem, V-shaped opened cloak
  cape-b   cape drawn again, flared to the 32 columns of the cells, wavy hem, V-shaped opened cloak
  bat-a    the fourth bat pose (cell 17, a copy of cell 15) is a sheared copy of cell 14: wings half raised
  bat-b    the four bat poses drawn again (body, ears, red eyes, wing membranes), a real 4-phase flap
  sickle-a six steel sickles (crescent blade, handle), the black box of the Castlevania-MD picture is gone, 60 degrees apart
  sickle-b six crimson sickles with a pale edge, same geometry
"""
import math

# ---- colours (levels 0..7), all of them already in the picture palette of the base art ------------------------------
R0, R1, R2, R3 = (1, 0, 0), (2, 0, 0), (4, 0, 0), (5, 1, 1)       # cloak reds, dark -> light
BLK = (0, 0, 0)
GOLD, GOLD2 = (7, 5, 0), (5, 3, 1)
S0, S1, S2, S3, S4, S5 = (1, 1, 2), (2, 2, 3), (3, 3, 5), (5, 5, 7), (5, 3, 7), (7, 7, 7)   # head / bat steel-violet ramp
BROWN = (3, 1, 0)
EYE = (7, 1, 0)

Z = lambda w, h: [[None] * w for _ in range(h)]


def blit(dst, src, x0, y0):
    for y, row in enumerate(src):
        for x, p in enumerate(row):
            if p is not None and 0 <= y + y0 < len(dst) and 0 <= x + x0 < len(dst[0]):
                dst[y + y0][x + x0] = p
    return dst


def mirror(img):
    return [r[::-1] for r in img]


def bbox(img):
    pts = [(x, y) for y, r in enumerate(img) for x, p in enumerate(r) if p is not None]
    return (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)) if pts else None


def outline(img, colour, only_none=True):
    """1-pixel outline (4-neighbourhood) around the opaque pixels."""
    h, w = len(img), len(img[0])
    out = [r[:] for r in img]
    for y in range(h):
        for x in range(w):
            if img[y][x] is None and any(0 <= y + dy < h and 0 <= x + dx < w and img[y + dy][x + dx] is not None
                                         for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y][x] = colour
    return out


# ---- supersampled shapes --------------------------------------------------------------------------------------------
def raster(w, h, classify, ss=5, need=0.5):
    """classify(x, y) -> a colour / None for a point in pixel units; majority of ss x ss samples (colour with most votes)."""
    out = Z(w, h)
    for y in range(h):
        for x in range(w):
            votes = {}
            for j in range(ss):
                for i in range(ss):
                    c = classify(x + (i + .5) / ss, y + (j + .5) / ss)
                    if c is not None:
                        votes[c] = votes.get(c, 0) + 1
            if sum(votes.values()) >= need * ss * ss:
                out[y][x] = max(votes, key=votes.get)
    return out


def rot(px, py, a):
    c, s = math.cos(a), math.sin(a)
    return px * c - py * s, px * s + py * c


# =============================================================================================================
# head: hood cell (2 for the left-facing poses, 6 for the mirrored ones)
# =============================================================================================================
def hood(head_cells, style, mirrored):
    """16 x 16 layer drawn OVER the head cell(s): pixels of the head stay transparent. head_cells: the pictures of the head
    cells that share this hood (A and V variants). Written for a head looking left (back of the head on the right), mirrored after."""
    head = Z(16, 16)
    for hc in head_cells:
        blit(head, mirror(hc) if mirrored else hc, 0, 0)
    x0, y0, x1, y1 = bbox(head)                  # head columns x0..x1, rows y0..y1
    img = Z(16, 16)
    cx = x1 + 1                                   # first column behind the head

    def put(x, y, c):
        if 0 <= x < 16 and 0 <= y < 16 and head[y][x] is None:
            img[y][x] = c

    if style == 'a':
        # high collar: a pointed wing behind the head (up to the ear), a low one in front, joined to the shoulders (row 16)
        top_back = max(y0 + 2, 3)
        for y in range(top_back, 16):
            t = (y - top_back) / (15 - top_back)          # 0 at the tip, 1 at the shoulders
            wid = 1 + round(t * (15 - cx - 1))
            for k in range(wid):
                x = cx + k + (1 if y < top_back + 3 else 0)
                shade = R3 if k == 0 and t > .2 else R2 if k < wid - 1 else R1
                put(x, y, shade)
            put(cx + wid + (1 if y < top_back + 3 else 0), y, R0)
        for y in range(11, 16):                            # front wing, low
            t = (y - 11) / 4
            for k in range(1 + round(t * (x0 - 0))):
                put(x0 - 1 - k, y, R2 if k else R3)
            put(x0 - 2 - round(t * x0), y, R0)
        for y in (14, 15):                                 # neck, under the chin
            for x in range(x0, cx):
                put(x, y, BLK)
    else:
        # cowl: a red hood standing round the face (symmetrical arch, gold edge), black lining against the face, fold shading
        hx, hy = (x0 + x1) / 2 + .3, y0 + 6.2
        for y in range(16):
            for x in range(16):
                dx, dy = (x + .5 - hx) / 6.8, (y + .5 - hy) / 8.6
                r = math.hypot(dx, dy)
                near = any(0 <= y + j < 16 and 0 <= x + i < 16 and head[y + j][x + i] is not None
                           for i in (-1, 0, 1) for j in (-1, 0, 1))
                if y >= 14 or r < 1.0:
                    if near and y < 15:
                        put(x, y, BLK)                         # shadow lining against the face
                    elif r > .84 or y >= 14:
                        put(x, y, GOLD2 if r > .93 and y < 13 else R2)
                    else:
                        put(x, y, R1 if (x + 2 * y) % 4 else R0)
                    if y >= 14 and not near:
                        put(x, y, R2 if (x + y) % 3 else R3)
        for y in (14, 15):
            for x in range(x0, x1 + 1):
                put(x, y, BLK)
    return mirror(img) if mirrored else img


def head_variant(style):
    def f(pics, boxes, E):
        # heads: A = cell 0, V = cell 5 (left-facing) and their mirror images, cells 1 and 9; hood cells 2 and 6 (empty in the base)
        pics[2] = hood([pics[0], pics[5]], style, False)
        pics[6] = hood([pics[1], pics[9]], style, True)
    return f


# =============================================================================================================
# cape and bust: layers 1..4 of the bust (32 x 32), cape cells 3, 4 (left-facing) and 7, 8 (mirrored)
# =============================================================================================================
def cloak(pics_bust1, style):
    """32 x 48 picture of the closed cloak (rows 0..31 = bust, 32..47 = cape cells) from the 32 x 32 layer 1 of the base art:
    the shoulders and the golden chain (rows 0..13) are kept, the rest is drawn again (curved pleats, notched hem)."""
    img = Z(32, 48)
    keep = 14
    for y in range(keep):
        for x in range(32):
            p = pics_bust1[y][x]
            if p is not None and not (p == BLK and x >= 22):          # the black strip on the right is dropped
                img[y][x] = p
    xs = [x for x in range(32) for y in range(keep) if img[y][x] is not None]
    left, right = min(xs), max(xs)                                   # the shoulders: columns left..right
    c0, hw0 = (left + right + 1) / 2, (right - left + 1) / 2
    bayer = ((0, 2), (3, 1))
    for y in range(keep, 48):
        t = (y - keep) / (47 - keep)
        if style == 'a':
            hw, cx = hw0 + .5 + 1.4 * t, c0 + .3 * t
        else:
            hw, cx = hw0 + .5 + (16 - hw0 - .5) * t ** 1.2, c0 + (16 - c0) * t ** 1.2      # flares to the 32 columns of the cells
        for x in range(32):
            u = (x + .5 - cx) / hw
            if abs(u) >= 1:
                continue
            ph = u * 2.6 * math.pi + .9 * math.sin(t * 3.3 + u * 1.7) + 1.1 * t * u
            ridge = (math.cos(ph) + 1) / 2
            s = ridge - .2 * u - .12 * t + .12 * math.sin(y / 2.7 + u * 3)
            s += (bayer[y & 1][x & 1] - 1.5) * .04
            tone = R0 if s < .24 else R1 if s < .48 else R2 if s < .76 else R3
            if u > .86:
                tone = R0
            elif u < -.86:
                tone = R1
            amp = 2.4 if style == 'a' else 3.4
            if y > 47 - round(amp * (1 - ridge)):                       # hem notches between the folds
                continue
            img[y][x] = tone
    return img


def open_overlay(style):
    """32 x 32 layer 2 (left-facing): the cloak parted in a V that shows its dark lining, a pleated flap swept to the right."""
    img = Z(32, 32)
    for y in range(6, 32):
        t = (y - 6) / 25
        xl = 12.0 + 3.0 * t
        xr = (27.0 - 2.5 * t) if style == 'a' else (28.0 - 1.5 * t)
        fw = 4.2 - 1.6 * t                                  # width of the flap
        for x in range(32):
            fx = x + .5
            if fx < xl or fx > xr:
                continue
            if fx > xr - fw:                                # flap: pleated cloak
                k = xr - fx
                img[y][x] = R3 if k < 1.0 and y % 4 else R2 if k < fw - 1 else R1
            elif fx < xl + 1.0:                              # lapel
                img[y][x] = R3 if y % 3 else R2
            else:                                            # lining, dark with soft folds
                d = (fx - xl) + y * .35
                img[y][x] = BLK if (int(d) % 3 == 0) else R0
    return img


def cape_variant(style):
    def f(pics, boxes, E):
        base1 = pics['bust'][1]
        c = cloak(base1, style)
        closed = [row[:] for row in c[:32]]
        over = open_overlay(style)
        # layer 2 draws only over the closed cloak (opaque pixels replace): keep the closed pixels as they are elsewhere
        pics['bust'][1] = closed
        pics['bust'][2] = over
        pics['bust'][3], pics['bust'][4] = mirror(closed), mirror(over)
        cape = c[32:48]
        for left, right, mir in ((3, 4, False), (7, 8, True)):
            canvas = mirror(cape) if mir else cape
            pics[left] = [row[0:16] for row in canvas]
            pics[right] = [row[16:32] for row in canvas]
    return f


# =============================================================================================================
# bats (cells 14..17)
# =============================================================================================================
def bat_a(pics, boxes, E):
    """cell 17 (a copy of cell 15) -> the flat bat of cell 14 with its wings half raised: columns away from the body shifted up."""
    src = pics[14]
    x0, y0, x1, y1 = bbox(src)
    mid = (x0 + x1) / 2
    out = Z(16, 16)
    for x in range(16):
        lift = round(abs(x + .5 - mid) / ((x1 - x0) / 2 + .01) * 2.4)
        for y in range(16):
            if src[y][x] is not None and 0 <= y - lift < 16:
                out[y - lift][x] = src[y][x]
    pics[17] = out


def bat_frame(theta, curve, body_dy=0):
    """16 x 16 bat looking at us, wings at the angle theta (radians above the horizontal), curve = trailing-edge bend."""
    cx, cy = 8.0, 8.0 + body_dy

    def wing_pts(side):
        sh = (cx + side * 1.4, cy - .6)
        ang = theta
        el = (sh[0] + side * 3.4 * math.cos(ang * .6), sh[1] - 3.4 * math.sin(ang * .6) - .3)      # wrist
        tip = (sh[0] + side * 7.0 * math.cos(ang), sh[1] - 7.0 * math.sin(ang))
        t2 = (sh[0] + side * 6.0 * math.cos(ang - .45 + curve * .3), sh[1] - 6.0 * math.sin(ang - .45 + curve * .3) + 2.4)
        t3 = (sh[0] + side * 3.6 * math.cos(ang - .9 + curve * .5), sh[1] - 3.6 * math.sin(ang - .9 + curve * .5) + 3.9)
        root = (cx + side * .9, cy + 2.6)
        return sh, el, tip, t2, t3, root

    polys = {s: wing_pts(s) for s in (-1, 1)}

    def inside(poly, x, y):
        c = False
        n = len(poly)
        for i in range(n):
            (x1, y1), (x2, y2) = poly[i], poly[(i + 1) % n]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    def cls(x, y):
        # body
        if ((x - cx) / 1.7) ** 2 + ((y - cy - .4) / 2.9) ** 2 < 1:
            if abs(x - cx - .9) < .55 and abs(y - cy + .2) < .55 or abs(x - cx + .9) < .55 and abs(y - cy + .2) < .55:
                return EYE
            return S1 if (x - cx) < .5 else S0
        # ears
        for sx in (-1, 1):
            if inside([(cx + sx * .7, cy - 2.0), (cx + sx * 1.6, cy - 3.6), (cx + sx * 1.9, cy - 1.7)], x, y):
                return S1
        for s in (-1, 1):
            sh, el, tip, t2, t3, root = polys[s]
            if inside([sh, el, tip, t2, t3, root], x, y):
                # bones: along sh->tip and sh->t2 (darker), membrane (mid), pale rim at the trailing edge
                def near(a, b, r):
                    ax, ay = b[0] - a[0], b[1] - a[1]
                    l = (ax * ax + ay * ay) or 1
                    tt = max(0, min(1, ((x - a[0]) * ax + (y - a[1]) * ay) / l))
                    return math.hypot(x - a[0] - tt * ax, y - a[1] - tt * ay) < r
                if near(sh, tip, .55) or near(el, t2, .5) or near(sh, t3, .5):
                    return S0
                if (y > sh[1] + 2.2 and not inside([sh, el, tip, t2, t3, root], x, y + 1.2)) or near(tip, t2, .7) or near(t2, t3, .7):
                    return S4
                return S2 if (x - cx) * s < 3.5 else S3
        return None

    img = raster(16, 16, cls, ss=4)
    return outline(img, S0)


def bat_b(pics, boxes, E):
    # four phases of the flap, in the order of the poses 2, 165, 166, 167 (cells 14..17): top, falling, bottom, rising
    for c, (th, cu, dy) in zip((14, 15, 16, 17), ((.85, 0.0, .5), (.15, .6, 0), (-.7, 0.0, -.3), (.1, -.6, 0))):
        pics[c] = bat_frame(th, cu, dy)


# =============================================================================================================
# sickles (cells 18..23)
# =============================================================================================================
def sickle_frame(angle, style):
    """16 x 16 crescent blade + handle turned by `angle`; light from the upper left in screen space."""
    cx, cy = 8.0, 8.0
    Ro, ri = 6.6, 5.3
    co = rot(0.0, 0.0, angle)
    ci = rot(2.3, -1.9, angle)                    # inner circle: the crescent opens toward the upper right in the unrotated frame
    h0 = rot(-3.4, 3.6, angle)                    # handle from the lower-left horn
    h1 = rot(-7.2, 7.3, angle)
    lx, ly = -.6, -.8                             # light direction (toward the upper left)

    def cls(x, y):
        px, py = x - cx, y - cy
        do = math.hypot(px - co[0], py - co[1])
        di = math.hypot(px - ci[0], py - ci[1])
        if do < Ro and di > ri:
            n = ((px - co[0]) / (do or 1), (py - co[1]) / (do or 1))
            lit = n[0] * lx + n[1] * ly
            edge = Ro - do
            inner = di - ri
            if style == 'steel':
                if edge < 1.15:
                    return S5 if lit > .15 else S3
                if inner < 1.0:
                    return S1
                return S3 if lit > .0 else S2
            if edge < 1.0:
                return GOLD2 if lit > .15 else R3
            if inner < 1.0:
                return R0
            return R3 if lit > .0 else R2
        # handle: a stick from h0 to h1
        ax, ay = h1[0] - h0[0], h1[1] - h0[1]
        l = ax * ax + ay * ay
        tt = max(0, min(1, ((px - h0[0]) * ax + (py - h0[1]) * ay) / l))
        dh = math.hypot(px - h0[0] - tt * ax, py - h0[1] - tt * ay)
        if dh < 1.0:
            return BROWN if style == 'steel' else R1
        if dh < .6 + .0 and tt > .9:
            return GOLD
        return None

    img = raster(16, 16, cls, ss=5)
    return outline(img, S0 if style == 'steel' else R0)


def sickles(style):
    def f(pics, boxes, E):
        for i, c in enumerate(range(18, 24)):
            pics[c] = sickle_frame(i * math.pi / 3, style)
    return f


# ---- 8: background face, palette re-grade (levels of the MSX palette bytes; the skin ramp only) -----------------------
FACE = {   # old (r, g, b) levels -> new ones ('a' ashen and cold, 'b' warm, torch-lit)
    'a': {(2, 1, 1): (1, 1, 2), (4, 2, 2): (3, 2, 3), (5, 3, 3): (4, 3, 4), (6, 4, 4): (5, 4, 5), (6, 5, 5): (6, 5, 6),
          (7, 5, 4): (7, 6, 6), (7, 5, 5): (7, 7, 6)},
    'b': {(2, 1, 1): (1, 0, 0), (4, 2, 2): (3, 1, 1), (5, 3, 3): (4, 2, 1), (6, 4, 4): (5, 3, 2), (6, 5, 5): (6, 4, 3),
          (7, 5, 4): (7, 5, 3), (7, 5, 5): (7, 6, 4), (6, 2, 3): (5, 1, 1)},
}


def face_palette(style, init):
    """init: the 32 MSX bytes (rb, g per entry: rb = blue | red << 4, 3 bits each) of vk_dracula_initial_palette. Returns the 32 re-graded
    bytes and the 16 MD words (0BGR, even levels) of PAL0: the fade of the end and the pulse of entry 6 work on the same bytes."""
    out, words = [], []
    for i in range(16):
        rb, g = init[2 * i], init[2 * i + 1]
        lv = (rb >> 4 & 7, g & 7, rb & 7)                 # r, g, b
        lv = FACE[style].get(lv, lv)
        out += [lv[2] | lv[0] << 4, lv[1]]
        words.append(lv[2] * 2 << 8 | lv[1] * 2 << 4 | lv[0] * 2)
    return out, words


RETAINED = ('head-b', 'cape-b', 'bat-b', 'sickle-a')     # adopted set (research/dracula-touchups.md); face: 8B
FACE_STYLE = 'b'

VARIANTS = {
    'head-a': head_variant('a'), 'head-b': head_variant('b'),
    'cape-a': cape_variant('a'), 'cape-b': cape_variant('b'),
    'bat-a': bat_a, 'bat-b': bat_b,
    'sickle-a': sickles('steel'), 'sickle-b': sickles('crimson'),
}


def apply(pics, boxes, variants, E):
    for v in variants:
        if v in ('all-a', 'all-b'):
            for k in VARIANTS:
                if k.endswith(v[-1]):
                    VARIANTS[k](pics, boxes, E)
        else:
            VARIANTS[v](pics, boxes, E)
