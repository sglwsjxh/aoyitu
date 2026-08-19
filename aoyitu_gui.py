# Source Generated with Decompyle++
# File: aoyitu_gui.pyc (Python 3.13)

'''
Aoyitu GUI — animation player with parameter controls.
Play/Pause, prev/next frame, adjust all parameters in real-time.
'''
import sys
import os
import json
import math
import numpy as np
import threading
import time
import subprocess
from PIL import Image, ImageFilter, ImageTk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
from aoyitu import AoyituRenderer, _make_gradient, _make_noise, _make_sub_bg, _make_motion_blur
OUTPUT_DIR = os.path.join(SCRIPT_DIR, 'output')
os.makedirs(OUTPUT_DIR, exist_ok=True)
BG = '#f0f0f0'
BG_FRAME = '#ffffff'
FG = '#222222'
FG_DIM = '#555555'
FG_FAINT = '#888888'
BTN_BG = '#e0e0e0'
BTN_GREEN = '#2d8a4e'
BTN_RED = '#c0392b'
ENTRY_BG = '#ffffff'
PREVIEW_BG = '#111111'

class AoyituGUI:
    '''AoyituGUI'''

    def __init__(self):
        self.root = tk.Tk()
        self.root.title('Aoyitu (奥义图) Generator')
        self.root.geometry('1100x720')
        self.root.configure(bg=BG)
        self.clear_img = None
        self.blur_img = None
        self.sub_img = None
        self.sub_bg_img = None
        self._chinese_text = None
        self._other_text = None
        self.renderer = None
        self.current_frame = 25
        self.playing = False
        self.frames_cache = {}
        self.total_frames = 86
        self._entries = {}
        self.use_audio = tk.BooleanVar(value=False)
        self._audio_entry = None
        self._audio_entries = []
        self.use_blur_file = tk.BooleanVar(value=False)
        self.use_sub_file = tk.BooleanVar(value=False)
        self._build_ui()
        self.root.after(100, self._auto_load)
        self.root.mainloop()

    def _auto_load(self):
        '''Auto-load default sprite paths.'''
        paths = {
            'clear': os.path.join(SCRIPT_DIR, 'Sprite', 'qx001.png'),
            'blur': os.path.join(SCRIPT_DIR, 'Sprite', 'mh001.png'),
            'sub': os.path.join(SCRIPT_DIR, 'Sprite', 'zm001.png') }
        for k, p in paths.items():
            if not os.path.exists(p):
                continue
            self._entries[k].delete(0, tk.END)
            self._entries[k].insert(0, p)
        # Load default sub_bg
        self.sub_bg_img = self._load_image(os.path.join(SCRIPT_DIR, 'Sprite', 'zuozhu_000_bg.png'))
        self._load_all()

    def _build_ui(self):
        FONT = ('SimHei', 9)
        FONT_SM = ('SimHei', 8)
        self._font_sm = FONT_SM
        left = tk.Frame(self.root, bg=BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)
        ff = tk.LabelFrame(left, text='素材文件', fg=FG, bg=BG, font=FONT)
        ff.pack(fill=tk.X, pady=5)
        _defaults = {
            'clear': 'qx001.png',
            'blur': 'mh001.png',
            'sub': 'zm001.png' }
        f = tk.Frame(ff, bg=BG)
        f.pack(fill=tk.X, pady=2)
        tk.Label(f, text='清晰角色:', fg=FG_DIM, bg=BG, font=FONT_SM, width=10).pack(side=tk.LEFT)
        e = tk.Entry(f, bg=ENTRY_BG, fg=FG, font=FONT_SM, relief=tk.SOLID, bd=1)
        e.insert(0, os.path.join('Sprite', _defaults['clear']))
        e.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self._entries['clear'] = e
        tk.Button(f, text='浏览...', bg=BTN_BG, fg=FG, font=FONT_SM, relief=tk.RAISED, bd=1,
                  command=lambda: self._browse('clear')).pack(side=tk.RIGHT, padx=3)
        sf = tk.Frame(ff, bg=BG)
        sf.pack(fill=tk.X, pady=2)
        self._sub_cb = tk.Checkbutton(sf, text='字幕图', variable=self.use_sub_file,
                                       fg=FG_DIM, bg=BG, font=FONT_SM, selectcolor=ENTRY_BG,
                                       activebackground=BG, activeforeground=FG,
                                       command=self._toggle_sub)
        self._sub_cb.pack(side=tk.LEFT)
        self._sub_entry = tk.Entry(sf, bg=ENTRY_BG, fg=FG_FAINT, font=FONT_SM,
                                    state=tk.DISABLED, relief=tk.SOLID, bd=1)
        self._sub_entry.insert(0, os.path.join('Sprite', _defaults['sub']))
        self._sub_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._entries['sub'] = self._sub_entry
        tk.Button(sf, text='浏览...', bg=BTN_BG, fg=FG, font=FONT_SM, relief=tk.RAISED, bd=1,
                  command=lambda: self._browse('sub')).pack(side=tk.RIGHT)
        self._text_frame = tk.Frame(ff, bg=BG)
        self._text_frame.pack(fill=tk.X, pady=2)
        tk.Label(self._text_frame, text='中文(必填):', fg=FG_DIM, bg=BG, font=FONT_SM, width=10).pack(side=tk.LEFT)
        self._chinese_text_entry = tk.Entry(self._text_frame, bg=ENTRY_BG, fg=FG, font=FONT_SM,
                                             relief=tk.SOLID, bd=1)
        self._chinese_text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        f2 = tk.Frame(ff, bg=BG)
        self._text_frame2 = f2
        f2.pack(fill=tk.X, pady=2)
        tk.Label(f2, text='其他语言:', fg=FG_DIM, bg=BG, font=FONT_SM, width=10).pack(side=tk.LEFT)
        self._other_text_entry = tk.Entry(f2, bg=ENTRY_BG, fg=FG, font=FONT_SM,
                                           relief=tk.SOLID, bd=1)
        self._other_text_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        bf = tk.Frame(ff, bg=BG)
        bf.pack(fill=tk.X, pady=2)
        self._blur_cb = tk.Checkbutton(bf, text='模糊图', variable=self.use_blur_file,
                                        fg=FG_DIM, bg=BG, font=FONT_SM, selectcolor=ENTRY_BG,
                                        activebackground=BG, activeforeground=FG,
                                        command=self._toggle_blur)
        self._blur_cb.pack(side=tk.LEFT)
        self._blur_entry = tk.Entry(bf, bg=ENTRY_BG, fg=FG_FAINT, font=FONT_SM,
                                     state=tk.DISABLED, relief=tk.SOLID, bd=1)
        self._blur_entry.insert(0, os.path.join('Sprite', _defaults['blur']))
        self._blur_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self._entries['blur'] = self._blur_entry
        tk.Button(bf, text='浏览...', bg=BTN_BG, fg=FG, font=FONT_SM, relief=tk.RAISED, bd=1,
                  command=lambda: self._browse('blur')).pack(side=tk.RIGHT)
        af = tk.Frame(ff, bg=BG)
        af.pack(fill=tk.X, pady=2)
        self._audio_cb = tk.Checkbutton(af, text='导入音频', variable=self.use_audio,
                                         fg=FG_DIM, bg=BG, font=FONT_SM, selectcolor=ENTRY_BG,
                                         activebackground=BG, activeforeground=FG,
                                         command=self._toggle_audio)
        self._audio_cb.pack(side=tk.LEFT)
        self._audio_entry = tk.Entry(af, bg=ENTRY_BG, fg=FG_FAINT, font=FONT_SM,
                                      state=tk.DISABLED, relief=tk.SOLID, bd=1)
        self._audio_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(af, text='浏览...', bg=BTN_BG, fg=FG, font=FONT_SM, relief=tk.RAISED, bd=1,
                  command=self._browse_audio).pack(side=tk.RIGHT)
        tk.Button(af, text='+', bg=BTN_BG, fg=FG, font=FONT_SM, relief=tk.RAISED, bd=1, width=2,
                  command=self._add_audio_row).pack(side=tk.RIGHT, padx=1)
        self._audio_extra_container = tk.Frame(ff, bg=BG)
        tk.Button(left, text='加载素材', bg=BTN_GREEN, fg='#fff', font=FONT,
                   command=self._load_all).pack(pady=3, fill=tk.X)
        self.preview_label = tk.Label(left, bg=PREVIEW_BG)
        self.preview_label.pack(pady=5)
        FONT_BTN = ('SimHei', 10)
        ctrl = tk.Frame(left, bg=BG)
        ctrl.pack(fill=tk.X)
        self._play_btn = tk.Button(ctrl, text='▶ 播放', bg=BTN_GREEN, fg='#fff', font=FONT_BTN,
                                    command=self._toggle_play, width=8)
        self._play_btn.pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl, text='◀◀', bg=BTN_BG, fg=FG, font=FONT_BTN,
                   command=lambda: self._goto(0)).pack(side=tk.LEFT, padx=2)
        tk.Button(ctrl, text='◀', bg=BTN_BG, fg=FG, font=FONT_BTN,
                   command=lambda e: self._goto(self.current_frame - 1)).pack(side=tk.LEFT, padx=2)
        tk.Button(ctrl, text='▶', bg=BTN_BG, fg=FG, font=FONT_BTN,
                   command=lambda e: self._goto(self.current_frame + 1)).pack(side=tk.LEFT, padx=2)
        tk.Button(ctrl, text='▶▶', bg=BTN_BG, fg=FG, font=FONT_BTN,
                   command=lambda: self._goto(85)).pack(side=tk.LEFT, padx=2)
        self._frame_label = tk.Label(ctrl, text='F25/85', fg=FG, bg=BG, font=FONT_BTN)
        self._frame_label.pack(side=tk.LEFT, padx=10)
        self._frame_slider = tk.Scale(left, from_=0, to=85, orient=tk.HORIZONTAL,
                                       command=lambda v: self._goto(int(v)),
                                       bg=BG_FRAME, fg=FG, troughcolor='#d0d0d0', highlightthickness=0)
        self._frame_slider.set(25)
        self._frame_slider.pack(fill=tk.X)
        btn_frame = tk.Frame(left, bg=BG)
        btn_frame.pack(fill=tk.X, pady=5)
        tk.Button(btn_frame, text='生成GIF', bg=BTN_RED, fg='#fff', font=('SimHei', 13, 'bold'),
                   command=self._generate).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(0, 3))
        tk.Button(btn_frame, text='生成MP4', bg=BTN_RED, fg='#fff', font=('SimHei', 13, 'bold'),
                   command=self._generate_mp4).pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=6, padx=(3, 0))
        self._status = tk.Label(left, text='', fg='#0a0', bg=BG, font=('SimHei', 11))
        self._status.pack()
        right = tk.Frame(self.root, bg=BG, width=460)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=10)
        right.pack_propagate(False)
        tk.Label(right, text='参数调整', fg=FG, bg=BG, font=('SimHei', 13, 'bold')).pack()
        canvas = tk.Canvas(right, bg=BG_FRAME, highlightthickness=0)
        scrollbar = tk.Scrollbar(right, orient=tk.VERTICAL, command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=BG_FRAME)
        scroll_frame.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
        canvas.create_window((0, 0), window=scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._params = {}
        self._param_scale = {}
        params = [
            ('FPS', 'fps', 30, 10, 60, 1, 1),
            ('角色缩放(%)', 'char_scale', 120, 50, 250, 1, 0.01),
            ('振动X(%)', 'vib_x', 100, 0, 300, 1, 0.01),
            ('振动Y(%)', 'vib_y', 100, 0, 300, 1, 0.01),
            ('模糊起始1', 'blur_start1', 22, 15, 35, 1, 1),
            ('模糊起始2', 'blur_start2', 60, 55, 75, 1, 1),
            ('缩放下限(%)', 'scale_min', 95, 80, 100, 1, 0.01),
            ('字幕Y', 'sub_y', 245, 200, 300, 1, 1),
            ('字幕H', 'sub_h', 32, 20, 80, 1, 1),
            ('字体平滑度(%)', 'font_smooth', 100, 0, 400, 1, 0.01),
            ('字幕透明度(%)', 'sub_opacity', 100, 0, 100, 1, 0.01),
            ('背景条Y', 'bg_y', 239, 200, 300, 1, 1),
            ('背景条H', 'bg_h', 44, 30, 60, 1, 1),
            ('噪点强度(%)', 'noise_str', 70, 0, 200, 1, 0.01),
            ('噪点大小', 'noise_scale', 35, 10, 80, 1, 0.1),
            ('闪光F1(%)', 'flash_f1', 42, 0, 100, 1, 0.01),
            ('闪光F2(%)', 'flash_f2', 48, 0, 100, 1, 0.01),
            ('闪光F3(%)', 'flash_f3', 62, 0, 100, 1, 0.01),
            ('xian1透明度(%)', 'xian_op_1', 110, 0, 200, 1, 0.01),
            ('xian2透明度(%)', 'xian_op_2', 70, 0, 200, 1, 0.01),
            ('xian3透明度(%)', 'xian_op_3', 80, 0, 200, 1, 0.01),
            ('xian4透明度(%)', 'xian_op_4', 55, 0, 200, 1, 0.01),
            ('xian2_h透明度(%)', 'xian_op_5', 50, 0, 200, 1, 0.01),
            ('xian3_h透明度(%)', 'xian_op_6', 15, 0, 200, 1, 0.01),
            ('xian4_h透明度(%)', 'xian_op_7', 18, 0, 200, 1, 0.01)]
        for label, key, default, minv, maxv, step, scale in params:
            f = tk.Frame(scroll_frame, bg=BG_FRAME)
            f.pack(fill=tk.X, pady=1)
            tk.Label(f, text=f'{label}:', fg=FG_DIM, bg=BG_FRAME, font=('SimHei', 10), width=16).pack(side=tk.LEFT)
            var = tk.IntVar(value=default)
            self._params[key] = var
            self._param_scale[key] = scale
            s = tk.Scale(f, from_=minv, to=maxv, variable=var, orient=tk.HORIZONTAL,
                          bg=BG_FRAME, fg=FG, resolution=step, length=180,
                          troughcolor='#d0d0d0', highlightthickness=0,
                          command=lambda v: self._goto(int(v)))
            s.pack(side=tk.LEFT)
            val_label = tk.Label(f, text=str(default), fg=FG_DIM, bg=BG_FRAME, font=('SimHei', 9), width=4)
            val_label.pack(side=tk.RIGHT)
            var.trace_add('write', lambda *a, v=var, l=val_label: l.config(text=str(v.get())))
        self.root.bind('<Left>', lambda e: self._goto(self.current_frame - 1))
        self.root.bind('<Right>', lambda e: self._goto(self.current_frame + 1))
        self.root.bind('<space>', lambda e: self._toggle_play())
        self.root.protocol('WM_DELETE_WINDOW', self.root.quit)

    def _browse(self, key):
        path = filedialog.askopenfilename(filetypes=[
            ('Image files', '*.png *.jpg *.jpeg *.bmp'),
            ('All files', '*.*')])
        if path:
            self._entries[key].delete(0, tk.END)
            self._entries[key].insert(0, path)
            self._load_all()
        return None

    def _toggle_audio(self):
        state = tk.NORMAL if self.use_audio.get() else tk.DISABLED
        fg_color = FG if self.use_audio.get() else FG_FAINT
        self._audio_entry.config(state=state, fg=fg_color)
        for ae in self._audio_entries:
            ae['entry'].config(state=state, fg=fg_color)

    def _toggle_blur(self):
        if self.use_blur_file.get():
            self._blur_entry.config(state=tk.NORMAL, fg=FG)
        else:
            self._blur_entry.config(state=tk.DISABLED, fg=FG_FAINT)
        if self.clear_img:
            self._load_all()

    def _toggle_sub(self):
        '''Toggle between text mode (unchecked) and image mode (checked).'''
        if self.use_sub_file.get():
            self._sub_entry.config(state=tk.NORMAL, fg=FG)
            self._text_frame.pack_forget()
            self._text_frame2.pack_forget()
        else:
            self._sub_entry.config(state=tk.DISABLED, fg=FG_FAINT)
            self._text_frame.pack(before=self._blur_cb, fill=tk.X, pady=2)
            self._text_frame2.pack(before=self._blur_cb, fill=tk.X, pady=2)
        if self.clear_img:
            self._load_all()

    def _browse_audio(self):
        path = filedialog.askopenfilename(filetypes=[
            ('Audio files', '*.mp3 *.wav *.ogg *.m4a *.aac *.flac *.opus'),
            ('All files', '*.*')])
        if path:
            self._audio_entry.config(state=tk.NORMAL)
            self._audio_entry.delete(0, tk.END)
            self._audio_entry.insert(0, path)
            self.use_audio.set(True)
            self._audio_entry.config(fg=FG)

    def _add_audio_row(self):
        '''Add a new audio file entry row with a remove button.'''
        if len(self._audio_entries) == 0:
            self._audio_extra_container.pack(fill=tk.X, pady=1)
        row_frame = tk.Frame(self._audio_extra_container, bg=BG)
        row_frame.pack(fill=tk.X, pady=2)
        var = tk.StringVar()
        state = tk.NORMAL if self.use_audio.get() else tk.DISABLED
        fg_color = FG if self.use_audio.get() else FG_FAINT
        entry = tk.Entry(row_frame, bg=ENTRY_BG, fg=fg_color, font=self._font_sm,
                          textvariable=var, relief=tk.SOLID, bd=1, state=state)
        entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Button(row_frame, text='浏览...', bg=BTN_BG, fg=FG, font=self._font_sm,
                   relief=tk.RAISED, bd=1,
                   command=lambda e=entry, s=self, v=var: self._browse_audio_entry(e, v)).pack(side=tk.RIGHT)
        tk.Button(row_frame, text='-', bg=BTN_RED, fg='#fff', font=self._font_sm,
                   relief=tk.RAISED, bd=1, width=2,
                   command=lambda e=entry, f=row_frame, s=self, v=var: self._remove_audio_row(f, e, v)).pack(side=tk.RIGHT, padx=1)
        self._audio_entries.append({'entry': entry, 'var': var, 'frame': row_frame})

    def _browse_audio_entry(self, entry, var):
        '''Browse for audio file for an additional audio row.'''
        path = filedialog.askopenfilename(filetypes=[
            ('Audio files', '*.mp3 *.wav *.ogg *.m4a *.aac *.flac *.opus'),
            ('All files', '*.*')])
        if path:
            entry.config(state=tk.NORMAL)
            entry.delete(0, tk.END)
            entry.insert(0, path)
            entry.config(fg=FG)
            if not self.use_audio.get():
                self.use_audio.set(True)
                self._toggle_audio()

    def _remove_audio_row(self, frame, entry, var):
        '''Remove a specific additional audio row.'''
        frame.destroy()
        self._audio_entries = [ae for ae in self._audio_entries if ae['entry'] is not entry]
        if len(self._audio_entries) == 0:
            self._audio_extra_container.pack_forget()

    def _load_image(self, path):
        if os.path.exists(path):
            return np.array(Image.open(path).convert('RGBA'))
        return None

    def _load_all(self):
        try:
            self.clear_img = self._load_image(self._entries['clear'].get())
            if self.use_sub_file.get():
                self.sub_img = self._load_image(self._entries['sub'].get())
                self._chinese_text = None
                self._other_text = None
            else:
                cn_text = self._chinese_text_entry.get().strip()
                if cn_text:
                    self.sub_img = None
                    self._chinese_text = cn_text
                    if self._other_text_entry.get().strip():
                        self._other_text = self._other_text_entry.get().strip()
                    else:
                        self._other_text = None
                else:
                    self.sub_img = None
                    self._chinese_text = None
                    self._other_text = None
            if self.use_blur_file.get():
                self.blur_img = self._load_image(self._blur_entry.get())
            else:
                self.blur_img = None
            if self.clear_img is not None:
                self._status.config(text='自动生成动感模糊...', fg='#c90')
                self.root.update()
                self.blur_img = _make_motion_blur(self.clear_img, angle=90, distance=10)
            if self.sub_bg_img is None:
                self.sub_bg_img = self._load_image(os.path.join(SCRIPT_DIR, 'Sprite', 'zuozhu_000_bg.png'))
            has_subtitle = bool(self._chinese_text) or self.sub_img is not None
            if self.clear_img is not None and self.blur_img is not None and has_subtitle and self.sub_bg_img is not None:
                self._status.config(text='已加载', fg='#0a0')
                self._rebuild_renderer()
                return None
            missing = []
            if self.clear_img is None:
                missing.append('清晰角色图')
            if self.blur_img is None:
                missing.append('模糊图')
            if not has_subtitle:
                missing.append('字幕图 或 中文字幕')
            self._status.config(text=f'缺少: {", ".join(missing)}', fg='#c00')
            return None
        except Exception as e:
            self._status.config(text=f'加载失败: {e}', fg='#c00')
            return None

    def _get_cfg(self):
        cfg = {}
        for k, v in self._params.items():
            cfg[k] = v.get() * self._param_scale.get(k, 1.0)
        return cfg

    def _rebuild_renderer(self):
        cfg = self._get_cfg()
        self.renderer = AoyituRenderer(self.clear_img, self.blur_img, self.sub_img,
                                        None, None, self.sub_bg_img,
                                        self._chinese_text, self._other_text, cfg)
        self._pre_render()

    def _on_param_change(self):
        if not self.renderer:
            return None
        cfg = self._get_cfg()
        self.renderer.cfg = cfg
        self.renderer.sprite_scale = cfg.get('char_scale', 1.2)
        if self._chinese_text:
            from aoyitu import _render_text_sprite
            font_size = int(27 * self.renderer.char_h / 320)
            font_smooth = cfg.get('font_smooth', 1.0)
            self.renderer.sub = _render_text_sprite(self._chinese_text, self._other_text,
                                                     font_size, self.renderer.char_h,
                                                     self.renderer.char_w, font_smooth)
        self._pre_render()

    def _pre_render(self):
        '''Pre-render all frames with progress.'''
        self.frames_cache = {}
        def run():
            for i in range(self.total_frames):
                if self.renderer:
                    self.frames_cache[i] = self.renderer.render(i)
                if i % 10 == 0:
                    self._status.config(text=f'渲染中 {i}/{self.total_frames}...', fg='#c90')
            self._status.config(text='就绪', fg='#0a0')
            self._show_frame()
        t = threading.Thread(target=run, daemon=True)
        t.start()

    def _get_frame(self, fi):
        if fi not in self.frames_cache and self.renderer:
            self.frames_cache[fi] = self.renderer.render(fi)
        return self.frames_cache.get(fi)

    def _show_frame(self):
        if not self.renderer:
            return None
        img = self._get_frame(self.current_frame)
        if not img:
            return None
        scale = min(680 / img.width, 400 / img.height, 1.0)
        dw = max(1, int(img.width * scale))
        dh = max(1, int(img.height * scale))
        display = img.resize((dw, dh), Image.NEAREST)
        photo = ImageTk.PhotoImage(display)
        self.preview_label.config(image=photo)
        self.preview_label.image = photo
        self._frame_label.config(text=f'F{self.current_frame}/{self.total_frames - 1}')
        self._frame_slider.set(self.current_frame)

    def _goto(self, fi):
        fi = max(0, min(self.total_frames - 1, fi))
        if fi != self.current_frame:
            self.current_frame = fi
            self._show_frame()
        return None

    def _toggle_play(self):
        if self.playing:
            self.playing = False
            self._play_btn.config(text='▶ 播放', bg=BTN_GREEN)
            return None
        self.playing = True
        self._play_btn.config(text='⏸ 暂停', bg=BTN_RED)
        self._play_loop()

    def _play_loop(self):
        if not self.playing:
            return None
        self.current_frame = (self.current_frame + 1) % self.total_frames
        self._show_frame()
        fps = int(self._params.get('fps', tk.DoubleVar(value=30)).get())
        delay = int(1000 / fps)
        self.root.after(delay, self._play_loop)

    def _generate(self):
        if not self.renderer:
            messagebox.showerror('错误', '请先加载素材')
            return None
        def run():
            cfg = self._get_cfg()
            fps = int(cfg.get('fps', 30))
            path = os.path.join(OUTPUT_DIR, 'aoyitu_output.gif')
            frames = [self.renderer.render(i) for i in range(self.total_frames)]
            out_frames = []
            for f in frames:
                if f.mode != 'P':
                    f = f.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
                out_frames.append(f)
            out_frames[0].save(path, save_all=True, append_images=out_frames[1:],
                                duration=1000 // fps, loop=0, optimize=True)
            self._status.config(text='完成: aoyitu_output.gif', fg='#0a0')
        def run_inner():
            try:
                run()
            except Exception as e:
                self._status.config(text=f'错误: {e}', fg='#c00')
        self._status.config(text='生成中...', fg='#c90')
        self.root.update()
        threading.Thread(target=run_inner, daemon=True).start()

    def _get_ffmpeg(self):
        '''Locate ffmpeg from system PATH (no bundled copy).'''
        import shutil
        return shutil.which('ffmpeg')

    def _get_audio_duration(self, ffmpeg, audio_path):
        '''Get audio duration in seconds using ffmpeg.'''
        import re
        result = subprocess.run([ffmpeg, '-i', audio_path], capture_output=True, text=True,
                                 encoding='utf-8', errors='replace', timeout=30)
        m = re.search(r'Duration: (\d+):(\d+):(\d+\.\d+)', result.stderr)
        if m:
            return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
        return None

    def _generate_mp4(self):
        if not self.renderer:
            messagebox.showerror('错误', '请先加载素材')
            return None
        def run():
            import shutil
            cfg = self._get_cfg()
            fps = int(cfg.get('fps', 30))
            ts = time.strftime('%H%M%S')
            fname = f'aoyitu_output_{ts}.mp4'
            path = os.path.join(OUTPUT_DIR, fname)
            frames = [self.renderer.render(i) for i in range(self.total_frames)]
            h = frames[0].height
            w = frames[0].width
            ffmpeg = self._get_ffmpeg()
            if ffmpeg is None:
                self._status.config(text='错误: 未找到 ffmpeg（请安装并加入 PATH）', fg='#c00')
                return
            audio_paths = []
            if self.use_audio.get():
                p = self._audio_entry.get().strip()
                if p and os.path.exists(p):
                    audio_paths.append(p)
                for ae in self._audio_entries:
                    pv = ae['var'].get().strip()
                    if pv and os.path.exists(pv):
                        audio_paths.append(pv)
            video_dur = self.total_frames / fps
            audio_dur = 0.0
            extra = False
            for ap in audio_paths:
                dur = self._get_audio_duration(ffmpeg, ap)
                if dur is None:
                    self._status.config(text='错误: 无法读取音频时长', fg='#c00')
                    return
                audio_dur += dur
                if audio_dur > video_dur:
                    extra = True
            black = Image.new('RGB', (w, h), (0, 0, 0))
            if extra:
                pad_frames = int((audio_dur - video_dur) * fps)
                if pad_frames > 0:
                    frames.extend([black] * pad_frames)
                    video_dur = audio_dur
            import subprocess as sp
            cmd = [ffmpeg, '-y', '-f', 'rawvideo', '-vcodec', 'rawvideo',
                    '-s', f'{w}x{h}', '-pix_fmt', 'rgb24', '-r', str(fps),
                    '-i', '-']
            inputs = []
            filter_strs = []
            for idx, ap in enumerate(audio_paths):
                inputs.extend(['-i', ap])
                filter_strs.append(f'[0:v][{idx + 1}:a]concat=n=1:v=1:a=1[v{idx}a{idx}]')
            if audio_paths:
                filter_str = ''.join(filter_strs)
                out_idx = len(audio_paths)
                filter_str += f'[v{out_idx-1}a{out_idx-1}]concat=n=1:v=1:a=1[outv][outa]'
                cmd.extend(['-filter_complex', filter_str, '-map', '[outv]', '-map', '[outa]'])
            else:
                cmd.extend(['-filter_complex', f'apad=whole_dur={video_dur:.3f}s', '-map', '0:v'])
            cmd.extend(['-c:v', 'libx264', '-crf', '18', '-preset', 'fast',
                         '-pix_fmt', 'yuv420p', '-movflags', '+faststart'])
            if audio_paths:
                cmd.extend(['-c:a', 'aac', '-shortest'])
            proc = sp.Popen(cmd, stdin=sp.PIPE, stdout=sp.PIPE, stderr=sp.PIPE)
            for f in frames:
                proc.stdin.write(f.convert('RGB').tobytes())
            proc.stdin.close()
            try:
                _, err = proc.communicate(timeout=300)
                if proc.returncode != 0:
                    self._status.config(text=f'编码失败: {err.decode("utf-8", errors="replace")[:200]}', fg='#c00')
                    return
            except sp.TimeoutExpired:
                proc.kill()
                self._status.config(text='编码超时(5分钟)', fg='#c00')
                return
            self._status.config(text=f'完成: {fname}', fg='#0a0')
        def run_inner():
            try:
                run()
            except Exception as e:
                self._status.config(text=f'错误: {e}', fg='#c00')
        self._status.config(text='生成MP4中...', fg='#c90')
        self.root.update()
        threading.Thread(target=run_inner, daemon=True).start()

if __name__ == '__main__':
    AoyituGUI()
