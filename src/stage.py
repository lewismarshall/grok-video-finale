"""Keyframe the party. All units are metres, seconds, and degrees."""

import math

import numpy as np

from config import (
    GROUND,
    MOON_C,
    MOON_R,
    T_ARGON,
    T_BACK,
    T_BANANA,
    T_CARD,
    T_CHAIRS,
    T_CLINK,
    T_CRUNCH,
    T_DROP,
    T_FINE,
    T_FLAG,
    T_GLITCH,
    T_GRAV,
    T_HOLE,
    T_HONK,
    T_IMPACT,
    T_JUGGLE,
    T_LAND,
    T_MOON2,
    T_RISER,
    T_SHADES,
    T_SNACK,
    T_VIBES,
    T_WELCOME,
)


def ease(t0, t1, t):
    if t <= t0:
        return 0.0
    if t >= t1:
        return 1.0
    x = (t - t0) / (t1 - t0)
    return x * x * (3.0 - 2.0 * x)


def lerp(a, b, u):
    return a + (b - a) * u


def vlerp(a, b, u):
    return np.asarray(a, np.float64) * (1.0 - u) + np.asarray(b, np.float64) * u


def clamp01(x):
    return max(0.0, min(1.0, x))


def rotate_around(vec, axis, deg):
    a = math.radians(deg)
    axis = np.asarray(axis, np.float64)
    axis = axis / (np.linalg.norm(axis) + 1e-8)
    vec = np.asarray(vec, np.float64)
    return (
        vec * math.cos(a)
        + np.cross(axis, vec) * math.sin(a)
        + axis * np.dot(axis, vec) * (1.0 - math.cos(a))
    )


def euler_basis(yaw_deg, pitch_deg, roll_deg):
    """Columns are the rocket's local X, Y, Z axes in world space."""
    y, p, r = map(math.radians, (yaw_deg, pitch_deg, roll_deg))
    cy, sy = math.cos(y), math.sin(y)
    cp, sp = math.cos(p), math.sin(p)
    cr, sr = math.cos(r), math.sin(r)
    ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]], np.float64)
    rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]], np.float64)
    rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]], np.float64)
    return rz @ rx @ ry


def ik2(base, target, l1, l2, pole):
    base = np.asarray(base, np.float64)
    target = np.asarray(target, np.float64)
    pole = np.asarray(pole, np.float64)
    delta = target - base
    dist = float(np.linalg.norm(delta))
    dist = min(max(dist, 1e-4), l1 + l2 - 1e-3)
    zhat = delta / (np.linalg.norm(delta) + 1e-8)
    x = pole - zhat * np.dot(pole, zhat)
    nx = float(np.linalg.norm(x))
    if nx < 1e-4:
        tmp = np.array([1.0, 0.0, 0.0]) if abs(zhat[0]) < 0.9 else np.array([0.0, 0.0, 1.0])
        x = tmp - zhat * np.dot(tmp, zhat)
        x /= np.linalg.norm(x) + 1e-8
    else:
        x /= nx
    cos_s = clamp( (dist * dist + l1 * l1 - l2 * l2) / (2.0 * dist * l1) )
    shoulder = math.acos(cos_s)
    elbow_dir = zhat * math.cos(shoulder) + x * math.sin(shoulder)
    elbow = base + elbow_dir * l1
    to_t = target - elbow
    hand = elbow + to_t / (np.linalg.norm(to_t) + 1e-8) * l2
    return base, elbow, hand


def clamp(x, lo=-1.0, hi=1.0):
    return max(lo, min(hi, x))


def claw_tips(elbow, hand, pole, open_amt):
    forward = hand - elbow
    forward = forward / (np.linalg.norm(forward) + 1e-8)
    side = np.cross(forward, pole)
    if np.linalg.norm(side) < 1e-4:
        side = np.cross(forward, np.array([0.0, 1.0, 0.0]))
    side = side / (np.linalg.norm(side) + 1e-8)
    spread = 0.045 + 0.11 * open_amt
    tip_l = hand + forward * 0.16 + side * spread
    tip_r = hand + forward * 0.16 - side * spread
    return tip_l, tip_r


def sample_keys(keys, t):
    if t <= keys[0][0]:
        return keys[0]
    if t >= keys[-1][0]:
        return keys[-1]
    for i in range(len(keys) - 1):
        t0 = keys[i][0]
        t1 = keys[i + 1][0]
        if t0 <= t <= t1:
            u = ease(t0, t1, t)
            out = [lerp(t0, t1, u)]
            for a, b in zip(keys[i][1:], keys[i + 1][1:]):
                if isinstance(a, (list, tuple, np.ndarray)):
                    out.append(vlerp(a, b, u))
                else:
                    out.append(lerp(float(a), float(b), u))
            return out
    return keys[-1]


def surface_y(x, z, center=MOON_C, radius=MOON_R):
    dx = x - center[0]
    dz = z - center[2]
    h2 = radius * radius - dx * dx - dz * dz
    if h2 <= 0.0:
        return center[1]
    return center[1] + math.sqrt(h2)


def moon_center(t):
    far = np.array([0.0, -2.0, -48.0])
    near = np.array(MOON_C, np.float64)
    u = ease(T_RISER, T_LAND, t)
    # Ease-in then a rush: bias the mix so the moon loiters, then commits.
    u = u * u * (3.0 - 2.0 * u)
    return vlerp(far, near, u), lerp(11.0, MOON_R, u)


def camera_at(t):
    keys = [
        (0.0, [0.0, 1.5, 9.2], [0.0, 1.0, 0.0], 42.0, 0.0),
        (T_IMPACT, [0.15, 1.35, 8.4], [0.0, 1.05, 2.0], 46.0, 0.0),
        (T_WELCOME, [1.8, 1.7, 6.4], [0.0, 1.0, 0.6], 40.0, -8.0),
        (12.0, [3.4, 1.9, 5.0], [0.0, 1.15, 0.0], 38.0, 10.0),
        (T_RISER, [0.3, 2.5, 8.0], [0.0, 1.1, 0.2], 46.0, -6.0),
        (T_DROP, [3.2, 2.3, 8.5], [0.0, 1.3, -4.0], 50.0, 0.0),
        (21.0, [1.4, 2.0, 6.2], [0.1, 1.2, -1.0], 48.0, 180.0),
        (T_LAND, [2.2, 1.25, 3.8], [0.15, 0.85, 0.05], 40.0, 360.0),
        (T_FINE, [2.6, 1.35, 4.3], [0.05, 0.9, 0.15], 38.0, 360.0),
        (T_CLINK, [2.2, 1.35, 4.6], [0.45, 1.15, -0.1], 40.0, 350.0),
        (T_GRAV, [1.2, 0.85, 6.6], [0.2, 1.7, 0.1], 42.0, 340.0),
        (T_BACK, [4.0, 2.05, 6.6], [0.15, 1.0, 0.0], 40.0, 360.0),
        (T_CARD, [3.6, 2.35, 8.2], [0.15, 1.05, 0.0], 42.0, 360.0),
        (60.0, [3.2, 2.2, 7.8], [0.1, 1.0, 0.05], 40.0, 360.0),
    ]
    _, eye, target, fov, roll = sample_keys(keys, t)
    return np.asarray(eye, np.float64), np.asarray(target, np.float64), float(fov), float(roll)


def rocket_at(t):
    keys = [
        (2.0, [0.0, 0.2, -0.4], 90.0, 0.0, 0.0, 1.0, 0.2),
        (T_HOLE + 0.4, [0.0, 0.15, 1.2], 90.0, 0.0, 0.0, 1.0, 0.8),
        (T_IMPACT, [0.0, 0.15, 3.6], 58.0, 18.0, 0.0, 0.8, 1.15),
        (T_HONK, [0.1, 0.2, 4.3], 48.0, -8.0, 0.0, 0.64, 1.0),
        (T_HONK + 0.35, [0.0, 0.1, 5.4], 84.0, 6.0, 0.0, 1.12, 0.7),
        (T_WELCOME, [0.1, -0.05, 1.6], 28.0, 18.0, 0.0, 1.0, 0.35),
        (12.4, [-0.05, -0.1, 0.15], 8.0, 24.0, 0.0, 1.0, 0.15),
        (T_RISER, [0.0, 0.15, 0.4], -20.0, 8.0, 0.0, 1.0, 0.7),
        (T_DROP, [0.0, 0.55, 1.4], -78.0, 0.0, 20.0, 1.0, 1.3),
        (21.0, [0.15, 0.85, 0.2], -35.0, 10.0, 200.0, 1.0, 1.2),
        (T_LAND, [0.0, -0.18, 0.05], 0.0, 16.0, 360.0, 0.68, 0.0),
        (T_LAND + 0.45, [0.0, -0.12, 0.05], 0.0, 18.0, 360.0, 1.08, 0.0),
        (T_LAND + 0.9, [0.0, -0.16, 0.05], 0.0, 20.0, 360.0, 1.0, 0.0),
        (60.0, [0.0, -0.16, 0.0], 0.0, 22.0, 360.0, 1.0, 0.0),
    ]
    _, pos, pitch, yaw, roll, squash, flame = sample_keys(keys, t)
    pos = np.asarray(pos, np.float64)
    if t >= T_LAND:
        # Sit the nozzle on the regolith, including the landing squash.
        pos = pos.copy()
        pos[1] = -0.16 + (squash - 1.0) * 0.25
    return pos, float(pitch), float(yaw), float(roll), float(squash), float(flame)


def party_positions(t, rocket_pos, basis):
    """Argon, triangle guest, knot. Affectionate, never flung off-screen."""
    # Entrance from the wings.
    ax = lerp(-4.2, -1.15, ease(7.4, T_ARGON + 0.6, t))
    tx = lerp(4.2, 1.15, ease(7.6, T_ARGON + 0.8, t))
    phase = (t - T_JUGGLE) * 2.35
    juggle = ease(T_JUGGLE, T_JUGGLE + 0.4, t) * (1.0 - ease(T_RISER, T_DROP, t))
    ay = 1.25 + math.sin(phase) * 0.9 * juggle
    ty = 1.25 + math.sin(phase + math.pi) * 0.9 * juggle
    argon = np.array([ax, ay, 0.25])
    tri = np.array([tx, ty, 0.15])
    knot = np.array([0.0, 1.7 + math.sin(t * 1.4) * 0.12, -0.35])

    # They grab on for the flight.
    ride = ease(T_RISER + 0.3, T_DROP + 0.3, t) * (1.0 - ease(T_LAND + 0.2, T_CHAIRS, t))
    if ride > 0.0:
        hold_a = rocket_pos + basis @ np.array([-0.62, 0.85, 0.12])
        hold_t = rocket_pos + basis @ np.array([0.62, 0.85, 0.08])
        hold_k = rocket_pos + basis @ np.array([0.0, 1.45, 0.0])
        argon = vlerp(argon, hold_a, ride)
        tri = vlerp(tri, hold_t, ride)
        knot = vlerp(knot, hold_k, ride)

    # Lawn chairs, close to the nose so the curved ground still meets them.
    sit = ease(T_LAND + 0.4, T_CHAIRS + 0.7, t)
    chair_a = np.array([-1.85, 0.0, 0.85])
    chair_t = np.array([1.75, 0.0, 0.55])
    if t > T_LAND:
        chair_a[1] = surface_y(chair_a[0], chair_a[2]) + 0.02
        chair_t[1] = surface_y(chair_t[0], chair_t[2]) + 0.02
    argon = vlerp(argon, chair_a + np.array([0.0, 0.72, 0.02]), sit)
    tri = vlerp(tri, chair_t + np.array([0.0, 0.68, 0.02]), sit)
    knot_flag = np.array([1.05, 1.55, -0.15])
    knot = vlerp(knot, knot_flag, ease(T_FLAG, T_FLAG + 1.2, t))

    show_a = ease(7.2, 8.2, t)
    show_t = ease(7.4, 8.4, t)
    show_k = ease(T_ARGON, T_ARGON + 0.8, t)
    return argon, tri, knot, chair_a, chair_t, show_a, show_t, show_k, sit


def banana_at(t, flag_pos):
    show = ease(T_BANANA, T_BANANA + 0.6, t)
    ang = (t - T_BANANA) * 1.6
    orbit = flag_pos + np.array(
        [math.cos(ang) * 0.72, 0.55 + math.sin(t * 3.0) * 0.06, math.sin(ang) * 0.72]
    )
    # Caught, then split toward the guests.
    caught = ease(T_CRUNCH - 0.45, T_CRUNCH, t)
    mid = np.array([0.0, 1.15, 0.7])
    pos = vlerp(orbit, mid, caught)
    split = ease(T_CRUNCH, T_SNACK + 0.4, t)
    yaw = math.degrees(ang) + 90.0
    return pos, yaw, split, show


def moon2_at(t):
    show = ease(T_MOON2 - 0.2, T_MOON2 + 0.5, t)
    start = np.array([6.5, 3.4, -1.2])
    clink = np.array([2.15, 1.85, 0.35])
    rest = np.array([2.45, 1.55, -0.15])
    u1 = ease(T_MOON2, T_CLINK, t)
    u2 = ease(T_CLINK, T_CLINK + 1.4, t)
    pos = vlerp(vlerp(start, clink, u1), rest, u2)
    # A little recoil on the clink.
    if T_CLINK <= t <= T_CLINK + 0.35:
        pos = pos + np.array([0.18, 0.12, 0.0]) * math.sin((t - T_CLINK) * 28.0) * (1.0 - (t - T_CLINK) / 0.35)
    radius = 0.72
    return pos, radius, show


def lift_amount(t):
    up = ease(T_GRAV, T_GRAV + 0.9, t)
    down = ease(T_BACK - 0.8, T_BACK, t)
    return up * (1.0 - down) * 1.55


def arm_pair(t, rocket_pos, basis, argon, tri, banana, flag_pos, squash):
    # Shoulders ride the body. Squash shortens Y a touch.
    sy = 0.95 * (0.65 + 0.35 * squash)
    shoulder_l = rocket_pos + basis @ np.array([-0.36, sy, 0.02])
    shoulder_r = rocket_pos + basis @ np.array([0.36, sy, 0.02])
    pole_l = basis @ np.array([-1.0, 0.35, 0.4])
    pole_r = basis @ np.array([1.0, 0.35, 0.4])

    wave = math.sin(t * 5.0) * 0.35
    if t < T_WELCOME:
        tgt_l = rocket_pos + np.array([-0.9, 0.35, 1.35])
        tgt_r = rocket_pos + np.array([0.95, 0.45 + wave, 1.25])
        open_l = open_r = 1.0
    elif t < T_JUGGLE:
        tgt_l = shoulder_l + basis @ np.array([-0.15, 0.55 + wave, 0.45])
        tgt_r = shoulder_r + basis @ np.array([0.15, 0.5 - wave, 0.5])
        open_l = open_r = 0.8
    elif t < T_RISER:
        tgt_l = argon + np.array([0.15, 0.0, 0.15])
        tgt_r = tri + np.array([-0.15, 0.0, 0.15])
        open_l = open_r = 0.25
    elif t < T_FLAG:
        tgt_l = argon
        tgt_r = tri
        open_l = open_r = 0.15
    elif t < T_CHAIRS + 0.8:
        tgt_r = flag_pos + np.array([0.05, 0.85, 0.0])
        tgt_l = shoulder_l + basis @ np.array([-0.25, 0.45, 0.55])
        open_l, open_r = 0.7, 0.2
    elif t < T_CRUNCH - 0.3:
        tgt_l = shoulder_l + basis @ np.array([-0.45, 0.15, 0.6])
        tgt_r = banana
        open_l, open_r = 0.5, 0.35
    elif t < T_BACK:
        tgt_l = argon + np.array([0.25, 0.05, 0.2])
        tgt_r = tri + np.array([-0.25, 0.05, 0.2])
        open_l = open_r = 0.55
    else:
        tgt_l = shoulder_l + basis @ np.array([-0.2, 0.6 + wave, 0.4])
        tgt_r = shoulder_r + basis @ np.array([0.35, 0.35, 0.55])
        open_l = open_r = 0.85

    l1, l2 = 0.58, 0.52
    b0, e0, h0 = ik2(shoulder_l, tgt_l, l1, l2, pole_l)
    b1, e1, h1 = ik2(shoulder_r, tgt_r, l1, l2, pole_r)
    c0, c1 = claw_tips(e0, h0, pole_l, open_l)
    c2, c3 = claw_tips(e1, h1, pole_r, open_r)
    left = np.stack([b0, e0, h0, c0, c1]).astype(np.float64)
    right = np.stack([b1, e1, h1, c2, c3]).astype(np.float64)
    return left, right


def shock_at(t):
    events = [(T_IMPACT, 0.7), (T_LAND, 0.7), (T_CLINK, 0.45)]
    radius = 0.0
    glow = 0.0
    for t0, dur in events:
        if t0 <= t <= t0 + dur:
            u = (t - t0) / dur
            radius = max(radius, lerp(0.2, 1.8, u))
            glow = max(glow, max(0.0, 1.0 - u) ** 1.4)
    return radius, glow


def shake_at(t):
    amp = 0.0
    for t0, mag, dur in (
        (T_IMPACT, 0.16, 0.5),
        (T_HONK, 0.09, 0.28),
        (T_LAND, 0.2, 0.6),
        (T_CLINK, 0.07, 0.3),
        (56.8, 0.05, 0.2),
    ):
        dt = t - t0
        if 0.0 < dt < dur:
            amp += mag * (1.0 - dt / dur)
    if amp < 1e-4:
        return np.zeros(3)
    return np.array(
        [math.sin(t * 97.0), math.cos(t * 81.0), math.sin(t * 63.0) * 0.3]
    ) * amp


def look_target(t, argon, tri, banana, cam_target):
    if T_JUGGLE <= t < T_RISER:
        return (argon + tri) * 0.5
    if T_BANANA <= t < T_CRUNCH:
        return banana
    if t >= T_CHAIRS:
        return (argon + tri) * 0.5
    return cam_target


def stage(t):
    eye, target, fov, roll = camera_at(t)
    shake = shake_at(t)
    if t < T_GLITCH:
        shake[:] = 0.0
    eye = eye + shake

    rpos, pitch, yaw, rroll, squash, flame = rocket_at(t)
    basis = euler_basis(yaw, pitch, rroll)

    argon, tri, knot, chair_a, chair_b, show_a, show_t, show_k, sit = party_positions(
        t, rpos, basis
    )
    m2, m2r, show_m2 = moon2_at(t)
    mcenter, mradius = moon_center(t)
    show_moon = 1.0 if t > T_RISER - 0.4 else 0.0

    flag = np.array([0.95, 0.0, -0.35])
    if t >= T_LAND - 0.2:
        flag[1] = surface_y(flag[0], flag[2])
    ban_pos, ban_yaw, ban_split, ban_show = banana_at(t, flag + np.array([0.0, 0.9, 0.0]))

    lift = lift_amount(t)
    if lift > 0.0:
        for arr in (argon, tri, chair_a, chair_b, ban_pos, m2, knot):
            arr[1] += lift
        # Rocket stays planted. Flag stays planted. That is the joke.

    # After landing, plant the rocket on the real surface.
    if t >= T_LAND:
        rpos = rpos.copy()
        rpos[1] = surface_y(rpos[0], rpos[2]) - 0.18 + (squash - 1.0) * 0.2

    arms_l, arms_r = arm_pair(t, rpos, basis, argon, tri, ban_pos, flag, squash)
    look = look_target(t, argon, tri, ban_pos, target)

    hole = ease(T_HOLE, T_IMPACT, t) * 0.34
    glitch = 0.0
    if t >= T_GLITCH:
        glitch = ease(T_GLITCH, T_GLITCH + 0.45, t)
        glitch *= 1.0 - ease(T_IMPACT, T_IMPACT + 1.1, t)
        glitch = max(glitch, 0.85 * ease(T_GLITCH + 0.2, T_HOLE, t) * (1.0 - ease(T_IMPACT + 0.2, T_IMPACT + 1.3, t)))
    photo = 1.0 - ease(T_IMPACT - 0.05, T_IMPACT + 0.85, t)
    if t < T_GLITCH:
        photo = 1.0
        glitch = 0.0
        hole = 0.0
    hud = ease(T_IMPACT + 0.55, T_IMPACT + 1.25, t)
    card = ease(T_CARD, T_CARD + 1.15, t)
    streaks = ease(T_DROP - 0.15, T_DROP + 0.3, t) * (1.0 - ease(T_LAND - 0.6, T_LAND, t))
    chaos = ease(T_VIBES, T_VIBES + 0.5, t) * (1.0 - ease(T_DROP, T_DROP + 1.0, t))
    shades = ease(T_SHADES, T_SHADES + 0.18, t)
    flag_show = ease(T_FLAG, T_FLAG + 0.7, t)
    shock_r, shock_g = shock_at(t)
    show_rocket = 1.0 if t >= T_HOLE - 0.05 else 0.0

    # Pupil / face squash lives on the rocket.
    return {
        "eye": eye,
        "target": target,
        "fov": fov,
        "roll": roll,
        "rocket_pos": rpos,
        "basis": basis,
        "squash": squash,
        "flame": flame if show_rocket else 0.0,
        "show_rocket": show_rocket,
        "look": look,
        "arm_l": arms_l,
        "arm_r": arms_r,
        "argon": argon,
        "tri": tri,
        "knot": knot,
        "show_argon": show_a,
        "show_tri": show_t,
        "show_knot": show_k,
        "chair_a": chair_a,
        "chair_b": chair_b,
        "show_chairs": sit,
        "moon_c": mcenter,
        "moon_r": mradius,
        "show_moon": show_moon,
        "moon2": m2,
        "moon2_r": m2r,
        "show_moon2": show_m2,
        "flag": flag,
        "show_flag": flag_show,
        "banana": ban_pos,
        "banana_yaw": ban_yaw,
        "banana_split": ban_split,
        "show_banana": ban_show,
        "shades": shades,
        "chaos": chaos,
        "hole": hole,
        "glitch": glitch,
        "photo": photo,
        "hud": hud * (1.0 - 0.35 * card),
        "card": card,
        "streaks": streaks,
        "shock_r": shock_r,
        "shock_g": shock_g,
        "lift": lift,
        "ground": surface_y(0.0, 0.0) if t >= T_LAND else float(rpos[1]),
    }

