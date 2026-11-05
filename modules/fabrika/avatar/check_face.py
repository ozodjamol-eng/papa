"""Проверка «это Озод?» — сравнивает лица на картинке/кадре видео с эталоном (ozod_centroid.npy).
Запуск: python3 check_face.py файл.png|файл.mp4 [...]. Порог: анфас/3-4 >= 0.80 — годно; 0.65–0.80 — сомнительно; ниже — брак.
(Профиль сам по себе даёт ~0.70 — для профиля порог 0.65.) Модель: insightface buffalo_l (бесплатно, CPU)."""
import sys, os, cv2, numpy as np
from insightface.app import FaceAnalysis
C = np.load(os.path.join(os.path.dirname(os.path.abspath(__file__)), "ozod_centroid.npy"))
app = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"]); app.prepare(ctx_id=-1, det_size=(1024, 1024))
def frames(p):
    if p.lower().endswith((".mp4", ".mov")):
        cap = cv2.VideoCapture(p); n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT)); fps = cap.get(cv2.CAP_PROP_FPS) or 24
        for k in range(0, n, max(1, int(fps / 2))):
            cap.set(cv2.CAP_PROP_POS_FRAMES, k); ok, im = cap.read()
            if ok: yield f"{k/fps:5.1f}s", im
    else: yield "img", cv2.imread(p)
for p in sys.argv[1:]:
    worst = 1
    for tag, im in frames(p):
        fs = [f for f in app.get(im) if f.det_score > .6]
        if not fs: print(f"{p} {tag}: лица нет"); continue
        f = max(fs, key=lambda f: float(f.normed_embedding @ C)); s = float(f.normed_embedding @ C)
        yaw = abs(float(f.pose[1])) if f.pose is not None else 0; lim = .65 if yaw > 50 else .80
        v = "✅ годно" if s >= lim else ("⚠️ сомнительно" if s >= lim - .15 else "❌ не он"); worst = min(worst, s)
        print(f"{p} {tag}: похожесть {s:.2f} (поворот {yaw:.0f}°) {v}")
    print(f"== {p}: худший кадр {worst:.2f}")
