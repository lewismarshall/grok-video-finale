"""GPU finale: raymarched party, bloom, HUD, piped to ffmpeg."""

import math
import subprocess
import sys
import time
from pathlib import Path

import moderngl
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))

from config import (  # noqa: E402
    DURATION,
    FPS,
    FRAMES,
    HEIGHT,
    SCENE_H,
    SCENE_W,
    T_ARGON,
    T_CARD,
    T_CLINK,
    T_CRUNCH,
    T_DROP,
    T_FLAG,
    T_GLITCH,
    T_HOLE,
    T_IMPACT,
    T_LAND,
    T_STAMP,
    WIDTH,
)
from stage import rotate_around, stage  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
SHADER = Path(__file__).resolve().parent / "shaders"
OUT = ROOT / "out"
FONT_BLACK = "/System/Library/Fonts/Supplemental/Arial Black.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_MONO = "/System/Library/Fonts/Supplemental/Andale Mono.ttf"

CAPTIONS = [
    (4.00, 5.15, "KNOCK KNOCK."),
    (5.20, 7.05, "HONK."),
    (7.20, 8.70, "YOU'RE WELCOME."),
    (8.80, 11.35, "ARGON: UNBOTHERED."),
    (11.50, 13.50, "SPHERES ARE JUST VERY BUSY TRIANGLES."),
    (13.60, 15.10, "g = 9.81 m/s²"),
    (15.20, 16.70, "g = VIBES"),
    (16.80, 18.30, "HOLD ON TO YOUR ELECTRONS."),
    (18.40, 22.90, "THE MOON COMPROMISED."),
    (23.20, 26.20, "384400 km. STILL METRIC."),
    (26.40, 29.20, "FLAG: PLANTED. POLITELY."),
    (29.60, 32.20, "THEY'RE FINE."),
    (32.80, 36.40, "PLUS ONE: ALSO A MOON."),
    (37.60, 40.60, "GRAVITY ASKED FOR PTO."),
    (40.80, 43.80, "SNACKS WERE SHARED."),
    (44.00, 47.05, "NO PROJECTORS WERE HARMED."),
]

CREDITS = [
    ("GEMINI 4 ARGON", True),
    ("the noble gas who started it", False),
    ("DEEPSEEK", True),
    ("still just triangles, now with snacks", False),
    ("GROK 4.7", True),
    ("uninvited, metric, and sharing", False),
]


def ease(a, b, t):
    if t <= a:
        return 0.0
    if t >= b:
        return 1.0
    x = (t - a) / (b - a)
    return x * x * (3.0 - 2.0 * x)


def load_shader(name):
    return (SHADER / name).read_text()


def upload_image(ctx, image, nearest=False):
    arr = np.flipud(np.asarray(image.convert("RGBA")))
    tex = ctx.texture((image.width, image.height), 4, arr.tobytes())
    filt = moderngl.NEAREST if nearest else moderngl.LINEAR
    tex.filter = (filt, filt)
    tex.repeat_x = False
    tex.repeat_y = False
    return tex


def text_image(text, font, fill, pad=(22, 12), bg=(5, 12, 22, 190), outline=(90, 210, 255, 230)):
    probe = ImageDraw.Draw(Image.new("RGBA", (4, 4)))
    box = probe.textbbox((0, 0), text, font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    w, h = tw + pad[0] * 2, th + pad[1] * 2
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    if bg is not None:
        draw.rounded_rectangle((1, 1, w - 2, h - 2), radius=16, fill=bg, outline=outline, width=2)
    draw.text((pad[0] - box[0], pad[1] - box[1]), text, font=font, fill=fill)
    return img


def centered(draw, text, y, font, fill, width=WIDTH):
    box = draw.textbbox((0, 0), text, font=font)
    x = (width - (box[2] - box[0])) / 2 - box[0]
    draw.text((x, y), text, font=font, fill=fill)


def make_flag():
    img = Image.new("RGBA", (512, 256), (255, 84, 58, 255))
    draw = ImageDraw.Draw(img)
    draw.ellipse((28, 78, 108, 158), fill=(255, 255, 255, 255))
    font = ImageFont.truetype(FONT_BLACK, 118)
    draw.text((130, 52), "GROK", font=font, fill=(255, 255, 255, 255))
    return img


def make_stamp():
    img = Image.new("RGBA", (460, 170), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((6, 6, 453, 163), radius=14, outline=(255, 72, 64, 255), width=7)
    font = ImageFont.truetype(FONT_BLACK, 68)
    box = draw.textbbox((0, 0), "APPROVED", font=font)
    x = (460 - (box[2] - box[0])) / 2 - box[0]
    y = (170 - (box[3] - box[1])) / 2 - box[1]
    draw.text((x, y), "APPROVED", font=font, fill=(255, 72, 64, 255))
    return img


def make_card():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        (110, 492, 1810, 1028),
        radius=34,
        fill=(5, 12, 24, 236),
        outline=(70, 200, 235, 255),
        width=3,
    )
    centered(draw, "GROK 4.7", 528, ImageFont.truetype(FONT_BLACK, 92), (255, 255, 255, 255))
    centered(
        draw,
        "I BROUGHT ROCKETS TO A TRIANGLE FIGHT.",
        640,
        ImageFont.truetype(FONT_BOLD, 36),
        (120, 225, 255, 255),
    )
    centered(
        draw,
        "Argon kept the electrons.  DeepSeek kept the corners.  I kept the receipt.",
        688,
        ImageFont.truetype(FONT_BOLD, 24),
        (255, 186, 90, 255),
    )
    footer = ImageFont.truetype(FONT_MONO, 22)
    centered(draw, "RENDERED ENTIRELY IN CODE", 918, footer, (120, 225, 255, 255))
    centered(draw, "1920×1080    ·    30 FPS    ·    AAC    ·    ZERO STOCK MEDIA", 952, footer, (255, 186, 90, 255))
    centered(draw, "ONE MOON LIGHTLY DINGED.    SNACKS WERE SHARED.", 986, footer, (200, 216, 230, 255))
    return img


def make_poster_overlay():
    img = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, 0, WIDTH, 210), fill=(6, 10, 18, 255))
    draw.rectangle((0, 800, WIDTH, HEIGHT), fill=(6, 10, 18, 255))
    centered(draw, "GROK FINALE", 48, ImageFont.truetype(FONT_BLACK, 84), (255, 255, 255, 255))
    centered(
        draw,
        "ARGON KEPT IT NOBLE   ·   DEEPSEEK KEPT THE TRIANGLES   ·   GROK BROUGHT THE MOON",
        150,
        ImageFont.truetype(FONT_BOLD, 26),
        (120, 225, 255, 255),
    )
    centered(draw, "A 60-SECOND PARTY CRASH, RENDERED ENTIRELY IN CODE", 940, ImageFont.truetype(FONT_MONO, 22), (255, 186, 90, 255))
    centered(draw, "1920×1080   ·   30 FPS   ·   METRIC THROUGHOUT", 978, ImageFont.truetype(FONT_MONO, 20), (200, 216, 230, 255))
    return img


class Particles:
    def __init__(self, n=7000):
        self.n = n
        self.pos = np.zeros((n, 3), np.float32)
        self.vel = np.zeros((n, 3), np.float32)
        self.col = np.zeros((n, 4), np.float32)
        self.size = np.zeros(n, np.float32)
        self.life = np.zeros(n, np.float32)
        self.maxlife = np.ones(n, np.float32)
        self.cursor = 0
        self.rng = np.random.default_rng(7)

    def spawn(self, pos, vel, col, size, life):
        pos = np.atleast_2d(np.asarray(pos, np.float32))
        count = pos.shape[0]
        idx = (np.arange(count) + self.cursor) % self.n
        self.cursor = int((self.cursor + count) % self.n)
        self.pos[idx] = pos
        self.vel[idx] = np.atleast_2d(np.asarray(vel, np.float32))
        c = np.atleast_2d(np.asarray(col, np.float32))
        if c.shape[0] == 1 and count > 1:
            c = np.repeat(c, count, axis=0)
        self.col[idx] = c
        self.size[idx] = size
        self.life[idx] = life
        self.maxlife[idx] = np.maximum(life, 1e-3)

    def burst(self, origin, count, speed, colors, size, life, upward=0.0):
        origin = np.asarray(origin, np.float32)
        pos = origin + self.rng.normal(0, 0.12, size=(count, 3)).astype(np.float32)
        vel = self.rng.normal(0, 1, size=(count, 3)).astype(np.float32)
        vel /= np.linalg.norm(vel, axis=1, keepdims=True) + 1e-6
        vel *= self.rng.uniform(0.3, 1.0, size=(count, 1)).astype(np.float32) * speed
        vel[:, 1] += upward
        col = np.asarray(colors, np.float32)[self.rng.integers(0, len(colors), count)]
        self.spawn(pos, vel, col, size, life)

    def update(self, dt, grav):
        alive = self.life > 0.0
        if not np.any(alive):
            return
        self.vel[alive, 1] += np.float32(grav * dt)
        self.pos[alive] += self.vel[alive] * np.float32(dt)
        self.vel[alive] *= np.float32(max(0.0, 1.0 - 0.7 * dt))
        self.life[alive] -= np.float32(dt)

    def pack(self):
        idx = np.nonzero(self.life > 0.0)[0]
        if idx.size == 0:
            return np.zeros((0, 4), np.float32), np.zeros((0, 4), np.float32)
        fade = np.clip(self.life[idx] / self.maxlife[idx], 0.0, 1.0).astype(np.float32)
        pos = np.zeros((idx.size, 4), np.float32)
        pos[:, :3] = self.pos[idx]
        pos[:, 3] = self.size[idx] * (0.35 + 0.65 * fade)
        col = self.col[idx].copy()
        col[:, 3] *= fade
        return pos, col


def crossed(prev, t, cue):
    return prev < cue <= t


def camera_basis(st):
    eye = np.asarray(st["eye"], np.float64)
    target = np.asarray(st["target"], np.float64)
    forward = target - eye
    forward /= np.linalg.norm(forward) + 1e-9
    world_up = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, world_up)
    if np.linalg.norm(right) < 1e-5:
        world_up = np.array([1.0, 0.0, 0.0])
        right = np.cross(forward, world_up)
    right /= np.linalg.norm(right)
    up = np.cross(right, forward)
    up /= np.linalg.norm(up)
    up = rotate_around(up, forward, st["roll"])
    right = np.cross(forward, up)
    right /= np.linalg.norm(right) + 1e-9
    up = np.cross(right, forward)
    up /= np.linalg.norm(up) + 1e-9
    z = -forward
    view = np.eye(4)
    view[0, :3] = right
    view[1, :3] = up
    view[2, :3] = z
    view[0, 3] = -np.dot(right, eye)
    view[1, 3] = -np.dot(up, eye)
    view[2, 3] = -np.dot(z, eye)
    aspect = SCENE_W / SCENE_H
    near, far = 0.06, 200.0
    f = 1.0 / math.tan(math.radians(st["fov"]) * 0.5)
    proj = np.zeros((4, 4))
    proj[0, 0] = f / aspect
    proj[1, 1] = f
    proj[2, 2] = (far + near) / (near - far)
    proj[2, 3] = (2.0 * far * near) / (near - far)
    proj[3, 2] = -1.0
    return view, proj, forward, right, up


def u3(prog, name, xyz):
    prog[name].value = (float(xyz[0]), float(xyz[1]), float(xyz[2]))


def uf(prog, name, value):
    prog[name].value = float(value)


def umat(prog, name, matrix):
    prog[name].write(np.ascontiguousarray(matrix.T, dtype=np.float32))


def quad(x, y, w, h):
    return np.array(
        [
            x, y, 0, 1,
            x + w, y, 1, 1,
            x + w, y + h, 1, 0,
            x, y, 0, 1,
            x + w, y + h, 1, 0,
            x, y + h, 0, 0,
        ],
        np.float32,
    )


def rotated_quad(cx, cy, w, h, deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    corners = [(-w / 2, -h / 2, 0, 1), (w / 2, -h / 2, 1, 1), (w / 2, h / 2, 1, 0), (-w / 2, h / 2, 0, 0)]
    pts = []
    for px, py, u, v in corners:
        pts.append((cx + px * c - py * s, cy + px * s + py * c, u, v))
    order = (0, 1, 2, 0, 2, 3)
    data = []
    for i in order:
        data.extend(pts[i])
    return np.array(data, np.float32)


class Film:
    def __init__(self):
        self.ctx = moderngl.create_context(standalone=True, require=410)
        self.ctx.enable(moderngl.PROGRAM_POINT_SIZE)
        vs = load_shader("fullscreen.vert")
        self.scene = self.ctx.program(vertex_shader=vs, fragment_shader=load_shader("scene.frag"))
        self.threshold = self.ctx.program(vertex_shader=vs, fragment_shader=load_shader("threshold.frag"))
        self.blur = self.ctx.program(vertex_shader=vs, fragment_shader=load_shader("blur.frag"))
        self.composite = self.ctx.program(vertex_shader=vs, fragment_shader=load_shader("composite.frag"))
        self.particles = self.ctx.program(
            vertex_shader=load_shader("particle.vert"),
            fragment_shader=load_shader("particle.frag"),
        )
        self.text = self.ctx.program(
            vertex_shader=load_shader("text.vert"),
            fragment_shader=load_shader("text.frag"),
        )
        self.fullscreen = self.ctx.vertex_array(self.scene, [])
        self.fs_threshold = self.ctx.vertex_array(self.threshold, [])
        self.fs_blur = self.ctx.vertex_array(self.blur, [])
        self.fs_composite = self.ctx.vertex_array(self.composite, [])
        self.scene_fbo, self.scene_tex = self._fbo(SCENE_W, SCENE_H, depth=True)
        self.half_a, self.half_a_tex = self._fbo(SCENE_W // 2, SCENE_H // 2)
        self.half_b, self.half_b_tex = self._fbo(SCENE_W // 2, SCENE_H // 2)
        self.out_tex = self.ctx.texture((WIDTH, HEIGHT), 4)
        self.out_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.out_fbo = self.ctx.framebuffer(color_attachments=[self.out_tex])
        self.ppos = self.ctx.buffer(reserve=7000 * 16)
        self.pcol = self.ctx.buffer(reserve=7000 * 16)
        self.pvao = self.ctx.vertex_array(
            self.particles,
            [(self.ppos, "4f", "aPosSize"), (self.pcol, "4f", "aColor")],
        )
        self.tbuf = self.ctx.buffer(reserve=4096)
        self.tvao = self.ctx.vertex_array(self.text, [(self.tbuf, "2f 2f", "aPos", "aUV")])
        photo = Image.open(OUT / "last_deepseek.png").convert("RGBA")
        self.photo = upload_image(self.ctx, photo, nearest=True)
        self.flag = upload_image(self.ctx, make_flag())
        self.card = upload_image(self.ctx, make_card())
        self.stamp = upload_image(self.ctx, make_stamp())
        self.poster_ov = upload_image(self.ctx, make_poster_overlay())
        font_cap = ImageFont.truetype(FONT_BLACK, 46)
        self.captions = [(a, b, upload_image(self.ctx, text_image(text, font_cap, (255, 255, 255, 255)))) for a, b, text in CAPTIONS]
        font_name = ImageFont.truetype(FONT_BLACK, 42)
        font_sub = ImageFont.truetype(FONT_BOLD, 26)
        self.credits = []
        for text, big in CREDITS:
            font = font_name if big else font_sub
            fill = (255, 255, 255, 255) if big else (120, 225, 255, 255)
            img = text_image(text, font, fill, pad=(8, 4), bg=None, outline=None)
            self.credits.append(upload_image(self.ctx, img))
        self.hud_font = ImageFont.truetype(FONT_MONO, 22)
        self.hud_font_sm = ImageFont.truetype(FONT_MONO, 18)
        self.bands = np.zeros((FRAMES, 32), np.float32)
        band_path = OUT / "bands.npy"
        if band_path.exists():
            self.bands = np.load(band_path)
        self.band_tex = self.ctx.texture((32, 1), 1, dtype="f4")
        self.band_tex.filter = (moderngl.NEAREST, moderngl.NEAREST)
        self.scene["uFlagTex"].value = 4
        self.composite["uScene"].value = 1
        self.composite["uBloom"].value = 2
        self.composite["uPhoto"].value = 0
        self.composite["uBands"].value = 3
        self.threshold["uTex"].value = 1
        self.blur["uTex"].value = 2
        self.text["uTex"].value = 5
        self.dummy_hud = upload_image(self.ctx, Image.new("RGBA", (4, 4), (0, 0, 0, 0)))
        self.hud_top_tex = None
        self.hud_bot_tex = None
        self._time = 0.0
        self._bloom_tex = self.half_a_tex

    def _fbo(self, w, h, depth=False):
        color = self.ctx.texture((w, h), 4, dtype="f2")
        color.filter = (moderngl.LINEAR, moderngl.LINEAR)
        color.repeat_x = False
        color.repeat_y = False
        if depth:
            fbo = self.ctx.framebuffer(color_attachments=[color], depth_attachment=self.ctx.depth_renderbuffer((w, h)))
        else:
            fbo = self.ctx.framebuffer(color_attachments=[color])
        return fbo, color

    def draw_fs(self, vao):
        vao.render(moderngl.TRIANGLES, vertices=3)

    def draw_tex(self, tex, data, alpha=1.0):
        self.tbuf.orphan(size=max(data.nbytes, 64))
        self.tbuf.write(data.tobytes())
        tex.use(5)
        self.text["uAlpha"].value = float(alpha)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.tvao.render(moderngl.TRIANGLES, vertices=6)

    def hud_textures(self, frame, t, st):
        top = Image.new("RGBA", (WIDTH, 56), (0, 0, 0, 0))
        draw = ImageDraw.Draw(top)
        sec, ff = divmod(frame, FPS)
        tc = f"TC  00:00:{sec:02d}:{ff:02d}"
        frm = "FRM  YES" if t >= 50.0 else f"FRM  {1800 + frame:04d}"
        if t < T_IMPACT:
            act = "ACT 00  //  INCOMING"
        elif t < T_ARGON:
            act = "ACT 01  //  KNOCK KNOCK"
        elif t < T_DROP:
            act = "ACT 02  //  GUESTS OF HONOUR"
        elif t < T_LAND:
            act = "ACT 03  //  MOON, INBOUND"
        elif t < 37.6:
            act = "ACT 04  //  PICNIC"
        elif t < T_CARD:
            act = "ACT 05  //  PTO"
        else:
            act = "ACT 06  //  SIGN-OFF"
        draw.text((48, 8), "GROK  //  ENGINE", font=self.hud_font, fill=(230, 244, 255, 255))
        box = draw.textbbox((0, 0), act, font=self.hud_font)
        draw.text(((WIDTH - (box[2] - box[0])) / 2, 8), act, font=self.hud_font, fill=(120, 225, 255, 255))
        right = f"{tc}     {frm}"
        box = draw.textbbox((0, 0), right, font=self.hud_font)
        draw.text((WIDTH - 48 - (box[2] - box[0]), 8), right, font=self.hud_font, fill=(230, 244, 255, 255))
        bot = Image.new("RGBA", (WIDTH, 40), (0, 0, 0, 0))
        if st["card"] < 0.35:
            bd = ImageDraw.Draw(bot)
            if t < T_IMPACT:
                status = "INCOMING    //    PLEASE REMAIN NOBLE"
            elif t < 8.8:
                status = "STATUS: UNINVITED     SNACKS: PACKED"
            elif t < 13.6:
                status = "GUESTS: ARGON + DEEPSEEK     MOOD: FOND"
            elif t < 15.2:
                status = "g = 9.81 m/s²"
            elif t < T_DROP:
                status = "g = VIBES     //     ELECTRONS HANGING ON"
            elif t < T_LAND:
                status = "THE MOON IS DOING THE TRAVELLING"
            elif t < 29.6:
                status = "384400 km     STILL METRIC"
            elif t < 37.6:
                status = "MOONS: 2     CHAIRS: 2     SNACKS: 1"
            elif t < 44.0:
                status = "GRAVITY: ON PTO"
            else:
                status = "GRAVITY: BACK     SNACKS: SHARED"
            bd.text((48, 4), status, font=self.hud_font_sm, fill=(255, 186, 90, 255))
        self.hud_top_tex = self._replace_tex(self.hud_top_tex, top)
        self.hud_bot_tex = self._replace_tex(self.hud_bot_tex, bot)
        return self.hud_top_tex, self.hud_bot_tex

    def _replace_tex(self, tex, image):
        arr = np.flipud(np.ascontiguousarray(np.asarray(image.convert("RGBA"))))
        if tex is None or tex.size != (image.width, image.height):
            if tex is not None:
                tex.release()
            return upload_image(self.ctx, image)
        tex.write(arr.tobytes())
        return tex

    def render_frame(self, frame, t, prev_t, parts, prev_eye, poster=False):
        self._time = t
        st = stage(t)
        view, proj, forward, right, up = camera_basis(st)
        self.band_tex.write(np.ascontiguousarray(self.bands[min(frame, FRAMES - 1)], dtype=np.float32))
        need = t >= T_HOLE - 0.2
        self.scene_fbo.use()
        self.ctx.disable(moderngl.BLEND)
        self.ctx.enable(moderngl.DEPTH_TEST)
        self.ctx.depth_func = "<="
        self.ctx.depth_mask = True
        self.scene_fbo.clear(0.004, 0.016, 0.038, 1.0, depth=1.0)
        if need:
            self._uniforms_scene(st, view, proj, forward, right, up)
            self.flag.use(4)
            self.draw_fs(self.fullscreen)
            self._spawn(parts, prev_t, t, st, forward)
            grav = 6.2 if st["lift"] > 0.35 else -3.4
            parts.update(1.0 / FPS, grav)
            pos, col = parts.pack()
            if pos.shape[0]:
                umat(self.particles, "uView", view)
                umat(self.particles, "uProj", proj)
                self.particles["uRes"].value = (SCENE_W, SCENE_H)
                self.ppos.write(pos.tobytes())
                self.pcol.write(col.tobytes())
                self.ctx.depth_mask = False
                self.ctx.enable(moderngl.BLEND)
                self.ctx.blend_func = moderngl.ONE, moderngl.ONE
                self.pvao.render(moderngl.POINTS, vertices=pos.shape[0])
                self.ctx.disable(moderngl.BLEND)
                self.ctx.depth_mask = True
        self._bloom()
        self.out_fbo.use()
        self.ctx.disable(moderngl.DEPTH_TEST)
        self.ctx.disable(moderngl.BLEND)
        blur = np.zeros(2, np.float32)
        if prev_eye is not None and need:
            vel = (st["eye"] - prev_eye) * FPS
            blur = np.array([np.dot(vel, right), np.dot(vel, up)], np.float32) * 0.0035
            mag = float(np.linalg.norm(blur))
            if mag > 0.014:
                blur *= 0.014 / mag
        self.scene_tex.use(1)
        self._bloom_tex.use(2)
        self.photo.use(0)
        self.band_tex.use(3)
        c = self.composite
        c["uRes"].value = (WIDTH, HEIGHT)
        uf(c, "uPhotoMix", 0.0 if poster else st["photo"])
        uf(c, "uGlitch", 0.0 if poster else st["glitch"])
        uf(c, "uHole", 0.0 if poster else st["hole"])
        uf(c, "uHud", 0.0 if poster else st["hud"])
        uf(c, "uCard", 0.0 if poster else st["card"])
        uf(c, "uStreaks", 0.0 if poster else st["streaks"])
        uf(c, "uTime", t)
        c["uBlur"].value = (float(blur[0]), float(blur[1]))
        self.draw_fs(self.fs_composite)
        self.ctx.enable(moderngl.BLEND)
        self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA
        self.text["uRes"].value = (float(WIDTH), float(HEIGHT))
        if poster:
            self.draw_tex(self.poster_ov, quad(0, 0, WIDTH, HEIGHT))
        else:
            if st["hud"] > 0.05:
                top, bot = self.hud_textures(frame, t, st)
                self.draw_tex(top, quad(0, 18, WIDTH, 56))
                self.draw_tex(bot, quad(0, 968, WIDTH, 40))
            for t0, t1, tex in self.captions:
                if t0 - 0.05 <= t <= t1 + 0.05 and st["card"] < 0.2:
                    a = ease(t0, t0 + 0.12, t) * (1.0 - ease(t1 - 0.14, t1, t))
                    if a <= 0.01:
                        continue
                    yoff = (1.0 - ease(t0, t0 + 0.22, t)) * 36.0
                    w, h = tex.size
                    x = (WIDTH - w) / 2
                    y = 860 + yoff
                    self.draw_tex(tex, quad(x, y, w, h), alpha=a)
            if st["card"] > 0.02:
                self.draw_tex(self.card, quad(0, 0, WIDTH, HEIGHT), alpha=st["card"])
                self._credits(t)
                if t >= T_STAMP - 0.05:
                    u = ease(T_STAMP, T_STAMP + 0.18, t)
                    bounce = 1.0
                    if t > T_STAMP + 0.18:
                        dt = t - (T_STAMP + 0.18)
                        bounce = 1.0 + 0.06 * math.sin(dt * 28.0) * math.exp(-dt * 7.0)
                    scale = (1.45 - 0.45 * u) * bounce
                    w, h = self.stamp.size
                    self.draw_tex(
                        self.stamp,
                        rotated_quad(1540, 760, w * 0.72 * scale, h * 0.72 * scale, -11),
                    )
        self.ctx.disable(moderngl.BLEND)
        self.ctx.scissor = None
        raw = self.out_fbo.read(components=3, alignment=1)
        image = np.flipud(np.frombuffer(raw, np.uint8).reshape(HEIGHT, WIDTH, 3))
        return image, st["eye"].copy()

    def _credits(self, t):
        if t < 49.0:
            return
        top, bot, row = 748, 880, 54
        self.ctx.scissor = (160, HEIGHT - bot, WIDTH - 320, bot - top)
        span = 56.6 - 49.4
        u = min(1.0, max(0.0, (t - 49.4) / span))
        total = len(self.credits) * row + (bot - top)
        base = bot - u * total
        for i, tex in enumerate(self.credits):
            w, h = tex.size
            y = base + i * row
            if y < top or y + h > bot:
                continue
            x = (WIDTH - w) / 2
            self.draw_tex(tex, quad(x, y, w, h))
        self.ctx.scissor = None

    def _uniforms_scene(self, st, view, proj, forward, right, up):
        p = self.scene
        p["uRes"].value = (SCENE_W, SCENE_H)
        uf(p, "uTime", self._time)
        uf(p, "uFov", st["fov"])
        uf(p, "uAspect", SCENE_W / SCENE_H)
        u3(p, "uCamPos", st["eye"])
        u3(p, "uForward", forward)
        u3(p, "uRight", right)
        u3(p, "uUp", up)
        u3(p, "uRocketPos", st["rocket_pos"])
        u3(p, "uRx", st["basis"][:, 0])
        u3(p, "uRy", st["basis"][:, 1])
        u3(p, "uRz", st["basis"][:, 2])
        uf(p, "uSquash", st["squash"])
        uf(p, "uFlame", st["flame"])
        uf(p, "uShowRocket", st["show_rocket"])
        u3(p, "uLook", st["look"])
        for i in range(5):
            u3(p, f"uAL{i}", st["arm_l"][i])
            u3(p, f"uAR{i}", st["arm_r"][i])
        u3(p, "uArgon", st["argon"])
        u3(p, "uTri", st["tri"])
        u3(p, "uKnot", st["knot"])
        uf(p, "uShowArgon", st["show_argon"])
        uf(p, "uShowTri", st["show_tri"])
        uf(p, "uShowKnot", st["show_knot"])
        uf(p, "uChaos", st["chaos"])
        u3(p, "uChairA", st["chair_a"])
        u3(p, "uChairB", st["chair_b"])
        uf(p, "uShowChairs", st["show_chairs"])
        u3(p, "uMoonC", st["moon_c"])
        uf(p, "uMoonR", st["moon_r"])
        uf(p, "uShowMoon", st["show_moon"])
        u3(p, "uMoon2", st["moon2"])
        uf(p, "uMoon2R", st["moon2_r"])
        uf(p, "uShowMoon2", st["show_moon2"])
        u3(p, "uFlag", st["flag"])
        uf(p, "uShowFlag", st["show_flag"])
        u3(p, "uBanana", st["banana"])
        uf(p, "uBananaYaw", st["banana_yaw"])
        uf(p, "uBananaSplit", st["banana_split"])
        uf(p, "uShowBanana", st["show_banana"])
        uf(p, "uShades", st["shades"])
        uf(p, "uShockR", st["shock_r"])
        uf(p, "uShockG", st["shock_g"])
        uf(p, "uGround", st["ground"])
        umat(p, "uView", view)
        umat(p, "uProj", proj)

    def _spawn(self, parts, prev, t, st, forward):
        if prev is None:
            prev = t - 1.0 / FPS
        colors = np.array(
            [
                [1.6, 2.0, 2.4, 0.9],
                [2.4, 1.1, 0.45, 0.9],
                [2.2, 2.2, 2.2, 0.85],
                [1.4, 0.7, 2.2, 0.9],
            ],
            np.float32,
        )
        if crossed(prev, t, T_IMPACT):
            origin = st["rocket_pos"] + forward * 0.4
            parts.burst(origin, 220, 5.0, colors, 0.12, 0.8, upward=1.0)
        if crossed(prev, t, T_LAND):
            parts.burst(st["rocket_pos"] + np.array([0, 0.2, 0]), 260, 3.2, colors[:3], 0.16, 1.6, upward=2.0)
        if crossed(prev, t, T_FLAG):
            parts.burst(st["flag"] + np.array([0.3, 1.2, 0]), 120, 2.6, colors, 0.14, 1.4, upward=2.2)
        if crossed(prev, t, T_CLINK):
            parts.burst(st["moon2"], 100, 2.0, colors, 0.12, 1.2, upward=0.8)
        if crossed(prev, t, T_CRUNCH):
            parts.burst(st["banana"], 90, 2.0, np.array([[2.2, 1.8, 0.4, 0.9]], np.float32), 10.0, 0.8, upward=1.4)
        if st["flame"] > 0.08 and st["show_rocket"] > 0.5:
            origin = st["rocket_pos"] + st["basis"] @ np.array([0.0, 0.22, 0.0])
            direction = st["basis"] @ np.array([0.0, -1.0, 0.0])
            n = 16
            jitter = parts.rng.normal(0, 0.05, size=(n, 3)).astype(np.float32)
            vel = direction * (1.2 + st["flame"] * 1.6) + parts.rng.normal(0, 0.25, size=(n, 3)).astype(np.float32)
            col = np.array([2.8, 1.15, 0.28, 0.95], np.float32)
            parts.spawn(origin + jitter, vel, col, 0.16, 0.28)
        if st["show_knot"] > 0.4 and int(t * FPS) % 2 == 0:
            parts.burst(st["knot"], 4, 0.4, colors[3:4], 8.0, 0.5, upward=0.2)

    def _bloom(self):
        self.half_a.use()
        self.scene_tex.use(1)
        self.threshold["uRes"].value = (SCENE_W // 2, SCENE_H // 2)
        self.draw_fs(self.fs_threshold)
        passes = (
            (self.half_a_tex, self.half_b, (1.0, 0.0)),
            (self.half_b_tex, self.half_a, (0.0, 1.0)),
            (self.half_a_tex, self.half_b, (1.0, 0.0)),
            (self.half_b_tex, self.half_a, (0.0, 1.0)),
        )
        for src, dst, direction in passes:
            dst.use()
            src.use(2)
            self.blur["uRes"].value = (SCENE_W // 2, SCENE_H // 2)
            self.blur["uDir"].value = direction
            self.draw_fs(self.fs_blur)
        self._bloom_tex = self.half_a_tex

    def frame_image(self, frame, t, prev_t, parts, prev_eye, poster=False):
        self._time = t
        return self.render_frame(frame, t, prev_t, parts, prev_eye, poster)


def save_png(path, rgb):
    Image.fromarray(rgb, "RGB").save(path)


def render_times(times):
    film = Film()
    # Fix bloom source: patch composite to use whichever texture _bloom left.
    parts = Particles()
    prev_eye = None
    prev_t = 0.0
    out_dir = Path("/tmp/finale-preview")
    out_dir.mkdir(exist_ok=True)
    for t in times:
        frame = int(round(t * FPS))
        frame = max(0, min(FRAMES - 1, frame))
        t0 = time.perf_counter()
        image, prev_eye = film.frame_image(frame, frame / FPS, prev_t, parts, prev_eye, poster=False)
        prev_t = frame / FPS
        # Use the bloom texture the pass actually produced.
        path = out_dir / f"t{t:05.2f}.png"
        save_png(path, image)
        print(f"preview {path}  {time.perf_counter() - t0:.2f}s  mean {image.mean():.1f}")


def render_movie(poster=True):
    film = Film()
    parts = Particles()
    wav = OUT / "finale.wav"
    log = open(OUT / "ffmpeg_finale.log", "w")
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
        "-i", "-",
        "-i", str(wav),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-preset", "veryfast",
        "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", "-shortest",
        str(OUT / "finale.mp4"),
    ]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=log)
    prev_eye = None
    prev_t = 0.0
    t0 = time.perf_counter()
    poster_rgb = None
    for frame in range(FRAMES):
        t = frame / FPS
        image, prev_eye = film.frame_image(frame, t, prev_t, parts, prev_eye, poster=False)
        prev_t = t
        proc.stdin.write(image.tobytes())
        if poster and abs(t - 45.8) < 0.5 / FPS:
            poster_rgb = image.copy()
        if frame % 30 == 0:
            elapsed = time.perf_counter() - t0
            fps = (frame + 1) / max(elapsed, 1e-6)
            remain = (FRAMES - frame) / max(fps, 1e-6)
            print(f"frame {frame:4d}/{FRAMES}  {fps:.2f} fps  ~{remain/60:.1f} min left", flush=True)
    proc.stdin.close()
    code = proc.wait()
    log.close()
    if code != 0:
        raise SystemExit(f"ffmpeg failed ({code}), see out/ffmpeg_finale.log")
    if poster_rgb is not None:
        base = Image.fromarray(poster_rgb, "RGB").convert("RGBA")
        over = make_poster_overlay()
        Image.alpha_composite(base, over).convert("RGB").save(OUT / "poster.png")
        print("poster", OUT / "poster.png")
    elapsed = time.perf_counter() - t0
    print(f"movie {elapsed:.1f}s")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    args = sys.argv[1:]
    if not args or args[0] == "--movie":
        render_movie(poster=True)
        return
    if args[0] == "--times":
        render_times([float(x) for x in args[1:]])
        return
    raise SystemExit("usage: render_finale.py [--movie | --times t ...]")


if __name__ == "__main__":
    main()
