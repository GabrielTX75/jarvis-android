"""JARVIS Hologram Lab: opt-in local webcam hand tracking + procedural 3D wireframes.

This first implementation is a transparent prototype: it renders editable wireframe
shapes, not photorealistic CAD assets. Camera frames stay in memory and are not saved
or transmitted. MediaPipe/OpenCV are optional runtime dependencies.
"""
import math
import tkinter as tk
from tkinter import ttk, messagebox

try:
    import cv2
    import mediapipe as mp
    from PIL import Image, ImageTk
except Exception:
    cv2 = mp = Image = ImageTk = None


class HologramLab:
    OBJECTS = ("Carro", "Moto", "Casa", "Edifício", "Robô", "Máquina",
               "Corpo humano (estudo)", "Mapa/terreno", "Objeto personalizado")

    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title("JARVIS — Laboratório de Hologramas")
        self.win.geometry("1120x720")
        self.win.minsize(850, 580)
        self.win.configure(bg="#06111d")
        self.cap = None
        self.hands = None
        self.camera_on = False
        self.after_id = None
        self.angle = 0.35
        self.pitch = -0.18
        self.zoom = 1.0
        self.offset_x = 0.0
        self.offset_y = 0.0
        self.explode = 0.0
        self.last_center = None
        self.last_pinch = None
        self.frame_photo = None
        self.object_name = tk.StringVar(value="Carro")
        self.status = tk.StringVar(value="Câmera desligada — processamento local")
        self._build()
        self.win.protocol("WM_DELETE_WINDOW", self.close)
        self.draw_model()

    def _build(self):
        top = tk.Frame(self.win, bg="#0b2031", padx=14, pady=10)
        top.pack(fill="x")
        tk.Label(top, text="HOLOGRAM LAB", fg="#58ddff", bg="#0b2031",
                 font=("Segoe UI", 17, "bold")).pack(side="left")
        tk.Label(top, text="3D INTERATIVO • CONTROLE POR GESTOS",
                 fg="#a9c8d8", bg="#0b2031", font=("Segoe UI", 9)).pack(side="right")

        body = tk.Frame(self.win, bg="#06111d")
        body.pack(fill="both", expand=True, padx=12, pady=12)
        left = tk.Frame(body, bg="#06111d")
        left.pack(side="left", fill="both", expand=True)
        right = tk.Frame(body, bg="#0b2031", padx=12, pady=12, width=300)
        right.pack(side="right", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        self.scene = tk.Canvas(left, bg="#04101b", highlightthickness=1,
                               highlightbackground="#17435b")
        self.scene.pack(fill="both", expand=True)
        self.scene.bind("<Configure>", lambda _e: self.draw_model())
        tk.Label(right, text="OBJETO 3D", fg="#58ddff", bg="#0b2031",
                 font=("Segoe UI", 11, "bold")).pack(anchor="w")
        ttk.Combobox(right, textvariable=self.object_name, values=self.OBJECTS,
                     state="readonly").pack(fill="x", pady=(6, 12))
        self.object_name.trace_add("write", lambda *_: self.draw_model())

        ttk.Button(right, text="Ativar câmera e gestos", command=self.start_camera).pack(fill="x", pady=4)
        ttk.Button(right, text="Desativar câmera", command=self.stop_camera).pack(fill="x", pady=4)
        ttk.Separator(right).pack(fill="x", pady=12)
        ttk.Button(right, text="Girar para a esquerda", command=lambda: self.rotate(-0.25, 0)).pack(fill="x", pady=3)
        ttk.Button(right, text="Girar para a direita", command=lambda: self.rotate(0.25, 0)).pack(fill="x", pady=3)
        ttk.Button(right, text="Abrir componentes", command=lambda: self.set_explode(min(1, self.explode + .2))).pack(fill="x", pady=3)
        ttk.Button(right, text="Reunir componentes", command=lambda: self.set_explode(max(0, self.explode - .2))).pack(fill="x", pady=3)
        ttk.Button(right, text="Redefinir visão", command=self.reset_view).pack(fill="x", pady=3)
        ttk.Separator(right).pack(fill="x", pady=12)
        tk.Label(right, textvariable=self.status, fg="#9bc8da", bg="#0b2031",
                 wraplength=260, justify="left").pack(anchor="w")
        tk.Label(right, text=("Gestos: mão aberta = girar • pinça polegar/indicador = zoom\n"
                              "Mover a mão = deslocar o objeto\n\n"
                              "Protótipo: modelos esquemáticos em arame. "
                              "Não são projetos técnicos nem modelos reais de fábrica."),
                 fg="#b8cbd5", bg="#0b2031", justify="left", wraplength=260).pack(anchor="w", pady=12)

        self.camera_label = tk.Label(left, bg="#071a28", fg="#9bc8da",
                                     text="Prévia da câmera aparece aqui quando ativada.")
        self.camera_label.pack(fill="x", pady=(8, 0))

    def start_camera(self):
        if self.camera_on:
            return
        if cv2 is None or mp is None or Image is None:
            messagebox.showerror("Dependências ausentes",
                "O rastreamento precisa de OpenCV, MediaPipe e Pillow. "
                "Instale as dependências opcionais do JARVIS EXE e tente novamente.")
            return
        try:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap.release()
                self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("Não foi possível acessar a câmera frontal/webcam padrão.")
            self.hands = mp.solutions.hands.Hands(
                static_image_mode=False, max_num_hands=1,
                min_detection_confidence=0.65, min_tracking_confidence=0.6)
            self.camera_on = True
            self.status.set("CÂMERA ATIVA • rastreamento local • sem gravação")
            self._camera_tick()
        except Exception as exc:
            self.stop_camera()
            messagebox.showerror("Câmera", str(exc))

    def _camera_tick(self):
        if not self.camera_on or self.cap is None:
            return
        ok, frame = self.cap.read()
        if ok:
            frame = cv2.flip(frame, 1)
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.hands.process(rgb)
            if result.multi_hand_landmarks:
                lm = result.multi_hand_landmarks[0].landmark
                center = ((lm[0].x + lm[9].x) / 2, (lm[0].y + lm[9].y) / 2)
                pinch = math.hypot(lm[4].x - lm[8].x, lm[4].y - lm[8].y)
                if self.last_center:
                    dx, dy = center[0] - self.last_center[0], center[1] - self.last_center[1]
                    if pinch < .075:
                        if self.last_pinch is not None:
                            self.zoom = max(.45, min(2.8, self.zoom + (pinch - self.last_pinch) * -4))
                    else:
                        self.angle += dx * 5
                        self.pitch = max(-1.15, min(1.15, self.pitch + dy * 4))
                    self.offset_x = max(-180, min(180, self.offset_x + dx * 450))
                    self.offset_y = max(-140, min(140, self.offset_y + dy * 350))
                    self.draw_model()
                self.last_center, self.last_pinch = center, pinch
                mp.solutions.drawing_utils.draw_landmarks(
                    frame, result.multi_hand_landmarks[0], mp.solutions.hands.HAND_CONNECTIONS)
            else:
                self.last_center = self.last_pinch = None
            small = cv2.resize(frame, (320, 180))
            image = ImageTk.PhotoImage(Image.fromarray(cv2.cvtColor(small, cv2.COLOR_BGR2RGB)))
            self.frame_photo = image
            self.camera_label.configure(image=image, text="")
        self.after_id = self.win.after(30, self._camera_tick)

    def stop_camera(self):
        self.camera_on = False
        if self.after_id:
            try: self.win.after_cancel(self.after_id)
            except Exception: pass
            self.after_id = None
        if self.hands:
            try: self.hands.close()
            except Exception: pass
            self.hands = None
        if self.cap:
            try: self.cap.release()
            except Exception: pass
            self.cap = None
        self.last_center = self.last_pinch = None
        self.camera_label.configure(image="", text="Prévia da câmera desligada.")
        self.frame_photo = None
        self.status.set("Câmera desligada — nenhuma imagem foi salva.")

    def close(self):
        self.stop_camera()
        self.win.destroy()

    def rotate(self, da, dp):
        self.angle += da
        self.pitch = max(-1.15, min(1.15, self.pitch + dp))
        self.draw_model()

    def set_explode(self, value):
        self.explode = value
        self.draw_model()

    def reset_view(self):
        self.angle, self.pitch, self.zoom = .35, -.18, 1.0
        self.offset_x = self.offset_y = self.explode = 0.0
        self.draw_model()

    def _geometry(self):
        # Procedural educational wireframes; coordinates are normalized.
        obj = self.object_name.get()
        if obj in ("Carro", "Moto"):
            # Main body, roof, wheels; deliberately schematic.
            verts = [(-1,-.35,-.45),(1,-.35,-.45),(1,-.35,.45),(-1,-.35,.45),
                     (-.65,.18,-.4),(.55,.18,-.4),(.55,.18,.4),(-.65,.18,.4),
                     (-.35,.55,-.32),(.35,.55,-.32),(.35,.55,.32),(-.35,.55,.32)]
            edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
                     (0,4),(1,5),(2,6),(3,7),(8,9),(9,10),(10,11),(11,8),
                     (4,8),(5,9),(6,10),(7,11)]
            if obj == "Moto":
                verts = [(-.9,-.2,-.2),(.9,-.2,-.2),(-.9,-.2,.2),(.9,-.2,.2),
                         (-.25,.15,0),(.25,.15,0),(0,.45,0)]
                edges = [(0,2),(2,3),(3,1),(1,0),(0,4),(4,5),(5,1),(4,6),(6,5)]
        elif obj in ("Casa", "Edifício"):
            h = 1.1 if obj == "Casa" else 1.8
            verts = [(-.7,-.7,-.7),(.7,-.7,-.7),(.7,-.7,.7),(-.7,-.7,.7),
                     (-.7,h-.7,-.7),(.7,h-.7,-.7),(.7,h-.7,.7),(-.7,h-.7,.7),
                     (0,h+.35,-.7),(0,h+.35,.7)]
            edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
                     (0,4),(1,5),(2,6),(3,7),(4,8),(8,5),(7,9),(9,6),(8,9)]
        elif obj in ("Robô", "Máquina"):
            verts = [(-.5,-.8,-.4),(.5,-.8,-.4),(.5,-.8,.4),(-.5,-.8,.4),
                     (-.5,.1,-.4),(.5,.1,-.4),(.5,.1,.4),(-.5,.1,.4),
                     (-.35,.75,-.3),(.35,.75,-.3),(.35,.75,.3),(-.35,.75,.3)]
            edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
                     (0,4),(1,5),(2,6),(3,7),(4,8),(5,9),(6,10),(7,11),
                     (8,9),(9,10),(10,11),(11,8)]
        elif obj.startswith("Corpo"):
            verts = [(0,1,0),(-.22,.55,0),(.22,.55,0),(-.3,-.2,0),(.3,-.2,0),
                     (-.2,-.85,0),(.2,-.85,0),(0,.72,0)]
            edges = [(7,0),(0,1),(0,2),(1,3),(2,4),(3,5),(4,6)]
        else:
            verts = [(-1,0,-1),(1,0,-1),(1,0,1),(-1,0,1),
                     (-.6,.6,-.6),(.6,.6,-.6),(.6,.6,.6),(-.6,.6,.6)]
            edges = [(0,1),(1,2),(2,3),(3,0),(4,5),(5,6),(6,7),(7,4),
                     (0,4),(1,5),(2,6),(3,7)]
            # Terrain/map grid
            for i in range(5):
                t = -.8 + i * .4
                verts.extend([(t, .05 * math.sin(i), -1), (t, .05 * math.cos(i), 1),
                              (-1, .05 * math.sin(i), t), (1, .05 * math.cos(i), t)])
                n = len(verts)
                edges.extend([(n-4,n-3),(n-2,n-1)])
        return verts, edges

    def draw_model(self):
        if not hasattr(self, "scene") or not self.scene.winfo_exists():
            return
        c = self.scene
        c.delete("all")
        w, h = max(200,c.winfo_width()), max(200,c.winfo_height())
        cx, cy = w/2 + self.offset_x, h/2 + self.offset_y
        c.create_text(18, 18, anchor="nw", text=self.object_name.get().upper(),
                      fill="#54dfff", font=("Segoe UI", 11, "bold"))
        c.create_text(18, 40, anchor="nw", text="VISUALIZAÇÃO 3D ESQUEMÁTICA",
                      fill="#648fa5", font=("Segoe UI", 8))
        # Ground grid
        for i in range(-5,6):
            c.create_line(cx-240+i*42, cy+130, cx+240+i*42, cy+130, fill="#0c2a3a")
            c.create_line(cx+i*42, cy+40, cx+i*42, cy+220, fill="#0c2a3a")
        verts, edges = self._geometry()
        projected = []
        ca, sa = math.cos(self.angle), math.sin(self.angle)
        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        for x,y,z in verts:
            x *= 1 + self.explode*.12
            y *= 1 + self.explode*.12
            z *= 1 + self.explode*.12
            xr, zr = x*ca-z*sa, x*sa+z*ca
            yr, zr2 = y*cp-zr*sp, y*sp+zr*cp
            scale = 125*self.zoom
            projected.append((cx+xr*scale, cy-yr*scale+zr2*scale*.12))
        for a,b in edges:
            x1,y1=projected[a]; x2,y2=projected[b]
            c.create_line(x1,y1,x2,y2,fill="#4ddfff",width=2)
        for x,y in projected:
            c.create_oval(x-3,y-3,x+3,y+3,fill="#a9f4ff",outline="")
        c.create_text(w-16,h-18,anchor="se",text=f"ZOOM {self.zoom:.1f}x  •  COMPONENTES {int(self.explode*100)}%",
                      fill="#4d9ab4",font=("Segoe UI",8))
