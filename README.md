# 🚍 BusBot

BusBot is a Telegram bot designed to monitor **non-guaranteed bus trips** (cancellations) from [Start Romagna](https://www.startromagna.it/corse-non-garantite/). It provides real-time notifications to users when their specific bus line is affected by cancellations in the areas of Forlì-Cesena, Rimini, and Ravenna.

---

## 🛠 Technical Architecture

The project is built with a modular Python architecture designed for stability and efficient resource usage, making it ideal for deployment on low-power devices like a Raspberry Pi.

### Core Components

1. **Scraper (`scraper.py`)**:
    * **Parsing Strategy**: Uses `BeautifulSoup4` to parse the Start Romagna cancellation page. It dynamically identifies the data table (skipping filter-only tables) and handles the site's 6-column layout.
    * **Prefix Matching**: Implements custom matching logic (`linea_matches`) to handle bus line names that include city suffixes (e.g., target "8" will correctly match "8 Forlì").
    * **API Targeting**: Programmatically interacts with the Start Romagna services endpoint using the `bacino` and `date` parameters.

2. **Telegram Bot (`bot.py`)**:
    * **Framework**: Built on `python-telegram-bot`.
    * **State Management**: Utilizes a `ConversationHandler` for a guided user setup process (Selecting area via Inline Keyboard → Entering bus line number).
    * **Asynchronous Processing**: All Telegram interactions and API calls are fully asynchronous to ensure responsiveness.

3. **Persistence Layer (`config.py`)**:
    * **Storage**: Maintains user configurations in a lightweight `user_config.json` file.
    * **Docker Integration**: Supports the `CONFIG_PATH` environment variable, allowing the JSON file to be mapped to a persistent Docker volume.

4. **Scheduler (`main.py`)**:
    * **Interval**: Runs a background job every 30 minutes.
    * **Optimized requests**: Groups users by area (`bacino`) to fetch data once per area per cycle, regardless of the number of users.
    * **Hash-based Deduplication**: Computes a hash of the cancellation set to prevent sending duplicate notifications for the same event.

---

## 🚀 Deployment & Usage

### Local Installation

1. **Install dependencies**:

    ```bash
    pip install -r requirements.txt
    ```

2. **Configuration**:
    Create a `.env` file (refer to `.env.example`) and add your Telegram Bot Token:

    ```bash
    TELEGRAM_BOT_TOKEN=your_token_here
    ```

3. **Run**:

    ```bash
    python main.py
    ```

### Docker Deployment (Recommended for Raspberry Pi)

The project includes a multi-architecture `Dockerfile` (supporting x86 and ARM/Raspberry Pi) and a `docker-compose.yml` for simplified management.

1. **Start Services**:

    ```bash
    docker compose up -d --build
    ```

2. **Persistence**:
    User data is stored in a named volume `busbot-data`. This ensures configuration is preserved across container restarts or image updates.

---

## 📋 Bot Commands

| Command | Description |
| :--- | :--- |
| `/start` | Initiate setup or reconfigure (area & line selection). |
| `/check` | Manually trigger an immediate check for cancellations. |
| `/status` | View your current monitoring settings. |
| `/stop` | Disable monitoring and clear your preferences. |

*Note: The bot automatically sends a check result immediately after configuration is completed.*

---

## 🧪 Testing and Verification

The project includes a comprehensive test suite in `tests/test_busbot.py` covering scraper parsing, line matching edge cases, and configuration management.

To run the tests:

```bash
python -m pytest tests/ -v
```

### Key Verified Features

* **Prefix Matching**: Verified that line numbers (3, 92, S1) correctly match the site's "NUMBER CITY" format.
* **Table Extraction**: Verified successful extraction from real-world HTML snapshots with multiple tables.
* **Data Integrity**: Verified that hashes correctly prevent duplicate notifications.
