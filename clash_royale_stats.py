#!/usr/bin/env python3
"""
Clash Royale Statistics App
A macOS application to view clan and player statistics from the Clash Royale API.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext, font as tkfont
import urllib.request
import urllib.parse
import urllib.error
import json
import os
import platform
from datetime import datetime
from typing import Optional, Dict, Any, List
from ctypes import cdll, c_void_p, c_bool, c_char_p, byref

from PIL import Image, ImageTk

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.ticker
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


def load_custom_font(font_path: str) -> bool:
    """Load a custom font file on macOS."""
    if platform.system() != 'Darwin':
        return False

    try:
        # Load Core Text framework
        ct = cdll.LoadLibrary('/System/Library/Frameworks/CoreText.framework/CoreText')

        # Create CFString for the font path
        cf = cdll.LoadLibrary('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        cf.CFStringCreateWithCString.restype = c_void_p
        cf.CFStringCreateWithCString.argtypes = [c_void_p, c_char_p, c_void_p]

        # Create CFURL from path
        cf.CFURLCreateWithFileSystemPath.restype = c_void_p
        cf.CFURLCreateWithFileSystemPath.argtypes = [c_void_p, c_void_p, c_void_p, c_bool]

        path_str = cf.CFStringCreateWithCString(None, font_path.encode('utf-8'), 0x08000100)
        url = cf.CFURLCreateWithFileSystemPath(None, path_str, 0, False)

        # Register the font
        ct.CTFontManagerRegisterFontsForURL.restype = c_bool
        ct.CTFontManagerRegisterFontsForURL.argtypes = [c_void_p, c_void_p, c_void_p]

        result = ct.CTFontManagerRegisterFontsForURL(url, 1, None)
        return result
    except Exception:
        return False

# Clash Royale Theme Colors
THEME = {
    'bg_dark': '#1E3A5F',        # Dark blue background
    'bg_medium': '#2B5278',      # Medium blue
    'bg_light': '#3B6B8C',       # Light blue
    'gold': '#D4A84B',           # Gold accent
    'gold_light': '#E8C252',     # Light gold
    'gold_dark': '#B8860B',      # Dark gold
    'text_light': '#FFFFFF',     # White text
    'text_primary': '#E0E0E0',   # Light grey text (easier to read)
    'text_secondary': '#B0B0B0', # Secondary text
    'crown_blue': '#4A90D9',     # Shield blue
    'success': '#28A745',        # Green for 1st place
    'warning': '#FFC107',        # Yellow for 2nd place
    'info': '#17A2B8',           # Cyan for 3rd place
    'danger': '#DC3545',         # Red for 4th+ place
}


class ClashRoyaleAPI:
    """Client for the Clash Royale API."""

    BASE_URL = "https://api.clashroyale.com/v1"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _make_request(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Make an authenticated request to the API."""
        url = f"{self.BASE_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json"
        }

        request = urllib.request.Request(url, headers=headers)

        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode())
        except urllib.error.HTTPError as e:
            error_body = e.read().decode()
            try:
                error_json = json.loads(error_body)
                raise Exception(f"API Error: {error_json.get('message', str(e))}")
            except json.JSONDecodeError:
                raise Exception(f"HTTP Error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise Exception(f"Connection Error: {e.reason}")
        except Exception as e:
            raise Exception(f"Request failed: {str(e)}")

    def get_clan(self, clan_tag: str) -> Dict[str, Any]:
        """Get clan information by tag."""
        encoded_tag = urllib.parse.quote(clan_tag, safe='')
        return self._make_request(f"/clans/{encoded_tag}")

    def get_clan_members(self, clan_tag: str) -> Dict[str, Any]:
        """Get clan members list."""
        encoded_tag = urllib.parse.quote(clan_tag, safe='')
        return self._make_request(f"/clans/{encoded_tag}/members")

    def get_clan_river_race(self, clan_tag: str) -> Dict[str, Any]:
        """Get current river race (clan war) info."""
        encoded_tag = urllib.parse.quote(clan_tag, safe='')
        return self._make_request(f"/clans/{encoded_tag}/currentriverrace")

    def get_clan_river_race_log(self, clan_tag: str) -> Dict[str, Any]:
        """Get past river race (clan war) history."""
        encoded_tag = urllib.parse.quote(clan_tag, safe='')
        return self._make_request(f"/clans/{encoded_tag}/riverracelog")

    def get_clan_war_log(self, clan_tag: str) -> Dict[str, Any]:
        """Get clan war log."""
        encoded_tag = urllib.parse.quote(clan_tag, safe='')
        return self._make_request(f"/clans/{encoded_tag}/warlog")

    def get_player(self, player_tag: str) -> Dict[str, Any]:
        """Get player information by tag."""
        encoded_tag = urllib.parse.quote(player_tag, safe='')
        return self._make_request(f"/players/{encoded_tag}")

    def get_player_battles(self, player_tag: str) -> list:
        """Get player's recent battles."""
        encoded_tag = urllib.parse.quote(player_tag, safe='')
        return self._make_request(f"/players/{encoded_tag}/battlelog")

    def get_player_chests(self, player_tag: str) -> Dict[str, Any]:
        """Get player's upcoming chests."""
        encoded_tag = urllib.parse.quote(player_tag, safe='')
        return self._make_request(f"/players/{encoded_tag}/upcomingchests")


class ClashRoyaleApp:
    """Main application class."""

    CONFIG_FILE = os.path.expanduser("~/.clash_royale_stats_config.json")

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Clash Royale Statistics")
        self.root.geometry("1100x800")
        self.root.minsize(1000, 700)
        self.root.configure(bg=THEME['bg_dark'])

        # Get the directory where the script is located
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Load custom Clash Royale font
        self.clash_font_loaded = False
        self._load_clash_font()

        # Configure themed style
        self._setup_theme()

        self.api: Optional[ClashRoyaleAPI] = None
        config = self._load_config()
        self.api_key = config.get('api_key')
        self.last_clan_tag = config.get('last_clan_tag', '')

        # Load logo
        self.logo_image = None
        self._load_logo()

        self._setup_ui()

        if self.api_key:
            self.api = ClashRoyaleAPI(self.api_key)

        if self.last_clan_tag:
            self.clan_tag_entry.insert(0, self.last_clan_tag)

    def _open_settings(self):
        """Open the settings dialog."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("500x200")
        settings_window.configure(bg=THEME['bg_dark'])
        settings_window.transient(self.root)
        settings_window.grab_set()

        # Center the window
        settings_window.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() - 500) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - 200) // 2
        settings_window.geometry(f"+{x}+{y}")

        # Settings content
        content_frame = ttk.Frame(settings_window, padding="20")
        content_frame.pack(fill=tk.BOTH, expand=True)

        # API Key section
        ttk.Label(content_frame, text="API Configuration", style='Gold.TLabel').pack(anchor=tk.W, pady=(0, 10))

        api_frame = ttk.Frame(content_frame)
        api_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(api_frame, text="API Key:").pack(side=tk.LEFT, padx=(0, 10))

        self.settings_api_entry = tk.Entry(api_frame, width=40, show="*",
                                           bg=THEME['bg_medium'], fg=THEME['text_light'],
                                           insertbackground=THEME['text_light'],
                                           relief=tk.FLAT, font=('Helvetica', 11))
        self.settings_api_entry.pack(side=tk.LEFT, padx=(0, 10), ipady=5)

        if self.api_key:
            self.settings_api_entry.insert(0, self.api_key)

        self.show_key_var = tk.BooleanVar()
        ttk.Checkbutton(api_frame, text="Show", variable=self.show_key_var,
                       command=lambda: self.settings_api_entry.config(
                           show="" if self.show_key_var.get() else "*")).pack(side=tk.LEFT)

        # Help text
        help_text = ttk.Label(content_frame,
                             text="Get your API key from developer.clashroyale.com",
                             font=('Helvetica', 10, 'italic'), foreground=THEME['text_secondary'])
        help_text.pack(anchor=tk.W, pady=(0, 20))

        # Buttons
        btn_frame = ttk.Frame(content_frame)
        btn_frame.pack(fill=tk.X)

        ttk.Button(btn_frame, text="Save", command=lambda: self._save_settings(settings_window)).pack(side=tk.RIGHT, padx=(10, 0))
        ttk.Button(btn_frame, text="Cancel", command=settings_window.destroy).pack(side=tk.RIGHT)

    def _save_settings(self, window):
        """Save settings from the dialog."""
        api_key = self.settings_api_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter an API key", parent=window)
            return

        self.api_key = api_key
        self.api = ClashRoyaleAPI(api_key)
        self._save_config(api_key=api_key)
        self.api_status_var.set("API Key: Configured")
        self.status_var.set("API key saved successfully")
        window.destroy()
        messagebox.showinfo("Success", "API key saved!")

    def _load_clash_font(self):
        """Load the custom Clash Royale font."""
        try:
            font_path = os.path.join(self.script_dir, 'assets', 'Clash_Regular.otf')
            if os.path.exists(font_path):
                self.clash_font_loaded = load_custom_font(font_path)
        except Exception:
            pass

    def _load_logo(self):
        """Load and resize the Clash Royale logo."""
        try:
            logo_path = os.path.join(self.script_dir, 'assets', 'Clash_Royale_Logo.png')
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                # Resize to fit header (height ~90px for larger logo)
                ratio = 90 / img.height
                new_size = (int(img.width * ratio), 90)
                img = img.resize(new_size, Image.Resampling.LANCZOS)
                self.logo_image = ImageTk.PhotoImage(img)
        except Exception:
            pass

    def _setup_theme(self):
        """Configure the ttk theme with Clash Royale colors."""
        self.style = ttk.Style()

        # Create custom fonts
        self.clash_font_name = 'Supercell-Magic' if self.clash_font_loaded else 'Helvetica'
        self.clash_font = tkfont.Font(family=self.clash_font_name, size=11)
        self.clash_font_large = tkfont.Font(family=self.clash_font_name, size=13)

        # Configure colors for various widgets
        self.style.configure('.',
                            background=THEME['bg_dark'],
                            foreground=THEME['text_primary'],
                            fieldbackground=THEME['bg_medium'])

        self.style.configure('TFrame', background=THEME['bg_dark'])
        self.style.configure('TLabel', background=THEME['bg_dark'], foreground=THEME['text_primary'])
        self.style.configure('TLabelframe', background=THEME['bg_dark'], foreground=THEME['gold'])
        self.style.configure('TLabelframe.Label', background=THEME['bg_dark'], foreground=THEME['gold'],
                            font=('Helvetica', 12, 'bold'))

        self.style.configure('TButton',
                            background=THEME['gold'],
                            foreground=THEME['bg_dark'],
                            font=('Helvetica', 11, 'bold'),
                            padding=(10, 5))
        self.style.map('TButton',
                      background=[('active', THEME['gold_light']), ('pressed', THEME['gold_dark'])])

        self.style.configure('TEntry',
                            fieldbackground=THEME['bg_medium'],
                            foreground=THEME['text_light'],
                            insertcolor=THEME['text_light'])

        self.style.configure('TCheckbutton',
                            background=THEME['bg_dark'],
                            foreground=THEME['text_primary'])

        # Make tabs more prominent and always visible
        self.style.configure('TNotebook', background=THEME['bg_dark'], borderwidth=0, tabmargins=[5, 5, 5, 0])
        self.style.configure('TNotebook.Tab',
                            background=THEME['bg_light'],
                            foreground=THEME['text_light'],
                            padding=(20, 10),
                            font=('Helvetica', 12, 'bold'))
        self.style.map('TNotebook.Tab',
                      background=[('selected', THEME['gold']), ('!selected', THEME['bg_medium'])],
                      foreground=[('selected', THEME['bg_dark']), ('!selected', THEME['text_primary'])],
                      expand=[('selected', [1, 1, 1, 0])])

        self.style.configure('Gold.TLabel',
                            background=THEME['bg_dark'],
                            foreground=THEME['gold'],
                            font=('Helvetica', 14, 'bold'))

        self.style.configure('Status.TLabel',
                            background=THEME['bg_medium'],
                            foreground=THEME['text_primary'],
                            font=('Helvetica', 10))

    def _load_config(self) -> Dict[str, Any]:
        """Load config from file."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def _save_config(self, **kwargs):
        """Save config values to file."""
        try:
            config = self._load_config()
            config.update(kwargs)
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not save config: {e}")

    def _setup_ui(self):
        """Set up the user interface."""
        # Main container
        main_frame = ttk.Frame(self.root, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Header with logo and settings button - compact layout
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 5))

        if self.logo_image:
            logo_label = ttk.Label(header_frame, image=self.logo_image, background=THEME['bg_dark'])
            logo_label.pack(side=tk.LEFT)

        # Settings button on the right
        settings_btn = ttk.Button(header_frame, text="Settings", command=self._open_settings)
        settings_btn.pack(side=tk.RIGHT, padx=(10, 0))

        # API key status indicator
        self.api_status_var = tk.StringVar(value="API Key: Not Set")
        if self.api_key:
            self.api_status_var.set("API Key: Configured")
        api_status_label = ttk.Label(header_frame, textvariable=self.api_status_var,
                                     font=('Helvetica', 10), foreground=THEME['text_secondary'])
        api_status_label.pack(side=tk.RIGHT, padx=(10, 0))

        # Search Section - compact single row
        search_frame = tk.Frame(main_frame, bg=THEME['bg_dark'])
        search_frame.pack(fill=tk.X, pady=(0, 5))

        # Clan search
        tk.Label(search_frame, text="Clan Tag:", bg=THEME['bg_dark'], fg=THEME['text_secondary'],
                 font=('Helvetica', 11)).pack(side=tk.LEFT, padx=(0, 5))
        self.clan_tag_entry = tk.Entry(search_frame, width=15,
                                       bg=THEME['bg_medium'], fg=THEME['text_light'],
                                       insertbackground=THEME['text_light'],
                                       relief=tk.FLAT, font=('Helvetica', 11))
        self.clan_tag_entry.pack(side=tk.LEFT, padx=(0, 5), ipady=3)
        ttk.Button(search_frame, text="Get Clan Stats", command=self._fetch_clan).pack(side=tk.LEFT, padx=(0, 20))

        # Player search
        tk.Label(search_frame, text="Player Tag:", bg=THEME['bg_dark'], fg=THEME['text_secondary'],
                 font=('Helvetica', 11)).pack(side=tk.LEFT, padx=(0, 5))
        self.player_tag_entry = tk.Entry(search_frame, width=15,
                                         bg=THEME['bg_medium'], fg=THEME['text_light'],
                                         insertbackground=THEME['text_light'],
                                         relief=tk.FLAT, font=('Helvetica', 11))
        self.player_tag_entry.pack(side=tk.LEFT, padx=(0, 5), ipady=3)
        ttk.Button(search_frame, text="Get Player Stats", command=self._fetch_player).pack(side=tk.LEFT, padx=(0, 10))

        # Hint inline
        hint_label = ttk.Label(search_frame, text="(Include #)",
                              font=('Helvetica', 9, 'italic'), foreground=THEME['text_secondary'])
        hint_label.pack(side=tk.LEFT)

        # Tab container (holds tab bar + content)
        tab_container = tk.Frame(main_frame, bg=THEME['bg_medium'])
        tab_container.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        # Custom tab bar frame - spans full width with background
        tab_bar_frame = tk.Frame(tab_container, bg=THEME['bg_medium'], height=45)
        tab_bar_frame.pack(fill=tk.X, side=tk.TOP)
        tab_bar_frame.pack_propagate(False)  # Keep fixed height

        # Tab buttons
        self.tab_buttons = []
        self.tab_frames = []
        tab_names = ["Clan Statistics", "Clan Members", "Player Statistics", "Battle Log"]

        for i, name in enumerate(tab_names):
            btn = tk.Button(tab_bar_frame, text=name,
                           font=('Helvetica', 12, 'bold'),
                           bg=THEME['bg_light'],
                           fg=THEME['text_primary'],
                           activebackground=THEME['gold'],
                           activeforeground=THEME['bg_dark'],
                           relief=tk.FLAT,
                           bd=0,
                           padx=20, pady=10,
                           cursor='hand2',
                           command=lambda idx=i: self._select_tab(idx))
            btn.pack(side=tk.LEFT, padx=(0, 2), pady=(5, 0))
            self.tab_buttons.append(btn)

        # Content container - below the tab bar
        self.content_frame = tk.Frame(tab_container, bg=THEME['bg_dark'])
        self.content_frame.pack(fill=tk.BOTH, expand=True)

        # Text widget styling
        text_config = {
            'bg': THEME['bg_medium'],
            'fg': THEME['text_primary'],
            'font': ('Menlo', 11),
            'relief': tk.FLAT,
            'insertbackground': THEME['text_light'],
            'selectbackground': THEME['gold'],
            'selectforeground': THEME['bg_dark'],
            'padx': 10,
            'pady': 10
        }

        # Clan Statistics tab (first)
        self.clan_frame = tk.Frame(self.content_frame, bg=THEME['bg_dark'], padx=10, pady=10)
        self.tab_frames.append(self.clan_frame)

        # Top: text stats
        self.clan_text_frame = tk.Frame(self.clan_frame, bg=THEME['bg_dark'])
        self.clan_text_frame.pack(fill=tk.BOTH, expand=True)

        self.clan_text = scrolledtext.ScrolledText(self.clan_text_frame, wrap=tk.WORD, height=12, **text_config)
        self.clan_text.pack(fill=tk.BOTH, expand=True)

        # Bottom: graph
        self.clan_graph_frame = tk.Frame(self.clan_frame, bg=THEME['bg_dark'])
        self.clan_graph_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.clan_canvas = None  # Will hold the matplotlib canvas

        # Clan Members tab (second)
        self.members_frame = tk.Frame(self.content_frame, bg=THEME['bg_dark'], padx=10, pady=10)
        self.tab_frames.append(self.members_frame)

        # Header label
        self.members_header = tk.Label(self.members_frame, text="CLAN MEMBERS",
                                       bg=THEME['bg_dark'], fg=THEME['gold'],
                                       font=('Helvetica', 14, 'bold'))
        self.members_header.pack(anchor=tk.W, pady=(0, 5))

        self.members_subheader = tk.Label(self.members_frame, text="Double-click a row to view player stats",
                                          bg=THEME['bg_dark'], fg=THEME['text_secondary'],
                                          font=('Helvetica', 10, 'italic'))
        self.members_subheader.pack(anchor=tk.W, pady=(0, 10))

        # Create Treeview with scrollbars
        tree_frame = tk.Frame(self.members_frame, bg=THEME['bg_dark'])
        tree_frame.pack(fill=tk.BOTH, expand=True)

        # Style the Treeview
        self.style.configure('Members.Treeview',
                            background=THEME['bg_medium'],
                            foreground=THEME['text_primary'],
                            fieldbackground=THEME['bg_medium'],
                            rowheight=25)
        self.style.configure('Members.Treeview.Heading',
                            background=THEME['bg_light'],
                            foreground=THEME['gold'],
                            font=('Helvetica', 10, 'bold'))
        self.style.map('Members.Treeview',
                      background=[('selected', THEME['gold'])],
                      foreground=[('selected', THEME['bg_dark'])])

        # Define columns
        self.members_columns = ('#', 'Name', 'Current', 'Avg', 'War-1', 'War-2', 'War-3', 'War-4', 'War-5', 'War-6', 'Role', 'Trophies', 'Donats', 'Last Seen')
        self.members_tree = ttk.Treeview(tree_frame, columns=self.members_columns, show='headings', style='Members.Treeview')

        # Scrollbars
        members_scrollbar_y = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.members_tree.yview)
        members_scrollbar_x = ttk.Scrollbar(tree_frame, orient=tk.HORIZONTAL, command=self.members_tree.xview)
        self.members_tree.configure(yscrollcommand=members_scrollbar_y.set, xscrollcommand=members_scrollbar_x.set)

        members_scrollbar_y.pack(side=tk.RIGHT, fill=tk.Y)
        members_scrollbar_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.members_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Bind click event for member names
        self.members_tree.bind('<Double-1>', self._on_member_tree_click)
        self.members_tree.bind('<Return>', self._on_member_tree_click)

        # Summary label at bottom
        self.members_summary = tk.Label(self.members_frame, text="",
                                        bg=THEME['bg_dark'], fg=THEME['text_primary'],
                                        font=('Menlo', 10), justify=tk.LEFT, anchor=tk.W)
        self.members_summary.pack(fill=tk.X, pady=(10, 0))

        # Player Statistics tab (third)
        self.player_frame = tk.Frame(self.content_frame, bg=THEME['bg_dark'], padx=10, pady=10)
        self.tab_frames.append(self.player_frame)

        self.player_text = scrolledtext.ScrolledText(self.player_frame, wrap=tk.WORD, **text_config)
        self.player_text.pack(fill=tk.BOTH, expand=True)

        # Battle Log tab (fourth/last)
        self.battles_frame = tk.Frame(self.content_frame, bg=THEME['bg_dark'], padx=10, pady=10)
        self.tab_frames.append(self.battles_frame)

        self.battles_text = scrolledtext.ScrolledText(self.battles_frame, wrap=tk.WORD, **text_config)
        self.battles_text.pack(fill=tk.BOTH, expand=True)

        # Select first tab by default
        self.current_tab = 0
        self._select_tab(0)

        # Status bar
        self.status_var = tk.StringVar(value="Ready - Enter a clan or player tag to get started")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, style='Status.TLabel',
                              padding=(10, 5))
        status_bar.pack(fill=tk.X, pady=(10, 0))

        # Bind Enter key
        self.clan_tag_entry.bind('<Return>', lambda e: self._fetch_clan())
        self.player_tag_entry.bind('<Return>', lambda e: self._fetch_player())

    def _select_tab(self, index: int):
        """Switch to the selected tab."""
        self.current_tab = index
        # Update button styles
        for i, btn in enumerate(self.tab_buttons):
            if i == index:
                btn.config(bg=THEME['gold'], fg=THEME['bg_dark'])
            else:
                btn.config(bg=THEME['bg_medium'], fg=THEME['text_primary'])
        # Show/hide frames
        for i, frame in enumerate(self.tab_frames):
            if i == index:
                frame.pack(fill=tk.BOTH, expand=True)
            else:
                frame.pack_forget()

    def _normalize_tag(self, tag: str) -> str:
        """Normalize a tag (ensure it starts with #)."""
        tag = tag.strip().upper()
        if not tag.startswith('#'):
            tag = '#' + tag
        return tag

    def _parse_last_seen(self, last_seen: str) -> str:
        """Parse lastSeen timestamp to human readable format."""
        if not last_seen:
            return "Unknown"
        try:
            # Format: 20210101T120000.000Z
            dt = datetime.strptime(last_seen[:15], "%Y%m%dT%H%M%S")
            now = datetime.utcnow()
            diff = now - dt

            if diff.days > 0:
                if diff.days == 1:
                    return "1 day ago"
                elif diff.days < 7:
                    return f"{diff.days} days ago"
                elif diff.days < 30:
                    weeks = diff.days // 7
                    return f"{weeks} week{'s' if weeks > 1 else ''} ago"
                else:
                    months = diff.days // 30
                    return f"{months} month{'s' if months > 1 else ''} ago"
            else:
                hours = diff.seconds // 3600
                if hours > 0:
                    return f"{hours} hour{'s' if hours > 1 else ''} ago"
                else:
                    mins = diff.seconds // 60
                    return f"{mins} min{'s' if mins > 1 else ''} ago"
        except Exception:
            return "Unknown"

    def _fetch_clan(self):
        """Fetch and display clan statistics."""
        if not self.api:
            messagebox.showerror("Error", "Please save your API key first")
            return

        tag = self.clan_tag_entry.get().strip()
        if not tag:
            messagebox.showerror("Error", "Please enter a clan tag")
            return

        tag = self._normalize_tag(tag)
        self.status_var.set(f"Fetching clan {tag}...")
        self.root.update()

        # Save the clan tag for next session
        self._save_config(last_clan_tag=tag)

        try:
            # Get clan info
            clan = self.api.get_clan(tag)

            # Get river race log for the graph
            river_race_log = []
            try:
                log_data = self.api.get_clan_river_race_log(tag)
                river_race_log = log_data.get('items', [])
            except Exception:
                pass

            self._display_clan(clan, tag, river_race_log)

            # Get members
            members = self.api.get_clan_members(tag)

            # Get river race (war) info for contribution points
            war_participants = {}
            try:
                river_race = self.api.get_clan_river_race(tag)
                clan_data = river_race.get('clan', {})
                participants = clan_data.get('participants', [])
                for p in participants:
                    war_participants[p.get('tag')] = p.get('fame', 0)
            except Exception:
                pass  # War data not available

            # Get past war history (up to 6 past wars)
            past_wars = []  # List of dicts mapping player_tag -> fame for each past war
            try:
                river_race_log = self.api.get_clan_river_race_log(tag)
                items = river_race_log.get('items', [])[:6]  # Get up to 6 past wars
                for war in items:
                    war_data = {}
                    # Find our clan's standings in this war
                    standings = war.get('standings', [])
                    for standing in standings:
                        clan_info = standing.get('clan', {})
                        if clan_info.get('tag') == tag:
                            participants = clan_info.get('participants', [])
                            for p in participants:
                                war_data[p.get('tag')] = p.get('fame', 0)
                            break
                    past_wars.append(war_data)
            except Exception:
                pass  # Past war data not available

            self._display_members(members, war_participants, past_wars)

            self._select_tab(0)  # Clan Statistics tab
            self.status_var.set(f"Loaded clan: {clan.get('name', 'Unknown')}")

        except Exception as e:
            self.status_var.set("Error fetching clan")
            messagebox.showerror("Error", str(e))

    def _fetch_player(self):
        """Fetch and display player statistics."""
        if not self.api:
            messagebox.showerror("Error", "Please save your API key first")
            return

        tag = self.player_tag_entry.get().strip()
        if not tag:
            messagebox.showerror("Error", "Please enter a player tag")
            return

        tag = self._normalize_tag(tag)
        self.status_var.set(f"Fetching player {tag}...")
        self.root.update()

        try:
            # Get player info
            player = self.api.get_player(tag)
            self._display_player(player)

            # Get battle log
            try:
                battles = self.api.get_player_battles(tag)
                self._display_battles(battles)
            except Exception:
                self.battles_text.delete(1.0, tk.END)
                self.battles_text.insert(tk.END, "Battle log not available")

            self._select_tab(2)  # Player Statistics tab
            self.status_var.set(f"Loaded player: {player.get('name', 'Unknown')}")

        except Exception as e:
            self.status_var.set("Error fetching player")
            messagebox.showerror("Error", str(e))

    def _on_member_tree_click(self, event):
        """Handle double-click on member row in treeview."""
        selection = self.members_tree.selection()
        if selection:
            item = selection[0]
            # Get the player tag stored in the item's tags
            tags = self.members_tree.item(item, 'tags')
            if tags:
                player_tag = tags[0]
                self._fetch_member_stats(player_tag)

    def _fetch_member_stats(self, player_tag: str):
        """Fetch and display stats and battle log for a clan member."""
        if not self.api:
            return

        self.status_var.set(f"Fetching stats for {player_tag}...")
        self.root.update()

        try:
            # Get player info
            player = self.api.get_player(player_tag)
            player_name = player.get('name', 'Unknown')

            # Display player stats
            self._display_player(player)

            # Get and display battles
            try:
                battles = self.api.get_player_battles(player_tag)
                self._display_battles_in_widget(battles, self.battles_text, player_name)
            except Exception:
                self.battles_text.delete(1.0, tk.END)
                self.battles_text.insert(tk.END, "Battle log not available")

            # Switch to Player Statistics tab
            self._select_tab(2)  # Player Statistics tab

            self.status_var.set(f"Loaded stats for {player_name}")

        except Exception as e:
            self.status_var.set("Error fetching member stats")
            messagebox.showerror("Error", str(e))

    def _display_clan(self, clan: Dict[str, Any], clan_tag: str = "", river_race_log: List[Dict] = None):
        """Display clan statistics and river race performance graph."""
        self.clan_text.delete(1.0, tk.END)

        if river_race_log is None:
            river_race_log = []

        lines = [
            "=" * 50,
            f"  CLAN: {clan.get('name', 'N/A')}",
            f"  Tag: {clan.get('tag', 'N/A')}",
            "=" * 50,
            "",
            "OVERVIEW",
            "-" * 40,
            f"  Description: {clan.get('description', 'N/A')}",
            f"  Type: {clan.get('type', 'N/A').replace('open', 'Open').replace('inviteOnly', 'Invite Only').replace('closed', 'Closed')}",
            f"  Location: {clan.get('location', {}).get('name', 'N/A')}",
            "",
            "STATISTICS",
            "-" * 40,
            f"  Clan Score: {clan.get('clanScore', 0):,}",
            f"  Clan War Trophies: {clan.get('clanWarTrophies', 0):,}",
            f"  Members: {clan.get('members', 0)}/50",
            f"  Required Trophies: {clan.get('requiredTrophies', 0):,}",
            f"  Donations Per Week: {clan.get('donationsPerWeek', 0):,}",
            "",
            "CLAN WAR",
            "-" * 40,
        ]

        clan_war_league = clan.get('clanWarLeague', {})
        if clan_war_league:
            lines.append(f"  War League: {clan_war_league.get('name', 'N/A')}")
        else:
            lines.append("  War League: N/A")

        self.clan_text.insert(tk.END, "\n".join(lines))

        # Create river race performance graph
        self._display_river_race_graph(clan_tag, river_race_log)

    def _display_river_race_graph(self, clan_tag: str, river_race_log: List[Dict]):
        """Display a line graph of river race performance."""
        # Clear existing canvas and labels
        for widget in self.clan_graph_frame.winfo_children():
            widget.destroy()
        self.clan_canvas = None

        if not river_race_log:
            # No data to display
            label = ttk.Label(self.clan_graph_frame, text="No river race history available")
            label.pack(expand=True)
            return

        # Extract data from river race log (most recent first, oldest last)
        weeks = []
        totals = []
        positions = []

        for i, race in enumerate(river_race_log[:10]):  # Last 10 races, most recent first
            week_num = i + 1
            weeks.append(f"W{week_num}")

            # Find our clan in standings
            standings = race.get('standings', [])
            clan_total = 0
            clan_position = 0

            for standing in standings:
                clan_info = standing.get('clan', {})
                if clan_info.get('tag') == clan_tag:
                    # Sum up all participant fame
                    participants = clan_info.get('participants', [])
                    clan_total = sum(p.get('fame', 0) for p in participants)
                    clan_position = standing.get('rank', 0)
                    break

            totals.append(clan_total)
            positions.append(clan_position)

        # Create figure with theme colors
        fig = Figure(figsize=(6, 3.5), dpi=100, facecolor=THEME['bg_dark'])
        ax = fig.add_subplot(111)
        ax.set_facecolor(THEME['bg_medium'])

        # Plot line graph with gold color
        x = range(len(weeks))
        ax.plot(x, totals, marker='o', linewidth=2.5, markersize=10,
                color=THEME['gold'], markerfacecolor=THEME['gold_light'],
                markeredgecolor=THEME['gold_dark'], markeredgewidth=2)

        # Add position annotations
        for i, (xi, yi, pos) in enumerate(zip(x, totals, positions)):
            if pos > 0:
                color = THEME['success'] if pos == 1 else THEME['warning'] if pos == 2 else THEME['danger'] if pos >= 4 else THEME['info']
                ax.annotate(f'#{pos}', (xi, yi), textcoords="offset points",
                           xytext=(0, 12), ha='center', fontsize=10, fontweight='bold', color=color)

        ax.set_xlabel('Week (1 = Most Recent)', color=THEME['text_primary'], fontsize=10)
        ax.set_ylabel('Total Fame', color=THEME['text_primary'], fontsize=10)
        ax.set_title('River Race Performance', color=THEME['gold'], fontsize=12, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(weeks, rotation=45, color=THEME['text_primary'])
        ax.tick_params(colors=THEME['text_primary'])
        ax.grid(True, alpha=0.3, color=THEME['text_primary'])

        # Style spines
        for spine in ax.spines.values():
            spine.set_color(THEME['bg_light'])

        # Format y-axis with commas
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

        # Add extra top margin for position labels
        ax.set_ylim(top=ax.get_ylim()[1] * 1.15)

        fig.tight_layout()

        # Embed in tkinter
        self.clan_canvas = FigureCanvasTkAgg(fig, master=self.clan_graph_frame)
        self.clan_canvas.draw()
        self.clan_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _display_members(self, members_data: Dict[str, Any], war_participants: Dict[str, int], past_wars: List[Dict[str, int]] = None):
        """Display clan members in treeview table."""
        # Clear existing items
        for item in self.members_tree.get_children():
            self.members_tree.delete(item)

        if past_wars is None:
            past_wars = []

        members = members_data.get('items', [])

        if not members:
            self.members_header.config(text="CLAN MEMBERS (0 total)")
            self.members_summary.config(text="No members found")
            return

        self.members_header.config(text=f"CLAN MEMBERS ({len(members)} total)")

        # Pre-calculate all data and averages first
        member_data = []
        for member in members:
            member_tag = member.get('tag', '')
            eligible_wars = []
            past_war_fames = []
            for j in range(6):
                if j < len(past_wars):
                    if member_tag in past_wars[j]:
                        fame = past_wars[j][member_tag]
                        past_war_fames.append(fame)
                        eligible_wars.append(fame)
                    else:
                        past_war_fames.append(None)  # Not a member at that time
                else:
                    past_war_fames.append(None)

            avg_fame = sum(eligible_wars) // len(eligible_wars) if eligible_wars else -1

            role = member.get('role', 'member')
            role_display = {
                'leader': 'Leader',
                'coLeader': 'Co-Leader',
                'elder': 'Elder',
                'member': 'Member'
            }.get(role, role)

            member_data.append({
                'tag': member_tag,
                'name': member.get('name', 'N/A'),
                'role': role_display,
                'trophies': member.get('trophies', 0),
                'donations': member.get('donations', 0),
                'last_seen': self._parse_last_seen(member.get('lastSeen', '')),
                'war_fame': war_participants.get(member_tag, 0),
                'avg_fame': avg_fame,
                'past_war_fames': past_war_fames,
                'weeks_completed': len(eligible_wars),
            })

        # Sort by average war contribution (descending)
        # Members with 3+ weeks completed are sorted first, others go to the end
        def sort_key(m):
            has_enough_weeks = m['weeks_completed'] >= 3
            avg = m['avg_fame'] if m['avg_fame'] >= 0 else -1
            # Primary: has 3+ weeks (True=1, False=0), Secondary: avg descending
            return (has_enough_weeks, avg)

        member_data.sort(key=sort_key, reverse=True)

        # Calculate dynamic column widths based on data (in pixels, approximate)
        def calc_width(values, header, multiplier=8):
            max_len = max(max(len(str(v)) for v in values), len(header))
            return max_len * multiplier + 10

        # Setup column headings and widths
        col_configs = {
            '#': {'width': 40, 'anchor': tk.CENTER},
            'Name': {'width': calc_width([m['name'] for m in member_data], 'Name', 9), 'anchor': tk.W},
            'Current': {'width': calc_width([f"{m['war_fame']:,}" for m in member_data], 'Current'), 'anchor': tk.E},
            'Avg': {'width': calc_width([f"{m['avg_fame']:,}" if m['avg_fame'] >= 0 else '-' for m in member_data], 'Avg'), 'anchor': tk.E},
            'Role': {'width': calc_width([m['role'] for m in member_data], 'Role'), 'anchor': tk.W},
            'Trophies': {'width': calc_width([f"{m['trophies']:,}" for m in member_data], 'Trophies'), 'anchor': tk.E},
            'Donats': {'width': calc_width([f"{m['donations']:,}" for m in member_data], 'Donats'), 'anchor': tk.E},
            'Last Seen': {'width': calc_width([m['last_seen'] for m in member_data], 'Last Seen'), 'anchor': tk.W},
        }

        # Add war columns
        for j in range(6):
            war_values = []
            for m in member_data:
                if m['past_war_fames'][j] is not None:
                    war_values.append(f"{m['past_war_fames'][j]:,}")
                else:
                    war_values.append('-')
            col_configs[f'War-{j+1}'] = {'width': calc_width(war_values, f'War-{j+1}'), 'anchor': tk.E}

        # Configure columns
        for col in self.members_columns:
            config = col_configs.get(col, {'width': 80, 'anchor': tk.CENTER})
            self.members_tree.heading(col, text=col, anchor=tk.CENTER)
            self.members_tree.column(col, width=config['width'], anchor=config['anchor'], minwidth=40)

        # Insert data rows
        for i, data in enumerate(member_data, 1):
            # Format values
            current_val = f"{data['war_fame']:,}"
            avg_val = f"{data['avg_fame']:,}" if data['avg_fame'] >= 0 else "-"
            trophies_val = f"{data['trophies']:,}"
            donations_val = f"{data['donations']:,}"

            # Past war values
            war_vals = []
            for j in range(6):
                if data['past_war_fames'][j] is not None:
                    war_vals.append(f"{data['past_war_fames'][j]:,}")
                else:
                    war_vals.append("-")

            # Build row values tuple
            row_values = (
                i,
                data['name'],
                current_val,
                avg_val,
                war_vals[0], war_vals[1], war_vals[2], war_vals[3], war_vals[4], war_vals[5],
                data['role'],
                trophies_val,
                donations_val,
                data['last_seen']
            )

            # Insert row with player tag stored in tags for click handling
            self.members_tree.insert('', tk.END, values=row_values, tags=(data['tag'],))

        # Summary stats
        total_donations = sum(m['donations'] for m in member_data)
        avg_trophies = sum(m['trophies'] for m in member_data) // len(member_data)
        total_war_fame = sum(m['war_fame'] for m in member_data)

        summary_text = f"Total Donations: {total_donations:,}  |  Average Trophies: {avg_trophies:,}  |  Total Current War Fame: {total_war_fame:,}"
        self.members_summary.config(text=summary_text)

    def _display_player(self, player: Dict[str, Any]):
        """Display player statistics."""
        self.player_text.delete(1.0, tk.END)

        # Get current deck
        current_deck = player.get('currentDeck', [])
        deck_cards = [card.get('name', 'Unknown') for card in current_deck]

        # Get best cards by level
        cards = player.get('cards', [])
        cards_sorted = sorted(cards, key=lambda x: x.get('level', 0), reverse=True)[:8]

        lines = [
            "=" * 60,
            f"  PLAYER: {player.get('name', 'N/A')}",
            f"  Tag: {player.get('tag', 'N/A')}",
            "=" * 60,
            "",
            "OVERVIEW",
            "-" * 40,
            f"  Experience Level: {player.get('expLevel', 0)}",
            f"  Trophies: {player.get('trophies', 0):,}",
            f"  Best Trophies: {player.get('bestTrophies', 0):,}",
            f"  Arena: {player.get('arena', {}).get('name', 'N/A')}",
            "",
            "CLAN INFO",
            "-" * 40,
        ]

        clan = player.get('clan')
        if clan:
            lines.extend([
                f"  Clan: {clan.get('name', 'N/A')}",
                f"  Clan Tag: {clan.get('tag', 'N/A')}",
                f"  Role: {player.get('role', 'N/A').replace('coLeader', 'Co-Leader').replace('elder', 'Elder').replace('member', 'Member').replace('leader', 'Leader')}",
            ])
        else:
            lines.append("  Not in a clan")

        lines.extend([
            "",
            "BATTLE STATISTICS",
            "-" * 40,
            f"  Wins: {player.get('wins', 0):,}",
            f"  Losses: {player.get('losses', 0):,}",
            f"  Three Crown Wins: {player.get('threeCrownWins', 0):,}",
            f"  Total Battles: {player.get('battleCount', 0):,}",
            "",
            "CHALLENGE STATISTICS",
            "-" * 40,
            f"  Challenge Cards Won: {player.get('challengeCardsWon', 0):,}",
            f"  Challenge Max Wins: {player.get('challengeMaxWins', 0)}",
            "",
            "DONATIONS",
            "-" * 40,
            f"  Donations: {player.get('donations', 0):,}",
            f"  Donations Received: {player.get('donationsReceived', 0):,}",
            f"  Total Donations: {player.get('totalDonations', 0):,}",
            "",
            "CARDS",
            "-" * 40,
            f"  Cards Found: {len(cards)}",
            "",
            "CURRENT DECK",
            "-" * 40,
        ])

        for card in deck_cards:
            lines.append(f"  - {card}")

        lines.extend([
            "",
            "HIGHEST LEVEL CARDS",
            "-" * 40,
        ])

        for card in cards_sorted:
            lines.append(f"  - {card.get('name', 'Unknown')} (Level {card.get('level', 0)})")

        self.player_text.insert(tk.END, "\n".join(lines))

    def _display_battles(self, battles: list):
        """Display battle log in the main battles tab."""
        self._display_battles_in_widget(battles, self.battles_text)

    def _display_battles_in_widget(self, battles: list, text_widget, player_name: str = None):
        """Display battle log in a given text widget."""
        text_widget.delete(1.0, tk.END)

        if not battles:
            text_widget.insert(tk.END, "No recent battles found")
            return

        title = f"  RECENT BATTLES" + (f" - {player_name}" if player_name else "")
        lines = [
            "=" * 80,
            title,
            "=" * 80,
            "",
        ]

        for i, battle in enumerate(battles[:25], 1):  # Show last 25 battles
            battle_type = battle.get('type', 'Unknown')
            battle_time = battle.get('battleTime', 'Unknown')

            # Get team and opponent info
            team = battle.get('team', [{}])[0]
            opponent = battle.get('opponent', [{}])[0]

            team_crowns = team.get('crowns', 0)
            opponent_crowns = opponent.get('crowns', 0)

            if team_crowns > opponent_crowns:
                result = "WIN"
            elif team_crowns < opponent_crowns:
                result = "LOSS"
            else:
                result = "DRAW"

            lines.extend([
                f"Battle #{i}",
                "-" * 40,
                f"  Type: {battle_type}",
                f"  Result: {result}",
                f"  Score: {team_crowns} - {opponent_crowns}",
                f"  Opponent: {opponent.get('name', 'Unknown')} ({opponent.get('trophies', 0):,} trophies)",
                f"  Arena: {battle.get('arena', {}).get('name', 'N/A')}",
                "",
            ])

        text_widget.insert(tk.END, "\n".join(lines))

    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    app = ClashRoyaleApp()
    app.run()


if __name__ == "__main__":
    main()
