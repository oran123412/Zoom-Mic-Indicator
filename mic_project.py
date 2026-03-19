import tkinter as tk, sounddevice as sd, numpy as np, pygetwindow as gw
from pywinauto import Desktop
from PIL import Image, ImageTk
import os, ctypes, threading, time

try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
except: pass

TRANS_COLOR, TURQUOISE, PINK, CYAN = "#000001", "#40C4A1", "#FF1493", "#00FFFF"
root = tk.Tk()
root.overrideredirect(True)
root.attributes("-topmost", True, "-transparentcolor", TRANS_COLOR)
root.config(bg=TRANS_COLOR)
root.withdraw()

SIZE = 400
canv = tk.Canvas(root, width=SIZE, height=SIZE, bg=TRANS_COLOR, highlightthickness=0)
canv.pack()
CENTER, ICON_R = SIZE // 2, 90
WAVE1_STROKE = 14
WAVE2_STROKE = 10

# מגבלת רדיוס בטוחה כדי למנוע חיתוך ע"י גבולות ה-canvas
MAX_R1_SAFE = (SIZE // 2) - (WAVE1_STROKE // 2) - 1
MAX_R2_SAFE = (SIZE // 2) - (WAVE2_STROKE // 2) - 1

# הגבלת גודל ההדים (כדי שלא יהיו גדולים מדי)
MAX_R1_CAP = ICON_R + 70
MAX_R2_CAP = ICON_R + 85
MAX_R1 = min(MAX_R1_SAFE, MAX_R1_CAP)
MAX_R2 = min(MAX_R2_SAFE, MAX_R2_CAP)
FADE_MARGIN1 = 35  # רדיוס אחרון שבו עושים דהייה רכה
FADE_MARGIN2 = 45
MIN_STROKE = 1

try:
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'microphone.png')
    img_pil = Image.open(path); mic_img = ImageTk.PhotoImage(img_pil)
    canv.create_oval(CENTER-ICON_R, CENTER-ICON_R, CENTER+ICON_R, CENTER+ICON_R, fill=TURQUOISE, width=0)
    # יצירת ההדים פעם אחת מראש
    wave1 = canv.create_oval(0,0,0,0, outline=PINK, width=WAVE1_STROKE, state='hidden')
    wave2 = canv.create_oval(0,0,0,0, outline=CYAN, width=WAVE2_STROKE, state='hidden')
    canv.create_image(CENTER, CENTER, image=mic_img); canv.image_ref = mic_img
except: pass

is_muted = False
def check_zoom_loop():
    global is_muted
    while True:
        try:
            if [w for w in gw.getWindowsWithTitle("Zoom Meeting") if w.visible]:
                root.deiconify()
                txt = str([c.window_text() for c in Desktop(backend="uia").window(title="Zoom Meeting").descendants()]).lower()
                is_muted = "audio muted" in txt or "unmuted" not in txt
            else: is_muted = False;root.withdraw()
        except: pass
        sd.sleep(1000)

def start_drag(e): root.x, root.y = e.x, e.y
def do_drag(e): root.geometry(f"+{root.winfo_x()+(e.x-root.x)}+{root.winfo_y()+(e.y-root.y)}")
canv.bind("<Button-1>", start_drag); canv.bind("<B1-Motion>", do_drag)

raw_v, anim_v = 0.0, 0.0
wave1_r, wave2_r = 0.0, 0.0
wave1_active, wave2_active = False, False
# כשיש קול מעל הסף הזה נתחיל "מחזור" הדים.
# אחרי שהתחיל מחזור, הוא ממשיך עד הסוף בלי קשר לקפיצות בעוצמה.
VOICE_GATE = 2.5
WAVE1_START_R = ICON_R + 5
WAVE2_START_R = ICON_R + 15

SPEED1 = 1.6  # פיקסלים לכל frame (פחות כדי שלא יהיה מהיר מדי)
SPEED2 = 1.9
START_COOLDOWN_MS = 120
cycle_cooldown_until = 0.0
def update_ui():
    global anim_v, wave1_r, wave2_r, wave1_active, wave2_active, cycle_cooldown_until
    if is_muted:
        wave1_active = wave2_active = False
        canv.itemconfig(wave1, state='hidden'); canv.itemconfig(wave2, state='hidden')
        cycle_cooldown_until = 0.0
    else:
        # עדכון חלק יותר של האנימציה + דעיכה איטית יותר, כדי שההדים יישארו יותר זמן
        if raw_v > anim_v:
            anim_v += (raw_v - anim_v) * 0.25
        else:
            anim_v *= 0.97

        voice_active = anim_v > VOICE_GATE
        now = time.monotonic()

        # אם אין כרגע מחזור פעיל - נתחיל חדש רק כשיש קול יציב (עם cooldown כדי למנוע התחלה מחדש מהר מדי)
        if voice_active and (not wave1_active) and (not wave2_active) and now >= cycle_cooldown_until:
            wave1_active = True
            wave2_active = False
            wave1_r = WAVE1_START_R
            canv.itemconfig(wave1, state='normal')
            canv.itemconfig(wave1, width=WAVE1_STROKE)
            canv.coords(wave1, CENTER-wave1_r, CENTER-wave1_r, CENTER+wave1_r, CENTER+wave1_r)
            canv.itemconfig(wave2, state='hidden')
            # שמור על wave2_r ברדיוס התחלה כדי שתהיה התחלה נקייה למחזור הבא
            wave2_r = WAVE2_START_R

        # גל ראשון: גדל עד הסוף ואז מסיים
        if wave1_active:
            wave1_r += SPEED1
            if wave1_r >= MAX_R1:
                wave1_r = MAX_R1
            canv.coords(wave1, CENTER-wave1_r, CENTER-wave1_r, CENTER+wave1_r, CENTER+wave1_r)

            # דהייה רכה לקראת הסוף (מוריד עובי קו)
            if wave1_r >= (MAX_R1 - FADE_MARGIN1):
                t = (MAX_R1 - wave1_r) / FADE_MARGIN1  # 1..0
                stroke = max(MIN_STROKE, int(WAVE1_STROKE * t))
                canv.itemconfig(wave1, width=stroke)
            else:
                canv.itemconfig(wave1, width=WAVE1_STROKE)

            if wave1_r >= MAX_R1:
                wave1_active = False
                canv.itemconfig(wave1, state='hidden')

                # מיד כשגל ראשון מגיע לסוף - מפעילים את גל שני
                wave2_active = True
                wave2_r = WAVE2_START_R
                canv.coords(wave2, CENTER-wave2_r, CENTER-wave2_r, CENTER+wave2_r, CENTER+wave2_r)
                canv.itemconfig(wave2, state='normal', width=WAVE2_STROKE)

        # גל שני: גדל עד הסוף ואז מסיים
        if wave2_active:
            wave2_r += SPEED2
            if wave2_r >= MAX_R2:
                wave2_r = MAX_R2
            canv.coords(wave2, CENTER-wave2_r, CENTER-wave2_r, CENTER+wave2_r, CENTER+wave2_r)

            # דהייה רכה לקראת הסוף (מוריד עובי קו)
            if wave2_r >= (MAX_R2 - FADE_MARGIN2):
                t = (MAX_R2 - wave2_r) / FADE_MARGIN2
                stroke = max(MIN_STROKE, int(WAVE2_STROKE * t))
                canv.itemconfig(wave2, width=stroke)
            else:
                canv.itemconfig(wave2, width=WAVE2_STROKE)

            if wave2_r >= MAX_R2:
                wave2_active = False
                canv.itemconfig(wave2, state='hidden')
                cycle_cooldown_until = now + (START_COOLDOWN_MS / 1000.0)
    root.after(16, update_ui)

def cb(d, f, t, s):
    global raw_v
    # רגישות מעט נמוכה יותר + דעיכה איטית יותר כדי למנוע "קפיצות" וכתמים
    vol = np.max(np.abs(d)) * 400
    if vol > raw_v:
        raw_v = vol
    else:
        raw_v *= 0.9

threading.Thread(target=check_zoom_loop, daemon=True).start()
update_ui()
with sd.InputStream(callback=cb, blocksize=128, latency='low'): root.mainloop()