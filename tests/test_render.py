"""渲染管线自检：素材生成 / 动感模糊 / 86 帧渲染 / GIF 导出 / 中文字幕。"""

import os
import sys
import tempfile

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import aoyitu


def _blank_char():
    clear = np.zeros((320, 568, 4), np.uint8)
    clear[..., 3] = 255
    return clear


def check_sprite_generators():
    grad = aoyitu._make_gradient(64)
    assert grad.shape == (64, 12, 4), grad.shape
    assert grad.dtype == np.uint8, grad.dtype

    noise = aoyitu._make_noise()
    assert noise.shape == (128, 128, 4), noise.shape
    assert noise.dtype == np.uint8, noise.dtype

    sub_bg = aoyitu._make_sub_bg()
    assert sub_bg.shape == (41, 293, 4), sub_bg.shape
    assert sub_bg.dtype == np.uint8, sub_bg.dtype
    print("素材生成 OK")


def check_motion_blur():
    blur = aoyitu._make_motion_blur(_blank_char(), 90, 10)
    assert blur.shape == (320, 568, 4), blur.shape
    assert blur.dtype == np.uint8, blur.dtype
    print("动感模糊 OK")


def check_render_and_export():
    clear = _blank_char()
    blur = aoyitu._make_motion_blur(clear, 90, 10)
    renderer = aoyitu.AoyituRenderer(clear, blur, None, None, None, None, None, None, {})
    frames = [renderer.render(f) for f in range(86)]
    assert len(frames) == 86, len(frames)
    for f in frames:
        assert f.size == (568, 320), f.size
        assert f.mode == "RGB", f.mode

    with tempfile.TemporaryDirectory() as tmp:
        out = os.path.join(tmp, "out.gif")
        aoyitu.save_gif(frames, out, 10)
        assert os.path.getsize(out) > 0, "GIF 为空"
    print("86 帧渲染 + GIF 导出 OK")


def check_chinese_text_mode():
    font = os.path.join(ROOT, "public", "方正艺黑_GBK.ttf")
    if not os.path.exists(font):
        print("字体缺失，跳过中文字幕检查")
        return
    clear = _blank_char()
    blur = aoyitu._make_motion_blur(clear, 90, 10)
    renderer = aoyitu.AoyituRenderer(clear, blur, None, None, None, None,
                                     "忍法·千鸟", None, {})
    frame = renderer.render(25)
    assert frame.size == (568, 320), frame.size
    print("中文字幕渲染 OK")


if __name__ == "__main__":
    check_sprite_generators()
    check_motion_blur()
    check_render_and_export()
    check_chinese_text_mode()
    print("全部通过")
