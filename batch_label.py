"""
Grid Batch Labeller  —  label many images fast
================================================
Shows a 5×4 grid of images. Select any number, press 1/2/3 to label them all at once.
Typical speed: ~200 images/minute.

Controls:
  Click image      → toggle selected (yellow border)
  A                → select ALL on current page
  1                → label selected as  Pollinating
  2                → label selected as  Pollinated
  3                → label selected as  Not Pollinated
  S                → skip selected (move to next page without labelling)
  Right / D        → next page
  Left  / B        → previous page (to re-label)
  Ctrl + Z         → undo last batch
  Ctrl + S / Q     → save & quit  → auto-organises into DATASETS_ORGANIZED

Run:  python batch_label.py
"""

import os, shutil, random, json
from pathlib import Path
from collections import Counter
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk

# ── Config ────────────────────────────────────────────────────────────────────
SOURCE_DIR   = r"C:\Users\Admin\Desktop\CAPS\DATASETS"
TARGET_DIR   = r"C:\Users\Admin\Desktop\CAPS\DATASETS_ORGANIZED"
PROGRESS_FILE= r"C:\Users\Admin\Desktop\CAPS\.label_progress.json"   # autosave

COLS, ROWS   = 3, 2          # grid size  (3×2 = 6 images per page)
THUMB_W      = 450
THUMB_H      = 380
PAD          = 8

CATEGORIES = {
    '1': 'pollinating',
    '2': 'pollinated',
    '3': 'not_pollinated',
}
CAT_COLORS = {
    'pollinating':    '#27ae60',
    'pollinated':     '#2980b9',
    'not_pollinated': '#e74c3c',
    None:             '#2b2b2b',
}

IMG_EXTS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'}

# ── Helpers ───────────────────────────────────────────────────────────────────
def load_images():
    imgs = sorted([
        str(p) for p in Path(SOURCE_DIR).iterdir()
        if p.is_file() and p.suffix.lower() in IMG_EXTS
    ])
    return imgs


def save_progress(labels: dict):
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(labels, f)


def load_progress() -> dict:
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE) as f:
            return json.load(f)
    return {}


def organize_and_split(labels: dict):
    """Copy labelled images into train/val/test splits."""
    by_class = {}
    for path, cat in labels.items():
        by_class.setdefault(cat, []).append(path)

    print("\nOrganising …")
    for cat, imgs in by_class.items():
        random.shuffle(imgs)
        n   = len(imgs)
        t_end = int(n * 0.70)
        v_end = t_end + int(n * 0.15)
        splits = {
            'train': imgs[:t_end],
            'val':   imgs[t_end:v_end],
            'test':  imgs[v_end:],
        }
        for split, paths in splits.items():
            dest = Path(TARGET_DIR) / split / cat
            dest.mkdir(parents=True, exist_ok=True)
            for p in paths:
                src  = Path(p)
                dst  = dest / src.name
                ctr  = 1
                while dst.exists():
                    dst = dest / f"{src.stem}_{ctr}{src.suffix}"
                    ctr += 1
                shutil.copy2(src, dst)
        print(f"  {cat}: {n} images → "
              f"train {len(splits['train'])} / "
              f"val {len(splits['val'])} / "
              f"test {len(splits['test'])}")

    print("\n✅ Done. Ready to train!")


# ── Main App ──────────────────────────────────────────────────────────────────
class BatchLabeller:
    def __init__(self, root):
        self.root    = root
        self.root.title("🏷️  Batch Image Labeller")
        self.root.configure(bg='#1a1a2e')
        self.root.state('zoomed')       # start maximised

        self.all_images  = load_images()
        self.labels      = load_progress()      # path → category
        self.undo_stack  = []                   # list of dicts for undo
        self.selected    = set()                # indices on current page
        self.page        = self._first_unlabelled_page()
        self.thumbs      = {}                   # cache: path → PhotoImage

        self._build_ui()
        self._render_page()
        self._bind_keys()

    # ── page helpers ─────────────────────────────────────────────────────────
    def _per_page(self):  return COLS * ROWS
    def _total_pages(self):
        return max(1, (len(self.all_images) + self._per_page() - 1) // self._per_page())

    def _first_unlabelled_page(self):
        pp = self._per_page()
        for i, p in enumerate(self.all_images):
            if p not in self.labels:
                return i // pp
        return 0

    def _page_images(self):
        s = self.page * self._per_page()
        return self.all_images[s: s + self._per_page()]

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build_ui(self):
        # ── top bar ──────────────────────────────────────────────────────────
        top = tk.Frame(self.root, bg='#16213e', pady=8)
        top.pack(fill=tk.X)

        self.progress_lbl = tk.Label(top, text="", font=('Segoe UI', 12, 'bold'),
                                     bg='#16213e', fg='#e2b96f')
        self.progress_lbl.pack(side=tk.LEFT, padx=16)

        self.count_lbl = tk.Label(top, text="", font=('Segoe UI', 11),
                                   bg='#16213e', fg='#aaaacc')
        self.count_lbl.pack(side=tk.LEFT, padx=10)

        # save/quit button
        tk.Button(top, text="💾  Save & Quit", font=('Segoe UI', 11, 'bold'),
                  bg='#27ae60', fg='white', relief=tk.FLAT, padx=14, pady=6,
                  command=self._save_quit).pack(side=tk.RIGHT, padx=10)

        tk.Button(top, text="↩  Undo", font=('Segoe UI', 11),
                  bg='#555577', fg='white', relief=tk.FLAT, padx=10, pady=6,
                  command=self._undo).pack(side=tk.RIGHT, padx=4)

        # ── label buttons ────────────────────────────────────────────────────
        btn_bar = tk.Frame(self.root, bg='#1a1a2e', pady=6)
        btn_bar.pack(fill=tk.X)

        btn_kw = dict(font=('Segoe UI', 13, 'bold'), relief=tk.FLAT,
                      padx=20, pady=10, cursor='hand2')

        tk.Button(btn_bar, text="1 — Pollinating",    bg='#27ae60', fg='white',
                  command=lambda: self._label_selected('1'), **btn_kw).pack(side=tk.LEFT, padx=8)
        tk.Button(btn_bar, text="2 — Pollinated",     bg='#2980b9', fg='white',
                  command=lambda: self._label_selected('2'), **btn_kw).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_bar, text="3 — Not Pollinated", bg='#e74c3c', fg='white',
                  command=lambda: self._label_selected('3'), **btn_kw).pack(side=tk.LEFT, padx=4)
        tk.Button(btn_bar, text="A — Select All",     bg='#8e44ad', fg='white',
                  command=self._select_all, **btn_kw).pack(side=tk.LEFT, padx=12)

        nav_kw = dict(font=('Segoe UI', 12), relief=tk.FLAT, padx=14, pady=10, cursor='hand2')
        tk.Button(btn_bar, text="◀ Back",  bg='#2c3e50', fg='white',
                  command=self._prev_page, **nav_kw).pack(side=tk.RIGHT, padx=4)
        tk.Button(btn_bar, text="Next ▶",  bg='#2c3e50', fg='white',
                  command=self._next_page, **nav_kw).pack(side=tk.RIGHT, padx=4)

        # hint
        tk.Label(btn_bar,
                 text="Click images to select  •  Yellow = selected  •  Coloured border = labelled",
                 font=('Segoe UI', 9), bg='#1a1a2e', fg='#666688').pack(side=tk.LEFT, padx=20)

        # ── image grid ───────────────────────────────────────────────────────
        grid_outer = tk.Frame(self.root, bg='#1a1a2e')
        grid_outer.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self.cells = []   # list of dicts with frame/label/img_label
        for row in range(ROWS):
            for col in range(COLS):
                idx = row * COLS + col
                outer = tk.Frame(grid_outer, bg='#2b2b2b',
                                 bd=3, relief=tk.FLAT)
                outer.grid(row=row, column=col, padx=PAD, pady=PAD, sticky='nsew')
                grid_outer.columnconfigure(col, weight=1)
                grid_outer.rowconfigure(row,    weight=1)

                img_lbl = tk.Label(outer, bg='#2b2b2b', cursor='hand2')
                img_lbl.pack(fill=tk.BOTH, expand=True)

                name_lbl = tk.Label(outer, text="", font=('Segoe UI', 10),
                                    bg='#2b2b2b', fg='#999999', pady=2)
                name_lbl.pack()

                cat_lbl = tk.Label(outer, text="", font=('Segoe UI', 12, 'bold'),
                                   bg='#2b2b2b', fg='white', pady=3)
                cat_lbl.pack()

                cell = {'frame': outer, 'img_lbl': img_lbl,
                        'name_lbl': name_lbl, 'cat_lbl': cat_lbl,
                        'path': None}
                self.cells.append(cell)

                img_lbl.bind('<Button-1>', lambda e, i=idx: self._toggle_select(i))
                outer.bind('<Button-1>',   lambda e, i=idx: self._toggle_select(i))

        # ── status bar ───────────────────────────────────────────────────────
        self.status_lbl = tk.Label(self.root, text="", font=('Segoe UI', 10),
                                   bg='#0f1e3d', fg='#99bbdd', pady=4)
        self.status_lbl.pack(fill=tk.X)

    # ── keyboard ──────────────────────────────────────────────────────────────
    def _bind_keys(self):
        self.root.bind('1',          lambda e: self._label_selected('1'))
        self.root.bind('2',          lambda e: self._label_selected('2'))
        self.root.bind('3',          lambda e: self._label_selected('3'))
        self.root.bind('a',          lambda e: self._select_all())
        self.root.bind('A',          lambda e: self._select_all())
        self.root.bind('s',          lambda e: self._next_page())
        self.root.bind('S',          lambda e: self._next_page())
        self.root.bind('<Right>',    lambda e: self._next_page())
        self.root.bind('d',          lambda e: self._next_page())
        self.root.bind('<Left>',     lambda e: self._prev_page())
        self.root.bind('b',          lambda e: self._prev_page())
        self.root.bind('<Control-z>',lambda e: self._undo())
        self.root.bind('<Control-Z>',lambda e: self._undo())
        self.root.bind('<Control-s>',lambda e: self._save_quit())
        self.root.bind('<Control-S>',lambda e: self._save_quit())
        self.root.bind('q',          lambda e: self._save_quit())
        self.root.bind('Q',          lambda e: self._save_quit())

    # ── rendering ─────────────────────────────────────────────────────────────
    def _render_page(self):
        imgs  = self._page_images()
        self.selected.clear()

        for idx, cell in enumerate(self.cells):
            if idx < len(imgs):
                path = imgs[idx]
                cell['path'] = path
                # thumbnail (cached)
                if path not in self.thumbs:
                    try:
                        img = Image.open(path).convert('RGB')
                        img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
                        self.thumbs[path] = ImageTk.PhotoImage(img)
                    except Exception:
                        self.thumbs[path] = None

                photo = self.thumbs.get(path)
                if photo:
                    cell['img_lbl'].config(image=photo, text='')
                    cell['img_lbl'].image = photo
                else:
                    cell['img_lbl'].config(image='', text='?', font=('Segoe UI', 20))

                cell['name_lbl'].config(text=Path(path).name[:28])
                cat = self.labels.get(path)
                if cat:
                    cell['cat_lbl'].config(text=cat.replace('_', ' '), fg=CAT_COLORS[cat])
                    cell['frame'].config(bg=CAT_COLORS[cat])
                else:
                    cell['cat_lbl'].config(text='unlabelled', fg='#555577')
                    cell['frame'].config(bg='#2b2b2b')
            else:
                # empty cell
                cell['path'] = None
                cell['img_lbl'].config(image='', text='')
                cell['name_lbl'].config(text='')
                cell['cat_lbl'].config(text='')
                cell['frame'].config(bg='#1a1a2e')

        self._update_status()

    def _update_status(self):
        total    = len(self.all_images)
        done     = len(self.labels)
        pages    = self._total_pages()
        counts   = Counter(self.labels.values())
        sel      = len(self.selected)

        self.progress_lbl.config(
            text=f"Page {self.page+1} / {pages}   |   "
                 f"Labelled {done} / {total}  ({100*done/total:.0f}%)"
        )
        self.count_lbl.config(
            text=f"🟢 {counts.get('pollinating',0)}  "
                 f"🔵 {counts.get('pollinated',0)}  "
                 f"🔴 {counts.get('not_pollinated',0)}"
        )
        hint = f"{sel} selected — press 1 / 2 / 3 to label" if sel else \
               "Click images to select, or press A to select all"
        self.status_lbl.config(text=hint)

    # ── interactions ─────────────────────────────────────────────────────────
    def _toggle_select(self, cell_idx):
        if cell_idx >= len(self._page_images()):
            return
        cell = self.cells[cell_idx]
        if cell_idx in self.selected:
            self.selected.discard(cell_idx)
            cat = self.labels.get(cell['path'])
            cell['frame'].config(bg=CAT_COLORS.get(cat, '#2b2b2b'))
        else:
            self.selected.add(cell_idx)
            cell['frame'].config(bg='#f1c40f')   # yellow = selected
        self._update_status()

    def _select_all(self):
        imgs = self._page_images()
        if self.selected == set(range(len(imgs))):
            # deselect all
            self.selected.clear()
            self._render_page()
        else:
            self.selected = set(range(len(imgs)))
            for i in self.selected:
                self.cells[i]['frame'].config(bg='#f1c40f')
        self._update_status()

    def _label_selected(self, key):
        if not self.selected:
            self._select_all()

        cat   = CATEGORIES[key]
        imgs  = self._page_images()
        snapshot = {}

        for i in self.selected:
            if i < len(imgs):
                path = imgs[i]
                snapshot[path] = self.labels.get(path)   # for undo
                self.labels[path] = cat

        self.undo_stack.append(snapshot)
        save_progress(self.labels)
        self.selected.clear()
        self._render_page()

        # auto-advance to next page when all cells labelled
        if all(imgs[i] in self.labels for i in range(len(imgs))):
            self._next_page()

    def _next_page(self):
        if self.page < self._total_pages() - 1:
            self.page += 1
            self._render_page()

    def _prev_page(self):
        if self.page > 0:
            self.page -= 1
            self._render_page()

    def _undo(self):
        if not self.undo_stack:
            return
        snapshot = self.undo_stack.pop()
        for path, old_cat in snapshot.items():
            if old_cat is None:
                self.labels.pop(path, None)
            else:
                self.labels[path] = old_cat
        save_progress(self.labels)
        self._render_page()

    def _save_quit(self):
        save_progress(self.labels)
        total  = len(self.all_images)
        done   = len(self.labels)
        counts = Counter(self.labels.values())

        msg = (f"Labelled {done} / {total} images\n\n"
               f"  Pollinating   : {counts.get('pollinating', 0)}\n"
               f"  Pollinated    : {counts.get('pollinated', 0)}\n"
               f"  Not Pollinated: {counts.get('not_pollinated', 0)}\n\n"
               f"Organise now into train/val/test folders?")

        if messagebox.askyesno("Save & Quit", msg):
            self.root.withdraw()
            try:
                organize_and_split(self.labels)
                if os.path.exists(PROGRESS_FILE):
                    os.remove(PROGRESS_FILE)
                messagebox.showinfo("Done",
                    f"✅ {done} images organised!\n\n"
                    f"Now run:\n  python train_high_accuracy.py")
            except Exception as e:
                messagebox.showerror("Error", str(e))

        self.root.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    if not os.path.exists(SOURCE_DIR) or not any(
        Path(SOURCE_DIR).glob('*')
    ):
        print(f"No images found in {SOURCE_DIR}")
    else:
        root = tk.Tk()
        app  = BatchLabeller(root)
        root.mainloop()
