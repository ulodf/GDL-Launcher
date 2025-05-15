#!/usr/bin/env python3
"""
Gallery-DL Launcher - A GUI for managing gallery-dl downloads
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinter.constants import *
import subprocess
import threading
import queue
import shlex
import os
import sys
import re
import json
import time
import sqlite3
import platform
import urllib.parse
import http.server
import socketserver
import webbrowser
import csv
from pathlib import Path
from datetime import datetime

# ──────────────────────────────────────────────────────────────────────────────
# Persistence paths and constants
# ──────────────────────────────────────────────────────────────────────────────
CONFIG_FILE = Path.home() / '.gallery_dl_launcher.cfg'
DATA_DIR = Path.home() / '.gallery_dl_launcher'
DATA_DIR.mkdir(exist_ok=True)

TIMESTAMP_FMT = '%Y-%m-%d %H%M%S'

# ──────────────────────────────────────────────────────────────────────────────
# Default configuration with correct option format
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = """# Gallery-dl global options - edit as needed
--cookies cookies.txt
-o filename={date%Y-%m-%d}_{user}_{title}_{id} {num02}.{extension}
# --download-archive global-archive.txt  # Uncomment to use a global archive"""

# ──────────────────────────────────────────────────────────────────────────────
# Config tab – global gallery‑dl CLI options
# ──────────────────────────────────────────────────────────────────────────────
class ConfigFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook):
        super().__init__(master)
        ttk.Label(self, text="Global gallery-dl options (one per line)").pack(anchor=W, padx=6, pady=(6, 0))

        # Create frame for the textbox with a scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=BOTH, expand=True, padx=6, pady=(0, 6))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Create and configure the text box
        self.box = tk.Text(text_frame, width=90, height=6, yscrollcommand=scrollbar.set)
        self.box.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.box.yview)

        # Add a status bar for feedback
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, anchor=W)
        self.status_bar.pack(fill=X, padx=6, pady=(0, 6))

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, padx=6, pady=(0, 6))

        ttk.Button(btn_frame, text="Save", command=self.save).pack(side=LEFT, padx=(0, 5))
        ttk.Button(btn_frame, text="Reset to Default", command=self.reset_to_default).pack(side=LEFT)

        # Load config
        self.load_config()

    def load_config(self):
        """Load configuration from file"""
        if CONFIG_FILE.exists():
            self.box.delete('1.0', 'end')
            self.box.insert('1.0', CONFIG_FILE.read_text())
        else:
            self.reset_to_default()

    def reset_to_default(self):
        """Reset configuration to default values"""
        self.box.delete('1.0', 'end')
        self.box.insert('1.0', DEFAULT_CONFIG)
        self.status_var.set("Reset to default configuration")

    def get_tokens(self) -> list[str]:
        """Parse configuration to get command line tokens"""
        tokens: list[str] = []
        for line in self.box.get('1.0', 'end').strip().splitlines():
            line = line.strip()
            if line and not line.startswith('#'):
                tokens.extend(shlex.split(line))
        return tokens

    def save(self):
        """Save configuration to file"""
        try:
            CONFIG_FILE.write_text(self.box.get('1.0', 'end').rstrip() + '\n')
            self.status_var.set(f"Configuration saved to {CONFIG_FILE}")
        except OSError as e:
            self.status_var.set(f"Error: Could not write to {CONFIG_FILE}")
            messagebox.showwarning("Save failed", f"Could not write {CONFIG_FILE}: {e}")

# ──────────────────────────────────────────────────────────────────────────────
# Unified log tab – aggregated stdout/stderr
# ──────────────────────────────────────────────────────────────────────────────
class UnifiedLogFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook):
        super().__init__(master)
        ttk.Label(self, text="Unified live log - all instances").pack(anchor=W, padx=6, pady=(6, 0))

        # Create frame for the textbox with a scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=BOTH, expand=True, padx=6, pady=(0, 6))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=RIGHT, fill=Y)

        # Create and configure the text box
        self.box = tk.Text(text_frame, height=20, wrap=WORD, yscrollcommand=scrollbar.set)
        self.box.pack(side=LEFT, fill=BOTH, expand=True)
        scrollbar.config(command=self.box.yview)

        # Configure tags for coloring
        self.box.tag_configure('error', foreground='red')
        self.box.tag_configure('info', foreground='blue')
        self.box.tag_configure('success', foreground='green')

        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, padx=6, pady=(0, 6))

        # Clear log button
        ttk.Button(btn_frame, text="Clear Log", command=self.clear_log).pack(side=LEFT, padx=(0, 5))

        # Save log button
        ttk.Button(btn_frame, text="Save Log", command=self.save_log).pack(side=LEFT)

    def clear_log(self):
        """Clear the log text box"""
        self.box.delete('1.0', 'end')

    def save_log(self):
        """Save log contents to a file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Save Log"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.box.get('1.0', 'end'))
                messagebox.showinfo("Save Successful", f"Log saved to {filename}")
            except Exception as e:
                messagebox.showerror("Save Failed", f"Error saving log: {str(e)}")

    def add_log(self, text, instance_idx=None, level="info"):
        """Add text to the log with timestamp and optional instance indicator"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        instance_text = f"[{instance_idx}] " if instance_idx is not None else ""
        log_text = f"[{timestamp}] {instance_text}{text}\n"
        
        tags = (level,) if level in ("error", "info", "success") else ()
        
        self.box.insert('end', log_text, tags)
        self.box.see('end')  # Scroll to the end

# ──────────────────────────────────────────────────────────────────────────────
# Instance tab – one gallery‑dl process
# ──────────────────────────────────────────────────────────────────────────────
class InstanceFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook, idx: int, get_global_opts, log_callback):
        super().__init__(master)
        self.idx = idx
        self.get_global_opts = get_global_opts
        self.log_callback = log_callback
        self.proc: subprocess.Popen = None
        
        # Instance settings
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Downloads"))
        self.temp_dir_var = tk.StringVar(value=str(Path.home() / "Downloads" / "temp"))
        self.archive_file_var = tk.StringVar(value=str(DATA_DIR / "archives" / f"instance_{self.idx}_archive.txt"))
        self.extra_opts_var = tk.StringVar()
        
        # Content type filters
        self.download_images_var = tk.BooleanVar(value=True)
        self.download_videos_var = tk.BooleanVar(value=True)
        
        # Create UI
        self._create_ui()
        
        # Load settings
        self._load_settings()
        
    def _create_ui(self):
        """Create the UI elements for this instance"""
        # Main controls frame
        controls_frame = ttk.LabelFrame(self, text=f"Instance {self.idx+1} Controls")
        controls_frame.pack(fill=X, padx=6, pady=6)
        
        # Output directory selector
        output_dir_frame = ttk.Frame(controls_frame)
        output_dir_frame.pack(fill=X, padx=6, pady=6)
        
        ttk.Label(output_dir_frame, text="Output Directory:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(output_dir_frame, text="Browse", command=self._browse_output_dir).pack(side=LEFT)
        
        # Extra options
        extra_opts_frame = ttk.Frame(controls_frame)
        extra_opts_frame.pack(fill=X, padx=6, pady=6)
        
        ttk.Label(extra_opts_frame, text="Extra Options:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(extra_opts_frame, textvariable=self.extra_opts_var, width=50).pack(side=LEFT, fill=X, expand=True)
        
        # URL list
        url_frame = ttk.LabelFrame(self, text="URLs to Download")
        url_frame.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        # URL textbox with scrollbar
        url_text_frame = ttk.Frame(url_frame)
        url_text_frame.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        url_scrollbar = ttk.Scrollbar(url_text_frame)
        url_scrollbar.pack(side=RIGHT, fill=Y)
        
        self.links_box = tk.Text(url_text_frame, height=10, yscrollcommand=url_scrollbar.set)
        self.links_box.pack(side=LEFT, fill=BOTH, expand=True)
        url_scrollbar.config(command=self.links_box.yview)
        
        # Button frame
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=X, padx=6, pady=6)
        
        # Start button
        self.start_btn = ttk.Button(btn_frame, text="Start Download", command=self.start)
        self.start_btn.pack(side=LEFT, padx=(0, 5))
        
        # Stop button
        self.stop_btn = ttk.Button(btn_frame, text="Stop", command=self.stop, state=DISABLED)
        self.stop_btn.pack(side=LEFT, padx=(0, 5))
        
        # Status frame
        status_frame = ttk.LabelFrame(self, text="Status")
        status_frame.pack(fill=X, padx=6, pady=6)
        
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.StringVar(value="")
        
        ttk.Label(status_frame, textvariable=self.status_var, width=30).pack(side=LEFT, padx=6, pady=6)
        ttk.Label(status_frame, textvariable=self.progress_var, width=30).pack(side=LEFT, padx=6, pady=6)
    
    def _browse_output_dir(self):
        """Open directory browser to select output directory"""
        directory = filedialog.askdirectory(
            initialdir=self.output_dir_var.get(),
            title="Select Output Directory"
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def _save_settings(self):
        """Save instance settings to a JSON file"""
        settings = {
            "output_dir": self.output_dir_var.get(),
            "extra_opts": self.extra_opts_var.get()
        }
        
        settings_dir = DATA_DIR / "instances"
        settings_dir.mkdir(exist_ok=True)
        
        settings_file = settings_dir / f"instance_{self.idx}.json"
        
        try:
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def _load_settings(self):
        """Load instance settings from a JSON file"""
        settings_file = DATA_DIR / "instances" / f"instance_{self.idx}.json"
        
        if settings_file.exists():
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                
                self.output_dir_var.set(settings.get("output_dir", str(Path.home() / "Downloads")))
                self.extra_opts_var.set(settings.get("extra_opts", ""))
            except Exception as e:
                print(f"Error loading settings: {e}")
    
    def _save_links(self):
        """Save links to a text file"""
        links_dir = DATA_DIR / "links"
        links_dir.mkdir(exist_ok=True)
        
        links_file = links_dir / f"instance_{self.idx}_links.txt"
        
        try:
            with open(links_file, 'w', encoding='utf-8') as f:
                f.write(self.links_box.get('1.0', 'end'))
        except Exception as e:
            print(f"Error saving links: {e}")
    
    def _load_links(self):
        """Load links from a text file"""
        links_file = DATA_DIR / "links" / f"instance_{self.idx}_links.txt"
        
        if links_file.exists():
            try:
                with open(links_file, 'r', encoding='utf-8') as f:
                    self.links_box.delete('1.0', 'end')
                    self.links_box.insert('1.0', f.read())
            except Exception as e:
                print(f"Error loading links: {e}")
    
    def is_running(self):
        """Check if the gallery-dl process is running"""
        return self.proc is not None and self.proc.poll() is None
    
    def start(self):
        """Start the gallery-dl process"""
        if self.is_running():
            return
        
        # Get URLs from the text box
        links = self.links_box.get('1.0', 'end').strip().splitlines()
        links = [link.strip() for link in links if link.strip()]
        
        if not links:
            messagebox.showinfo("No URLs", "Please enter URLs to download")
            return
        
        # Save settings and links
        self._save_settings()
        self._save_links()
        
        # Build command
        cmd = ["gallery-dl"]
        
        # Add global options
        cmd.extend(self.get_global_opts())
        
        # Add instance-specific options
        output_dir = self.output_dir_var.get()
        if output_dir:
            cmd.extend(["-d", output_dir])
        
        extra_opts = self.extra_opts_var.get().strip()
        if extra_opts:
            cmd.extend(shlex.split(extra_opts))
        
        # Add URLs
        cmd.extend(links)
        
        # Update UI
        self.start_btn.config(state=DISABLED)
        self.stop_btn.config(state=NORMAL)
        self.status_var.set("Running...")
        self.progress_var.set("")
        
        # Log the command
        cmd_str = " ".join(cmd)
        self.log_callback(f"Starting gallery-dl: {cmd_str}", self.idx)
        
        # Start the process
        try:
            self.proc = subprocess.Popen(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            # Start a thread to read output
            threading.Thread(target=self._read_output, daemon=True).start()
            
        except Exception as e:
            self.status_var.set("Error")
            self.start_btn.config(state=NORMAL)
            self.stop_btn.config(state=DISABLED)
            self.log_callback(f"Error starting gallery-dl: {str(e)}", self.idx, "error")
    
    def stop(self):
        """Stop the gallery-dl process"""
        if not self.is_running():
            return
        
        try:
            self.proc.terminate()
            self.log_callback("Stopping gallery-dl...", self.idx)
            
            # Wait for process to terminate
            def check_terminated():
                if self.proc and self.proc.poll() is None:
                    # Still running, try again in 100ms
                    self.after(100, check_terminated)
                else:
                    # Process terminated
                    self.start_btn.config(state=NORMAL)
                    self.stop_btn.config(state=DISABLED)
                    self.status_var.set("Stopped")
                    self.log_callback("gallery-dl process stopped", self.idx)
            
            check_terminated()
            
        except Exception as e:
            self.log_callback(f"Error stopping gallery-dl: {str(e)}", self.idx, "error")
    
    def _read_output(self):
        """Read output from the gallery-dl process"""
        for line in iter(self.proc.stdout.readline, ""):
            if line:
                line = line.strip()
                self.log_callback(line, self.idx)
                self._parse_download_info(line)
        
        # Process completed
        self.start_btn.config(state=NORMAL)
        self.stop_btn.config(state=DISABLED)
        
        if self.proc.poll() == 0:
            self.status_var.set("Completed")
            self.log_callback("Download completed successfully", self.idx, "success")
        else:
            self.status_var.set(f"Error (code {self.proc.poll()})")
            self.log_callback(f"Download failed with code {self.proc.poll()}", self.idx, "error")
        
        self.proc = None
    
    def _parse_download_info(self, line: str):
        """Parse download information from gallery-dl output"""
        try:
            # Try to extract progress information
            if "[download]" in line:
                match = re.search(r"\[download\].+?(\d+\.\d+)%", line)
                if match:
                    progress = match.group(1)
                    self.progress_var.set(f"{progress}% complete")
                    return
                
                match = re.search(r"\[download\].+?(\d+\.\d+)([KMG]iB)/s", line)
                if match:
                    speed = f"{match.group(1)} {match.group(2)}/s"
                    self.progress_var.set(f"Speed: {speed}")
                    return
        except Exception:
            pass  # Ignore parsing errors

# ──────────────────────────────────────────────────────────────────────────────
# Main application
# ──────────────────────────────────────────────────────────────────────────────
class Application(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gallery-DL Launcher")
        self.geometry("900x700")
        
        # Create the main notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        # Create config tab
        self.config_frame = ConfigFrame(self.notebook)
        self.notebook.add(self.config_frame, text="Global Config")
        
        # Create unified log tab
        self.log_frame = UnifiedLogFrame(self.notebook)
        self.notebook.add(self.log_frame, text="Unified Log")
        
        # Create instance tabs (default to 3)
        self.instances = []
        for i in range(3):
            self._create_instance(i)
        
        # Create menu
        self._create_menu()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        # Set up clean exit
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _create_menu(self):
        """Create the application menu"""
        menu_bar = tk.Menu(self)
        
        # File menu
        file_menu = tk.Menu(menu_bar, tearoff=0)
        file_menu.add_command(label="Save All", command=self.save_all)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menu_bar.add_cascade(label="File", menu=file_menu)
        
        # Instance menu
        instance_menu = tk.Menu(menu_bar, tearoff=0)
        instance_menu.add_command(label="Add Instance", command=self.add_instance)
        menu_bar.add_cascade(label="Instances", menu=instance_menu)
        
        # Help menu
        help_menu = tk.Menu(menu_bar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menu_bar.add_cascade(label="Help", menu=help_menu)
        
        self.config(menu=menu_bar)
    
    def _create_instance(self, idx):
        """Create a new instance tab"""
        instance = InstanceFrame(
            self.notebook, 
            idx, 
            self.config_frame.get_tokens,
            lambda text, inst_idx=idx, level="info": self.log_frame.add_log(text, inst_idx, level)
        )
        self.notebook.add(instance, text=f"Instance {idx+1}")
        self.instances.append(instance)
    
    def add_instance(self):
        """Add a new instance tab"""
        new_idx = len(self.instances)
        self._create_instance(new_idx)
        self.notebook.select(new_idx + 2)  # +2 for config and log tabs
        self.status_var.set(f"Added instance {new_idx+1}")
    
    def save_all(self):
        """Save all configuration and instance data"""
        # Save global config
        self.config_frame.save()
        
        # Save instance settings
        for instance in self.instances:
            instance._save_settings()
            instance._save_links()
        
        self.status_var.set("All settings saved")
    
    def on_closing(self):
        """Handle application closing"""
        # Check if any instances are running
        running_instances = [i for i, inst in enumerate(self.instances, 1) if inst.is_running()]
        
        if running_instances:
            if messagebox.askyesno("Confirm Exit", 
                                  f"Instances {', '.join(map(str, running_instances))} are still running. "
                                  f"Stop them and exit?"):
                # Stop all running instances
                for instance in self.instances:
                    if instance.is_running():
                        instance.stop()
                
                # Save all settings
                self.save_all()
                
                # Destroy the application
                self.destroy()
        else:
            # Save all settings
            self.save_all()
            
            # Destroy the application
            self.destroy()
    
    def show_about(self):
        """Show about dialog"""
        about_text = """Gallery-DL Launcher

A graphical interface for managing multiple gallery-dl downloads.

Gallery-DL is a command-line program to download image galleries and collections from several image hosting sites.

Visit https://github.com/mikf/gallery-dl for more information about gallery-dl."""
        
        messagebox.showinfo("About Gallery-DL Launcher", about_text)

# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────
def main():
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)
    
    # Start the application
    app = Application()
    app.mainloop()

if __name__ == "__main__":
    main()
