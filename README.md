# Clash Royale Stats

A macOS desktop application to view Clash Royale clan and player statistics.

## Features

- **Clan Statistics** - View clan overview, score, war trophies, donations, and member count
- **Clan Members** - See all members with their roles, trophies, and donation stats
- **Player Statistics** - View trophies, battle stats, challenge wins, cards, and current deck
- **Battle Log** - See recent battle results with scores and opponents
- **API Key Storage** - Securely saves your API key between sessions

## Requirements

- Python 3.x
- Tkinter (included with Python on macOS)
- Clash Royale API key from [developer.clashroyale.com](https://developer.clashroyale.com)

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/YOUR_USERNAME/ClashRoyaleStats.git
   cd ClashRoyaleStats
   ```

2. Run the application:
   ```bash
   python3 clash_royale_stats.py
   ```

## Usage

1. Launch the app
2. Enter your Clash Royale API key and click "Save Key"
3. Enter a clan tag (e.g., `#ABC123`) and click "Get Clan Stats"
4. Enter a player tag (e.g., `#XYZ789`) and click "Get Player Stats"
5. Use the tabs to switch between different statistics views

## Getting an API Key

1. Go to [developer.clashroyale.com](https://developer.clashroyale.com)
2. Create an account or log in
3. Create a new API key with your IP address
4. Copy the key and paste it into the app

## License

MIT License
