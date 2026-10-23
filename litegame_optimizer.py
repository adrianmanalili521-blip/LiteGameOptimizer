"""
LiteGame Optimizer — safe Windows 11 gaming helper
Designed for low-memory PCs. This tool does not disable Windows services,
edit the registry, overclock hardware, or change security settings.

Install:
    py -m pip install customtkinter psutil

Run:
    py litegame_optimizer.py
"""

import os
import re
import sys
import time
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import psutil


APP_TITLE = "LiteGame Optimizer"
REFRESH_MS = 1800

# Processes that should never be offered for closing from this app.
PROTECTED_PROCESSES = {
    "system", "system idle process", "registry", "smss.exe", "csrss.exe",
    "wininit.exe", "services.exe", "lsass.exe", "winlogon.exe",
    "svchost.exe", "fontdrvhost.exe", "dwm.exe", "explorer.exe",
    "runtimebroker.exe", "sihost.exe", "ctfmon.exe", "taskhostw.exe",
    "securityhealthservice.exe", "msmpeng.exe", "audiodg.exe",
    "litegame_optimizer.exe", "python.exe", "pythonw.exe",
}

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def run_powercfg(args):
    """Run powercfg and return (return_code, stdout, stderr)."""
    try:
        result = subprocess.run(
            ["powercfg", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as exc:
        return 1, "", str(exc)


def get_active_power_plan():
    rc, out, err = run_powercfg(["/getactivescheme"])
    if rc != 0:
        return None
    match = re.search(r"([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12})", out)
    return match.group(1) if match else None


def find_performance_plan():
    """Return a supported High performance plan GUID if listed by Windows."""
    rc, out, _ = run_powercfg(["/list"])
    if rc != 0:
        return None
    plans = []
    for line in out.splitlines():
        match = re.search(
            r"([0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}).*?\((.*?)\)",
            line,
        )
        if match:
            plans.append((match.group(1), match.group(2).strip().lower()))
    for guid, name in plans:
        if "high performance" in name:
            return guid
    for guid, name in plans:
        if "ultimate performance" in name:
            return guid
    # SCHEME_MIN is Windows' alias for High performance; use only as fallback.
    return "SCHEME_MIN"


class LiteGameOptimizer(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x720")
        self.minsize(850, 620)

        self.game_path = tk.StringVar(value="")
        self.status_text = tk.StringVar(value="Ready. Select a game to get started.")
        self.cpu_text = tk.StringVar(value="CPU: reading…")
        self.ram_text = tk.StringVar(value="RAM: reading…")
        self.disk_text = tk.StringVar(value="Disk: reading…")
        self.power_text = tk.StringVar(value="Power plan: checking…")
        self.previous_power_plan = None
        self.process_map = {}
        self._closing = False

        psutil.cpu_percent(interval=None)
        self._build_ui()
        self.refresh_processes()
        self.update_stats()
        self.update_power_status()
        self.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, width=220, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(
            sidebar, text="LITEGAME", font=ctk.CTkFont(size=25, weight="bold")
        ).grid(row=0, column=0, padx=20, pady=(28, 2), sticky="w")
        ctk.CTkLabel(
            sidebar, text="OPTIMIZER  •  WINDOWS 11",
            font=ctk.CTkFont(size=10), text_color="#8FA3B8"
        ).grid(row=1, column=0, padx=21, pady=(0, 28), sticky="w")

        self._side_button(sidebar, "Dashboard", lambda: self.set_status("Dashboard is active."), 2)
        self._side_button(sidebar, "Refresh processes", self.refresh_processes, 3)
        self._side_button(sidebar, "Gaming mode", self.enable_gaming_mode, 4)
        self._side_button(sidebar, "Restore power plan", self.restore_power_plan, 5)

        ctk.CTkLabel(
            sidebar,
            text="SAFE MODE\nNo registry tweaks\nNo service disabling\nNo overclocking",
            justify="left", text_color="#9CAFC1",
            font=ctk.CTkFont(size=12)
        ).grid(row=9, column=0, padx=20, pady=20, sticky="sw")

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.grid(row=0, column=1, sticky="nsew", padx=22, pady=20)
        main.grid_columnconfigure((0, 1), weight=1)
        main.grid_rowconfigure(3, weight=1)

        ctk.CTkLabel(
            main, text="Gaming dashboard",
            font=ctk.CTkFont(size=28, weight="bold")
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        ctk.CTkLabel(
            main, text="Lightweight controls for a 4 GB RAM laptop",
            text_color="#9CAFC1", font=ctk.CTkFont(size=13)
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 18))

        metrics = ctk.CTkFrame(main, fg_color="transparent")
        metrics.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        metrics.grid_columnconfigure((0, 1, 2), weight=1)

        self.cpu_card, self.cpu_bar = self._metric_card(metrics, 0, "CPU USAGE", self.cpu_text)
        self.ram_card, self.ram_bar = self._metric_card(metrics, 1, "MEMORY USAGE", self.ram_text)
        self.disk_card, self.disk_bar = self._metric_card(metrics, 2, "SYSTEM DRIVE", self.disk_text)

        game_frame = ctk.CTkFrame(main)
        game_frame.grid(row=3, column=0, sticky="nsew", padx=(0, 8), pady=(0, 10))
        game_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(game_frame, text="Game launcher",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=16, pady=(16, 8)
        )
        ctk.CTkLabel(game_frame, text="Choose the game's .exe file.",
                     text_color="#9CAFC1").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=16, pady=(0, 10)
        )
        self.game_entry = ctk.CTkEntry(game_frame, textvariable=self.game_path,
                                       placeholder_text=r"C:\Games\YourGame\game.exe")
        self.game_entry.grid(row=2, column=0, sticky="ew", padx=(16, 8), pady=5)
        ctk.CTkButton(game_frame, text="Browse", width=90,
                      command=self.browse_game).grid(row=2, column=1, padx=(0, 16), pady=5)
        ctk.CTkButton(game_frame, text="Optimize & Launch",
                      command=self.optimize_and_launch, height=40).grid(
            row=3, column=0, columnspan=2, sticky="ew", padx=16, pady=(10, 8)
        )
        ctk.CTkButton(game_frame, text="Launch only",
                      fg_color="#34495E", hover_color="#405B73",
                      command=self.launch_game).grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 16)
        )

        proc_frame = ctk.CTkFrame(main)
        proc_frame.grid(row=3, column=1, sticky="nsew", padx=(8, 0), pady=(0, 10))
        proc_frame.grid_columnconfigure(0, weight=1)
        proc_frame.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(proc_frame, text="Optional app cleanup",
                     font=ctk.CTkFont(size=18, weight="bold")).grid(
            row=0, column=0, sticky="w", padx=16, pady=(16, 4)
        )
        ctk.CTkLabel(
            proc_frame, text="Select only apps you recognize. Save your work first.",
            text_color="#9CAFC1", wraplength=320, justify="left"
        ).grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))
        self.process_list = tk.Listbox(
            proc_frame, selectmode=tk.EXTENDED, bg="#202A35", fg="#E7EDF4",
            selectbackground="#2369A8", relief="flat", borderwidth=0,
            highlightthickness=0, font=("Consolas", 9), activestyle="none"
        )
        self.process_list.grid(row=2, column=0, sticky="nsew", padx=16, pady=(0, 10))
        ctk.CTkButton(proc_frame, text="Close selected apps",
                      fg_color="#9B4D38", hover_color="#B45D45",
                      command=self.close_selected_processes).grid(
            row=3, column=0, sticky="ew", padx=16, pady=(0, 16)
        )

        footer = ctk.CTkFrame(main)
        footer.grid(row=4, column=0, columnspan=2, sticky="ew", pady=(0, 4))
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(footer, textvariable=self.power_text,
                     text_color="#9CAFC1").grid(row=0, column=0, sticky="w", padx=14, pady=(10, 2))
        ctk.CTkLabel(footer, textvariable=self.status_text,
                     wraplength=650, justify="left").grid(
            row=1, column=0, sticky="w", padx=14, pady=(2, 10)
        )

        ctk.CTkLabel(
            main,
            text="Tip: plug in your charger, close browser tabs, and lower in-game resolution/render scale.",
            text_color="#9CAFC1", wraplength=700, justify="left"
        ).grid(row=5, column=0, columnspan=2, sticky="w", pady=(5, 0))

    def _side_button(self, parent, label, command, row):
        ctk.CTkButton(
            parent, text=label, command=command, anchor="w",
            fg_color="transparent", hover_color="#263747", height=38
        ).grid(row=row, column=0, sticky="ew", padx=12, pady=3)

    def _metric_card(self, parent, col, title, variable):
        card = ctk.CTkFrame(parent)
        card.grid(row=0, column=col, sticky="ew", padx=5)
        ctk.CTkLabel(card, text=title, text_color="#9CAFC1",
                     font=ctk.CTkFont(size=10, weight="bold")).pack(
            anchor="w", padx=12, pady=(12, 4)
        )
        ctk.CTkLabel(card, textvariable=variable,
                     font=ctk.CTkFont(size=20, weight="bold")).pack(
            anchor="w", padx=12, pady=(0, 8)
        )
        bar = ctk.CTkProgressBar(card, height=8)
        bar.pack(fill="x", padx=12, pady=(0, 12))
        bar.set(0)
        return card, bar

    def set_status(self, text):
        self.status_text.set(text)

    def update_stats(self):
        if self._closing:
            return
        try:
            cpu = psutil.cpu_percent(interval=None)
            mem = psutil.virtual_memory()
            try:
                disk = psutil.disk_usage(os.environ.get("SystemDrive", "C:") + "\\")
                disk_percent = disk.percent
                disk_label = f"Disk: {disk_percent:.0f}% used"
            except Exception:
                disk_percent = 0
                disk_label = "Disk: unavailable"

            self.cpu_text.set(f"CPU: {cpu:.0f}%")
            self.ram_text.set(f"RAM: {mem.percent:.0f}%")
            self.disk_text.set(disk_label)
            self.cpu_bar.set(max(0.0, min(1.0, cpu / 100)))
            self.ram_bar.set(max(0.0, min(1.0, mem.percent / 100)))
            self.disk_bar.set(max(0.0, min(1.0, disk_percent / 100)))
        except Exception:
            pass
        self.after(REFRESH_MS, self.update_stats)

    def update_power_status(self):
        active = get_active_power_plan()
        if active:
            self.power_text.set(f"Active power plan GUID: {active}")
        else:
            self.power_text.set("Power plan: unable to read")
        self.after(10000, self.update_power_status)

    def refresh_processes(self):
        self.process_list.delete(0, tk.END)
        self.process_map.clear()
        rows = []
        for proc in psutil.process_iter(["pid", "name", "memory_info"]):
            try:
                pid = proc.info["pid"]
                name = (proc.info.get("name") or "Unknown").strip()
                lower = name.lower()
                if pid == os.getpid() or lower in PROTECTED_PROCESSES:
                    continue
                # Keep the list useful: omit tiny Windows host processes where possible.
                if lower in {"conhost.exe", "dllhost.exe", "taskhost.exe"}:
                    continue
                mem_mb = 0.0
                info = proc.info.get("memory_info")
                if info:
                    mem_mb = info.rss / (1024 * 1024)
                rows.append((mem_mb, pid, name))
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        rows.sort(reverse=True)
        for mem_mb, pid, name in rows[:70]:
            label = f"{name[:27]:27}  PID {pid:<6}  {mem_mb:>5.0f} MB"
            self.process_list.insert(tk.END, label)
            self.process_map[self.process_list.size() - 1] = (pid, name)
        self.set_status(f"Process list refreshed: showing {min(len(rows), 70)} processes.")

    def close_selected_processes(self):
        selected = self.process_list.curselection()
        if not selected:
            messagebox.showinfo("Select apps", "Select one or more processes in the list first.")
            return
        targets = [self.process_map[i] for i in selected if i in self.process_map]
        names = "\n".join(f"• {name} (PID {pid})" for pid, name in targets)
        if not messagebox.askyesno(
            "Confirm closing apps",
            "This sends a termination request to the selected processes.\n"
            "Unsaved work may be lost. Do not close apps you do not recognize.\n\n"
            + names,
        ):
            return

        closed, skipped = 0, []
        for pid, name in targets:
            if name.lower() in PROTECTED_PROCESSES:
                skipped.append(name)
                continue
            try:
                proc = psutil.Process(pid)
                # Re-check PID/name immediately before termination.
                if proc.name().lower() in PROTECTED_PROCESSES:
                    skipped.append(name)
                    continue
                proc.terminate()
                try:
                    proc.wait(timeout=2)
                except psutil.TimeoutExpired:
                    # Do not force-kill; leave it alone if it does not exit.
                    skipped.append(name + " (did not close)")
                    continue
                closed += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                skipped.append(name + " (permission/process changed)")
        self.refresh_processes()
        message = f"Closed {closed} process(es)."
        if skipped:
            message += "\nSkipped: " + ", ".join(skipped[:8])
        self.set_status(message)
        messagebox.showinfo("Cleanup result", message)

    def enable_gaming_mode(self):
        if self.previous_power_plan is None:
            self.previous_power_plan = get_active_power_plan()
        plan = find_performance_plan()
        if not plan:
            self.set_status("Could not find a performance power plan.")
            messagebox.showwarning(
                "Power plan unavailable",
                "Windows did not report a usable power plan. No change was made."
            )
            return
        rc, out, err = run_powercfg(["/setactive", plan])
        if rc == 0:
            self.set_status(
                "Gaming mode enabled: requested a performance power plan. "
                "Close only apps you do not need; no system services were disabled."
            )
            self.update_power_status()
        else:
            self.set_status("Windows did not allow the power plan change.")
            messagebox.showwarning(
                "Could not change power plan",
                "Windows rejected the request. Try running normally first; "
                "if your laptop vendor manages power modes, use its official utility.\n\n"
                + (err or out)
            )

    def restore_power_plan(self):
        if not self.previous_power_plan:
            self.set_status("No saved power plan in this session to restore.")
            messagebox.showinfo(
                "Nothing to restore",
                "Enable Gaming Mode first in this session to save the current power plan."
            )
            return
        rc, out, err = run_powercfg(["/setactive", self.previous_power_plan])
        if rc == 0:
            self.set_status("Restored the power plan that was active before Gaming Mode.")
            self.previous_power_plan = None
            self.update_power_status()
        else:
            self.set_status("Could not restore the saved power plan.")
            messagebox.showwarning("Restore failed", err or out or "Windows rejected the request.")

    def browse_game(self):
        path = filedialog.askopenfilename(
            title="Select a game executable",
            filetypes=[("Windows applications", "*.exe"), ("All files", "*.*")]
        )
        if path:
            self.game_path.set(path)

    def launch_game(self):
        path = self.game_path.get().strip().strip('"')
        if not path:
            messagebox.showinfo("Choose a game", "Browse to the game's .exe file first.")
            return
        if not os.path.isfile(path):
            messagebox.showerror("File not found", "That executable path does not exist.")
            return
        try:
            # Use the executable's own directory as the working directory.
            subprocess.Popen([path], cwd=os.path.dirname(path) or None)
            self.set_status(f"Launched: {os.path.basename(path)}")
        except Exception as exc:
            messagebox.showerror("Launch failed", str(exc))
            self.set_status("Could not launch the selected game.")

    def optimize_and_launch(self):
        self.enable_gaming_mode()
        # If the power change succeeded or Windows does not support the plan,
        # launching is still the user's choice. Don't launch if the path is invalid.
        path = self.game_path.get().strip().strip('"')
        if not path or not os.path.isfile(path):
            messagebox.showinfo(
                "Choose a game",
                "Select a valid game's .exe file first. Gaming Mode can remain enabled."
            )
            return
        self.launch_game()

    def on_close(self):
        if messagebox.askyesno(
            "Exit LiteGame Optimizer",
            "Exit the optimizer? If you changed the power plan, restore it first if desired."
        ):
            self._closing = True
            self.destroy()


def main():
    if sys.platform != "win32":
        print("LiteGame Optimizer is designed for Windows 10/11.")
        raise SystemExit(1)
    app = LiteGameOptimizer()
    app.mainloop()


if __name__ == "__main__":
    main()
