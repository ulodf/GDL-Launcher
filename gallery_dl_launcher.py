import tkinter as tk
from tkinter import ttk, filedialog, messagebox
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
CONFIG_FILE = Path.home()  .gallery_dl_launcher.cfg
DATA_DIR = Path.home()  .gallery_dl_launcher
DATA_DIR.mkdir(exist_ok=True)

TIMESTAMP_FMT = %Y-%m-%d %H%M%S

# ──────────────────────────────────────────────────────────────────────────────
# Default configuration with correct option format
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_CONFIG = # Gallery-dl global options - edit as needed
--cookies cookies.txt
-o filename={date%Y-%m-%d}_{user}_{title}_{id} {num02}.{extension}
# --download-archive global-archive.txt  # Uncomment to use a global archive



# ──────────────────────────────────────────────────────────────────────────────
# Config tab – global gallery‑dl CLI options
# ──────────────────────────────────────────────────────────────────────────────
class ConfigFrame(ttk.Frame)
    def __init__(self, master ttk.Notebook)
        super().__init__(master)
        ttk.Label(self, text=Global gallery-dl options (one per line)).pack(anchor=w, padx=6, pady=(6, 0))

        # Create frame for the textbox with a scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=both, expand=True, padx=6, pady=(0, 6))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=right, fill=y)

        # Create and configure the text box
        self.box = tk.Text(text_frame, width=90, height=6, yscrollcommand=scrollbar.set)
        self.box.pack(side=left, fill=both, expand=True)
        scrollbar.config(command=self.box.yview)

        # Add a status bar for feedback
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(self, textvariable=self.status_var, anchor=w)
        self.status_bar.pack(fill=x, padx=6, pady=(0, 6))

        # Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=x, padx=6, pady=(0, 6))

        ttk.Button(btn_frame, text=Save, command=self.save).pack(side=left, padx=(0, 5))
        ttk.Button(btn_frame, text=Reset to Default, command=self.reset_to_default).pack(side=left)

        # Load config
        self.load_config()

    def load_config(self)
        Load configuration from file
        if CONFIG_FILE.exists()
            self.box.delete(1.0, end)
            self.box.insert(1.0, CONFIG_FILE.read_text())
        else
            self.reset_to_default()

    def reset_to_default(self)
        Reset configuration to default values
        self.box.delete(1.0, end)
        self.box.insert(1.0, DEFAULT_CONFIG)
        self.status_var.set(Reset to default configuration)

    def get_tokens(self) - list[str]
        Parse configuration to get command line tokens
        tokens list[str] = []
        for line in self.box.get(1.0, end).strip().splitlines()
            line = line.strip()
            if line and not line.startswith(#)
                tokens.extend(shlex.split(line))
        return tokens

    def save(self)
        Save configuration to file
        try
            CONFIG_FILE.write_text(self.box.get(1.0, end).rstrip() + n)
            self.status_var.set(fConfiguration saved to {CONFIG_FILE})
        except OSError as e
            self.status_var.set(fError Could not write to {CONFIG_FILE})
            messagebox.showwarning(Save failed, fCould not write {CONFIG_FILE} {e})


# ──────────────────────────────────────────────────────────────────────────────
# Unified log tab – aggregated stdoutstderr
# ──────────────────────────────────────────────────────────────────────────────
class UnifiedLogFrame(ttk.Frame)
    def __init__(self, master ttk.Notebook)
        super().__init__(master)
        ttk.Label(self, text=Unified live log – all instances).pack(anchor=w, padx=6, pady=(6, 0))

        # Create frame for the textbox with a scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=both, expand=True, padx=6, pady=(0, 6))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=right, fill=y)

        # Create and configure the text box
        self.box = tk.Text(text_frame, width=100, height=25, state=disabled, yscrollcommand=scrollbar.set)
        self.box.pack(side=left, fill=both, expand=True)
        scrollbar.config(command=self.box.yview)

        # Add control buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=x, padx=6, pady=(0, 6))

        ttk.Button(btn_frame, text=Clear Log, command=self.clear_log).pack(side=left, padx=(0, 5))
        ttk.Button(btn_frame, text=Save Log, command=self.save_log).pack(side=left)

        # Track autoscroll state
        self.autoscroll = tk.BooleanVar(value=True)
        ttk.Checkbutton(btn_frame, text=Auto-scroll, variable=self.autoscroll).pack(side=right)

    def append(self, msg str)
        Append a message to the log with timestamp
        # ignore gallery-dl #… skip lines
        if msg.lstrip().startswith(#) or  # F in msg or n# F in msg
            return
        if not msg.endswith('n')
            msg += 'n'

        ts = datetime.now().strftime(TIMESTAMP_FMT)
        line = f[{ts}] {msg}

        self.box.config(state=normal)
        self.box.insert(end, line)

        # Limit log size to prevent performance issues (keep last 5000 lines)
        num_lines = int(self.box.index('end-1c').split('.')[0])
        if num_lines  5000
            self.box.delete(1.0, f{num_lines - 5000}.0)

        if self.autoscroll.get()
            self.box.see(end)

        self.box.config(state=disabled)

    def clear_log(self)
        Clear the log content
        self.box.config(state=normal)
        self.box.delete(1.0, end)
        self.box.config(state=disabled)

    def save_log(self)
        Save log content to a file
        filename = filedialog.asksaveasfilename(
            defaultextension=.log,
            filetypes=[(Log files, .log), (Text files, .txt), (All files, .)],
            initialdir=DATA_DIR,
            title=Save Log
        )
        if filename
            try
                with open(filename, 'w', encoding='utf-8') as f
                    f.write(self.box.get(1.0, end))
                messagebox.showinfo(Success, fLog saved to {filename})
            except Exception as e
                messagebox.showerror(Error, fFailed to save log {e})


# ──────────────────────────────────────────────────────────────────────────────
# Unified links tab – view links across all instances
# ──────────────────────────────────────────────────────────────────────────────
class UnifiedLinksFrame(ttk.Frame)
    def __init__(self, master ttk.Notebook, get_instances)
        super().__init__(master)
        self.get_instances = get_instances

        # URL to instance mapping
        self.url_mappings = {}
        self.load_url_mappings()

        # Search frame
        search_frame = ttk.LabelFrame(self, text=Search & Check URLs)
        search_frame.pack(fill=x, padx=6, pady=6)
        
        # URL Search
        search_input_frame = ttk.Frame(search_frame)
        search_input_frame.pack(fill=x, padx=6, pady=(6, 3))
        
        self.search_var = tk.StringVar()
        ttk.Label(search_input_frame, text=Search URL).pack(side=left, padx=(0, 5))
        ttk.Entry(search_input_frame, textvariable=self.search_var, width=60).pack(side=left, fill=x, expand=True, padx=(0, 5))
        ttk.Button(search_input_frame, text=Search, command=self.search_url).pack(side=left)
        
        # Domain Filter
        domain_filter_frame = ttk.Frame(search_frame)
        domain_filter_frame.pack(fill=x, padx=6, pady=(0, 3))
        
        self.domain_filter_var = tk.StringVar()
        ttk.Label(domain_filter_frame, text=Filter by domain).pack(side=left, padx=(0, 5))
        ttk.Entry(domain_filter_frame, textvariable=self.domain_filter_var, width=30).pack(side=left, padx=(0, 5))
        ttk.Button(domain_filter_frame, text=Apply Filter, command=self.filter_by_domain).pack(side=left)
        ttk.Button(domain_filter_frame, text=Clear Filter, command=self.clear_domain_filter).pack(side=left, padx=(5, 0))
        
        # Bulk URL Check
        bulk_check_frame = ttk.Frame(search_frame)
        bulk_check_frame.pack(fill=x, padx=6, pady=(0, 3))
        
        ttk.Label(bulk_check_frame, text=Bulk check URLs (one per line)).pack(anchor=w)
        
        # Create frame for the bulk URLs textbox with a scrollbar
        bulk_text_frame = ttk.Frame(search_frame)
        bulk_text_frame.pack(fill=both, expand=False, padx=6, pady=(0, 3))
        
        # Add scrollbar for bulk URLs
        bulk_scrollbar = ttk.Scrollbar(bulk_text_frame)
        bulk_scrollbar.pack(side=right, fill=y)
        
        # Create and configure the bulk URLs text box
        self.bulk_urls_box = tk.Text(bulk_text_frame, width=80, height=5, yscrollcommand=bulk_scrollbar.set)
        self.bulk_urls_box.pack(side=left, fill=both, expand=True)
        bulk_scrollbar.config(command=self.bulk_urls_box.yview)
        
        # Bulk check controls
        bulk_controls = ttk.Frame(search_frame)
        bulk_controls.pack(fill=x, padx=6, pady=(0, 3))
        
        ttk.Button(bulk_controls, text=Paste URLs, command=self._paste_bulk_urls).pack(side=left, padx=(0, 5))
        ttk.Button(bulk_controls, text=Clear, command=self._clear_bulk_urls).pack(side=left, padx=(0, 5))
        ttk.Button(bulk_controls, text=Check All URLs, command=self.check_bulk_urls).pack(side=left)
        
        # Search results
        results_frame = ttk.LabelFrame(search_frame, text=Results)
        results_frame.pack(fill=both, expand=True, padx=6, pady=(3, 6))
        
        # Create frame for the results textbox with a scrollbar
        results_text_frame = ttk.Frame(results_frame)
        results_text_frame.pack(fill=both, expand=True, padx=6, pady=6)
        
        # Add scrollbar for results
        results_scrollbar = ttk.Scrollbar(results_text_frame)
        results_scrollbar.pack(side=right, fill=y)
        
        # Create and configure the results text box
        self.results_box = tk.Text(results_text_frame, width=80, height=8, state=disabled, yscrollcommand=results_scrollbar.set)
        self.results_box.pack(side=left, fill=both, expand=True)
        results_scrollbar.config(command=self.results_box.yview)
        
        # Quick add frame
        quick_add_frame = ttk.LabelFrame(self, text=Quick Add URL)
        quick_add_frame.pack(fill=x, padx=6, pady=6)

        self.new_url_var = tk.StringVar()
        ttk.Entry(quick_add_frame, textvariable=self.new_url_var, width=80).pack(side=left, fill=x, expand=True,
                                                                                 padx=6, pady=6)
        ttk.Button(quick_add_frame, text=Add to Best Instance, command=self.quick_add_url).pack(side=left, padx=6,
                                                                                                  pady=6)

        # Links view header
        header = ttk.Frame(self)
        header.pack(fill=x, padx=6, pady=(6, 0))
        ttk.Label(header, text=All queued links).pack(side=left)
        ttk.Button(header, text=Refresh, command=self.refresh).pack(side=right)
        ttk.Button(header, text=Copy All, command=self.copy_all).pack(side=right, padx=5)
        ttk.Button(header, text=Export, command=self.export_links).pack(side=right, padx=(0, 5))
        ttk.Button(header, text=Import, command=self.import_links).pack(side=right, padx=(0, 5))
        ttk.Button(header, text=Export All with Mapping, command=self.export_with_mapping).pack(side=right)

        # Create frame for the textbox with a scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(fill=both, expand=True, padx=6, pady=(6, 6))

        # Add scrollbar
        scrollbar = ttk.Scrollbar(text_frame)
        scrollbar.pack(side=right, fill=y)

        # Create and configure the text box
        self.box = tk.Text(text_frame, width=100, height=25, state=disabled, yscrollcommand=scrollbar.set)
        self.box.pack(side=left, fill=both, expand=True)
        scrollbar.config(command=self.box.yview)

        self.refresh()

    def load_url_mappings(self)
        Load URL to instance mappings from file
        url_mappings_file = DATA_DIR  url_mappings.json
        if url_mappings_file.exists()
            try
                with open(url_mappings_file, 'r') as f
                    self.url_mappings = json.load(f)
            except (json.JSONDecodeError, OSError)
                self.url_mappings = {}

    def save_url_mappings(self)
        Save URL to instance mappings to file
        url_mappings_file = DATA_DIR  url_mappings.json
        try
            with open(url_mappings_file, 'w') as f
                json.dump(self.url_mappings, f, indent=2)
        except OSError
            pass

    def _paste_bulk_urls(self)
        Paste URLs from clipboard into bulk URLs box
        try
            clipboard_content = self.clipboard_get()
            self.bulk_urls_box.delete(1.0, end)
            self.bulk_urls_box.insert(1.0, clipboard_content)
        except tk.TclError
            pass  # No clipboard content
            
    def _clear_bulk_urls(self)
        Clear the bulk URLs box
        self.bulk_urls_box.delete(1.0, end)
            
    def _update_results_box(self, text)
        Update the results text box
        self.results_box.config(state=normal)
        self.results_box.delete(1.0, end)
        self.results_box.insert(1.0, text)
        self.results_box.config(state=disabled)

    def normalize_url(self, url str) - str
        Normalize URL to ensure consistent comparison
        try
            # Remove trailing slashes, common query parameters and fragments
            parsed = urllib.parse.urlparse(url)
            netloc = parsed.netloc.lower()
            
            # Remove 'www.' prefix from domain if present
            if netloc.startswith('www.')
                netloc = netloc[4]
                
            # Remove common query parameters that don't affect content
            # (like tracking parameters, page numbers for some sites, etc.)
            query_params = urllib.parse.parse_qs(parsed.query)
            for param in ['utm_source', 'utm_medium', 'utm_campaign', 'ref', 'source', 'page']
                if param in query_params
                    del query_params[param]
            
            # Reconstruct the query string
            query_string = urllib.parse.urlencode(query_params, doseq=True)
            
            # Rebuild the URL without fragments (everything after #)
            normalized = urllib.parse.urlunparse((
                parsed.scheme.lower(),
                netloc,
                parsed.path.rstrip(''),
                parsed.params,
                query_string,
                ''
            ))
            
            return normalized
        except Exception
            # If parsing fails, just return the original URL
            return url
            
    def search_url(self)
        Search for a URL across all instances
        search_url = self.search_var.get().strip()
        if not search_url
            self._update_results_box(Please enter a URL to search)
            return
        
        # Normalize the search URL
        normalized_search_url = self.normalize_url(search_url)
            
        # Dictionary to store found URLs by instance
        found_instances = {}
        
        # Get all instances
        instances = self.get_instances()
        
        # Search through each instance
        for idx, instance in enumerate(instances)
            # Get URLs from the instance
            if hasattr(instance, 'links_box')
                instance_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                
                # Normalize and check each URL
                for url in instance_urls
                    normalized_url = self.normalize_url(url)
                    
                    # Check for exact matches using normalized URLs
                    if normalized_search_url == normalized_url
                        found_instances[idx] = True  # True indicates exact match
                        break
                    
                    # Check for partial matches (URL might be part of another URL)
                    elif normalized_search_url in normalized_url or normalized_url in normalized_search_url
                        if idx not in found_instances
                            found_instances[idx] = False  # False indicates partial match
        
        # Display results
        if found_instances
            result_text = fResults for URL {search_url}n
            result_text += ------------------------------------------n
            result_text += Found in instancesn
            for idx, exact_match in found_instances.items()
                match_type = Exact match if exact_match else Partial match
                result_text += fInstance {idx+1} {match_type}n
            self._update_results_box(result_text)
        else
            self._update_results_box(fURL '{search_url}' not found in any instance)
            
    def check_bulk_urls(self)
        Check multiple URLs at once
        # Get URLs from the bulk URLs box
        bulk_urls = self.bulk_urls_box.get(1.0, end-1c).strip().splitlines()
        
        # Remove empty lines and whitespace
        bulk_urls = [url.strip() for url in bulk_urls if url.strip()]
        
        if not bulk_urls
            self._update_results_box(Please enter URLs to check)
            return
        
        # Get all instances
        instances = self.get_instances()
        
        # Dictionary to store results for each URL
        results = {}
        
        # Check each URL
        for url in bulk_urls
            # Normalize the URL
            normalized_url = self.normalize_url(url)
            
            # Dictionary to store found instances for this URL
            found_instances = {}
            
            # Search through each instance
            for idx, instance in enumerate(instances)
                # Get URLs from the instance
                if hasattr(instance, 'links_box')
                    instance_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                    
                    # Normalize and check each URL
                    for instance_url in instance_urls
                        normalized_instance_url = self.normalize_url(instance_url)
                        
                        # Check for exact matches using normalized URLs
                        if normalized_url == normalized_instance_url
                            found_instances[idx] = True  # True indicates exact match
                            break
                        
                        # Check for partial matches (URL might be part of another URL)
                        elif normalized_url in normalized_instance_url or normalized_instance_url in normalized_url
                            if idx not in found_instances
                                found_instances[idx] = False  # False indicates partial match
            
            # Store results for this URL
            results[url] = found_instances
        
        # Display results
        result_text = Bulk URL Check Resultsn
        result_text += =======================n
        
        for url, found_instances in results.items()
            result_text += fURL {url}n
            
            if found_instances
                for idx, exact_match in found_instances.items()
                    match_type = Exact match if exact_match else Partial match
                    result_text += f  Instance {idx+1} {match_type}n
            else
                result_text +=   Not found in any instancen
            
            result_text += ------------------------------------------n
            
        self._update_results_box(result_text)
        
    def filter_by_domain(self)
        Filter and display URLs by domain
        domain_filter = self.domain_filter_var.get().strip().lower()
        
        if not domain_filter
            self._update_results_box(Please enter a domain to filter by)
            return
            
        # Get all instances
        instances = self.get_instances()
        
        # Dictionary to store filtered URLs by instance
        filtered_urls = {}
        
        # Search through each instance
        for idx, instance in enumerate(instances)
            # Get URLs from the instance
            if hasattr(instance, 'links_box')
                instance_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                
                # Filter URLs by domain
                matching_urls = []
                for url in instance_urls
                    try
                        parsed = urllib.parse.urlparse(url)
                        netloc = parsed.netloc.lower()
                        
                        # Remove 'www.' prefix from domain if present
                        if netloc.startswith('www.')
                            netloc = netloc[4]
                            
                        if domain_filter in netloc
                            matching_urls.append(url)
                    except Exception
                        # Skip malformed URLs
                        continue
                        
                if matching_urls
                    filtered_urls[idx] = matching_urls
        
        # Display results
        if filtered_urls
            result_text = fURLs with domain '{domain_filter}'n
            result_text += =======================n
            
            for idx, urls in filtered_urls.items()
                result_text += fInstance {idx+1}n
                for url in urls
                    result_text += f  {url}n
                result_text += ------------------------------------------n
                
            self._update_results_box(result_text)
        else
            self._update_results_box(fNo URLs found with domain '{domain_filter}')
            
    def clear_domain_filter(self)
        Clear domain filter
        self.domain_filter_var.set()
        self._update_results_box(Domain filter cleared)
            
    def extract_base_url(self, url str) - str
        Extract base URL for consistent mapping
        try
            # Normalize the URL first
            normalized_url = self.normalize_url(url)
            
            # Extract domain and first path component
            parts = normalized_url.split()
            if len(parts) = 3  # has at least httpdomain.com
                domain = parts[2]

                # For certain sites, also include the userprofile path
                if user in normalized_url or profile in normalized_url
                    # Find the user part in the URL
                    user_parts = normalized_url.split(user) if user in normalized_url else normalized_url.split(profile)
                    if len(user_parts)  1
                        # Extract username (stop at the next slash if present)
                        username = user_parts[1].split()[0]
                        return f{domain}user{username}

                return domain
            return normalized_url
        except
            # If parsing fails, just return the URL
            return url

    def quick_add_url(self)
        Add URL to the best instance, checking for duplicates first
        url = self.new_url_var.get().strip()
        if not url
            messagebox.showinfo(Empty URL, Please enter a URL to add)
            return

        instances = self.get_instances()
        if not instances
            messagebox.showinfo(No Instances, No instances available to add URL)
            return
            
        # Check if URL already exists in any instance
        found_instances = {}
        for idx, instance in enumerate(instances)
            if hasattr(instance, 'links_box')
                instance_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                
                # Check for exact matches
                if url in instance_urls
                    found_instances[idx] = True  # True indicates exact match
                    continue
                    
                # Check for partial matches (URL might be part of another URL)
                for instance_url in instance_urls
                    if url in instance_url or instance_url in url
                        if idx not in found_instances
                            found_instances[idx] = False  # False indicates partial match
        
        # If URL exists, ask user if they want to add it anyway
        if found_instances
            result_text = URL already exists inn
            for idx, exact_match in found_instances.items()
                match_type = Exact match if exact_match else Partial match
                result_text += fInstance {idx+1} {match_type}n
                
            result_text += nAdd anyway
            if not messagebox.askyesno(Duplicate URL, result_text)
                return

        # Get best instance for this URL
        instance_idx = self.get_best_instance_for_url(url, instances)
        instance = instances[instance_idx]

        # Add URL to instance
        current_text = instance.links_box.get(1.0, end).strip()
        if current_text
            instance.links_box.insert(end, fn{url})
        else
            instance.links_box.insert(1.0, url)

        # Save links
        instance._save_links()

        # Clear entry and update
        self.new_url_var.set()
        self.refresh()

        # Show confirmation
        messagebox.showinfo(URL Added, fAdded URL to Instance {instance_idx + 1})

    def get_best_instance_for_url(self, url str, instances)
        Get the best instance for a URL
        base_url = self.extract_base_url(url)

        # Check if this URL already has an assigned instance
        if base_url in self.url_mappings
            idx = self.url_mappings[base_url]
            # Verify index is valid
            if 0 = idx  len(instances)
                return idx

        # Find instance with fewest links
        min_links = float('inf')
        best_instance = 0

        for i, inst in enumerate(instances)
            # Skip running instances
            if not inst.is_running()
                link_count = len([ln for ln in inst.links_box.get(1.0, end).splitlines() if ln.strip()])
                if link_count  min_links
                    min_links = link_count
                    best_instance = i

        # Save the mapping
        self.url_mappings[base_url] = best_instance
        self.save_url_mappings()

        return best_instance

    def check_bulk_urls(self)
        Check multiple URLs at once
        # Get URLs from the bulk URLs box
        bulk_urls = self.bulk_urls_box.get(1.0, end-1c).strip().splitlines()
        
        # Remove empty lines and whitespace
        bulk_urls = [url.strip() for url in bulk_urls if url.strip()]
        
        if not bulk_urls
            self._update_results_box(Please enter URLs to check)
            return
        
        # Get all instances
        instances = self.get_instances()
        
        # Dictionary to store results for each URL
        results = {}
        
        # Check each URL
        for url in bulk_urls
            # Normalize the URL
            normalized_url = self.normalize_url(url)
            
            # Dictionary to store found instances for this URL
            found_instances = {}
            
            # Search through each instance
            for idx, instance in enumerate(instances)
                # Get URLs from the instance
                if hasattr(instance, 'links_box')
                    instance_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                    
                    # Normalize and check each URL
                    for instance_url in instance_urls
                        normalized_instance_url = self.normalize_url(instance_url)
                        
                        # Check for exact matches using normalized URLs
                        if normalized_url == normalized_instance_url
                            found_instances[idx] = True  # True indicates exact match
                            break
                        
                        # Check for partial matches (URL might be part of another URL)
                        elif normalized_url in normalized_instance_url or normalized_instance_url in normalized_url
                            if idx not in found_instances
                                found_instances[idx] = False  # False indicates partial match
            
            # Store results for this URL
            results[url] = found_instances
        
        # Display results
        result_text = Bulk URL Check Resultsn
        result_text += =======================n
        
        for url, found_instances in results.items()
            result_text += fURL {url}n
            
            if found_instances
                for idx, exact_match in found_instances.items()
                    match_type = Exact match if exact_match else Partial match
                    result_text += f  Instance {idx+1} {match_type}n
            else
                result_text +=   Not found in any instancen
            
            result_text += ------------------------------------------n
            
        self._update_results_box(result_text)
        
    def filter_by_domain(self)
        Filter and display URLs by domain
        domain_filter = self.domain_filter_var.get().strip().lower()
        
        if not domain_filter
            self._update_results_box(Please enter a domain to filter by)
            return
            
        # Get all instances
        instances = self.get_instances()
        
        # Dictionary to store filtered URLs by instance
        filtered_urls = {}
        
        # Search through each instance
        for idx, instance in enumerate(instances)
            # Get URLs from the instance
            if hasattr(instance, 'links_box')
                instance_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                
                # Filter URLs by domain
                matching_urls = []
                for url in instance_urls
                    try
                        parsed = urllib.parse.urlparse(url)
                        netloc = parsed.netloc.lower()
                        
                        # Remove 'www.' prefix from domain if present
                        if netloc.startswith('www.')
                            netloc = netloc[4]
                            
                        if domain_filter in netloc
                            matching_urls.append(url)
                    except Exception
                        # Skip malformed URLs
                        continue
                        
                if matching_urls
                    filtered_urls[idx] = matching_urls
        
        # Display results
        if filtered_urls
            result_text = fURLs with domain '{domain_filter}'n
            result_text += =======================n
            
            for idx, urls in filtered_urls.items()
                result_text += fInstance {idx+1}n
                for url in urls
                    result_text += f  {url}n
                result_text += ------------------------------------------n
                
            self._update_results_box(result_text)
        else
            self._update_results_box(fNo URLs found with domain '{domain_filter}')
            
    def clear_domain_filter(self)
        Clear domain filter
        self.domain_filter_var.set()
        self._update_results_box(Domain filter cleared)

    def refresh(self)
        Refresh the list of all links from all instances
        self.box.config(state=normal)
        self.box.delete(1.0, end)
        for inst in self.get_instances()
            links = [ln.strip() for ln in inst.links_box.get(1.0, end).splitlines() if ln.strip()]
            if not links
                continue
            self.box.insert(end, fInstance {inst.idx + 1}n)
            for ln in links
                self.box.insert(end, f  {ln}n)
            self.box.insert(end, n)
        self.box.config(state=disabled)

    def copy_all(self)
        Copy all links to clipboard
        self.refresh()  # Make sure we have the latest links
        content = self.box.get(1.0, end).strip()
        if content
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo(Copied, All links copied to clipboard)
        else
            messagebox.showinfo(No Links, No links to copy)

    def export_links(self)
        Export all links to a text file
        self.refresh()  # Make sure we have the latest links
        content = self.box.get(1.0, end).strip()
        if not content
            messagebox.showinfo(No Links, No links to export)
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=.txt,
            filetypes=[(Text files, .txt), (All files, .)],
            initialdir=DATA_DIR,
            title=Export Links
        )
        if filename
            try
                with open(filename, 'w', encoding='utf-8') as f
                    f.write(content)
                messagebox.showinfo(Success, fLinks exported to {filename})
            except Exception as e
                messagebox.showerror(Error, fFailed to export links {e})
                
    def export_with_mapping(self)
        Export all links with instance mapping to a JSON file
        # Get all instances
        instances = self.get_instances()
        
        # Collect URLs with their instance mappings
        url_mappings = {}
        for idx, instance in enumerate(instances)
            if hasattr(instance, 'links_box')
                instance_urls = [url.strip() for url in instance.links_box.get(1.0, end-1c).strip().splitlines() if url.strip()]
                
                for url in instance_urls
                    # Store with instance index and normalize URL for consistent lookup
                    normalized_url = self.normalize_url(url)
                    url_mappings[url] = {
                        instance idx,
                        normalized_url normalized_url,
                        base_url self.extract_base_url(url)
                    }
        
        if not url_mappings
            messagebox.showinfo(No Links, No links to export)
            return
            
        # Ask user for file location
        filename = filedialog.asksaveasfilename(
            defaultextension=.json,
            filetypes=[(JSON files, .json), (All files, .)],
            initialdir=DATA_DIR,
            title=Export URL Mappings
        )
        
        if filename
            try
                with open(filename, 'w', encoding='utf-8') as f
                    json.dump(url_mappings, f, indent=2)
                messagebox.showinfo(Success, fURL mappings exported to {filename})
            except Exception as e
                messagebox.showerror(Error, fFailed to export URL mappings {e})
                
    def import_links(self)
        Import links from a file
        # Ask user for file
        filename = filedialog.askopenfilename(
            filetypes=[
                (All supported files, .txt .json),
                (Text files, .txt),
                (JSON files, .json),
                (All files, .)
            ],
            initialdir=DATA_DIR,
            title=Import Links
        )
        
        if not filename
            return
            
        # Check file extension
        file_ext = os.path.splitext(filename)[1].lower()
        
        try
            if file_ext == .json
                self._import_json_links(filename)
            else  # Default to text file format
                self._import_text_links(filename)
        except Exception as e
            messagebox.showerror(Import Error, fFailed to import links {e})
    
    def _import_json_links(self, filename)
        Import links from a JSON file with instance mappings
        # Load URL mappings from JSON
        with open(filename, 'r', encoding='utf-8') as f
            url_mappings = json.load(f)
            
        if not url_mappings
            messagebox.showinfo(Empty File, No links found in the file)
            return
            
        # Get all instances
        instances = self.get_instances()
        if not instances
            messagebox.showinfo(No Instances, No instances available to import URLs)
            return
            
        # Dictionary to track URLs added to each instance
        imported_counts = {idx 0 for idx in range(len(instances))}
        
        # Add URLs to instances based on their mappings
        for url, mapping in url_mappings.items()
            if isinstance(mapping, dict) and instance in mapping
                instance_idx = mapping[instance]
                
                # Make sure instance index is valid
                if 0 = instance_idx  len(instances)
                    instance = instances[instance_idx]
                    
                    # Add URL to instance if it doesn't already exist
                    current_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                    if url not in current_urls
                        # Add URL to instance
                        if current_urls  # If there are already URLs, add a newline
                            instance.links_box.insert(end, fn{url})
                        else  # If this is the first URL, don't add a newline
                            instance.links_box.insert(1.0, url)
                            
                        # Save links
                        instance._save_links()
                        imported_counts[instance_idx] += 1
            else
                # If no valid mapping, add to best instance
                self._import_single_url(url, instances, imported_counts)
                
        # Refresh view
        self.refresh()
        
        # Show results
        result_msg = Import Resultsn
        for idx, count in imported_counts.items()
            if count  0
                result_msg += fInstance {idx+1} {count} URLs addedn
                
        if sum(imported_counts.values())  0
            messagebox.showinfo(Import Complete, result_msg)
        else
            messagebox.showinfo(Import Complete, No new URLs were added (all were duplicates))
    
    def _import_text_links(self, filename)
        Import links from a text file
        # Read the file
        with open(filename, 'r', encoding='utf-8') as f
            content = f.read()
            
        # Parse URLs from content
        urls = []
        current_instance = None
        
        for line in content.splitlines()
            line = line.strip()
            if not line
                continue
                
            # Check if line starts with Instance X
            instance_match = re.match(r^Instance (d+)$, line)
            if instance_match
                # Update current instance
                current_instance = int(instance_match.group(1)) - 1
                continue
                
            # If line is indented with spaces or starts with a URL, add it
            if line.startswith(  ) or line.startswith(http)
                # Remove leading spaces
                url = line.lstrip()
                if url.startswith(http)
                    urls.append((url, current_instance))
        
        if not urls
            messagebox.showinfo(No URLs, No valid URLs found in the file)
            return
            
        # Get all instances
        instances = self.get_instances()
        if not instances
            messagebox.showinfo(No Instances, No instances available to import URLs)
            return
            
        # Dictionary to track URLs added to each instance
        imported_counts = {idx 0 for idx in range(len(instances))}
        
        # Add URLs to instances
        for url, instance_idx in urls
            # If instance_idx is valid, use it; otherwise find the best instance
            if instance_idx is not None and 0 = instance_idx  len(instances)
                instance = instances[instance_idx]
                
                # Check if URL already exists in this instance
                current_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
                if url not in current_urls
                    # Add URL to instance
                    if current_urls  # If there are already URLs, add a newline
                        instance.links_box.insert(end, fn{url})
                    else  # If this is the first URL, don't add a newline
                        instance.links_box.insert(1.0, url)
                        
                    # Save links
                    instance._save_links()
                    imported_counts[instance_idx] += 1
            else
                # If no valid instance, add to best instance
                self._import_single_url(url, instances, imported_counts)
                
        # Refresh view
        self.refresh()
        
        # Show results
        result_msg = Import Resultsn
        for idx, count in imported_counts.items()
            if count  0
                result_msg += fInstance {idx+1} {count} URLs addedn
                
        if sum(imported_counts.values())  0
            messagebox.showinfo(Import Complete, result_msg)
        else
            messagebox.showinfo(Import Complete, No new URLs were added (all were duplicates))
    
    def _import_single_url(self, url, instances, imported_counts)
        Import a single URL to the best instance
        # Find best instance
        instance_idx = self.get_best_instance_for_url(url, instances)
        instance = instances[instance_idx]
        
        # Check if URL already exists
        current_urls = instance.links_box.get(1.0, end-1c).strip().splitlines()
        if url not in current_urls
            # Add URL to instance
            if current_urls  # If there are already URLs, add a newline
                instance.links_box.insert(end, fn{url})
            else  # If this is the first URL, don't add a newline
                instance.links_box.insert(1.0, url)
                
            # Save links
            instance._save_links()
            imported_counts[instance_idx] += 1


# ──────────────────────────────────────────────────────────────────────────────
# Instance tab – one gallery‑dl process
# ──────────────────────────────────────────────────────────────────────────────
class InstanceFrame(ttk.Frame)
    def __init__(self, master ttk.Notebook, idx int, get_global_opts, log_callback)
        super().__init__(master)
        self.idx = idx
        self.get_global_opts = get_global_opts
        self.log_callback = log_callback
        self.proc subprocess.Popen  None = None
        self.q queue.Queue[str] = queue.Queue()
        self.after_id str  None = None
        self.auto_restart = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar(value=Ready)
        self.total_downloaded = 0
        self.current_speed = 0.0
        self._in_prioritized_mode = False
        self._all_urls_for_second_phase = None

        # Links box frame
        links_frame = ttk.LabelFrame(self, text=Download URLs)
        links_frame.pack(fill=x, padx=6, pady=(6, 0))

        # Link controls
        link_controls = ttk.Frame(links_frame)
        link_controls.pack(fill=x, padx=6, pady=(6, 0))

        ttk.Button(link_controls, text=Paste, command=self._paste_links).pack(side=left, padx=(0, 5))
        ttk.Button(link_controls, text=Clear, command=self._clear_links).pack(side=left)
        ttk.Button(link_controls, text=Load, command=self._load_links).pack(side=left, padx=5)
        ttk.Button(link_controls, text=Save, command=self._save_links).pack(side=left)

        # Create frame for the links textbox with a scrollbar
        links_text_frame = ttk.Frame(links_frame)
        links_text_frame.pack(fill=both, expand=False, padx=6, pady=6)

        # Add scrollbar for links
        links_scrollbar = ttk.Scrollbar(links_text_frame)
        links_scrollbar.pack(side=right, fill=y)

        # Create and configure the links text box
        self.links_box = tk.Text(links_text_frame, width=80, height=8, yscrollcommand=links_scrollbar.set)
        self.links_box.pack(side=left, fill=both, expand=True)
        links_scrollbar.config(command=self.links_box.yview)

        # Load previously saved links if available
        self.links_file = DATA_DIR  flinks_instance_{idx + 1}.txt
        if self.links_file.exists()
            self.links_box.insert(1.0, self.links_file.read_text())

        # Options frame
        options_frame = ttk.LabelFrame(self, text=Download Options)
        options_frame.pack(fill=x, padx=6, pady=6)

        # Output directory
        dir_row = ttk.Frame(options_frame)
        dir_row.pack(fill=x, padx=6, pady=(6, 3))
        ttk.Label(dir_row, text=Output directory).pack(side=left)
        self.output_dir_var = tk.StringVar(value=str(Path.home()  Downloads))
        ttk.Entry(dir_row, textvariable=self.output_dir_var, width=40).pack(side=left, padx=4, expand=True, fill=x)
        ttk.Button(dir_row, text=…, command=self._choose_output_dir).pack(side=left)

        # Archive
        archive_row = ttk.Frame(options_frame)
        archive_row.pack(fill=x, padx=6, pady=3)
        ttk.Label(archive_row, text=Archive file).pack(side=left)
        self.archive_var = tk.StringVar(value=str(DATA_DIR  farchive_instance_{idx + 1}.txt))
        ttk.Entry(archive_row, textvariable=self.archive_var, width=40).pack(side=left, padx=4, expand=True, fill=x)
        ttk.Button(archive_row, text=…, command=self._choose_archive).pack(side=left)

        # Filter options
        filter_row = ttk.Frame(options_frame)
        filter_row.pack(fill=x, padx=6, pady=3)
        ttk.Label(filter_row, text=Content filters).pack(side=left)

        # Create checkbuttons for common filters
        self.images_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_row, text=Images, variable=self.images_var).pack(side=left, padx=(10, 5))

        self.videos_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_row, text=Videos, variable=self.videos_var).pack(side=left, padx=5)

        self.other_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(filter_row, text=Other Files, variable=self.other_var).pack(side=left, padx=5)
        
        # Video prioritization option (especially for coomer.su)
        # Video prioritization feature removed

        # Custom filter
        custom_filter_row = ttk.Frame(options_frame)
        custom_filter_row.pack(fill=x, padx=6, pady=3)
        ttk.Label(custom_filter_row, text=Custom filter).pack(side=left)
        self.custom_filter_var = tk.StringVar()
        ttk.Entry(custom_filter_row, textvariable=self.custom_filter_var, width=40).pack(side=left, padx=4,
                                                                                         expand=True, fill=x)

        # Additional options
        opts_row = ttk.Frame(options_frame)
        opts_row.pack(fill=x, padx=6, pady=(3, 6))
        ttk.Label(opts_row, text=Additional options).pack(side=left)
        self.additional_opts_var = tk.StringVar()
        ttk.Entry(opts_row, textvariable=self.additional_opts_var, width=40).pack(side=left, padx=4, expand=True,
                                                                                  fill=x)

        # Controls frame
        controls_frame = ttk.LabelFrame(self, text=Controls)
        controls_frame.pack(fill=x, padx=6, pady=6)

        # Buttons
        btns = ttk.Frame(controls_frame)
        btns.pack(fill=x, padx=6, pady=6)
        self.start_btn = ttk.Button(btns, text=Run, command=self.start)
        self.start_btn.pack(side=left)
        self.stop_btn = ttk.Button(btns, text=Stop, command=self.stop, state=disabled)
        self.stop_btn.pack(side=left, padx=6)

        # Auto-restart checkbox
        ttk.Checkbutton(btns, text=Auto-restart on exit, variable=self.auto_restart).pack(side=left, padx=6)

        # Status label
        ttk.Label(btns, textvariable=self.status_var).pack(side=right)

        # Log
        log_frame = ttk.LabelFrame(self, text=Instance Log)
        log_frame.pack(fill=both, expand=True, padx=6, pady=(0, 6))

        log_control = ttk.Frame(log_frame)
        log_control.pack(fill=x, padx=6, pady=(6, 0))
        ttk.Button(log_control, text=Clear, command=self._clear_log).pack(side=left)
        ttk.Button(log_control, text=Save, command=self._save_log).pack(side=left, padx=5)

        # Create frame for the log textbox with a scrollbar
        log_text_frame = ttk.Frame(log_frame)
        log_text_frame.pack(fill=both, expand=True, padx=6, pady=6)

        # Add scrollbar for log
        log_scrollbar = ttk.Scrollbar(log_text_frame)
        log_scrollbar.pack(side=right, fill=y)

        # Create and configure the log text box
        self.log_box = tk.Text(log_text_frame, width=80, height=10, state=disabled, yscrollcommand=log_scrollbar.set)
        self.log_box.pack(side=left, fill=both, expand=True)
        log_scrollbar.config(command=self.log_box.yview)

        # Load saved settings
        self._load_settings()

    # Settings management ---------------------------------------------------
    def _save_settings(self)
        Save instance settings to a JSON file
        settings = {
            output_dir self.output_dir_var.get(),
            archive_file self.archive_var.get(),
            additional_opts self.additional_opts_var.get(),
            auto_restart self.auto_restart.get(),
            images self.images_var.get(),
            videos self.videos_var.get(),
            other self.other_var.get(),
            custom_filter self.custom_filter_var.get()
        }

        settings_file = DATA_DIR  fsettings_instance_{self.idx + 1}.json
        try
            with open(settings_file, 'w', encoding='utf-8') as f
                json.dump(settings, f, indent=2)
        except Exception as e
            self.log_callback(f[Inst {self.idx + 1}] Error saving settings {e}n)

    def _load_settings(self)
        Load instance settings from a JSON file
        settings_file = DATA_DIR  fsettings_instance_{self.idx + 1}.json
        if not settings_file.exists()
            return

        try
            with open(settings_file, 'r', encoding='utf-8') as f
                settings = json.load(f)

            if output_dir in settings
                self.output_dir_var.set(settings[output_dir])
            if archive_file in settings
                self.archive_var.set(settings[archive_file])
            if additional_opts in settings
                self.additional_opts_var.set(settings[additional_opts])
            if auto_restart in settings
                self.auto_restart.set(settings[auto_restart])
            if images in settings
                self.images_var.set(settings[images])
            if videos in settings
                self.videos_var.set(settings[videos])
            if other in settings
                self.other_var.set(settings[other])
            if custom_filter in settings
                self.custom_filter_var.set(settings[custom_filter])
        except Exception as e
            self.log_callback(f[Inst {self.idx + 1}] Error loading settings {e}n)

    # Helper methods --------------------------------------------------------
    def _choose_output_dir(self)
        Choose output directory using file dialog
        path = filedialog.askdirectory(initialdir=self.output_dir_var.get(), title=Select output directory)
        if path
            self.output_dir_var.set(path)
            self._save_settings()

    def _choose_archive(self)
        Choose archive file using file dialog
        path = filedialog.asksaveasfilename(
            initialfile=self.archive_var.get(),
            title=Select archive file,
            filetypes=[(Text files, .txt), (All files, .)]
        )
        if path
            self.archive_var.set(path)
            self._save_settings()

    def _set_tab_status(self, running bool)
        Update tab appearance based on running status
        symbol = ● if running else ✓
        self.master.tab(self, text=fInstance {self.idx + 1} {symbol})
        if running
            self.status_var.set(Running)
        else
            self.status_var.set(Ready)

    def _enqueue_output(self, pipe)
        Read output from subprocess and add to queue
        if pipe is None
            return
            
        try
            # Print a confirmation message that we're capturing output
            self._append_log(Reading gallery-dl output...n)
            
            with pipe
                for raw in iter(pipe.readline, b)
                    try
                        txt = raw.decode('utf-8', errors='replace').rstrip()
                        
                        # Add to queue for UI display
                        self.q.put(txt)
                        
                        # Also immediately append to log for instant feedback
                        self._append_log(f{txt}n)
                        
                        # Log to unified log
                        self.log_callback(f[Inst {self.idx + 1}] {txt})
                    except Exception as e
                        # Make sure we catch any errors in output processing
                        err_msg = fError processing output {e}n
                        self.log_callback(f[Inst {self.idx + 1}] {err_msg})
                        self._append_log(err_msg)
        except Exception as e
            # Catch any errors with the pipe itself
            err_msg = fError reading from process {e}n
            self.log_callback(f[Inst {self.idx + 1}] {err_msg})
            self._append_log(err_msg)

    def _parse_download_info(self, line str)
        Parse download information from gallery-dl output
        try
            # Try to extract speed information
            if [download] in line
                speed_match = re.search(r([0-9.]+[KMG]iBs), line)
                if speed_match
                    speed_str = speed_match.group(1)
                    speed_val = 0.0

                    if KiBs in speed_str
                        speed_val = float(re.search(r([0-9.]+), speed_str).group(1))  1024
                    elif MiBs in speed_str
                        speed_val = float(re.search(r([0-9.]+), speed_str).group(1))  1024  1024
                    elif GiBs in speed_str
                        speed_val = float(re.search(r([0-9.]+), speed_str).group(1))  1024  1024  1024
                    
                    self.current_speed = speed_val
        except Exception as e
            # Silently ignore parsing errors
            pass
            
    def _drain_queue(self)
        Process and display queued gallery-dl output
        try
            while True
                line = self.q.get_nowait()
                if isinstance(line, bytes)
                    try
                        line = line.decode('utf-8', errors='replace').rstrip()
                    except UnicodeDecodeError
                        line = str(line).rstrip()
                
                self.total_downloaded += 1
                
                # Handle JSON events (if --print-json used)
                if line.startswith('{') and line.endswith('}')
                    try
                        event = json.loads(line)
                        # Only record completed downloads
                        if event.get('status') == 'finished'
                            dest = event.get('filename') or event.get('file', '')
                            url = event.get('url', '')
                            file_type = Path(dest).suffix.lstrip('.').lower() if dest else ''
                            if DownloadHistoryFrame.instance
                                DownloadHistoryFrame.instance.add_download_entry(self.idx, url, file_type)
                    except Exception
                        pass
                
                # Handle text-based Destination lines
                dest_match = re.search(r'Destination (.+)$', line)
                if dest_match
                    dest = dest_match.group(1)
                    file_type = dest.rsplit('.', 1)[1].lower() if '.' in dest else ''
                    if DownloadHistoryFrame.instance
                        DownloadHistoryFrame.instance.add_download_entry(self.idx, dest, file_type)
                
                # Update the log with proper formatting
                self._append_log(f{line}n)
                
        except queue.Empty
            pass
            
        if self.is_running()
            # Process still running, check back in 100ms
            self.after_id = self.after(100, self._drain_queue)
        else
            # Process has ended
            
            # Prioritized mode handling removed
            
            # Regular process completion (or end of phase 2)
            self.start_btn.config(state=normal)
            self.stop_btn.config(state=disabled)
            self._set_tab_status(False)  # Update tab appearance
            self.status_var.set(Ready)
            self.after_id = None
            
            # Reset current speed
            self.current_speed = 0.0
            
            # Auto-restart if enabled
            if self.auto_restart.get() and self.proc is not None
                self.start()
                
    def stop(self)
        Stop the gallery-dl process
        if not self.is_running()
            return
            
        try
            self._append_log(Stopping download process...n)
            self.log_callback(f[Inst {self.idx + 1}] Stopping processn)
            
            # Store the auto-restart setting temporarily and disable it for manual stop
            old_auto_restart = self.auto_restart.get()
            self.auto_restart.set(False)
            
            # Terminate the process
            if platform.system() == Windows
                self.proc.terminate()
            else
                self.proc.terminate()
                
            # Wait for up to 1 second for process to terminate
            for _ in range(10)
                if not self.is_running()
                    break
                time.sleep(0.1)
                
            # Force kill if still running
            if self.is_running()
                self._append_log(Process not responding, force killing...n)
                if platform.system() == Windows
                    subprocess.run([taskkill, F, T, PID, str(self.proc.pid)],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                else
                    self.proc.kill()
            
            # Restore auto-restart setting for next run
            self.auto_restart.set(old_auto_restart)
            
        except Exception as e
            self._append_log(fError stopping process {e}n)

    def _save_links(self)
        Save links to a file
        try
            links = self.links_box.get(1.0, end).rstrip()
            self.links_file.write_text(links)
            self.log_callback(f[Inst {self.idx + 1}] Links saved to {self.links_file}n)
        except OSError as e
            messagebox.showwarning(Save failed, fCould not write {self.links_file} {e})

    def _load_links(self)
        Load links from a file
        file_path = filedialog.askopenfilename(
            title=Select links file,
            filetypes=[(Text files, .txt), (All files, .)],
            initialdir=DATA_DIR
        )
        if file_path
            try
                with open(file_path, 'r', encoding='utf-8') as f
                    content = f.read()
                self.links_box.delete(1.0, end)
                self.links_box.insert(1.0, content)
                self.log_callback(f[Inst {self.idx + 1}] Links loaded from {file_path}n)
            except Exception as e
                messagebox.showerror(Load failed, fCould not read {file_path} {e})

    def _paste_links(self)
        Paste links from clipboard
        try
            content = self.clipboard_get()
            if content
                current_pos = self.links_box.index(insert)
                self.links_box.insert(current_pos, content)
        except tk.TclError
            pass  # No content in clipboard

    def _clear_links(self)
        Clear links text box
        if messagebox.askyesno(Confirm, Clear all links)
            self.links_box.delete(1.0, end)

    def _append_log(self, msg)
        Append a message to the log
        self.log_box.config(state=normal)
        self.log_box.insert(end, msg)
        self.log_box.see(end)
        self.log_box.config(state=disabled)
        
        # Keep the UI responsive
        self.update()

    def _clear_log(self)
        Clear log text box
        self.log_box.config(state=normal)
        self.log_box.delete(1.0, end)
        self.log_box.config(state=disabled)

    def _save_log(self)
        Save log to a file
        filename = filedialog.asksaveasfilename(
            defaultextension=.log,
            filetypes=[(Log files, .log), (Text files, .txt), (All files, .)],
            initialdir=DATA_DIR,
            title=fSave Instance {self.idx + 1} Log
        )
        if filename
            try
                with open(filename, 'w', encoding='utf-8') as f
                    f.write(self.log_box.get(1.0, end))
                messagebox.showinfo(Success, fLog saved to {filename})
            except Exception as e
                messagebox.showerror(Error, fFailed to save log {e})

    # Public API ------------------------------------------------------------
    def is_running(self)
        Check if gallery-dl process is running
        return self.proc is not None and self.proc.poll() is None

    def start(self)
        Start gallery-dl process
        if self.is_running()
            messagebox.showinfo(Already running, This instance is already running)
            return

        # Get links
        links = [ln.strip() for ln in self.links_box.get(1.0, end).splitlines() if ln.strip()]
        if not links
            messagebox.showwarning(No links, Please add at least one link)
            return
            
        # Always do a regular single-phase download
        self._start_normal_download(links)
    
    def _start_normal_download(self, links)
        Start a normal gallery-dl process with all settings
        # Save links and settings
        self._save_links()
        self._save_settings()
        
        # Reset download stats and flags
        self.total_downloaded = 0
        self.current_speed = 0.0
        self._in_prioritized_mode = False
        self._all_urls_for_second_phase = None
        
        # Build command
        cmd = [gallery-dl]
        
        # Add global options
        cmd.extend(self.get_global_opts())
        
        # Add instance-specific options
        output_dir = self.output_dir_var.get()
        if output_dir
            cmd.extend([-d, output_dir])
            
        # Handle archive file
        archive_file = self.archive_var.get()
        if archive_file
            if archive_instance_ in archive_file and not archive_file.endswith(f_{self.idx + 1}.txt)
                archive_file = str(DATA_DIR  farchive_instance_{self.idx + 1}.txt)
                self.archive_var.set(archive_file)
                self.log_callback(f[Inst {self.idx + 1}] Using unique archive file {archive_file}n)
                
            cmd.extend([--download-archive, archive_file])
        
        # Add filter options
        filter_expressions = []
        
        # File type filters
        file_type_filters = []
        
        if self.images_var.get()
            file_type_filters.append(extension in ('jpg', 'jpeg', 'png', 'gif', 'webp'))
            
        if self.videos_var.get()
            file_type_filters.append(extension in ('mp4', 'webm', 'avi', 'mov', 'mkv'))
            
        if self.other_var.get()
            file_type_filters.append(extension not in ('jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'webm', 'avi', 'mov', 'mkv'))
            
        if file_type_filters
            if len(file_type_filters) == 1
                filter_expressions.append(file_type_filters[0])
            else
                filter_expressions.append(( +  or .join(file_type_filters) + ))
                
        # Custom filter
        custom_filter = self.custom_filter_var.get().strip()
        if custom_filter
            filter_expressions.append(f({custom_filter}))
            
        # Add combined filter to command
        if filter_expressions
            combined_filter =  and .join(filter_expressions)
            cmd.extend([--filter, combined_filter])
            
        # Add additional options
        additional_opts = self.additional_opts_var.get().strip()
        if additional_opts
            cmd.extend(shlex.split(additional_opts))
            
        # Clear log
        self.log_box.config(state=normal)
        self.log_box.delete(1.0, end)
        self.log_box.config(state=disabled)
        
        # Add links
        cmd.extend(links)
        
        # Log command
        cmd_str =  .join([str(item) for item in cmd])
        self.log_callback(f[Inst {self.idx + 1}] Starting gallery-dl {cmd_str}n)
        self._append_log(fStarting download with all settingsn{cmd_str})
        
        # Start process
        try
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                bufsize=1,
                text=False,  # Don't use text mode to get raw bytes for proper decoding
                shell=False,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == Windows else 0
            )
            
            # Log that the process is starting
            self._append_log(fProcess started with PID {self.proc.pid}n)
            
            # Start output reader thread
            threading.Thread(
                target=self._enqueue_output,
                args=(self.proc.stdout,),
                daemon=True
            ).start()
            
            # Start queue processing
            self._drain_queue()
            
            # Update UI
            self.start_btn.config(state=disabled)
            self.stop_btn.config(state=normal)
            self.status_var.set(Running)
            self._set_tab_status(True)
            
        except Exception as e
            self.log_callback(f[Inst {self.idx + 1}] Failed to start {e}n)
            messagebox.showerror(Start failed, fFailed to start gallery-dl {e})


# ... (rest of the code remains the same)
class DownloadHistoryFrame(ttk.Frame)
    # Class variable to store the single instance
    instance = None
    
    def __init__(self, master ttk.Notebook)
        super().__init__(master)

        # Store instance reference for global access
        DownloadHistoryFrame.instance = self

        # Initialize database if needed
        self.init_database()

        # Main container
        self.main_frame = ttk.Frame(self)
        self.main_frame.pack(fill=both, expand=True, padx=6, pady=6)

        # Statistics bar
        stats_frame = ttk.LabelFrame(self.main_frame, text=Download Statistics)
        stats_frame.pack(fill=x, padx=0, pady=(0, 6))

        stats_grid = ttk.Frame(stats_frame)
        stats_grid.pack(fill=x, padx=6, pady=6)

        # Total downloads
        ttk.Label(stats_grid, text=Total Downloads).grid(row=0, column=0, sticky=w, padx=5, pady=2)
        self.total_downloads_var = tk.StringVar(value=0)
        ttk.Label(stats_grid, textvariable=self.total_downloads_var).grid(row=0, column=1, sticky=w, padx=5, pady=2)

        # Success rate
        ttk.Label(stats_grid, text=Successful).grid(row=0, column=2, sticky=w, padx=5, pady=2)
        self.success_var = tk.StringVar(value=0 (0%))
        ttk.Label(stats_grid, textvariable=self.success_var).grid(row=0, column=3, sticky=w, padx=5, pady=2)

        # Active instances
        ttk.Label(stats_grid, text=Images).grid(row=1, column=0, sticky=w, padx=5, pady=2)
        self.images_var = tk.StringVar(value=0)
        ttk.Label(stats_grid, textvariable=self.images_var).grid(row=1, column=1, sticky=w, padx=5, pady=2)

        # Videos
        ttk.Label(stats_grid, text=Videos).grid(row=1, column=2, sticky=w, padx=5, pady=2)
        self.videos_var = tk.StringVar(value=0)
        ttk.Label(stats_grid, textvariable=self.videos_var).grid(row=1, column=3, sticky=w, padx=5, pady=2)

        # Create content area with treeview
        content_frame = ttk.Frame(self.main_frame)
        content_frame.pack(fill=both, expand=True, padx=0, pady=0)

        # Treeview with scrollbars
        tree_frame = ttk.Frame(content_frame)
        tree_frame.pack(fill=both, expand=True, side=left)

        # Create vertical scrollbar
        vsb = ttk.Scrollbar(tree_frame, orient=vertical)
        vsb.pack(fill=y, side=right)

        # Create horizontal scrollbar
        hsb = ttk.Scrollbar(tree_frame, orient=horizontal)
        hsb.pack(fill=x, side=bottom)

        # Create treeview
        self.tree = ttk.Treeview(tree_frame, selectmode=browse,
                                 yscrollcommand=vsb.set,
                                 xscrollcommand=hsb.set)
        self.tree.pack(fill=both, expand=True, side=left)

        # Configure scrollbars
        vsb.config(command=self.tree.yview)
        hsb.config(command=self.tree.xview)

        # Define columns
        self.tree[columns] = (timestamp, instance, url, type, status)

        # Format columns
        self.tree.column(#0, width=0, stretch=tk.NO)  # Hide first column
        self.tree.column(timestamp, width=150, anchor=w)
        self.tree.column(instance, width=80, anchor=center)
        self.tree.column(url, width=300, anchor=w)
        self.tree.column(type, width=80, anchor=center)
        self.tree.column(status, width=80, anchor=center)

        # Create headings
        self.tree.heading(#0, text=)
        self.tree.heading(timestamp, text=Timestamp)
        self.tree.heading(instance, text=Instance)
        self.tree.heading(url, text=URL)
        self.tree.heading(type, text=Type)
        self.tree.heading(status, text=Status)

        # Add some control buttons
        button_frame = ttk.Frame(self)
        button_frame.pack(fill=x, padx=6, pady=6)

        ttk.Button(button_frame, text=Refresh, command=self.refresh_history).pack(side=left, padx=(0, 5))
        ttk.Button(button_frame, text=Clear History, command=self.clear_history).pack(side=left)
        ttk.Button(button_frame, text=Export History, command=self.export_history).pack(side=right)

        # Initial refresh
        self.refresh_history()

    def init_database(self)
        Initialize the download history database
        db_dir = DATA_DIR  database
        db_dir.mkdir(exist_ok=True)

        db_file = db_dir  download_history.db

        try
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Create table if not exists
            cursor.execute('''
                        CREATE TABLE IF NOT EXISTS downloads (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            timestamp TEXT,
                            instance_id INTEGER,
                            url TEXT,
                            file_type TEXT,
                            status TEXT
                        )
                    ''')

            conn.commit()
            conn.close()
        except sqlite3.Error as e
            messagebox.showerror(Database Error, fError initializing database {e})

    def refresh_history(self)
        Refresh the download history view
        # Clear existing items
        for item in self.tree.get_children()
            self.tree.delete(item)

        try
            # Connect to database
            db_file = DATA_DIR  database  download_history.db
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            # Get recent downloads (most recent first)
            cursor.execute('''
                        SELECT timestamp, instance_id, url, file_type, status
                        FROM downloads
                        ORDER BY timestamp DESC
                        LIMIT 1000
                    ''')

            rows = cursor.fetchall()

            # Add to treeview
            for i, row in enumerate(rows)
                timestamp, instance_id, url, file_type, status = row
                self.tree.insert(, end, iid=str(i), values=(
                    timestamp,
                    fInstance {instance_id + 1},
                    url,
                    file_type or Unknown,
                    status
                ))

            # Update statistics
            self.update_statistics(cursor)

            conn.close()
        except sqlite3.Error as e
            messagebox.showerror(Database Error, fError refreshing history {e})

    def update_statistics(self, cursor)
        Update the statistics display
        try
            # Total downloads
            cursor.execute(SELECT COUNT() FROM downloads)
            total = cursor.fetchone()[0]
            self.total_downloads_var.set(str(total))

            # Successful downloads
            cursor.execute(SELECT COUNT() FROM downloads WHERE status = 'Success')
            success = cursor.fetchone()[0]
            success_rate = 0 if total == 0 else (success  total)  100
            self.success_var.set(f{success} ({success_rate.1f}%))

            # Image count
            cursor.execute(SELECT COUNT() FROM downloads WHERE file_type IN ('jpg', 'jpeg', 'png', 'gif', 'webp'))
            images = cursor.fetchone()[0]
            self.images_var.set(str(images))

            # Video count
            cursor.execute(SELECT COUNT() FROM downloads WHERE file_type IN ('mp4', 'webm', 'avi', 'mov', 'mkv'))
            videos = cursor.fetchone()[0]
            self.videos_var.set(str(videos))

        except sqlite3.Error as e
            messagebox.showerror(Database Error, fError updating statistics {e})

    def clear_history(self)
        Clear the download history
        if messagebox.askyesno(
                Confirm,
                Are you sure you want to clear all download history This cannot be undone.)
            try
                db_file = DATA_DIR  database  download_history.db
                conn = sqlite3.connect(db_file)
                cursor = conn.cursor()

                cursor.execute(DELETE FROM downloads)
                conn.commit()
                conn.close()

                self.refresh_history()
                messagebox.showinfo(Success, Download history cleared)
            except sqlite3.Error as e
                messagebox.showerror(Database Error, fError clearing history {e})

    def add_download_entry(self, instance_id, url, file_type, status=Success)
        Add a new download entry to the history database
        
        Args
            instance_id The instance ID (0-based)
            url The URL that was downloaded
            file_type The file type (extension) of the downloaded file
            status The download status (default Success)
        
        try
            # Connect to database
            db_file = DATA_DIR  database  download_history.db
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()
            
            # Current timestamp
            timestamp = datetime.now().strftime(TIMESTAMP_FMT)
            
            # Insert the new download entry
            cursor.execute(
                INSERT INTO downloads (timestamp, instance_id, url, file_type, status)
                VALUES (, , , , )
            , (timestamp, instance_id, url, file_type, status))
            
            conn.commit()
            conn.close()
            
            # Auto-refresh history view
            self.refresh_history()
                
        except sqlite3.Error as e
            print(fError adding download to history {e})
    
    def export_history(self)
        Export download history to CSV file
        filename = filedialog.asksaveasfilename(
            defaultextension=.csv,
            filetypes=[(CSV files, .csv), (Text files, .txt), (All files, .)],
            initialdir=DATA_DIR,
            title=Export Download History
        )

        if not filename
            return

        try
            db_file = DATA_DIR  database  download_history.db
            conn = sqlite3.connect(db_file)
            cursor = conn.cursor()

            cursor.execute('''
                        SELECT timestamp, instance_id, url, file_type, status
                        FROM downloads
                        ORDER BY timestamp DESC
                    ''')

            rows = cursor.fetchall()

            with open(filename, 'w', newline='') as csvfile
                writer = csv.writer(csvfile)
                writer.writerow([Timestamp, Instance, URL, File Type, Status])

                for row in rows
                    timestamp, instance_id, url, file_type, status = row
                    writer.writerow([timestamp, fInstance {instance_id + 1}, url, file_type or Unknown, status])

            conn.close()
            messagebox.showinfo(Success, fDownload history exported to {filename})
        except Exception as e
            messagebox.showerror(Export Error, fFailed to export history {e})

# ──────────────────────────────────────────────────────────────────────────────
# HTTP Server for browser extension integration
# ──────────────────────────────────────────────────────────────────────────────
class GalleryDLHandler(http.server.BaseHTTPRequestHandler)
    unified_links_frame = None  # Will be set by the main app
    
    def do_OPTIONS(self)
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
    
    def do_GET(self)
        # Serve the extension receiver HTML file
        if self.path == '' or self.path == 'index.html'
            self.send_response(200)
            self.send_header('Content-type', 'texthtml')
            self.end_headers()
            
            with open(Path(__file__).parent  'extension_receiver.html', 'rb') as f
                self.wfile.write(f.read())
        else
            self.send_response(404)
            self.send_header('Content-type', 'textplain')
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self)
        # Handle URL submission from extension
        if self.path == 'add-url'
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try
                data = json.loads(post_data.decode('utf-8'))
                url = data.get('url', '').strip()
                
                if url and self.unified_links_frame
                    # Set the URL in the entry and trigger the quick add
                    self.unified_links_frame.new_url_var.set(url)
                    
                    # Use after_idle to ensure this runs in the main thread
                    self.unified_links_frame.after_idle(self.unified_links_frame.quick_add_url)
                    
                    response = {'status' 'success', 'message' f'URL added to gallery-dl queue'}
                else
                    response = {'status' 'error', 'message' 'Invalid URL or application not ready'}
            except Exception as e
                response = {'status' 'error', 'message' f'Error processing request {str(e)}'}
            
            self.send_response(200)
            self.send_header('Content-type', 'applicationjson')
            self.send_header('Access-Control-Allow-Origin', '')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode('utf-8'))
        else
            self.send_response(404)
            self.send_header('Content-type', 'textplain')
            self.end_headers()
            self.wfile.write(b'Not Found')
            
    def log_message(self, format, args)
        # Silence the HTTP server logs
        pass

class HTTPServerThread(threading.Thread)
    def __init__(self, unified_links_frame)
        super().__init__(daemon=True)
        self.unified_links_frame = unified_links_frame
        self.server = None
        self.port = 6580  # Default port
        
    def run(self)
        # Set the handler class to use our frame
        GalleryDLHandler.unified_links_frame = self.unified_links_frame
        
        # Try to start the server on the default port, if it fails, try another port
        max_attempts = 5
        for attempt in range(max_attempts)
            try
                self.server = socketserver.TCPServer(('localhost', self.port), GalleryDLHandler)
                print(fBrowser extension server started on port {self.port})
                self.server.serve_forever()
                break
            except OSError
                # Port is in use, try the next one
                self.port += 1
                
                if attempt == max_attempts - 1
                    print(Failed to start browser extension server all ports in use)
                    return

    def stop(self)
        if self.server
            self.server.shutdown()
            self.server.server_close()

# ──────────────────────────────────────────────────────────────────────────────
# Main application
# ──────────────────────────────────────────────────────────────────────────────
class Application(tk.Tk)
    def __init__(self)
        super().__init__()
        self.title(Gallery-DL Launcher)
        self.geometry(900x700)

        # Make the window resizable
        self.minsize(800, 600)

        # Try to set a nicer theme if available
        try
            self.tk_setPalette(background='#f0f0f0', foreground='#000000')
        except Exception
            pass  # If theme setting fails, continue with default theme
            
        # Configure window icon if available
        try
            if platform.system() == Windows
                self.iconbitmap(default=)  # Replace with path to .ico file if available
            else
                # For LinuxmacOS systems
                pass
        except Exception
            pass  # Icon loading is non-critical

        # Set up the notebook
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=both, expand=True, padx=4, pady=4)

        # Create the configuration tab
        self.config_frame = ConfigFrame(self.notebook)
        self.notebook.add(self.config_frame, text=Global Config)

        # Create unified log tab
        self.log_frame = UnifiedLogFrame(self.notebook)
        self.notebook.add(self.log_frame, text=Unified Log)

        # Create instances
        self.instances list[InstanceFrame] = []
        self.num_instances = self._load_instance_count()

        # Create initial instances (at least 3)
        self.ensure_instances(max(3, self.num_instances))

        # Create unified links tab
        self.links_frame = UnifiedLinksFrame(self.notebook, self.get_instances)
        self.notebook.add(self.links_frame, text=All Links)

        # Create download history tab
        self.history_frame = DownloadHistoryFrame(self.notebook)
        self.notebook.add(self.history_frame, text=Download History)

        # Create menu
        self.create_menu()

        # Set up status bar
        self.status_var = tk.StringVar(value=Ready)
        self.status_bar = ttk.Label(self, textvariable=self.status_var, relief=sunken, anchor=w)
        self.status_bar.pack(side=bottom, fill=x)

        # Auto-save on close
        self.protocol(WM_DELETE_WINDOW, self.on_close)

        # Periodically refresh links view
        self._schedule_links_refresh()

        # Log startup
        self.log_frame.append(Gallery-DL Launcher startedn)

        # Start the HTTP server for browser extension integration
        self.http_server_thread = HTTPServerThread(self.links_frame)
        self.http_server_thread.start()

    # ... (rest of the code remains the same)

    def on_close(self)
        Handle application close
        # Ask for confirmation if any instance is running
        running_count = sum(1 for inst in self.instances if inst.is_running())
        if running_count  0
            if not messagebox.askyesno(
                    Confirm Exit,
                    fThere are {running_count} running instances. Do you want to exit anyway
            )
                return

        # Stop all instances
        self.stop_all()

        # Save all settings
        self.save_all()

        # Stop the HTTP server
        self.http_server_thread.stop()

        # Close the window
        self.destroy()
        
    def _load_instance_count(self)
        Load the saved instance count
        count_file = DATA_DIR  instance_count.txt
        if count_file.exists()
            try
                return int(count_file.read_text().strip())
            except (ValueError, OSError)
                pass
        return 3  # Default count
    
    def _save_instance_count(self)
        Save the current instance count
        count_file = DATA_DIR  instance_count.txt
        try
            count_file.write_text(str(len(self.instances)))
        except OSError
            pass
            
    def _schedule_links_refresh(self)
        Schedule periodic refresh of the links view
        self.links_frame.refresh()
        self.after(30000, self._schedule_links_refresh)
        
    def get_instances(self) - list[InstanceFrame]
        Get all instance frames
        return self.instances
        
    def add_instance(self)
        Add a new instance tab
        idx = len(self.instances)
        instance = InstanceFrame(
            self.notebook,
            idx,
            self.config_frame.get_tokens,
            self.log_frame.append
        )
        self.notebook.add(instance, text=fInstance {idx + 1} ✓)
        self.instances.append(instance)
        self.notebook.select(instance)
        self._save_instance_count()
        self.log_frame.append(fAdded Instance {idx + 1}n)
        
    def ensure_instances(self, count int)
        Ensure at least 'count' instances exist
        while len(self.instances)  count
            self.add_instance()
            
    def save_all(self)
        Save all configuration and instance data
        # Save global config
        self.config_frame.save()

        # Save links for each instance
        for inst in self.instances
            try
                # Save links
                links = inst.links_box.get(1.0, end).rstrip()
                inst.links_file.write_text(links)

                # Save settings
                inst._save_settings()
            except OSError
                pass

        self.status_var.set(All settings saved)
        self.log_frame.append(All settings savedn)
        
    def run_all(self)
        Start all instances with a slight delay between each
        for idx, inst in enumerate(self.instances)
            if not inst.is_running()
                self.after(idx  1000, lambda i=inst i.start())  # Start with 1 second delay between instances
                self.update()  # Force UI update

    def stop_all(self)
        Stop all running instances with a slight delay between each
        for idx, inst in enumerate(self.instances)
            if inst.is_running()
                self.after(idx  500, lambda i=inst i.stop())  # Stop with 0.5 second delay between instances
                self.update()  # Force UI update
                
    def create_menu(self)
        Create application menu
        menubar = tk.Menu(self)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label=Save All, command=self.save_all)
        file_menu.add_separator()
        file_menu.add_command(label=Exit, command=self.on_close)
        menubar.add_cascade(label=File, menu=file_menu)

        # Instances menu
        instances_menu = tk.Menu(menubar, tearoff=0)
        instances_menu.add_command(label=New Instance, command=self.add_instance)
        instances_menu.add_command(label=Run All, command=self.run_all)
        instances_menu.add_command(label=Stop All, command=self.stop_all)
        menubar.add_cascade(label=Instances, menu=instances_menu)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label=Check Gallery-DL Version, command=self.check_version)
        tools_menu.add_command(label=Open Data Directory, command=self.open_data_dir)
        menubar.add_cascade(label=Tools, menu=tools_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label=About, command=self.show_about)
        help_menu.add_command(label=Gallery-DL Documentation, command=self.open_docs)
        menubar.add_cascade(label=Help, menu=help_menu)

        self.config(menu=menubar)
        
    def check_version(self)
        Check gallery-dl version
        try
            proc = subprocess.Popen(
                [gallery-dl, --version],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            output, _ = proc.communicate()
            version_text = output.strip()
            messagebox.showinfo(Gallery-DL Version, version_text)
            self.log_frame.append(fGallery-DL version {version_text}n)

            # Check if we need to display a hint about command-line options
            if version_text
                self.log_frame.append(Hint For a list of command-line options, run gallery-dl --helpn)

        except Exception as e
            error_msg = fError checking gallery-dl version {e}
            messagebox.showerror(Error, error_msg)
            self.log_frame.append(f{error_msg}n)

            # Check if gallery-dl is installed
            if isinstance(e, FileNotFoundError)
                self.log_frame.append(Gallery-dl does not appear to be installed or is not in your PATH.n)
                self.log_frame.append(Visit httpsgithub.commikfgallery-dl for installation instructions.n)
                messagebox.showerror(Gallery-DL Not Found,
                                    Gallery-dl does not appear to be installed or is not in your PATH.nn
                                    Please install gallery-dl firstn
                                    pip install gallery-dlnn
                                    Visit httpsgithub.commikfgallery-dl for more information.)
    
    def open_data_dir(self)
        Open the data directory in file explorer
        try
            if platform.system() == Windows
                os.startfile(DATA_DIR)
            elif platform.system() == Darwin  # macOS
                subprocess.run([open, DATA_DIR])
            else  # Linux and other Unix-like
                subprocess.run([xdg-open, DATA_DIR])
            self.log_frame.append(fOpened data directory {DATA_DIR}n)
        except Exception as e
            self.log_frame.append(fError opening data directory {e}n)
            
    def show_about(self)
        Show about dialog
        about_text = Gallery-DL Launcher

        A graphical interface for managing multiple gallery-dl downloads.

        Features
        - Multiple download instances 
        - Custom content filters
        - Smart URL distribution
        - Download history tracking
        - URL management and search
        - Browser extension integration

        gallery-dl is a command-line program to download image galleries and 
        collections from various websites.

        This launcher allows you to manage multiple download instances with 
        different configurations.
        
        messagebox.showinfo(About Gallery-DL Launcher, about_text)

    def open_docs(self)
        Open gallery-dl documentation in web browser
        url = httpsgithub.commikfgallery-dlblobmasterREADME.rst
        webbrowser.open(url)
        self.log_frame.append(fOpened documentation {url}n)


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────
def main()
    # Create data directory if it doesn't exist
    DATA_DIR.mkdir(exist_ok=True)

    # Create database directory
    db_dir = DATA_DIR  database
    db_dir.mkdir(exist_ok=True)

    # Import csv for export functionality
    try
        import csv
    except ImportError
        print(CSV module not available)

    # Start application
    app = Application()
    app.mainloop()


if __name__ == __main__
    main()