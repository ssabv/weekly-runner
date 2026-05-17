"""
WeeklyRunner - 每周定时运行工具
Python + tkinter GUI，可编译为 EXE
支持多选星期几执行
"""

import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timedelta
from pathlib import Path

# ============================================================
#  路径辅助（兼容 PyInstaller 打包）
# ============================================================
def get_base_dir():
    if getattr(sys, 'frozen', False):
        return Path(sys.executable).parent
    return Path(__file__).parent

def get_config_path():
    return get_base_dir() / "config.json"

def get_log_path():
    return get_base_dir() / "log.txt"

DAYS_CN = ["周日", "周一", "周二", "周三", "周四", "周五", "周六"]


# ============================================================
#  配置管理
# ============================================================
class Config:
    def __init__(self):
        self.ahk_path = r"C:\Users\Administrator\Desktop\自动脚本.ahk"
        self.days = [0]           # 选中的星期几列表，0=周日
        self.hour = 10
        self.minute = 0
        self.auto_start = False

    def load(self):
        try:
            p = get_config_path()
            if p.exists():
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.ahk_path = data.get("ahk_path", self.ahk_path)
                self.days = data.get("days", data.get("day_of_week", [0]))
                if isinstance(self.days, int):
                    self.days = [self.days]
                self.hour = data.get("hour", self.hour)
                self.minute = data.get("minute", self.minute)
                self.auto_start = data.get("auto_start", self.auto_start)
            else:
                self.save()
        except Exception:
            self.save()

    def save(self):
        try:
            data = {
                "ahk_path": self.ahk_path,
                "days": self.days,
                "hour": self.hour,
                "minute": self.minute,
                "auto_start": self.auto_start,
            }
            with open(get_config_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass


# ============================================================
#  定时调度器
# ============================================================
class Scheduler:
    def __init__(self, config, on_run=None, on_tick=None):
        self.config = config
        self.on_run = on_run
        self.on_tick = on_tick
        self._running = False
        self._thread = None
        self._stop_event = threading.Event()

    @property
    def running(self):
        return self._running

    def start(self):
        if self._running:
            return
        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self._stop_event.set()

    def get_next_run(self):
        """计算下一次执行时间（从今天起，遍历未来7天找最近的目标日）"""
        now = datetime.now()
        # Python weekday: Mon=0, Sun=6 → 转为 Sun=0, Mon=1 ... Sat=6
        current_day_py = (now.weekday() + 1) % 7

        best = None
        for target_day in sorted(self.config.days):
            days_until = target_day - current_day_py
            if days_until < 0:
                days_until += 7

            candidate = now.replace(
                hour=self.config.hour,
                minute=self.config.minute,
                second=0, microsecond=0
            ) + timedelta(days=days_until)

            # 如果是今天但时间已过，跳到下周
            if candidate <= now:
                candidate += timedelta(days=7)

            if best is None or candidate < best:
                best = candidate

        return best

    def _loop(self):
        while not self._stop_event.is_set():
            next_run = self.get_next_run()
            if next_run is None:
                time.sleep(1)
                continue

            if self.on_tick:
                self.on_tick(next_run)

            wait_seconds = (next_run - datetime.now()).total_seconds()
            if wait_seconds <= 0:
                time.sleep(1)
                continue

            for _ in range(int(wait_seconds)):
                if self._stop_event.is_set():
                    return
                time.sleep(1)

            if self._stop_event.is_set():
                return

            self._run_script()
            if self.on_tick:
                self.on_tick(self.get_next_run())

            for _ in range(61):
                if self._stop_event.is_set():
                    return
                time.sleep(1)

    def _run_script(self):
        path = self.config.ahk_path
        if not os.path.exists(path):
            append_log(f"[ERROR] Script not found: {path}")
            return
        try:
            os.startfile(path)
            append_log(f"[OK] {datetime.now():%Y-%m-%d %H:%M:%S} Executed: {path}")
        except Exception as e:
            append_log(f"[ERROR] {datetime.now():%Y-%m-%d %H:%M:%S} {e}")


def append_log(msg):
    try:
        with open(get_log_path(), "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


# ============================================================
#  主界面
# ============================================================
class App:
    def __init__(self):
        self.config = Config()
        self.config.load()
        self.scheduler = Scheduler(self.config, on_tick=self._on_tick)

        self.root = tk.Tk()
        self.root.title("每周定时运行工具")
        self.root.geometry("500x380")
        self.root.resizable(False, False)

        self._build_ui()

        if self.config.auto_start:
            self.root.after(500, self._auto_start)

    def _build_ui(self):
        pad = {"padx": 10, "pady": 5}

        # ---- 脚本路径 ----
        frm_path = ttk.LabelFrame(self.root, text="脚本路径", padding=8)
        frm_path.pack(fill="x", **pad)

        self.var_path = tk.StringVar(value=self.config.ahk_path)
        ttk.Entry(frm_path, textvariable=self.var_path, width=44, state="readonly").pack(side="left", padx=(0, 5))
        ttk.Button(frm_path, text="浏览...", command=self._browse).pack(side="left")

        # ---- 执行时间 ----
        frm_time = ttk.LabelFrame(self.root, text="执行时间", padding=8)
        frm_time.pack(fill="x", **pad)

        # 星期多选（Checkbutton）
        frm_days = ttk.Frame(frm_time)
        frm_days.pack(fill="x", pady=(0, 5))

        ttk.Label(frm_days, text="执行日:").pack(side="left")

        self.day_vars = []
        for i, name in enumerate(DAYS_CN):
            var = tk.BooleanVar(value=(i in self.config.days))
            self.day_vars.append(var)
            cb = ttk.Checkbutton(frm_days, text=name, variable=var, command=self._on_days_changed)
            cb.pack(side="left", padx=2)

        # 时间
        frm_clock = ttk.Frame(frm_time)
        frm_clock.pack(fill="x")

        ttk.Label(frm_clock, text="执行时间:").pack(side="left")
        self.var_hour = tk.StringVar(value=f"{self.config.hour:02d}")
        self.var_minute = tk.StringVar(value=f"{self.config.minute:02d}")
        ttk.Combobox(frm_clock, textvariable=self.var_hour,
                     values=[f"{i:02d}" for i in range(24)],
                     state="readonly", width=3).pack(side="left", padx=2)
        ttk.Label(frm_clock, text=":").pack(side="left")
        ttk.Combobox(frm_clock, textvariable=self.var_minute,
                     values=[f"{i:02d}" for i in range(60)],
                     state="readonly", width=3).pack(side="left", padx=2)

        # ---- 状态 ----
        frm_status = ttk.LabelFrame(self.root, text="状态", padding=8)
        frm_status.pack(fill="x", **pad)

        self.lbl_status = ttk.Label(frm_status, text="已停止", foreground="gray",
                                     font=("Microsoft YaHei UI", 10, "bold"))
        self.lbl_status.pack(side="left")

        self.lbl_next = ttk.Label(frm_status, text="下次执行: --")
        self.lbl_next.pack(side="right")

        # ---- 按钮 ----
        frm_btn = ttk.Frame(self.root, padding=8)
        frm_btn.pack(fill="x", **pad)

        self.btn_toggle = ttk.Button(frm_btn, text="▶ 启动", command=self._toggle)
        self.btn_toggle.pack(side="left", padx=5, ipadx=10, ipady=5)

        ttk.Button(frm_btn, text="⚡ 立即测试", command=self._test).pack(side="left", padx=5, ipadx=10, ipady=5)

        ttk.Button(frm_btn, text="隐藏到托盘", command=self._minimize).pack(side="right", padx=5)

    # ---- 浏览 ----
    def _browse(self):
        path = filedialog.askopenfilename(
            title="选择 AutoHotkey 脚本",
            filetypes=[("AHK 脚本", "*.ahk"), ("所有文件", "*.*")]
        )
        if path:
            self.var_path.set(path)
            self.config.ahk_path = path
            self.config.save()

    # ---- 星期多选变更 ----
    def _on_days_changed(self):
        self.config.days = [i for i, v in enumerate(self.day_vars) if v.get()]
        if not self.config.days:
            # 至少选一天
            self.day_vars[0].set(True)
            self.config.days = [0]
        self.config.save()

    # ---- 时间变更 ----
    def _on_setting_changed(self):
        self._on_days_changed()
        self.config.hour = int(self.var_hour.get())
        self.config.minute = int(self.var_minute.get())
        self.config.save()

    # ---- 启动/停止 ----
    def _toggle(self):
        if self.scheduler.running:
            self.scheduler.stop()
            self.config.auto_start = False
            self.config.save()
            self.btn_toggle.config(text="▶ 启动")
            self.lbl_status.config(text="已停止", foreground="gray")
            self.lbl_next.config(text="下次执行: --")
        else:
            if not os.path.exists(self.var_path.get()):
                messagebox.showerror("错误", "脚本文件不存在，请检查路径！")
                return
            self._on_setting_changed()
            if not self.config.days:
                messagebox.showwarning("提示", "请至少选择一个执行日！")
                return
            self.config.ahk_path = self.var_path.get()
            self.config.auto_start = True
            self.config.save()
            self.scheduler.start()
            self.btn_toggle.config(text="⏹ 停止")
            self.lbl_status.config(text="运行中", foreground="green")

    def _auto_start(self):
        self._toggle()

    # ---- 测试 ----
    def _test(self):
        path = self.var_path.get()
        if not os.path.exists(path):
            messagebox.showerror("错误", "脚本文件不存在！")
            return
        try:
            os.startfile(path)
            append_log(f"[TEST] {datetime.now():%Y-%m-%d %H:%M:%S} {path}")
            messagebox.showinfo("测试", "已执行脚本，请检查是否正常运行。")
        except Exception as e:
            messagebox.showerror("错误", str(e))

    # ---- 定时回调 ----
    def _on_tick(self, next_run):
        self.root.after(0, self._update_next, next_run)

    def _update_next(self, next_run):
        day_name = DAYS_CN[(next_run.weekday() + 1) % 7]
        self.lbl_next.config(text=f"下次执行: {next_run:%Y-%m-%d %H:%M} ({day_name})")

    # ---- 最小化 ----
    def _minimize(self):
        self.root.withdraw()

    def run(self):
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()

    def _on_close(self):
        if messagebox.askyesno("退出", "确定退出定时任务？\n选\"否\"将最小化到后台。"):
            self.scheduler.stop()
            self.root.destroy()
        else:
            self._minimize()


# ============================================================
#  入口
# ============================================================
if __name__ == "__main__":
    app = App()
    app.run()
