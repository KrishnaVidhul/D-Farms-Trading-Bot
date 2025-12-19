# 🦅 D-Farms Trading Bot

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Docker](https://img.shields.io/badge/docker-ready-brightgreen.svg)](https://www.docker.com/)
[![OCI](https://img.shields.io/badge/cloud-OCI-red.svg)](https://www.oracle.com/cloud/)

An automated "Boardroom" style trading bot running on Oracle Cloud Infrastructure (OCI). The bot uses a multi-agent system to analyze the market, manage a paper trading portfolio, and execute strategies based on technical and fundamental analysis.

## ✨ Features

- **🤖 Multi-Agent Architecture**: CEO (Orchestrator), Portfolio Manager (Otto), Technical Analyst
- **📊 5-Day Swing Trading Strategy**: Optimized for short-term momentum trades
- **💰 Paper Trading**: Risk-free testing with Wealthsimple fee simulation
- **📈 Real-time Dashboard**: Streamlit-based monitoring with live metrics
- **☁️ OCI Cost Tracking**: Automated hourly cost monitoring with Telegram alerts
- **🎯 ARM Instance Sniper**: Auto-provision high-performance Ampere A1 instances
- **🔔 Telegram Alerts**: Real-time trade signals and system notifications

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Orchestrator (CEO)                  │
│         Daily Morning Conference & Coordination      │
└──────────────┬──────────────────────┬────────────────┘
               │                      │
       ┌───────▼────────┐    ┌────────▼────────┐
       │  Manager Otto  │    │ Technical       │
       │  (Portfolio)   │    │ Analyst         │
       └───────┬────────┘    └────────┬────────┘
               │                      │
               └──────────┬───────────┘
                          │
                  ┌───────▼────────┐
                  │ Trade Executor │
                  │ & Paper Trader │
                  └────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- OCI account (for cost monitoring)
- Telegram bot token (for alerts)

### Running Locally

```bash
# Clone the repository
git clone https://github.com/KrishnaVidhul/D-Farms-Trading-Bot.git
cd D-Farms-Trading-Bot

# Set up environment variables
cp trading_bot/.env.example trading_bot/.env
# Edit .env with your API keys

# Start the system
cd trading_bot
docker-compose up -d --build
```

### Accessing the Dashboard

- **Local**: http://localhost:8501
- **Production**: http://129.153.60.198:8501
- **Cloudflare Tunnel**: https://preferences-randy-crystal-lcd.trycloudflare.com/

## 📖 Documentation

- [Project Status & Protocol](trading_bot/docs/PROJECT_STATUS.md) - **READ THIS FIRST**
- [OCI Setup Guide](trading_bot/docs/OCI_SETUP.md) - Cost monitoring & ARM sniper setup
- [Trading Bot README](trading_bot/README.md) - Architecture details

## 💡 Trading Strategy

### Buy Signals
- Price > SMA 50 (Uptrend)
- RSI rising between 40-70 (Momentum)
- Sentiment Score > 0.90 (Positive news)
- Volume Spike > 1.2x average

### Sell Rules
- **Profit Target**: +5.0% (Aggressive exit)
- **Stop Loss**: -4.0% (Swing volatility buffer)
- **Time Stop**: 5 days (Force sell if PnL > -2%)

## 🛡️ Risk Management

- **Panic Check**: Monitors SPY/BTC for >2% drops
- **Trading Hours**: 08:30-17:00 ET (Mon-Fri)
- **Position Sizing**: 20% of portfolio per trade
- **Emergency Board Meeting**: Triggered on market crashes

## 📊 Monitored Assets

**Stocks**: SHOP.TO, NVDA, COIN  
**Crypto Miners**: HUT.TO, BITF.TO, HIVE.TO  
**Crypto**: BTC-USD, ETH-USD

## 🔧 OCI Automation

### Cost Monitor
- Runs hourly via cron
- Tracks cumulative MTD costs
- Sends daily Telegram reports at 8 AM UTC

### ARM Sniper
- Checks Ampere A1 availability every 5 minutes
- Auto-provisions instances when capacity detected
- Sends success/failure alerts via Telegram

## 🐳 Deployment

### To OCI VM

```bash
./deploy_bot.sh
```

This script:
1. Packages the bot (excludes logs/data)
2. Uploads to OCI VM via SCP
3. Restarts Docker containers

## 📁 Project Structure

```
D-Farms-Trading-Bot/
├── trading_bot/           # Main application
│   ├── core/             # Market scanner, executor, sentiment
│   ├── agents/           # Manager Otto (allocation)
│   ├── dashboard.py      # Streamlit UI
│   └── main_orchestrator.py
├── oci_automation/       # Cloud management
│   ├── cost_tracker.py   # Billing monitor
│   └── arm_sniper.py     # Instance provisioner
├── Terraform/            # Infrastructure as Code
└── deploy_bot.sh         # Deployment script
```

## 🔐 Environment Variables

Required in `trading_bot/.env`:

```bash
TELEGRAM_TOKEN=your_bot_token
CHAT_ID=your_chat_id
GROQ_API_KEY=your_groq_key
OPENAI_API_KEY=your_openai_key
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This bot is for **educational and research purposes only**. It uses paper trading and does not execute real trades. Always do your own research and consult with financial advisors before making investment decisions.

## 🙏 Acknowledgments

- Built with [yfinance](https://github.com/ranaroussi/yfinance) for market data
- Powered by [Streamlit](https://streamlit.io/) for the dashboard
- Sentiment analysis using [FinBERT](https://huggingface.co/yiyanghkust/finbert-tone)
- Hosted on [Oracle Cloud Infrastructure](https://www.oracle.com/cloud/)

## 📞 Contact

**Krishna Vidhul** - [@KrishnaVidhul](https://github.com/KrishnaVidhul)

**Project Link**: https://github.com/KrishnaVidhul/D-Farms-Trading-Bot

---

⭐ Star this repo if you find it helpful!
