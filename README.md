# DeFi-Scope-Test-Telegram-Bot

A powerful Telegram bot for analyzing DeFi tokens, tracking wallets, and discovering profitable opportunities in the decentralized finance space.

## Features

### Token Analysis
- First buyers detection
- All-time high market cap analysis
- Deployer wallet analysis (Premium)
- Top holders analysis (Premium)

### Wallet Analysis
- Most profitable wallets in a token
- Wallet holding time analysis
- Tokens deployed by a wallet (Premium)

### Tracking & Monitoring
- Track tokens, wallets, or deployers (Premium)
- Profitable wallets across all tokens (Premium)
- High net worth wallet monitoring (Premium)

### Special Lists
- Most profitable token deployer wallets
- KOL (Key Opinion Leaders) wallets profitability


## Commands

### Token Analysis
- `/fb <token_address>` - First 1-50 buy wallets of a token
- `/ath <token_address>` - All time high market cap of a token
- `/dw <token_address>` - Scan token contract to reveal deployer wallet (Premium)
- `/th <token_address>` - Scan token for top holders (Premium)

### Wallet Analysis
- `/mpw <token_address>` - Most profitable wallets in a token
- `/wh <wallet_address> <token_address>` - How long a wallet holds a token
- `/td <wallet_address>` - Tokens deployed by a wallet (Premium)

### Tracking & Monitoring
- `/track <type> <address>` - Track tokens, wallets or deployments (Premium)
- `/pw` - Profitable wallets in any token (Premium)
- `/hnw` - High net worth wallet holders (Premium)

### Special Lists
- `/ptd` - Most profitable token deployer wallets
- `/kol` - KOL wallets profitability

### Other Commands
- `/premium` - Upgrade to premium
- `/help` - Show help information

### Premium Features

Upgrade to premium to unlock:

- Unlimited token and wallet scans
- Access to deployer wallet analysis
- Tracking tokens, wallets, and deployers
- View top holders of any token
- Access to profitable wallets database
- High net worth wallet monitoring
- Priority support

Pricing Plans

- Quarterly: $49.99 ($16.66/month)
- Annual: $149.99 ($12.50/month)
- Monthly: $19.99/month


## Setup and Installation

1. Clone the repository:
```bash
git clone https://github.com/dodger213/DeFi-Scope-Test-Telegram-Bot.git
cd DeFi-Scope-Test-Telegram-Bot
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Set up environment variables:

```bash
TELEGRAM_BOT_TOKEN=your_bot_token
MONGODB_URI=your_mongodb_uri
DB_NAME=defi_scope_bot
```

4. Run the bot:
```
python bot/main.py
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License
This project is licensed under the [MIT License](./LICENSE) - see the LICENSE file for details.