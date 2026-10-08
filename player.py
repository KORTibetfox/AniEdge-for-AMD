"""AniEdge for AMD: Real-CUGAN Pro FP16 playback on RX 9070 XT."""
from pathlib import Path
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys

ROOT = Path(__file__).resolve().parent


def command(video):
    executable = Path(sys.executable)
    console = executable.with_name("python.exe") if executable.name.lower() == "pythonw.exe" else executable
    return [str(console), str(ROOT / "hq_stream.py"), str(Path(video).resolve())]


class Player:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("AniEdge for AMD")
        self.root.geometry("750x350")
        self.root.minsize(700, 350)
        self.process = None
        self.path = tk.StringVar()
        self.status = tk.StringVar(value="영상을 선택하세요. RX 9070 XT에서 Real-CUGAN Pro FP16으로 2배 복원합니다.")
        frame = ttk.Frame(self.root, padding=24)
        frame.pack(fill="both", expand=True)
        ttk.Label(frame, text="AniEdge for AMD · 애니메이션 실시간 복원", font=("Malgun Gothic", 16, "bold")).pack(anchor="w")
        ttk.Label(frame, text="HQ — Real-CUGAN Pro FP16 · 2배 복원 · MP4 / MKV", padding=(0, 8)).pack(anchor="w")
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=12)
        ttk.Entry(row, textvariable=self.path).pack(side="left", fill="x", expand=True)
        ttk.Button(row, text="파일 선택", command=self.browse).pack(side="right", padx=(8, 0))
        ttk.Label(frame, text="720p 이하 · 순차 재생 / 권장: 480p 이하·30fps 이하\n720p에서는 영상에 따라 실시간 속도가 부족할 수 있습니다.").pack(anchor="w", pady=4)
        row = ttk.Frame(frame)
        row.pack(fill="x", pady=16)
        ttk.Button(row, text="재생", command=self.play).pack(side="left")
        ttk.Button(row, text="재생 종료", command=self.stop).pack(side="left", padx=8)
        ttk.Button(row, text="로그 폴더", command=self.logs).pack(side="right")
        ttk.Label(frame, text="Space 일시정지 · F 전체화면 · I 통계 · Q 종료\n시간 탐색은 지원하지 않습니다. 외부 SRT / ASS / SSA 자막을 연결합니다.").pack(anchor="w")
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
            self.process = subprocess.Popen(command(video),
                                            cwd=ROOT, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            self.status.set("HQ — Real-CUGAN Pro FP16으로 재생 중입니다. 시간 탐색은 지원하지 않습니다.")
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
