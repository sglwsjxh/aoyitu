# Aoyitu (奥义图) Animation Generator — All-in-One
#
# Copyright (C) 2026 sglwsjxh
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.


import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont


if getattr(sys, 'frozen', False):
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SPRITE_DIR = os.path.join(SCRIPT_DIR, 'public', 'Sprite')

_font_candidates = [
    os.path.join(SCRIPT_DIR, 'public', '方正艺黑_GBK.ttf'),
]
FONT_PATH = None
for _candidate in _font_candidates:
    if os.path.exists(_candidate):
        FONT_PATH = _candidate
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
    grad_w = max(1, char_w // 5)
    grad = np.zeros((char_h, grad_w, 4), dtype=np.uint8)
    for x in range(grad_w):
        grad[:, x, 3] = np.array(255 * (1.0 - x / grad_w) ** 0.5, dtype=np.uint8)
    return grad


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


# 86 帧角色振动位移表（索引 = frame % 86）
CHAR_VIBRATION_X = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -2, -3, -3, -2, -2, -1, -1, 0,
    0, 1, 3, 7, 8, 10, 7, 2, 2, 3, 3, 4, 4, 3, 3, 3, 2, 0, -4,
    -7, -5, -4, -1, -3, -5, -8, -9, -7, -7, -9, -15, -20, -15, 3,
    8, 11, 9, 3, 2, -2, -2, 3, 10, 12, 12, 5, 2, -5, -9, -8, -5,
    5, 13, -7, -12, -10, -2, 6, 6, 0, -2, -3, -1, 2, 2, 2, 2, 3]
CHAR_VIBRATION_Y = [
    0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 2, 0, -6, -6, -2, 0, -1,
    -8, -11, -11, -9, -8, -7, -5, 2, 1, -8, -10, -10, -6, -5, -5,
    -9, -10, -14, -17, -19, -15, -13, -8, -6, -7, -8, -7, -7, -7,
    -15, -28, -38, -36, -15, -9, -4, -5, -10, -10, -12, -12, -8,
    -3, -5, -10, -30, -31, -22, -16, -25, -41, -17, 25, 4, -5, -9,
    -10, -8, -8, 0, 2, 2, -1, -5, -3, -2, -2, -2]

# 仙线精灵名 → cfg 透明度键
XIAN_OP_MAP = {
    'xian.png': 'xian_op_1',
    'xian2.png': 'xian_op_2',
    'xian3.png': 'xian_op_3',
    'xian4.png': 'xian_op_4',
    'xian2_h.png': 'xian_op_5',
    'xian3_h.png': 'xian_op_6',
    'xian4_h.png': 'xian_op_7',
}

XIAN_SPRITE_NAMES = (
    'xian.png', 'xian2.png', 'xian3.png', 'xian4.png',
    'xian2_h.png', 'xian3_h.png', 'xian4_h.png',
)


class AoyituRenderer:
    '''单帧渲染器，86 帧循环驱动。'''

    def __init__(self, clear, blur, subtitle, gradient, noise, sub_bg,
                 chinese_text=None, other_text=None, cfg=None):
        self.clear = clear
        self.blur = blur
        self.sub = subtitle

        if gradient is not None:
            self.grad = gradient
        else:
            for name in ('heisejianbian.png', '黑色渐变.png'):
                path = os.path.join(SPRITE_DIR, name)
                if os.path.exists(path):
                    self.grad = np.array(Image.open(path).convert('RGBA'))
                    break
            else:
                self.grad = _make_gradient(clear.shape[0], clear.shape[1])

        if noise is not None:
            self.noise_sprite = noise
        else:
            noise_path = os.path.join(SPRITE_DIR, 'noise-OldMovie.png')
            if os.path.exists(noise_path):
                self.noise_sprite = np.array(Image.open(noise_path).convert('RGBA'))
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
            self.sub = _render_text_sprite(chinese_text, other_text, font_size,
                                           self.char_h, self.char_w, font_smooth)
            self.cfg.setdefault('sub_h', 60)

        # 渐变尺寸对齐画布
        self.grad_w = self.grad.shape[1]
        self.grad_h = self.grad.shape[0]
        target_grad_w = max(1, self.char_w // 5)
        if self.grad_h != self.char_h or self.grad_w != target_grad_w:
            self.grad = np.array(Image.fromarray(self.grad).resize(
                (target_grad_w, self.char_h), Image.LANCZOS))
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

        self.noise_sprite_h, self.noise_sprite_w = self.noise_sprite.shape[:2]

        self._load_xian()
        self._xian_sprites = {}
        for name in XIAN_SPRITE_NAMES:
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
        dx = CHAR_VIBRATION_X[idx] if idx < len(CHAR_VIBRATION_X) else 0
        dy = CHAR_VIBRATION_Y[idx] if idx < len(CHAR_VIBRATION_Y) else 0
        scale = self.H / 320
        return (int(dx * self.cfg.get('vib_x', 1.0) * scale),
                int(dy * self.cfg.get('vib_y', 1.0) * scale))

    def _get_xian_sprite(self, name, scale=1.0):
        spr = self._xian_sprites.get(name)
        if spr is None:
            return None
        sprite_img = Image.fromarray(spr)
        orig_w, orig_h = sprite_img.size
        if 'xian3' in name and '_h' in name:
            nh = self.H
            nw = max(1, int(orig_w * self.H / orig_h * scale))
        elif 'xian4' in name and '_h' in name:
            nh = self.H
            nw = max(1, int(orig_w * self.H / orig_h * scale))
        elif 'xian3_h' in name:
            nw = self.W
            nh = max(2, int(orig_h * self.W / orig_w * scale))
        elif 'xian4_h' in name:
            nw = self.W
            nh = max(2, int(orig_h * self.W / orig_w * scale))
        else:
            nh = int(orig_h * scale)
            nw = int(orig_w * scale)
        return np.array(sprite_img.resize((nw, nh), Image.LANCZOS))

    def render(self, frame):
        H = self.H
        W = self.W
        flash = self._get_flash(frame)
        reveal = self._get_reveal(frame)
        blur_amt = self._blur_amount(frame)
        blur_scale = self._blur_scale(frame)
        dx, dy = self._get_offset(frame)
        scene = np.zeros((H, W, 3), dtype=np.float32)

        # --- 角色合成（清晰图与模糊图按 blur_amt 混合） ---
        eff_scale = self.sprite_scale * blur_scale
        sprite_w = int(self.char_w * eff_scale)
        sprite_h = int(self.char_h * eff_scale)
        clear_char = np.array(Image.fromarray(self.clear).resize(
            (sprite_w, sprite_h), Image.LANCZOS)).astype(np.float32)
        blur_pil = Image.fromarray(self.blur).resize((sprite_w, sprite_h), Image.LANCZOS)
        blur_pil = blur_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
        blur_char = np.array(blur_pil).astype(np.float32)
        char_blend = clear_char * (1 - blur_amt) + blur_char * blur_amt if blur_amt > 0.01 else clear_char
        char_alpha = char_blend[:, :, 3:4] / 255.0
        char_rgb = char_blend[:, :, :3]
        scale_off_x = (self.char_w - sprite_w) // 2
        scale_off_y = (self.char_h - sprite_h) // 2
        paste_x = self.char_x + dx + scale_off_x
        paste_y = self.char_y + dy + scale_off_y
        sx1 = max(0, paste_x)
        sx2 = min(W, paste_x + sprite_w)
        sy1 = max(0, paste_y)
        sy2 = min(H, paste_y + sprite_h)
        if sx2 > sx1 and sy2 > sy1:
            ix1 = sx1 - paste_x
            iy1 = sy1 - paste_y
            ix2 = sprite_w - (paste_x + sprite_w - sx2)
            iy2 = sprite_h - (paste_y + sprite_h - sy2)
            region = scene[sy1:sy2, sx1:sx2]
            scene[sy1:sy2, sx1:sx2] = (char_rgb[iy1:iy2, ix1:ix2] * char_alpha[iy1:iy2, ix1:ix2]
                                       + region * (1 - char_alpha[iy1:iy2, ix1:ix2]))

        # --- 左右黑色渐变（收尾压暗） ---
        grad_alpha_l = self.grad_left[:, :, 3:4] / 255.0
        grad_alpha_r = self.grad_right[:, :, 3:4] / 255.0
        scene[:, :self.grad_w] *= (1 - grad_alpha_l)
        scene[:, W - self.grad_w:] *= (1 - grad_alpha_r)

        # --- 仙线特效（按 xian_positions.json 逐帧摆放） ---
        frame_key = str(frame)
        if frame_key in self._xian_data:
            for name in ('xian4_h.png', 'xian3_h.png', 'xian4.png', 'xian3.png',
                         'xian2.png', 'xian.png', 'xian2_h.png'):
                if name not in self._xian_data[frame_key]:
                    continue
                for placement in self._xian_data[frame_key][name]:
                    if len(placement) < 2:
                        continue
                    x = int(placement[0] * W / 568)
                    y = int(placement[1] * H / 320)
                    scale = placement[3] if len(placement) > 3 else 1.0
                    angle = placement[2] if len(placement) > 2 else 0
                    sprite = self._get_xian_sprite(name, scale)
                    if sprite is None:
                        continue
                    if angle != 0:
                        sprite = np.array(Image.fromarray(sprite).rotate(
                            angle, expand=True, resample=Image.BILINEAR))
                    sprite_h, sprite_w = sprite.shape[:2]
                    sx1_ = max(0, x)
                    sx2_ = min(W, x + sprite_w)
                    sy1_ = max(0, y)
                    sy2_ = min(H, y + sprite_h)
                    if sx1_ >= sx2_ or sy1_ >= sy2_:
                        continue
                    sprite_alpha = sprite[sy1_-y:sy2_-y, sx1_-x:sx2_-x, 3:4].astype(float) / 255.0
                    opacity = self.cfg.get(XIAN_OP_MAP.get(name, ''), 1.0)
                    scene[sy1_:sy2_, sx1_:sx2_] = (
                        scene[sy1_:sy2_, sx1_:sx2_] * (1 - sprite_alpha * opacity)
                        + sprite[sy1_-y:sy2_-y, sx1_-x:sx2_-x, :3].astype(float) / 255.0 * sprite_alpha * opacity)

        # --- 字幕与背景条 ---
        if self.sub is not None and self.sub.size > 0:
            sub_h_ratio = self.cfg.get('sub_h', 32)
            sub_h = int(H * sub_h_ratio / 320)
            sub_w = int(sub_h * self.sub.shape[1] / self.sub.shape[0])
            sub_pil = Image.fromarray(self.sub).resize((sub_w, sub_h), Image.LANCZOS)
            sub_sprite = np.array(sub_pil).astype(np.float32)
            sub_opacity = self.cfg.get('sub_opacity', 1.0)
            sub_rgb = sub_sprite[:, :, :3]
            sub_alpha = sub_sprite[:, :, 3:4] / 255.0 * sub_opacity
            if self.sub_bg is not None:
                bg_h_ratio = self.cfg.get('bg_h', 44)
                bg_y_ratio = self.cfg.get('bg_y', 239)
                bg_h_px = int(H * bg_h_ratio / 320)
                bg_w = int(bg_h_px * self.sub_bg.shape[1] / self.sub_bg.shape[0])
                bg_pil = Image.fromarray(self.sub_bg).resize((bg_w, bg_h_px), Image.LANCZOS)
                bg = np.array(bg_pil).astype(np.float32)
                bg_h = bg.shape[0]
                bg_w = bg.shape[1]
                bg_y = int(H * bg_y_ratio / 320)
                bg_x = int(W * 137 / 684)
                clip_w = min(bg_w, W - bg_x)
                clip_h = min(bg_h, H - bg_y)
                if clip_w > 0 and clip_h > 0:
                    bg_rgb = bg[:clip_h, :clip_w, :3].astype(float) / 255.0
                    bg_alpha = bg[:clip_h, :clip_w, 3:4] / 255.0
                    region = scene[bg_y:bg_y+clip_h, bg_x:bg_x+clip_w]
                    scene[bg_y:bg_y+clip_h, bg_x:bg_x+clip_w] = bg_rgb * bg_alpha + region * (1 - bg_alpha)
            sub_y_ratio = self.cfg.get('sub_y', 245)
            sub_y = int(H * sub_y_ratio / 320)
            sub_x = (W - sub_w) // 2
            clip_h = min(sub_h, H - sub_y)
            clip_w = min(sub_w, W - sub_x)
            if clip_h > 0 and clip_w > 0:
                region = scene[sub_y:sub_y+clip_h, sub_x:sub_x+clip_w]
                scene[sub_y:sub_y+clip_h, sub_x:sub_x+clip_w] = (
                    sub_rgb[:clip_h, :clip_w] * sub_alpha[:clip_h, :clip_w]
                    + region * (1 - sub_alpha[:clip_h, :clip_w]))

        # --- 胶片噪点 ---
        if self.noise_sprite is not None:
            noise_scale_v = self.cfg.get('noise_scale', 3.5)
            noise_strength = self.cfg.get('noise_str', 0.7)
            noise_h = int(self.noise_sprite_h * noise_scale_v)
            noise_w = int(self.noise_sprite_w * noise_scale_v)
            noise_pil = Image.fromarray(self.noise_sprite).resize((noise_w, noise_h), Image.BILINEAR)
            noise_pil = noise_pil.filter(ImageFilter.GaussianBlur(radius=1.5))
            noise_base = np.array(noise_pil)
            noise_tiles = np.tile(noise_base, (H // noise_h + 2, W // noise_w + 2, 1))
            rng = np.random.default_rng(frame * 997 + 7)
            noise_ox = rng.integers(0, noise_w)
            noise_oy = rng.integers(0, noise_h)
            noise_alpha = noise_tiles[noise_oy:noise_oy+H, noise_ox:noise_ox+W, 3:4].astype(float) / 255.0
            scene = scene + 255.0 * noise_alpha * noise_strength

        scene = np.clip(scene, 0, 255)
        final = scene * reveal + 255.0 * flash * (1 - reveal)
        return Image.fromarray(np.clip(final, 0, 255).astype(np.uint8))


def save_gif(frames, path, fps):
    frames = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT,
                         dither=Image.Dither.FLOYDSTEINBERG) if f.mode != 'P' else f
              for f in frames]
    frames[0].save(path, save_all=True, append_images=frames[1:],
                   duration=int(1000 / fps), loop=0, optimize=True)
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
        subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8',
                       errors='replace', timeout=300, check=True)
        print(f'Saved: {path}')
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser('Aoyitu Generator — All-in-One',
                                     description='Aoyitu Generator — All-in-One')
    parser.add_argument('-c', '--clear', help='Clear character PNG')
    parser.add_argument('-b', '--blur', help='Blurred character PNG')
    parser.add_argument('-s', '--subtitle', help='Subtitle text PNG (or use --chinese-text)')
    parser.add_argument('--chinese-text', help='Chinese subtitle text (top line, enables text mode)')
    parser.add_argument('--other-text', help='Other language subtitle text (bottom line, optional)')
    parser.add_argument('--sub-bg', required=True,
                        help='Subtitle background bar PNG (zuozhu_000_bg.png)')
    parser.add_argument('-o', '--output', default='aoyitu_output.gif', help='Output file')
    parser.add_argument('--fps', type=int, default=30, help='Frames per second')
    parser.add_argument('--format', choices=['auto', 'video', 'gif'], default='auto',
                        help='Output format')
    parser.add_argument('--loops', type=int, default=1, help='86-frame loops')
    parser.add_argument('--vib-x', type=float, default=1.0, help='Vibration X scale (0=off)')
    parser.add_argument('--vib-y', type=float, default=1.0, help='Vibration Y scale (0=off)')
    parser.add_argument('--blur-start1', type=int, default=22, help='First blur fade-in start frame')
    parser.add_argument('--blur-start2', type=int, default=60, help='Second blur fade-in start frame')
    parser.add_argument('--scale-min', type=float, default=0.95,
                        help='Min scale during blur (0.95=95%%)')
    parser.add_argument('--sub-y', type=int, default=245, help='Subtitle Y position')
    parser.add_argument('--sub-h', type=int, default=32, help='Subtitle height')
    parser.add_argument('--bg-y', type=int, default=239, help='Background bar Y position')
    parser.add_argument('--bg-h', type=int, default=44, help='Background bar height')
    parser.add_argument('--noise-str', type=float, default=0.7, help='Noise intensity (0-2)')
    parser.add_argument('--noise-scale', type=float, default=3.5, help='Noise grain size')
    parser.add_argument('--char-scale', type=float, default=1.2, help='Character sprite scale')
    parser.add_argument('--flash-f1', type=float, default=0.42, help='Flash F1 brightness')
    parser.add_argument('--flash-f2', type=float, default=0.48, help='Flash F2 brightness')
    parser.add_argument('--flash-f3', type=float, default=0.62, help='Flash F3 brightness')
    args = parser.parse_args()

    if not args.clear:
        parser.error('Generator mode requires -c.')
    if not args.subtitle and not args.chinese_text:
        parser.error('Must provide either -s (subtitle PNG) or --chinese-text (text subtitle)')

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
            parser.error("Font '方正艺黑_GBK.ttf' not found. Cannot render text subtitle.")
    else:
        sub = np.array(Image.open(args.subtitle).convert('RGBA'))

    grad_path = os.path.join(SPRITE_DIR, '黑色渐变.png')
    noise_path = os.path.join(SPRITE_DIR, 'noise-OldMovie.png')
    grad = np.array(Image.open(grad_path).convert('RGBA')) if os.path.exists(grad_path) else _make_gradient(clear.shape[0], clear.shape[1])
    noise = np.array(Image.open(noise_path).convert('RGBA')) if os.path.exists(noise_path) else _make_noise()
    sub_bg = np.array(Image.open(args.sub_bg).convert('RGBA'))

    W = clear.shape[1]
    print(f'Canvas: {W}x{clear.shape[0]} | {86 * args.loops}f @ {args.fps}fps')
    cfg = {k: v for k, v in vars(args).items() if v is not None}
    renderer = AoyituRenderer(clear, blur, sub, grad, noise, sub_bg,
                              args.chinese_text, args.other_text, cfg)

    total_frames = 86 * args.loops
    frames = []
    for i in range(total_frames):
        if i % 20 == 0:
            print(f'  {i+1}/{total_frames}...', True)
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