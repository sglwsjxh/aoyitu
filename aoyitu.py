# Source Generated with Decompyle++
# File: aoyitu.pyc (Python 3.13)

'''
Aoyitu (奥义图) Animation Generator — All-in-One
================================================
Usage:
  python aoyitu.py -c clear.png -b blur.png -s subtitle.png
  python aoyitu.py -c clear.png -b blur.png -s subtitle.png --fps 30 -o out.gif
  python aoyitu.py --edit-xian    (launch xian placement tool)
  python aoyitu.py --edit-subtitle (launch subtitle positioning tool)

All sprite assets (gradient, noise, xian, subtitle bg) auto-loaded from
./Sprite/ folder or auto-generated if missing.
'''
import argparse
import os
import sys
import json
import math
import numpy as np
from PIL import Image, ImageFilter, ImageFont, ImageDraw

if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SPRITE_DIR = os.path.join(SCRIPT_DIR, 'Sprite')

_font_candidates = [
    os.path.join(SCRIPT_DIR, '方正艺黑_GBK.ttf'),
    os.path.join(SCRIPT_DIR, 'dist', '方正艺黑_GBK.ttf')]
FONT_PATH = None
for _fp in _font_candidates:
    if os.path.exists(_fp):
        FONT_PATH = _fp
        break

def _load_sprite(name):
    '''Load RGBA sprite, return None if not found.'''
    path = os.path.join(SPRITE_DIR, name)
    if os.path.exists(path):
        return np.array(Image.open(path).convert('RGBA'))
    return None


def _load_or_make(name, make_fn):
    '''Load sprite or auto-generate it.'''
    spr = _load_sprite(name)
    if spr is not None:
        return spr
    return make_fn()

def _make_gradient(char_h, char_w=None):
    '''Auto-generate black gradient (width = char_w / 5).'''
    if char_w is None:
        char_w = char_h
    gw = max(1, char_w // 5)
    g = np.zeros((char_h, gw, 4), dtype=np.uint8)
    for x in range(gw):
        g[:, x, 3] = np.array(255 * (1.0 - x / gw) ** 0.5, dtype=np.uint8)
    return g

def _make_noise():
    '''Auto-generate film grain (128x128 white dots).'''
    rng = np.random.default_rng(42)
    size = 128
    rgb = np.full((size, size, 3), 255, dtype=np.uint8)
    alpha = rng.integers(0, 57, (size, size), dtype=np.uint8)
    mask = rng.random((size, size)) > 0.34
    alpha[mask] = 0
    return np.dstack([rgb, alpha])


def _make_sub_bg():
    '''Auto-generate dark subtitle background bar.'''
    w, h = (293, 41)
    bg = np.zeros((h, w, 4), dtype=np.uint8)
    bg[:, :, :3] = 15
    bg[:, :, 3] = 130
    return bg

def _render_text_sprite(chinese_text, other_text, font_size, H, W, font_smooth=1.0):
    '''Render two-line subtitle text into a transparent RGBA sprite.'''
    if FONT_PATH is None:
        raise FileNotFoundError("Font '方正艺黑_GBK.ttf' not found.")
    font = ImageFont.truetype(FONT_PATH, font_size)
    text_area_h = int(60 * H / 320)
    base_w = int(264 * H / 320)
    tmp = Image.new('RGBA', (1, 1))
    tmp_draw = ImageDraw.Draw(tmp)
    cn_bbox = tmp_draw.textbbox((0, 0), chinese_text, font=font)
    cn_w = cn_bbox[2] - cn_bbox[0]
    ot_w = 0
    ot_h = 0
    if other_text:
        ot_bbox = tmp_draw.textbbox((0, 0), other_text, font=font)
        ot_w = ot_bbox[2] - ot_bbox[0]
        ot_h = ot_bbox[3] - ot_bbox[1]
    text_area_w = min(base_w, int(W * 0.85), max(base_w, max(cn_w, ot_w) + 4))
    sprite = Image.new('RGBA', (text_area_w, text_area_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(sprite)
    cn_x = (text_area_w - cn_w) // 2
    draw.text((cn_x, 0), chinese_text, fill=(255, 255, 255, 255), font=font)
    if other_text:
        ot_x = (text_area_w - ot_w) // 2
        ot_y = text_area_h - ot_h
        draw.text((ot_x, ot_y), other_text, fill=(255, 255, 255, 255), font=font)
    if abs(1.0 - font_smooth) > 0.01:
        from PIL import ImageFilter
        alpha = sprite.getchannel('A')
        if font_smooth < 1.0:
            radius = max(1, int(3 * (1.0 - font_smooth)))
            if radius > 0:
                alpha = alpha.filter(ImageFilter.MinFilter(2 * radius + 1))
        else:
            radius = max(1, int(3 * (font_smooth - 1.0)))
            if radius > 0:
                alpha = alpha.filter(ImageFilter.MaxFilter(2 * radius + 1))
        sprite.putalpha(alpha)
    return np.array(sprite)

def _make_motion_blur(img, angle=90, distance=10):
    '''
    Simulate Photoshop motion blur: half-res -> directional blur -> resize back.
    '''
    import cv2
    h, w = img.shape[:2]
    scaled_dist = int(distance * h / 320)
    half_w = max(1, w // 2)
    half_h = max(1, h // 2)
    half = Image.fromarray(img).resize((half_w, half_h), Image.LANCZOS)
    size = int(scaled_dist)
    if size % 2 == 0:
        size += 1
    kernel = np.zeros((size, size), dtype=np.float32)
    center = size // 2
    rad = math.radians(angle)
    dx = math.cos(rad)
    dy = math.sin(rad)
    for i in range(size):
        x = center + i * dx - center
        y = center + i * dy - center
        xi = int(round(x))
        yi = int(round(y))
        if 0 <= xi < size and 0 <= yi < size:
            kernel[yi, xi] = 1.0
    kernel = kernel / kernel.sum()
    half_arr = np.array(half).astype(np.float32)
    result = np.zeros_like(half_arr)
    for c in range(half_arr.shape[2]):
        result[:, :, c] = cv2.filter2D(half_arr[:, :, c], -1, kernel)
    blurred_half = np.clip(result, 0, 255).astype(np.uint8)
    img_half = Image.fromarray(blurred_half).resize((w, h), Image.LANCZOS)
    return np.array(img_half)

_CHAR_DX = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, -3, -3, -2, -2, -1, -1, 0,
    0, 1, 3, 7, 8, 10, 7, 2, 2, 3, 3, 4, 4, 3, 3, 3, 2, 0, -4,
    -7, -5, -4, -1, -3, -5, -8, -9, -7, -7, -9, -15, -20, -15, 3,
    8, 11, 9, 3, 2, -2, -2, 3, 10, 12, 12, 5, 2, -5, -9, -8, -5,
    5, 13, -7, -12, -10, -2, 6, 6, 0, -2, -3, -1, 2, 2, 2, 2, 3]
_CHAR_DY = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, -6, -6, -2, 0, -1,
    -8, -11, -11, -9, -8, -7, -5, 2, 1, -8, -10, -10, -6, -5, -5,
    -9, -10, -14, -17, -19, -15, -13, -8, -6, -7, -8, -7, -7, -7,
    -15, -28, -38, -36, -15, -9, -4, -5, -10, -10, -12, -12, -8,
    -3, -5, -10, -30, -31, -22, -16, -25, -41, -17, 25, 4, -5, -9,
    -10, -8, -8, 0, 2, 2, -1, -5, -3, -2, -2, -2]

class AoyituRenderer:
    '''AoyituRenderer'''
    def __init__(self, clear, blur, subtitle, gradient, noise, sub_bg, chinese_text=None, other_text=None, cfg=None):
        self.clear = clear
        self.blur = blur
        self.sub = subtitle
        if gradient is not None:
            self.grad = gradient
        else:
            for _name in ('heisejianbian.png', '黑色渐变.png'):
                _dir = SPRITE_DIR
                _gp = os.path.join(_dir, _name)
                if os.path.exists(_gp):
                    self.grad = np.array(Image.open(_gp).convert('RGBA'))
                    break
            else:
                self.grad = None
            while not hasattr(self, 'grad'):
                self.grad = _make_gradient(clear.shape[0], clear.shape[1])
        if noise is not None:
            self.noise_sprite = noise
        else:
            _np = os.path.join(SPRITE_DIR, 'noise-OldMovie.png')
            if not os.path.exists(_np):
                _np = os.path.join(SCRIPT_DIR, 'Sprite', 'noise-OldMovie.png')
            if os.path.exists(_np):
                self.noise_sprite = np.array(Image.open(_np).convert('RGBA'))
            else:
                self.noise_sprite = _make_noise()
        self.sub_bg = sub_bg if sub_bg is not None else _make_sub_bg()
        self.cfg = dict(cfg) if cfg else {}
        self.char_w = clear.shape[1]
        self.char_h = clear.shape[0]
        MAX_CANVAS_H = 640
        if self.char_h > MAX_CANVAS_H:
            scale = MAX_CANVAS_H / self.char_h
            new_h = MAX_CANVAS_H
            new_w = int(self.char_w * scale)
            self.clear = np.array(Image.fromarray(clear).resize((new_w, new_h), Image.LANCZOS))
            self.blur = np.array(Image.fromarray(blur).resize((new_w, new_h), Image.LANCZOS))
            self.char_w = new_w
            self.char_h = new_h
        if chinese_text:
            font_size = int(27 * self.char_h / 320)
            font_smooth = self.cfg.get('font_smooth', 1.0)
            self.sub = _render_text_sprite(chinese_text, other_text, font_size, self.char_h, self.char_w, font_smooth)
            self.cfg.setdefault('sub_h', 60)
        self.grad_w = self.grad.shape[1]
        self.grad_h = self.grad.shape[0]
        target_gw = max(1, self.char_w // 5)
        if self.grad_h != self.char_h or self.grad_w != target_gw:
            self.grad = np.array(Image.fromarray(self.grad).resize((target_gw, self.char_h), Image.LANCZOS))
            self.grad_w = self.grad.shape[1]
            self.grad_h = self.grad.shape[0]
        self.W = self.char_w
        self.H = self.char_h
        self.sprite_scale = self.cfg.get('char_scale', 1.2)
        self.char_y = 0
        self.grad_y = 0
        self.char_x = 0
        self.grad_left_x = 0
        self.grad_right_x = self.char_w - self.grad_w
        self.grad_left = self.grad.astype(np.float32)
        self.grad_right = np.fliplr(self.grad).astype(np.float32)
        ns_h, ns_w = self.noise_sprite.shape[:2]
        self._ns_h = ns_h
        self._ns_w = ns_w
        self._load_xian()
        self._xian_sprites = {}
        for name in ('xian.png', 'xian2.png', 'xian3.png', 'xian4.png', 'xian2_h.png', 'xian3_h.png', 'xian4_h.png'):
            path = os.path.join(SPRITE_DIR, name)
            if os.path.exists(path):
                self._xian_sprites[name] = np.array(Image.open(path).convert('RGBA'))
            else:
                self._xian_sprites[name] = None

    def _load_xian(self):
        path = os.path.join(SCRIPT_DIR, 'xian_positions.json')
        try:
            with open(path) as f:
                self._xian_data = json.load(f)
        except Exception:
            self._xian_data = {}

    def _get_flash(self, frame):
        c = self.cfg
        if frame <= 0:
            return 0.0
        if frame == 1:
            return c.get('flash_f1', 0.42)
        if frame == 2:
            return c.get('flash_f2', 0.48)
        if frame == 3:
            return c.get('flash_f3', 0.62)
        if frame <= 6:
            return c.get('flash_f3', 0.62) + (1 - c.get('flash_f3', 0.62)) * ((frame - 3) / 3) ** 0.5
        if frame <= 7:
            return 1.0
        if frame == 8:
            return 1.0
        if frame == 9:
            return 0.97
        if frame == 10:
            return 0.9
        if frame == 11:
            return 0.8
        if frame == 12:
            return 0.75
        if frame == 13:
            return 0.66
        if frame == 14:
            return 0.5
        if frame == 15:
            return 0.27
        if frame == 16:
            return 0.0
        return 0.0

    def _get_reveal(self, frame):
        f = self._get_flash(frame)
        if frame > 7:
            return 1.0 - f
        return 0.0

    def _blur_amount(self, frame):
        c = self.cfg
        idx = frame % 86
        bs1 = c.get('blur_start1', 22)
        bs2 = c.get('blur_start2', 60)
        if bs1 <= idx <= bs1 + 1:
            return ((idx - bs1) + 1) / 1.5
        if bs1 + 2 <= idx <= 29:
            return 1.0
        if 30 <= idx <= 32:
            if idx <= 32:
                return (33 - idx) / 3.0
        if bs2 <= idx <= bs2 + 3:
            return ((idx - bs2) + 1) / 4.0
        if bs2 + 4 <= idx <= 69:
            return 1.0
        if 70 <= idx <= 72:
            if idx <= 72:
                return 0.0
            return (73 - idx) / 4.0
        return 0.0

    def _blur_scale(self, frame):
        c = self.cfg
        idx = frame % 86
        sm = c.get('scale_min', 0.95)
        if idx == 19:
            return 1.0
        if idx == 20:
            return (1 + sm) / 2
        if idx == 21:
            return sm + (1 - sm) * 0.4
        if 22 <= idx <= 25:
            return sm
        if 26 <= idx <= 29:
            if idx <= 29:
                return 1.0
            return sm + ((idx - 25) / 4.0) * (1 - sm)
        return 1.0

    def _get_offset(self, frame):
        idx = frame % 86
        dx = _CHAR_DX[idx] if idx < len(_CHAR_DX) else 0
        dy = _CHAR_DY[idx] if idx < len(_CHAR_DY) else 0
        scale = self.H / 320
        return (int(dx * self.cfg.get('vib_x', 1.0) * scale), int(dy * self.cfg.get('vib_y', 1.0) * scale))

    def _get_xian_sprite(self, name, scale=1.0):
        spr = self._xian_sprites.get(name)
        if spr is None:
            return None
        orig = Image.fromarray(spr)
        ow, oh = orig.size
        if 'xian3' in name and '_h' in name:
            nh = self.H
            nw = max(1, int(ow * self.H / oh * scale))
        elif 'xian4' in name and '_h' in name:
            nh = self.H
            nw = max(1, int(ow * self.H / oh * scale))
        elif 'xian3_h' in name:
            nw = self.W
            nh = max(2, int(oh * self.W / ow * scale))
        elif 'xian4_h' in name:
            nw = self.W
            nh = max(2, int(oh * self.W / ow * scale))
        else:
            nh = int(oh * scale)
            nw = int(ow * scale)
        return np.array(orig.resize((nw, nh), Image.LANCZOS))

    def render(self, frame):
        H = self.H
        W = self.W
        flash = self._get_flash(frame)
        reveal = self._get_reveal(frame)
        blur_amt = self._blur_amount(frame)
        blur_scale = self._blur_scale(frame)
        dx, dy = self._get_offset(frame)
        scene = np.zeros((H, W, 3), dtype=np.float32)
        ss = self.sprite_scale * blur_scale
        sw = int(self.char_w * ss)
        sh = int(self.char_h * ss)
        c_clear = np.array(Image.fromarray(self.clear).resize((sw, sh), Image.LANCZOS)).astype(np.float32)
        b_blur = Image.fromarray(self.blur).resize((sw, sh), Image.LANCZOS)
        b_blur = b_blur.filter(ImageFilter.GaussianBlur(radius=1.5))
        c_blur = np.array(b_blur).astype(np.float32)
        c = c_clear * (1 - blur_amt) + c_blur * blur_amt if blur_amt > 0.01 else c_clear
        ca = c[:, :, 3:4] / 255.0
        cr = c[:, :, :3]
        scale_off_x = (self.char_w - sw) // 2
        scale_off_y = (self.char_h - sh) // 2
        cx = self.char_x + dx + scale_off_x
        cy = self.char_y + dy + scale_off_y
        sx1 = max(0, cx)
        sx2 = min(W, cx + sw)
        sy1 = max(0, cy)
        sy2 = min(H, cy + sh)
        if sx2 > sx1 and sy2 > sy1:
            ix1 = sx1 - cx
            iy1 = sy1 - cy
            ix2 = sw - (cx + sw - sx2)
            iy2 = sh - (cy + sh - sy2)
            rgn = scene[sy1:sy2, sx1:sx2]
            scene[sy1:sy2, sx1:sx2] = cr[iy1:iy2, ix1:ix2] * ca[iy1:iy2, ix1:ix2] + rgn * (1 - ca[iy1:iy2, ix1:ix2])
        gw = self.grad_w
        ga_l = self.grad_left[:, :, 3:4] / 255.0
        ga_r = self.grad_right[:, :, 3:4] / 255.0
        scene[:, :gw] *= (1 - ga_l)
        scene[:, W - gw:] *= (1 - ga_r)
        fi = str(frame)
        if fi in self._xian_data:
            for name in ('xian4_h.png', 'xian3_h.png', 'xian4.png', 'xian3.png', 'xian2.png', 'xian.png', 'xian2_h.png'):
                if name not in self._xian_data[fi]:
                    continue
                for inst in self._xian_data[fi][name]:
                    if len(inst) < 2:
                        continue
                    x = int(inst[0] * W / 568)
                    y = int(inst[1] * H / 320)
                    scale = inst[3] if len(inst) > 3 else 1.0
                    angle = inst[2] if len(inst) > 2 else 0
                    spr = self._get_xian_sprite(name, scale)
                    if spr is None:
                        continue
                    if angle != 0:
                        spr = np.array(Image.fromarray(spr).rotate(angle, expand=True, resample=Image.BILINEAR))
                    sh_s, sw_s = spr.shape[:2]
                    sx1_ = max(0, x)
                    sx2_ = min(W, x + sw_s)
                    sy1_ = max(0, y)
                    sy2_ = min(H, y + sh_s)
                    if sx1_ >= sx2_ or sy1_ >= sy2_:
                        continue
                    a = spr[sy1_-y:sy2_-y, sx1_-x:sx2_-x, 3:4].astype(float) / 255.0
                    _op_map = {
                        'xian.png': 'xian_op_1',
                        'xian2.png': 'xian_op_2',
                        'xian3.png': 'xian_op_3',
                        'xian4.png': 'xian_op_4',
                        'xian2_h.png': 'xian_op_5',
                        'xian3_h.png': 'xian_op_6',
                        'xian4_h.png': 'xian_op_7'}
                    xop = self.cfg.get(_op_map.get(name, ''), 1.0)
                    scene[sy1_:sy2_, sx1_:sx2_] = scene[sy1_:sy2_, sx1_:sx2_] * (1 - a * xop) + spr[sy1_-y:sy2_-y, sx1_-x:sx2_-x, :3].astype(float) / 255.0 * a * xop
        if self.sub is not None and self.sub.size > 0:
            _sh = self.cfg.get('sub_h', 32)
            sh_sub = int(H * _sh / 320)
            sw_sub = int(sh_sub * self.sub.shape[1] / self.sub.shape[0])
            sub_pil = Image.fromarray(self.sub).resize((sw_sub, sh_sub), Image.LANCZOS)
            s = np.array(sub_pil).astype(np.float32)
            sub_opacity = self.cfg.get('sub_opacity', 1.0)
            sr = s[:, :, :3]
            sa = s[:, :, 3:4] / 255.0 * sub_opacity
            bg_h = 0
            if self.sub_bg is not None:
                bg = self.sub_bg.astype(np.float32)
                _bh = self.cfg.get('bg_h', 44)
                _by = self.cfg.get('bg_y', 239)
                bg_h_target = int(H * _bh / 320)
                bg_w = int(bg_h_target * self.sub_bg.shape[1] / self.sub_bg.shape[0])
                bg_pil = Image.fromarray(self.sub_bg).resize((bg_w, bg_h_target), Image.LANCZOS)
                bg = np.array(bg_pil).astype(np.float32)
                bg_h = bg.shape[0]
                bg_w = bg.shape[1]
                sy_bg = int(H * _by / 320)
                sx_bg = int(W * 137 / 684)
                ewh = min(bg_w, W - sx_bg)
                ehh = min(bg_h, H - sy_bg)
                if ewh > 0 and ehh > 0:
                    br = bg[:ehh, :ewh, :3].astype(float) / 255.0
                    ba = bg[:ehh, :ewh, 3:4] / 255.0
                    rgn = scene[sy_bg:sy_bg+ehh, sx_bg:sx_bg+ewh]
                    scene[sy_bg:sy_bg+ehh, sx_bg:sx_bg+ewh] = br * ba + rgn * (1 - ba)
            _sy = self.cfg.get('sub_y', 245)
            sy_sub = int(H * _sy / 320)
            sx_sub = (W - sw_sub) // 2
            eh = min(sh_sub, H - sy_sub)
            ew = min(sw_sub, W - sx_sub)
            if eh > 0 and ew > 0:
                rgn = scene[sy_sub:sy_sub+eh, sx_sub:sx_sub+ew]
                scene[sy_sub:sy_sub+eh, sx_sub:sx_sub+ew] = sr[:eh, :ew] * sa[:eh, :ew] + rgn * (1 - sa[:eh, :ew])
        if self.noise_sprite is not None:
            ns = self.cfg.get('noise_scale', 3.5)
            nsi = self.cfg.get('noise_str', 0.7)
            nsh = int(self._ns_h * ns)
            nsw = int(self._ns_w * ns)
            noise_pil = Image.fromarray(self.noise_sprite).resize((nsw, nsh), Image.BILINEAR)
            noise_pil = noise_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
            noise_scaled = np.array(noise_pil)
            noise_tiled = np.tile(noise_scaled, (H // nsh + 2, W // nsw + 2, 1))
            rng = np.random.default_rng(frame * 997 + 7)
            ox = rng.integers(0, nsw)
            oy = rng.integers(0, nsh)
            na = noise_tiled[oy:oy+H, ox:ox+W, 3:4].astype(float) / 255.0
            scene = scene + 255.0 * na * nsi
        scene = np.clip(scene, 0, 255)
        final = scene * reveal + 255.0 * flash * (1 - reveal)
        return Image.fromarray(np.clip(final, 0, 255).astype(np.uint8))

def save_gif(frames, path, fps):
    frames = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG) if f.mode != 'P' else f for f in frames]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=int(1000 / fps), loop=0, optimize=True)
    print(f'Saved: {path}')
    return None


def save_video(frames, path, fps):
    import subprocess
    import tempfile
    import shutil
    import os
    w = frames[0].width
    h = frames[0].height
    ffmpeg = shutil.which('ffmpeg')
    if ffmpeg is None:
        import cv2
        out = cv2.VideoWriter(path, cv2.VideoWriter_fourcc(*'mp4v'), fps, (w, h))
        for f in frames:
            out.write(cv2.cvtColor(np.array(f), cv2.COLOR_RGB2BGR))
        out.release()
        print(f'Saved: {path} (mp4v codec — ffmpeg not found in PATH, install it for H.264)')
        return None
    tmpdir = tempfile.mkdtemp(prefix='aoyitu_')
    try:
        for i, f in enumerate(frames):
            f.save(os.path.join(tmpdir, f'frame_{i:04d}.png'))
        cmd = [ffmpeg, '-y', '-framerate', str(fps), '-i', os.path.join(tmpdir, 'frame_%04d.png'),
               '-c:v', 'libx264', '-crf', '18', '-preset', 'medium', '-pix_fmt', 'yuv420p', path]
        subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300, check=True)
        print(f'Saved: {path}')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

def main():
    p = argparse.ArgumentParser('Aoyitu Generator — All-in-One', description='Aoyitu Generator — All-in-One')
    p.add_argument('-c', '--clear', help='Clear character PNG')
    p.add_argument('-b', '--blur', help='Blurred character PNG')
    p.add_argument('-s', '--subtitle', help='Subtitle text PNG (or use --chinese-text)')
    p.add_argument('--chinese-text', help='Chinese subtitle text (top line, enables text mode)')
    p.add_argument('--other-text', help='Other language subtitle text (bottom line, optional)')
    p.add_argument('--sub-bg', required=True, help='Subtitle background bar PNG (zuozhu_0001_bg.png)')
    p.add_argument('-o', '--output', default='aoyitu_output.gif', help='Output file')
    p.add_argument('--fps', type=int, default=30, help='Frames per second')
    p.add_argument('--format', choices=['auto', 'video', 'gif', 'frames'], default='auto', help='Output format')
    p.add_argument('--outdir', default='output_frames', help='Output directory for frames')
    p.add_argument('--loops', type=int, default=1, help='86-frame loops')
    p.add_argument('--vib-x', type=float, default=1.0, help='Vibration X scale (0=off)')
    p.add_argument('--vib-y', type=float, default=1.0, help='Vibration Y scale (0=off)')
    p.add_argument('--blur-start1', type=int, default=22, help='First blur fade-in start frame')
    p.add_argument('--blur-start2', type=int, default=60, help='Second blur fade-in start frame')
    p.add_argument('--scale-min', type=float, default=0.95, help='Min scale during blur (0.95=95%)')
    p.add_argument('--sub-y', type=int, default=245, help='Subtitle Y position')
    p.add_argument('--sub-h', type=int, default=32, help='Subtitle height')
    p.add_argument('--bg-y', type=int, default=239, help='Background bar Y position')
    p.add_argument('--bg-h', type=int, default=44, help='Background bar height')
    p.add_argument('--noise-str', type=float, default=0.7, help='Noise intensity (0-2)')
    p.add_argument('--noise-scale', type=float, default=3.5, help='Noise grain size')
    p.add_argument('--char-scale', type=float, default=1.2, help='Character sprite scale')
    p.add_argument('--flash-f1', type=float, default=0.42, help='Flash F1 brightness')
    p.add_argument('--flash-f2', type=float, default=0.48, help='Flash F2 brightness')
    p.add_argument('--flash-f3', type=float, default=0.62, help='Flash F3 brightness')
    p.add_argument('--edit-xian', action='store_true', help='Launch xian editor')
    p.add_argument('--edit-subtitle', action='store_true', help='Launch subtitle editor')
    args = p.parse_args()
    if args.edit_xian:
        print('Launching xian editor...')
        os.system(f'"{sys.executable}" "{os.path.join(SCRIPT_DIR, "xian_tool.py")}"')
        return None
    if args.edit_subtitle:
        print('Launching subtitle editor...')
        os.system(f'"{sys.executable}" "{os.path.join(SCRIPT_DIR, "subtitle_tool.py")}"')
        return None
    if not args.clear:
        p.error('Generator mode requires -c. Or use --edit-xian / --edit-subtitle')
    if not args.subtitle and not args.chinese_text:
        p.error('Must provide either -s (subtitle PNG) or --chinese-text (text subtitle)')
    print('Aoyitu Generator — All-in-One')
    clear = np.array(Image.open(args.clear).convert('RGBA'))
    if args.blur:
        blur = np.array(Image.open(args.blur).convert('RGBA'))
    else:
        print('Blur image not provided, auto-generating motion blur (90°, distance=10)...')
        blur = _make_motion_blur(clear, angle=90, distance=10)
    sub = None
    if args.chinese_text:
        if FONT_PATH is None:
            p.error("Font '方正艺黑_GBK.ttf' not found. Cannot render text subtitle.")
    else:
        sub = np.array(Image.open(args.subtitle).convert('RGBA'))
    grad_path = os.path.join(SPRITE_DIR, '黑色渐变.png')
    noise_path = os.path.join(SPRITE_DIR, 'noise-OldMovie.png')
    bg_path = os.path.join(SPRITE_DIR, 'zuozhu_0001_bg.png')
    grad = np.array(Image.open(grad_path).convert('RGBA')) if os.path.exists(grad_path) else _make_gradient(clear.shape[0], clear.shape[1])
    noise = np.array(Image.open(noise_path).convert('RGBA')) if os.path.exists(noise_path) else _make_noise()
    sub_bg = np.array(Image.open(args.sub_bg).convert('RGBA'))
    W = clear.shape[1]
    print(f'Canvas: {W}x{clear.shape[0]} | {86 * args.loops}f @ {args.fps}fps')
    cfg = {k: v for k, v in vars(args).items() if v is not None}
    renderer = AoyituRenderer(clear, blur, sub, grad, noise, sub_bg, args.chinese_text, args.other_text, cfg)
    total = 86 * args.loops
    frames = []
    for i in range(total):
        if i % 20 == 0:
            print(f'  {i+1}/{total}...', True)
        frames.append(renderer.render(i))
    fmt = args.format
    if fmt == 'auto':
        fmt = 'gif' if args.output.endswith('.gif') else 'video'
    if fmt == 'video':
        save_video(frames, args.output, args.fps)
    else:
        save_gif(frames, args.output, args.fps)
    print('Done!')
    return None

if __name__ == '__main__':
    main()
