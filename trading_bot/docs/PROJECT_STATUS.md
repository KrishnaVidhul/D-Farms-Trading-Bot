# 🦅 D-Farms Trading Bot - Project Status

> **🛑 AGENT PROTOCOL (MANDATORY READ)**
> 1.  **NO LOCAL EXECUTION:** Do NOT run `python main.py` or `.sh` scripts on the local (macOS) machine. The runtime environment is the **Oracle Cloud VM** (`129.153.60.198`). Local is for *editing only*.
> 2.  **DEPLOYMENT ONLY:** Testing logic? Write a test, then run `./deploy_bot.sh` to execute it on the VM.
> 3.  **NO SURPRISES:** Do not change strategy parameters (e.g., stops, targets) without explicit user approval.
> 4.  **RESPECT THE PLAN:** Follow the "Active Strategy" section below. Do not reinvent the wheel.

## 🏗️ Infrastructure
*   **Host:** Oracle Cloud Infrastructure (OCI) VM (Compute Ampere/AMD).
*   **IP Address:** `129.153.60.198`
*   **Deployment:** Docker Compose (v2).
*   **Deployment Script:** `deploy_bot.sh` (Root level).
    *   *Usage:* `./deploy_bot.sh` (Auto-packages, uploads, and restarts `docker compose`).
*   **Database:** PostgreSQL 15 (Docker Service: `postgres`).
    *   *Note:* `database.py` uses SQLAlchemy to connect. `costs.db` (SQLite) is used *independently* by `oci_automation`.
*   **Host Directory Structure (Critical):**
    *   `~/trading_bot/`: Main App.
    *   `~/oci_monitor/`: Cost Tracker Logs (Mounted to container).
    *   `~/arm_sniper/`: Sniper Logs & Terraform Config.
        *   *Requires:* `~/.oci/config` (OCI Credentials for Sniper).
        *   *Requires:* `~/arm_sniper/terraform/` (Terraform scripts).

## 🔑 Required Environment Variables
*   **App (`.env`):**
    *   `TELEGRAM_TOKEN`, `CHAT_ID`: For Alerts.
    *   `GROQ_API_KEY`, `OPENAI_API_KEY`: For LLM/Otto Brain.
    *   `DATABASE_URL`: Set automatically by Docker (Postgres).
*   **Host (`.bashrc` / Cron):**
    *   `TELEGRAM_TOKEN`, `CHAT_ID` (Required for OCI scripts).

## 🏗️ System Architecture ("The Boardroom")
The system follows a multi-agent "Boardroom" pattern:
1.  **CEO (Orchestrator):** `main_orchestrator.py`. Runs the daily cycle, checking for panic and coordinating the meeting.
2.  **Portfolio Manager (Otto):** `agents/manager_otto.py`. Decides high-level asset allocation (Stocks vs Crypto) based on market briefings.
3.  **Analyst:** `technical_analyst.py`. Provides pure technical signals (RSI, SMA, Bollinger).
4.  **Trader:** `paper_trader.py`. Manages the portfolio state, fee calculations, and P&L usage.
5.  **Executor:** `core/trade_executor.py`. Gatekeeper that combines all inputs to execute or reject trades.

## ☁️ OCI Automation Features
Independent scripts running on the VM (outside Docker) to manage cloud resources:
*   **ARM Sniper (`oci_automation/arm_sniper.py`):** Automatically attempts to provision high-performance Ampere A1 instances when simple "Out of Capacity" errors occur.
*   **Cost Monitor (`oci_automation/cost_tracker.py`):** Tracks hourly OCI spending and sends daily Telegram reports to prevent billing surprises.

## 🖥️ Dashboard Access
*   **Direct IP:** `http://129.153.60.198:8501`
*   **Cloudflare Tunnel:** `https://preferences-randy-crystal-lcd.trycloudflare.com/`
    *   *Note:* Use this for stable access if IP changes or for mobile.

## 💰 Paper Trading Rules (`paper_trader.py`)
*   **Allocation:** 20% of Portfolio Balance per trade (Fixed).
*   **Fees (Wealthsimple Logic):**
    *   **TSX (.TO):** 0.0% (Free).
    *   **US/Crypto:** 1.5% (FX Fee).
    *   *Note:* Break-even price calculation includes entry fee.
*   **Monitored Tickers:**
    *   **Stocks:** SHOP.TO, NVDA, COIN
    *   **Crypto:** HUT.TO, BITF.TO, HIVE.TO (Miners), BTC-USD, ETH-USD

## 🧠 Active Strategy: "5-Day Swing"
The bot is currently tuned for short-term swing trades.

### Buy Rules (`technical_analyst.py`, `market_scanner.py`)
1.  **Trend:** Price > SMA 50.
2.  **Momentum:** RSI rising (Current > Previous) AND RSI between 40-70.
    *   *Kill Switch:* Reject if RSI > 75 (Overbought).
3.  **Fundamentals:**
    *   Sentiment Score > 0.90 (Positive News).
    *   Volume Spike > 1.2x Average.
    *   P/E Ratio < 150 (Exception: Strong Momentum allows high P/E).

### Sell Rules (`trade_executor.py`)
1.  **Profit Target:** +5.0% Net (Aggressive exit).
2.  **Stop Loss:** -4.0% (Wider to allow swing volatility).
3.  **Time Stop:** **5 Days**. If held > 5 days and PnL > -2%, force sell to free up capital.

## 🔔 Alert System (Latest Update)
*   **Logic:** The bot sends Telegram alerts for **ALL** valid buy signals.
*   **Manual Mode:** If Paper Trading funds are insufficient, the alert is sent as **"BUY SIGNAL (Manual)"** so the user can execute on their own broker.
*   **Execution:** If funds exist, it executes internally and alerts as **"BUY EXEC"**.

## 🛡️ Risk Management & Safety
*   **Panic Check (`main_orchestrator.py`):**
    *   Runs before every scan loop.
    *   **Trigger:** If SPY or BTC drops > 2.0% in the last 1 hour.
    *   **Action:** Triggers "Emergency Board Meeting" (Forces Otto to re-evaluate budget).
*   **Trading Hours:**
    *   Orchestrator pauses scanning outside 08:30 - 17:00 ET (Mon-Fri).
    *   "Heartbeat" continues 24/7 (Hourly status checks) but skips scanning.

## 📂 Key Files
*   `trading_bot/main_orchestrator.py`: Entry point, daily "Morning Conference".
*   `trading_bot/core/trade_executor.py`: Handles Trade Logic & Telegram Alerts.
*   `trading_bot/core/market_scanner.py`: Scans tickers and applies "Gatekeeper" logic.
*   `trading_bot/agents/manager_otto.py`: "Portfolio Manager" deciding Stocks vs Crypto allocation.

## 📜 Project Evolution & Lessons Learned
*Analysis of development history to prevent regressions.*

### Version 1.0: Foundation (Dec 08 - Dec 12)
*   **Goal:** Establish OCI Infrastructure and basic checking.
*   **Lesson:** **Docker Permissions.** Initially failed with "Permission denied". *Fix:* Always use `sudo docker-compose` or `docker compose` (v2) on the VM.
*   **Lesson:** **OCI Capacity.** Ampere A1 instances are rare. *Fix:* Built `arm_sniper.py` to auto-provision when capacity appears. Do not manually retry indefinitely; let the bot do it.

### Version 2.0: The "Boardroom" (Dec 13 - Dec 16)
*   **Goal:** Multi-agent architecture (Otto, CEO, Analyst).
*   **Mistake:** **Silent Failures.** Early versions of the Market Intel agent failed silently. *Fix:* Implemented robust logging to `logs/` and `database.py` for persistent tracking.
*   **Mistake:** **Timezones.** VM is UTC, User is ET. *Fix:* `main_orchestrator.py` now explicitly handles `pytz.timezone('US/Eastern')` for market hours (08:30-17:00 ET).

### Version 3.0: Swing Strategy Pivot (Dec 17 - Dec 18)
*   **Goal:** Move from Day Trading to 5-Day Swing.
*   **Pivot:** Dropped tight 1% stops for wider -4% stops and 5-day time horizons.
*   **Lesson:** **Dashboard Clarity.** Users couldn't tell why scans were happening but no trades. *Fix:* Added specific "BUY_SIGNAL" vs "SCAN" event types in DB.

### Version 4.0: Real-Time Alerts (Dec 19 - Present)
*   **Goal:** Manual Execution Capability.
*   **Critical Fix:** **Never suppress signals.** Previously, if Paper Funds were $0, the bot validated the signal but stayed silent. *Rule:* Always alert "SIGNAL ONLY - Funds" so the human can trade manually.
*   **Lesson:** **Deployment.** Do not run bot commands locally. Always package (`pack_deploy.sh`) and execute on VM.

## 🚫 "Never Do This" (Regression Prevention)
1.  **Do NOT run `docker-compose up` locally.** The bot logic often depends on DB state that differs from Prod.
2.  **Do NOT use `datetime.now()` without timezone.** The VM will drift from ET market hours.
3.  **Do NOT suppress errors/signals.** If a trade fails (funds, API error), **Alert the User**. Silent failures look like "broken bot".

## 📝 Current Todo / Known Issues
*   [ ] **Optimization:** Refine "Market Panic" logic (currently dumps if SPY drops 2%).
*   [ ] **Visuals:** Dashboard PnL chart needs to be verified after recent database changes.
*   [x] **Alerts:** Fixed silent failure on low balance (Dec 2025).

## 🚀 How to Resume Work
1.  **Deploy:** Always use `./deploy_bot.sh`. Do NOT run `docker-compose` locally on Mac.
2.  **Logs:** Check specific logs via `logs/trade_executor.log` or `logs/market_scanner.log`.
3.  **Verify:** Check `test_simulation.py` for logic changes, but **delete** local temporary test files before deploying.
