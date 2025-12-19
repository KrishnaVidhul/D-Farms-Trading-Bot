# D-Farms Trading Bot 🦅

An automated "Boardroom" style trading bot running on Oracle Cloud Infrastructure (OCI). The bot uses a multi-agent system to analyze the market, manage a paper trading portfolio, and execute strategies based on technical and fundamental analysis.

## Architecture

The system mimics a corporate boardroom structure:

*   **Orchestrator (`main_orchestrator.py`)**: The CEO. Runs the daily "Morning Conference," manages the budget, and coordinates all other agents. Entry point for the Docker container.
*   **Otto (`agents/manager_otto.py`)**: The Portfolio Manager. Decides asset allocation (Stocks vs. Crypto) based on market briefings and performance.
*   **Technical Analyst (`technical_analyst.py`)**: Provides technical signals (RSI, Moving Averages).
*   **Paper Trader (`paper_trader.py`)**: Manages the virtual portfolio, fee calculations (Wealthsimple logic), and P&L tracking.
*   **Dashboard (`dashboard.py`)**: A Streamlit-based UI for monitoring the bot's decisions, trades, and OCI infrastructure costs.

## Getting Started

### Prerequisites
*   Docker & Docker Compose
*   OCI specific configuration (for cost monitoring)

### Running the Bot (Docker)

To start the full system (Bot + Dashboard):

```bash
cd trading_bot
docker-compose up -d --build
```

### Accessing the Dashboard

The dashboard runs on port `8501`.
*   **Direct IP**: `http://129.153.60.198:8501`
*   **Cloudflare Tunnel**: [https://preferences-randy-crystal-lcd.trycloudflare.com/](https://preferences-randy-crystal-lcd.trycloudflare.com/) (e.g., `https://trading.yourdomain.com`) - *Requires `cloudflared` setup on VM.*

## Documentation

*   [OCI Automation & Setup Guide](docs/OCI_SETUP.md): Instructions for setting up the OCI cost monitor and ARM instance sniper.

## Project Structure

*   `trading_bot/`: Main application source code.
    *   `core/`: Shared modules (Market Scanner, Trade Executor).
    *   `agents/`: Intelligence logic (Otto).
    *   `logs/`: Application logs.
    *   `data/`: Local data persistence.
*   `oci_automation/`: Scripts for managing OCI resources (e.g., Cost Tracker, ARM Sniper).
*   `Terraform/`: Infrastructure as Code for OCI deployment.
