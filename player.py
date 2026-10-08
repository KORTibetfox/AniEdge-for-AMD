"""AniEdge for AMD: local anime restoration player for RX 9070 XT."""
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import time
import sys

ROOT = Path(__file__).resolve().parent


def command(video, mode="light", automatic=False, deinterlace=False):
    return [str(ROOT / "vendor/mpv/mpv.exe"), "--no-config", "--vo=gpu-next",
            "--gpu-api=vulkan", "--vulkan-device=AMD Radeon RX 9070 XT",
            "--hwdec=auto-safe", "--sub-auto=fuzzy", "--osd-level=1",
            "--keep-open=yes", "--save-position-on-quit=no",
            f"--deinterlace={'yes' if deinterlace else 'no'}",
            f"--script={ROOT / 'restore'}",
            f"--script-opts=restore-mode={mode},restore-auto={'yes' if automatic else 'no'}",
            f"--log-file={ROOT / 'logs' / ('playback-' + str(time.time_ns()) + '.log')}",
            "--", str(Path(video).resolve())]


class Player:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AniEdge for AMD")
        self.root.geometry("750x550")
        self.root.minsize(700, 530)
        self.process = None
        self.path = tk.StringVar()
        self.mode = tk.StringVar(value="adaptive")
        self.auto = tk.BooleanVar(value=False)
        self.interlaced = tk.BooleanVar(value=False)
        self.status = tk.StringVar(value="영상을 선택하세요. RX 9070 XT Vulkan 장치를 사용합니다.")
        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AniEdge for AMD · 애니메이션 실시간 복원", font=("Malgun Gothic", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="MP4 · MKV / Real-CUGAN Pro · ArtCNN · Anime4K / 별도 재생 창", padding=(0, 8)).pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=12)
        ttk.Entry(row, textvariable=self.path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="파일 선택", command=self.browse).pack(side="right", padx=(8, 0))
        for value, text in [("adaptive", "자동 — 저해상도 Real-CUGAN FP16 / 고해상도·고FPS ArtCNN"),
                            ("off", "원본 — AI 복원 끄기"),
                            ("light", "가벼운 복원 — 노이즈 제거 + CNN 2배 확대"),
                            ("strong", "강한 복원 — 선 복원 + 노이즈 제거 + CNN 2배 확대"),
                            ("hq", "HQ — Real-CUGAN Pro FP16 2배 (720p 이하 · 순차 재생)"),
                            ("hd", "HD — ArtCNN C4F32 (해상도 유지·확대 · 탐색 가능)")]:
            ttk.Radiobutton(frame, text=text, value=value, variable=self.mode).pack(anchor="w", pady=4)
        ttk.Checkbutton(frame, text="Anime4K에서 드롭이 계속되면 복원 강도를 낮추기", variable=self.auto).pack(anchor="w", pady=(10, 3))
        ttk.Checkbutton(frame, text="인터레이스 영상 처리 (빗살 무늬가 있는 소스만)", variable=self.interlaced).pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=16)
        ttk.Button(row, text="재생", command=self.play).pack(side="left")
        ttk.Button(row, text="재생 종료", command=self.stop).pack(side="left", padx=8)
        ttk.Button(row, text="로그 폴더", command=self.logs).pack(side="right")
        ttk.Label(frame, text="Space 일시정지 · F 전체화면 · I 통계 · Q 종료\n←/→ 탐색: HD·Anime4K / 1~4 복원 전환: Anime4K만 지원").pack(anchor="w")
        ttk.Label(frame, textvariable=self.status, wraplength=650).pack(anchor="w", pady=10)
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(500, self.poll)

    def browse(self):
        path = filedialog.askopenfilename(filetypes=[("영상", "*.mp4 *.mkv"), ("모든 파일", "*.*")])
        if path:
            self.path.set(path)

    def play(self):
        video = Path(self.path.get())
        if not video.is_file() or video.suffix.lower() not in (".mp4", ".mkv"):
            messagebox.showerror("파일 확인", "존재하는 MP4 또는 MKV 파일을 선택하세요.")
            return
        if not (ROOT / "vendor/mpv/mpv.exe").is_file():
            messagebox.showerror("재생 엔진", "vendor/mpv/mpv.exe 파일이 없습니다.")
            return
        self.stop()
        (ROOT / "logs").mkdir(exist_ok=True)
        try:
            if self.mode.get() in ("hq", "adaptive", "hd"):
                if self.interlaced.get() and self.mode.get() == "hq":
                    messagebox.showerror("HQ 범위", "첫 HQ 모드는 인터레이스 처리를 지원하지 않습니다.")
                    return
                executable = Path(sys.executable)
                console = executable.with_name("python.exe") if executable.name.lower() == "pythonw.exe" else executable
                profile = {"hq": "pro-fast", "adaptive": "auto", "hd": "hd"}[self.mode.get()]
                args = [str(console), str(ROOT / "hq_stream.py"), str(video.resolve()), "--profile", profile]
                if self.interlaced.get():
                    args.append("--deinterlace")
            else:
                args = command(video, self.mode.get(), self.auto.get(), self.interlaced.get())
            self.process = subprocess.Popen(args,
                                            cwd=ROOT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.status.set("자동 모드: 640×480 상당 이하·30fps 이하에서는 HQ, 그 외에는 HD를 선택합니다." if self.mode.get() == "adaptive"
                            else "HD: ArtCNN을 GPU에서 처리합니다. 시간 탐색이 가능합니다." if self.mode.get() == "hd"
                            else "HQ는 순차 재생만 지원합니다. 탐색·1~4 복원 전환은 지원하지 않습니다." if self.mode.get() == "hq"
                            else "재생 창에서 1·2·3으로 복원 강도를 즉시 비교할 수 있습니다.")
        except OSError as error:
            messagebox.showerror("실행 실패", str(error))

    def stop(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.process = None

    def logs(self):
        folder = ROOT / "logs"
        folder.mkdir(exist_ok=True)
        os.startfile(folder)

    def poll(self):
        if self.process and self.process.poll() is not None:
            code = self.process.returncode
            self.status.set("재생 종료" if code == 0 else f"재생 실패 (코드 {code}). 로그 폴더를 확인하세요.")
            self.process = None
        self.root.after(500, self.poll)

    def close(self):
        self.stop()
        self.root.destroy()


if __name__ == "__main__":
    Player().root.mainloop()
