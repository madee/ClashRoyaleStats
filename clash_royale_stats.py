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
from typing import Optional, Dict, Any


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
        self.root.geometry("900x700")
        self.root.minsize(800, 600)

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use('aqua' if os.name == 'darwin' else 'clam')

        self.api: Optional[ClashRoyaleAPI] = None
        self.api_key = self._load_api_key()

        self._setup_ui()

        if self.api_key:
            self.api = ClashRoyaleAPI(self.api_key)
            self.api_key_entry.insert(0, self.api_key)

    def _load_api_key(self) -> Optional[str]:
        """Load API key from config file."""
        try:
            if os.path.exists(self.CONFIG_FILE):
                with open(self.CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    return config.get('api_key')
        except Exception:
            pass
        return None

    def _save_api_key(self, api_key: str):
        """Save API key to config file."""
        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump({'api_key': api_key}, f)
        except Exception as e:
            messagebox.showwarning("Warning", f"Could not save API key: {e}")

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

        # Clan tab
        self.clan_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.clan_frame, text="Clan Statistics")

        self.clan_text = scrolledtext.ScrolledText(self.clan_frame, wrap=tk.WORD, font=('Menlo', 11))
        self.clan_text.pack(fill=tk.BOTH, expand=True)

        # Player tab
        self.player_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.player_frame, text="Player Statistics")

        self.player_text = scrolledtext.ScrolledText(self.player_frame, wrap=tk.WORD, font=('Menlo', 11))
        self.player_text.pack(fill=tk.BOTH, expand=True)

        # Clan Members tab
        self.members_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(self.members_frame, text="Clan Members")

        self.members_text = scrolledtext.ScrolledText(self.members_frame, wrap=tk.WORD, font=('Menlo', 11))
        self.members_text.pack(fill=tk.BOTH, expand=True)

        # Battle Log tab
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
        self._save_api_key(api_key)
        self.status_var.set("API key saved successfully")
        messagebox.showinfo("Success", "API key saved!")

    def _normalize_tag(self, tag: str) -> str:
        """Normalize a tag (ensure it starts with #)."""
        tag = tag.strip().upper()
        if not tag.startswith('#'):
            tag = '#' + tag
        return tag

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

        try:
            # Get clan info
            clan = self.api.get_clan(tag)
            self._display_clan(clan)

            # Get members
            members = self.api.get_clan_members(tag)
            self._display_members(members)

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

    def _display_clan(self, clan: Dict[str, Any]):
        """Display clan statistics."""
        self.clan_text.delete(1.0, tk.END)

        lines = [
            "=" * 60,
            f"  CLAN: {clan.get('name', 'N/A')}",
            f"  Tag: {clan.get('tag', 'N/A')}",
            "=" * 60,
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

    def _display_members(self, members_data: Dict[str, Any]):
        """Display clan members."""
        self.members_text.delete(1.0, tk.END)

        members = members_data.get('items', [])

        lines = [
            "=" * 80,
            f"  CLAN MEMBERS ({len(members)} total)",
            "=" * 80,
            "",
            f"{'#':<4} {'Name':<20} {'Role':<12} {'Trophies':<10} {'Donations':<10} {'Tag':<12}",
            "-" * 80,
        ]

        for i, member in enumerate(members, 1):
            role = member.get('role', 'member')
            role_display = {
                'leader': 'Leader',
                'coLeader': 'Co-Leader',
                'elder': 'Elder',
                'member': 'Member'
            }.get(role, role)

            lines.append(
                f"{i:<4} {member.get('name', 'N/A'):<20} {role_display:<12} "
                f"{member.get('trophies', 0):<10,} {member.get('donations', 0):<10,} {member.get('tag', 'N/A'):<12}"
            )

        # Summary stats
        total_donations = sum(m.get('donations', 0) for m in members)
        avg_trophies = sum(m.get('trophies', 0) for m in members) // len(members) if members else 0

        lines.extend([
            "",
            "-" * 80,
            f"Total Donations: {total_donations:,}",
            f"Average Trophies: {avg_trophies:,}",
        ])

        self.members_text.insert(tk.END, "\n".join(lines))

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
        """Display battle log."""
        self.battles_text.delete(1.0, tk.END)

        if not battles:
            self.battles_text.insert(tk.END, "No recent battles found")
            return

        lines = [
            "=" * 80,
            "  RECENT BATTLES",
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

        self.battles_text.insert(tk.END, "\n".join(lines))

    def run(self):
        """Run the application."""
        self.root.mainloop()


def main():
    app = ClashRoyaleApp()
    app.run()


if __name__ == "__main__":
    main()
