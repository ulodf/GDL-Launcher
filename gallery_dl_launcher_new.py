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
        output_dir_frame.pack(fill=X, padx=6, pady=(6, 3))
        
        ttk.Label(output_dir_frame, text="Output Directory:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(output_dir_frame, textvariable=self.output_dir_var, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(output_dir_frame, text="Browse", command=self._browse_output_dir).pack(side=LEFT)
        
        # Temporary directory selector
        temp_dir_frame = ttk.Frame(controls_frame)
        temp_dir_frame.pack(fill=X, padx=6, pady=(0, 3))
        
        ttk.Label(temp_dir_frame, text="Temporary Directory:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(temp_dir_frame, textvariable=self.temp_dir_var, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(temp_dir_frame, text="Browse", command=self._browse_temp_dir).pack(side=LEFT)
        
        # Download archive file selector
        archive_frame = ttk.Frame(controls_frame)
        archive_frame.pack(fill=X, padx=6, pady=(0, 3))
        
        ttk.Label(archive_frame, text="Download Archive File:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(archive_frame, textvariable=self.archive_file_var, width=50).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(archive_frame, text="Browse", command=self._browse_archive_file).pack(side=LEFT)
        
        # Content type filtering
        filter_frame = ttk.Frame(controls_frame)
        filter_frame.pack(fill=X, padx=6, pady=(0, 3))
        
        ttk.Label(filter_frame, text="Content Types:").pack(side=LEFT, padx=(0, 5))
        ttk.Checkbutton(filter_frame, text="Download Images", variable=self.download_images_var).pack(side=LEFT, padx=(0, 15))
        ttk.Checkbutton(filter_frame, text="Download Videos", variable=self.download_videos_var).pack(side=LEFT)
        
        # Extra options
        extra_opts_frame = ttk.Frame(controls_frame)
        extra_opts_frame.pack(fill=X, padx=6, pady=(0, 6))
        
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
    
    def _browse_temp_dir(self):
        """Open directory browser to select temporary directory for .part files"""
        directory = filedialog.askdirectory(
            initialdir=self.temp_dir_var.get(),
            title="Select Temporary Directory for .part Files"
        )
        if directory:
            self.temp_dir_var.set(directory)
            # Create directory if it doesn't exist
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def _browse_archive_file(self):
        """Open file browser to select download archive file"""
        filename = filedialog.asksaveasfilename(
            initialfile=self.archive_file_var.get(),
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            title="Select Download Archive File"
        )
        if filename:
            self.archive_file_var.set(filename)
            # Ensure parent directory exists
            Path(filename).parent.mkdir(parents=True, exist_ok=True)
    
    def _save_settings(self):
        """Save instance settings to a JSON file"""
        settings = {
            "output_dir": self.output_dir_var.get(),
            "temp_dir": self.temp_dir_var.get(),
            "archive_file": self.archive_file_var.get(),
            "extra_opts": self.extra_opts_var.get(),
            "download_images": self.download_images_var.get(),
            "download_videos": self.download_videos_var.get()
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
                self.temp_dir_var.set(settings.get("temp_dir", str(Path.home() / "Downloads" / "temp")))
                self.archive_file_var.set(settings.get("archive_file", str(DATA_DIR / "archives" / f"instance_{self.idx}_archive.txt")))
                self.extra_opts_var.set(settings.get("extra_opts", ""))
                self.download_images_var.set(settings.get("download_images", True))
                self.download_videos_var.set(settings.get("download_videos", True))
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
        
        # Create directories if they don't exist
        output_dir = Path(self.output_dir_var.get())
        temp_dir = Path(self.temp_dir_var.get())
        archive_file = Path(self.archive_file_var.get())
        
        output_dir.mkdir(parents=True, exist_ok=True)
        temp_dir.mkdir(parents=True, exist_ok=True)
        archive_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Build command
        cmd = ["gallery-dl"]
        
        # Add global options
        cmd.extend(self.get_global_opts())
        
        # Add instance-specific options
        if output_dir:
            cmd.extend(["-d", str(output_dir)])
        
        # Add temporary directory for .part files
        cmd.extend(["--temporary-directory", str(temp_dir)])
        
        # Add download archive file
        cmd.extend(["--download-archive", str(archive_file)])
        
        # Add content type filters
        content_types = []
        if self.download_images_var.get():
            content_types.append("image")
        if self.download_videos_var.get():
            content_types.append("video")
        
        if content_types:
            cmd.extend(["--filter", "content=" + ",".join(content_types)])
        elif not self.download_images_var.get() and not self.download_videos_var.get():
            # If no content types are selected, don't download anything
            messagebox.showinfo("No Content Types Selected", "Please select at least one content type to download")
            return
        
        # Add extra options
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
# URL checker and distributor tab
# ──────────────────────────────────────────────────────────────────────────────
class URLCheckerFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook, get_instances):
        super().__init__(master)
        self.get_instances = get_instances
        
        # Create UI Elements
        self._create_ui()
    
    def _create_ui(self):
        """Create the UI elements for the URL checker"""
        # URL Input Frame
        input_frame = ttk.LabelFrame(self, text="URL Checker & Distributor")
        input_frame.pack(fill=X, padx=6, pady=6)
        
        # Single URL check/distribution
        single_url_frame = ttk.Frame(input_frame)
        single_url_frame.pack(fill=X, padx=6, pady=(6, 3))
        
        self.url_var = tk.StringVar()
        ttk.Label(single_url_frame, text="URL:").pack(side=LEFT, padx=(0, 5))
        ttk.Entry(single_url_frame, textvariable=self.url_var, width=60).pack(side=LEFT, fill=X, expand=True, padx=(0, 5))
        ttk.Button(single_url_frame, text="Check", command=self.check_url).pack(side=LEFT, padx=(0, 5))
        ttk.Button(single_url_frame, text="Add to Best Instance", command=self.add_to_best_instance).pack(side=LEFT)
        
        # Bulk URLs input
        bulk_frame = ttk.LabelFrame(self, text="Bulk URL Processing")
        bulk_frame.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        # Bulk URL textbox with scrollbar
        bulk_text_frame = ttk.Frame(bulk_frame)
        bulk_text_frame.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        bulk_scrollbar = ttk.Scrollbar(bulk_text_frame)
        bulk_scrollbar.pack(side=RIGHT, fill=Y)
        
        self.bulk_urls_box = tk.Text(bulk_text_frame, height=10, yscrollcommand=bulk_scrollbar.set)
        self.bulk_urls_box.pack(side=LEFT, fill=BOTH, expand=True)
        bulk_scrollbar.config(command=self.bulk_urls_box.yview)
        
        # Bulk URL buttons
        bulk_btn_frame = ttk.Frame(bulk_frame)
        bulk_btn_frame.pack(fill=X, padx=6, pady=(0, 6))
        
        ttk.Button(bulk_btn_frame, text="Check All URLs", command=self.check_bulk_urls).pack(side=LEFT, padx=(0, 5))
        ttk.Button(bulk_btn_frame, text="Distribute All URLs", command=self.distribute_bulk_urls).pack(side=LEFT)
        
        # Results frame
        results_frame = ttk.LabelFrame(self, text="Results")
        results_frame.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        # Results textbox with scrollbar
        results_text_frame = ttk.Frame(results_frame)
        results_text_frame.pack(fill=BOTH, expand=True, padx=6, pady=6)
        
        results_scrollbar = ttk.Scrollbar(results_text_frame)
        results_scrollbar.pack(side=RIGHT, fill=Y)
        
        self.results_box = tk.Text(results_text_frame, height=10, yscrollcommand=results_scrollbar.set)
        self.results_box.pack(side=LEFT, fill=BOTH, expand=True)
        results_scrollbar.config(command=self.results_box.yview)
        
        # Configure tags for coloring
        self.results_box.tag_configure('found', foreground='green')
        self.results_box.tag_configure('not_found', foreground='blue')
        self.results_box.tag_configure('added', foreground='purple')
        self.results_box.tag_configure('error', foreground='red')
    
    def check_url(self):
        """Check if a URL exists in any instance"""
        url = self.url_var.get().strip()
        if not url:
            self._update_results("Please enter a URL to check", 'error')
            return
        
        instances = self.get_instances()
        found_in = []
        
        for idx, instance in enumerate(instances):
            if hasattr(instance, 'links_box'):
                instance_urls = instance.links_box.get('1.0', 'end').strip().splitlines()
                if url in instance_urls:
                    found_in.append(idx)
        
        if found_in:
            instances_str = ", ".join([str(idx+1) for idx in found_in])
            self._update_results(f"URL found in instance(s): {instances_str}", 'found')
        else:
            self._update_results("URL not found in any instance", 'not_found')
    
    def add_to_best_instance(self):
        """Add the URL to the instance with the fewest URLs"""
        url = self.url_var.get().strip()
        if not url:
            self._update_results("Please enter a URL to add", 'error')
            return
        
        instances = self.get_instances()
        if not instances:
            self._update_results("No instances available", 'error')
            return
        
        # Check if URL already exists in any instance
        for idx, instance in enumerate(instances):
            if hasattr(instance, 'links_box'):
                instance_urls = instance.links_box.get('1.0', 'end').strip().splitlines()
                if url in instance_urls:
                    self._update_results(f"URL already exists in instance {idx+1}", 'found')
                    return
        
        # Find the instance with the fewest URLs
        instance_counts = []
        for idx, instance in enumerate(instances):
            if hasattr(instance, 'links_box'):
                links = instance.links_box.get('1.0', 'end').strip().splitlines()
                instance_counts.append((idx, len(links)))
        
        if not instance_counts:
            self._update_results("No valid instances found", 'error')
            return
        
        # Sort by URL count
        instance_counts.sort(key=lambda x: x[1])
        best_idx = instance_counts[0][0]
        
        # Add the URL to the instance with the fewest URLs
        instance = instances[best_idx]
        current_text = instance.links_box.get('1.0', 'end').strip()
        
        if current_text:
            instance.links_box.insert('end', f"\n{url}")
        else:
            instance.links_box.insert('1.0', url)
        
        self._update_results(f"Added URL to instance {best_idx+1}", 'added')
    
    def check_bulk_urls(self):
        """Check multiple URLs at once"""
        urls = self.bulk_urls_box.get('1.0', 'end').strip().splitlines()
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            self._update_results("Please enter URLs to check", 'error')
            return
        
        instances = self.get_instances()
        results = []
        
        for url in urls:
            found_in = []
            for idx, instance in enumerate(instances):
                if hasattr(instance, 'links_box'):
                    instance_urls = instance.links_box.get('1.0', 'end').strip().splitlines()
                    if url in instance_urls:
                        found_in.append(idx)
            
            if found_in:
                instances_str = ", ".join([str(idx+1) for idx in found_in])
                results.append((url, f"Found in instance(s): {instances_str}", 'found'))
            else:
                results.append((url, "Not found in any instance", 'not_found'))
        
        self._clear_results()
        for url, result, tag in results:
            self.results_box.insert('end', f"{url}: {result}\n", tag)
    
    def distribute_bulk_urls(self):
        """Distribute multiple URLs across instances to maintain balance"""
        urls = self.bulk_urls_box.get('1.0', 'end').strip().splitlines()
        urls = [url.strip() for url in urls if url.strip()]
        
        if not urls:
            self._update_results("Please enter URLs to distribute", 'error')
            return
        
        instances = self.get_instances()
        if not instances:
            self._update_results("No instances available", 'error')
            return
        
        # Get current URL counts for all instances
        instance_counts = []
        for idx, instance in enumerate(instances):
            if hasattr(instance, 'links_box'):
                links = instance.links_box.get('1.0', 'end').strip().splitlines()
                instance_counts.append((idx, links))
        
        if not instance_counts:
            self._update_results("No valid instances found", 'error')
            return
        
        # Filter out URLs that already exist in instances
        new_urls = []
        skipped_urls = []
        for url in urls:
            exists = False
            for _, links in instance_counts:
                if url in links:
                    exists = True
                    skipped_urls.append(url)
                    break
            if not exists:
                new_urls.append(url)
        
        # Distribute new URLs evenly
        results = []
        
        for url in new_urls:
            # Find instance with fewest URLs
            instance_counts.sort(key=lambda x: len(x[1]))
            best_idx, links = instance_counts[0]
            
            # Add URL to instance
            instance = instances[best_idx]
            current_text = instance.links_box.get('1.0', 'end').strip()
            
            if current_text:
                instance.links_box.insert('end', f"\n{url}")
            else:
                instance.links_box.insert('1.0', url)
            
            # Update count for this instance
            instance_counts[0] = (best_idx, links + [url])
            
            results.append((url, f"Added to instance {best_idx+1}", 'added'))
        
        # Add skipped URLs to results
        for url in skipped_urls:
            results.append((url, "Skipped (already exists)", 'found'))
        
        self._clear_results()
        for url, result, tag in results:
            self.results_box.insert('end', f"{url}: {result}\n", tag)
    
    def _update_results(self, message, tag=None):
        """Update the results text box"""
        self._clear_results()
        if tag:
            self.results_box.insert('1.0', f"{message}\n", tag)
        else:
            self.results_box.insert('1.0', f"{message}\n")
    
    def _clear_results(self):
        """Clear the results text box"""
        self.results_box.delete('1.0', 'end')

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
        
        # Create URL checker tab
        self.url_checker_frame = URLCheckerFrame(self.notebook, lambda: self.instances)
        self.notebook.add(self.url_checker_frame, text="URL Checker")
        
        # Create instance tabs (will be loaded from state or defaults)
        self.instances = []
        
        # Create menu
        self._create_menu()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=SUNKEN, anchor=W)
        self.status_bar.pack(side=BOTTOM, fill=X)
        
        # Set up clean exit
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Load application state
        self.load_state()
    
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
        
        # Load saved links for this instance
        instance._load_links()
    
    def add_instance(self):
        """Add a new instance tab"""
        new_idx = len(self.instances)
        self._create_instance(new_idx)
        self.notebook.select(new_idx + 3)  # +3 for config, log, and URL checker tabs
        self.status_var.set(f"Added instance {new_idx+1}")
        
        # Save application state after adding instance
        self.save_state()
    
    def save_all(self):
        """Save all configuration and instance data"""
        # Save global config
        self.config_frame.save()
        
        # Save instance settings
        for instance in self.instances:
            instance._save_settings()
            instance._save_links()
        
        # Save application state
        self.save_state()
        
        self.status_var.set("All settings saved")
        
    def save_state(self):
        """Save the application state, including number of instances and window geometry"""
        state_dir = DATA_DIR / "state"
        state_dir.mkdir(exist_ok=True)
        
        state = {
            "instance_count": len(self.instances),
            "geometry": self.geometry(),
            "timestamp": datetime.now().strftime(TIMESTAMP_FMT)
        }
        
        state_file = state_dir / "app_state.json"
        
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            print(f"Error saving application state: {e}")
    
    def load_state(self):
        """Load the application state, including number of instances and window geometry"""
        state_file = DATA_DIR / "state" / "app_state.json"
        
        # Default state
        instance_count = 3
        
        if state_file.exists():
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                
                # Get instance count from state
                instance_count = state.get("instance_count", 3)
                
                # Restore window geometry
                if "geometry" in state:
                    try:
                        self.geometry(state["geometry"])
                    except:
                        pass  # Ignore geometry errors
                        
                self.status_var.set(f"Loaded application state from {state.get('timestamp', 'unknown')}")
            except Exception as e:
                print(f"Error loading application state: {e}")
        
        # Create instances
        for i in range(instance_count):
            self._create_instance(i)
    
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
                
                # Save all settings and state
                self.save_all()
                self.save_state()  # Ensure state is saved when closing
                
                # Destroy the application
                self.destroy()
        else:
            # Save all settings and state
            self.save_all()
            self.save_state()  # Ensure state is saved when closing
            
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
