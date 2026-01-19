#!/usr/bin/env python3
"""
Clash Royale Statistics App
A macOS application to view clan and player statistics from the Clash Royale API.
"""

import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import urllib.request
import urllib.parse
import urllib.error
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List

import matplotlib
matplotlib.use('TkAgg')
import matplotlib.ticker
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


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
        self.root.geometry("1000x700")
        self.root.minsize(900, 600)

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('aqua' if os.name == 'darwin' else 'clam')

        self.api: Optional[ClashRoyaleAPI] = None
        config = self._load_config()
        self.api_key = config.get('api_key')
        self.last_clan_tag = config.get('last_clan_tag', '')

        self._setup_ui()

        if self.api_key:
            self.api = ClashRoyaleAPI(self.api_key)
            self.api_key_entry.insert(0, self.api_key)

        if self.last_clan_tag:
            self.clan_tag_entry.insert(0, self.last_clan_tag)

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
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # API Key Section
        api_frame = ttk.LabelFrame(main_frame, text="API Configuration", padding="10")
        api_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(api_frame, text="API Key:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.api_key_entry = ttk.Entry(api_frame, width=60, show="*")
        self.api_key_entry.grid(row=0, column=1, sticky=tk.EW, padx=(0, 10))

        self.show_key_var = tk.BooleanVar()
        ttk.Checkbutton(api_frame, text="Show", variable=self.show_key_var,
                       command=self._toggle_key_visibility).grid(row=0, column=2, padx=(0, 10))

        ttk.Button(api_frame, text="Save Key", command=self._save_key).grid(row=0, column=3)

        api_frame.columnconfigure(1, weight=1)

        # Search Section
        search_frame = ttk.LabelFrame(main_frame, text="Search", padding="10")
        search_frame.pack(fill=tk.X, pady=(0, 10))

        # Clan search
        ttk.Label(search_frame, text="Clan Tag:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.clan_tag_entry = ttk.Entry(search_frame, width=20)
        self.clan_tag_entry.grid(row=0, column=1, sticky=tk.W, padx=(0, 10))
        ttk.Button(search_frame, text="Get Clan Stats", command=self._fetch_clan).grid(row=0, column=2, padx=(0, 20))

        # Player search
        ttk.Label(search_frame, text="Player Tag:").grid(row=0, column=3, sticky=tk.W, padx=(0, 10))
        self.player_tag_entry = ttk.Entry(search_frame, width=20)
        self.player_tag_entry.grid(row=0, column=4, sticky=tk.W, padx=(0, 10))
        ttk.Button(search_frame, text="Get Player Stats", command=self._fetch_player).grid(row=0, column=5)

        ttk.Label(search_frame, text="(Include # at start, e.g., #ABC123)",
                 font=('TkDefaultFont', 10, 'italic')).grid(row=1, column=0, columnspan=6, sticky=tk.W, pady=(5, 0))

        # Notebook for results
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Clan Statistics tab (first)
        self.clan_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.clan_frame, text="Clan Statistics")

        # Top: text stats
        self.clan_text_frame = ttk.Frame(self.clan_frame)
        self.clan_text_frame.pack(fill=tk.BOTH, expand=True)

        self.clan_text = scrolledtext.ScrolledText(self.clan_text_frame, wrap=tk.WORD, font=('Menlo', 11), height=12)
        self.clan_text.pack(fill=tk.BOTH, expand=True)

        # Bottom: graph
        self.clan_graph_frame = ttk.Frame(self.clan_frame)
        self.clan_graph_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.clan_canvas = None  # Will hold the matplotlib canvas

        # Clan Members tab (second)
        self.members_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.members_frame, text="Clan Members")

        self.members_text = tk.Text(self.members_frame, wrap=tk.WORD, font=('Menlo', 11))
        members_scrollbar = ttk.Scrollbar(self.members_frame, orient=tk.VERTICAL, command=self.members_text.yview)
        self.members_text.configure(yscrollcommand=members_scrollbar.set)
        members_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.members_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure tag for clickable names
        self.members_text.tag_configure("clickable", foreground="blue", underline=True)
        self.members_text.tag_bind("clickable", "<Button-1>", self._on_member_click)
        self.members_text.tag_bind("clickable", "<Enter>", lambda e: self.members_text.config(cursor="hand2"))
        self.members_text.tag_bind("clickable", "<Leave>", lambda e: self.members_text.config(cursor=""))

        # Player Statistics tab (third)
        self.player_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.player_frame, text="Player Statistics")

        self.player_text = scrolledtext.ScrolledText(self.player_frame, wrap=tk.WORD, font=('Menlo', 11))
        self.player_text.pack(fill=tk.BOTH, expand=True)

        # Battle Log tab (fourth/last)
        self.battles_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.battles_frame, text="Battle Log")

        self.battles_text = scrolledtext.ScrolledText(self.battles_frame, wrap=tk.WORD, font=('Menlo', 11))
        self.battles_text.pack(fill=tk.BOTH, expand=True)

        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(fill=tk.X, pady=(10, 0))

        # Bind Enter key
        self.clan_tag_entry.bind('<Return>', lambda e: self._fetch_clan())
        self.player_tag_entry.bind('<Return>', lambda e: self._fetch_player())

    def _toggle_key_visibility(self):
        """Toggle API key visibility."""
        self.api_key_entry.config(show="" if self.show_key_var.get() else "*")

    def _save_key(self):
        """Save the API key."""
        api_key = self.api_key_entry.get().strip()
        if not api_key:
            messagebox.showerror("Error", "Please enter an API key")
            return

        self.api_key = api_key
        self.api = ClashRoyaleAPI(api_key)
        self._save_config(api_key=api_key)
        self.status_var.set("API key saved successfully")
        messagebox.showinfo("Success", "API key saved!")

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

            self.notebook.select(self.clan_frame)
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

            self.notebook.select(self.player_frame)
            self.status_var.set(f"Loaded player: {player.get('name', 'Unknown')}")

        except Exception as e:
            self.status_var.set("Error fetching player")
            messagebox.showerror("Error", str(e))

    def _on_member_click(self, event):
        """Handle click on member name to show their battle log."""
        # Get the tag from the clicked position
        index = self.members_text.index(f"@{event.x},{event.y}")

        # Get all tags at this position
        tags = self.members_text.tag_names(index)

        # Find the member tag (starts with 'member_')
        member_tag = None
        for tag in tags:
            if tag.startswith("member_"):
                member_tag = tag[7:]  # Remove 'member_' prefix
                break

        if member_tag:
            self._fetch_member_stats(member_tag)

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
            self.notebook.select(self.player_frame)

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

        # Create figure
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)

        # Plot line graph
        x = range(len(weeks))
        ax.plot(x, totals, marker='o', linewidth=2, markersize=8, color='#1f77b4')

        # Add position annotations
        for i, (xi, yi, pos) in enumerate(zip(x, totals, positions)):
            if pos > 0:
                color = '#28a745' if pos == 1 else '#ffc107' if pos == 2 else '#dc3545' if pos >= 4 else '#17a2b8'
                ax.annotate(f'#{pos}', (xi, yi), textcoords="offset points",
                           xytext=(0, 10), ha='center', fontsize=9, fontweight='bold', color=color)

        ax.set_xlabel('Week (1 = Most Recent)')
        ax.set_ylabel('Total Fame')
        ax.set_title('River Race Performance')
        ax.set_xticks(x)
        ax.set_xticklabels(weeks, rotation=45)
        ax.grid(True, alpha=0.3)

        # Format y-axis with commas
        ax.get_yaxis().set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))

        fig.tight_layout()

        # Embed in tkinter
        self.clan_canvas = FigureCanvasTkAgg(fig, master=self.clan_graph_frame)
        self.clan_canvas.draw()
        self.clan_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    def _display_members(self, members_data: Dict[str, Any], war_participants: Dict[str, int], past_wars: List[Dict[str, int]] = None):
        """Display clan members with clickable names."""
        self.members_text.delete(1.0, tk.END)
        self.members_text.config(state=tk.NORMAL)

        if past_wars is None:
            past_wars = []

        members = members_data.get('items', [])

        # Build header with past war columns
        past_war_headers = ""
        for i in range(6):
            past_war_headers += f"{'War-' + str(i+1):<8}"

        # Header
        header = [
            "=" * 158,
            f"  CLAN MEMBERS ({len(members)} total)",
            "  Click on a player name to view their stats",
            "=" * 158,
            "",
            f"{'#':<4} {'Name':<16} {'Current':<8} {'Avg':<8} {past_war_headers}{'Role':<10} {'Trophies':<9} {'Donats':<8} {'Last Seen':<12}",
            "-" * 158,
        ]

        self.members_text.insert(tk.END, "\n".join(header) + "\n")

        # Pre-calculate averages for sorting
        member_data = []
        for member in members:
            member_tag = member.get('tag', '')
            eligible_wars = []
            for j in range(min(6, len(past_wars))):
                if member_tag in past_wars[j]:
                    eligible_wars.append(past_wars[j][member_tag])

            avg_fame = sum(eligible_wars) // len(eligible_wars) if eligible_wars else -1
            member_data.append((member, avg_fame))

        # Sort by average war contribution (descending), -1 values go to bottom
        member_data.sort(key=lambda x: x[1] if x[1] >= 0 else -1, reverse=True)

        for i, (member, avg_fame) in enumerate(member_data, 1):
            role = member.get('role', 'member')
            role_display = {
                'leader': 'Leader',
                'coLeader': 'Co-Leader',
                'elder': 'Elder',
                'member': 'Member'
            }.get(role, role)

            member_tag = member.get('tag', '')
            member_name = member.get('name', 'N/A')
            last_seen = self._parse_last_seen(member.get('lastSeen', ''))
            war_fame = war_participants.get(member_tag, 0)
            trophies = member.get('trophies', 0)
            donations = member.get('donations', 0)

            # Get past war contributions
            past_war_values = ""
            for j in range(6):
                if j < len(past_wars):
                    if member_tag in past_wars[j]:
                        fame = past_wars[j][member_tag]
                        past_war_values += f"{fame:<8,}"
                    else:
                        past_war_values += f"{'-':<8}"
                else:
                    past_war_values += f"{'-':<8}"

            # Format average display
            if avg_fame >= 0:
                avg_display = f"{avg_fame:<8,}"
            else:
                avg_display = f"{'-':<8}"

            # Insert row number
            self.members_text.insert(tk.END, f"{i:<4} ")

            # Insert clickable name with unique tag
            name_tag = f"member_{member_tag}"
            self.members_text.tag_configure(name_tag, foreground="blue", underline=True)
            self.members_text.tag_bind(name_tag, "<Button-1>", self._on_member_click)
            self.members_text.tag_bind(name_tag, "<Enter>", lambda e: self.members_text.config(cursor="hand2"))
            self.members_text.tag_bind(name_tag, "<Leave>", lambda e: self.members_text.config(cursor=""))

            display_name = member_name[:14] if len(member_name) > 14 else member_name
            self.members_text.insert(tk.END, f"{display_name:<16}", (name_tag,))

            # Insert rest of the row
            self.members_text.insert(
                tk.END,
                f" {war_fame:<8,} {avg_display}{past_war_values}{role_display:<10} {trophies:<9,} {donations:<8,} {last_seen:<12}\n"
            )

        # Summary stats
        total_donations = sum(m.get('donations', 0) for m in members)
        avg_trophies = sum(m.get('trophies', 0) for m in members) // len(members) if members else 0
        total_war_fame = sum(war_participants.get(m.get('tag', ''), 0) for m in members)

        summary = [
            "",
            "-" * 158,
            f"Total Donations: {total_donations:,}",
            f"Average Trophies: {avg_trophies:,}",
            f"Total Current War Fame: {total_war_fame:,}",
        ]

        self.members_text.insert(tk.END, "\n".join(summary))

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
