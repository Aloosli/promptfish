# 🎣 PromptFish

> **Hook your next big idea.**  
> A minimalist, terminal-based writing prompt generator that fishes for inspiration in your own ebook library.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Style](https://img.shields.io/badge/code%20style-black-000000.svg)

---

## ✨ Features

-   **Deep Sea Fishing**: Recursively scans your Unraid (or any remote) server for `.epub` files.
-   **Smart Catch**: Filters out garbage text, headers, and short fragments to find *actual* sentences.
-   **Zero Friction**: Connects via robust SSH/SFTP (perfect for Tailscale/VPNs).
-   **Beautiful UI**: Slick terminal interface with loading spinners and clean typography.
-   **Private**: Your library stays on your server. No cloud needed (except for GitHub updates!).

---

## 🚀 Installation

### Prerequisites
-   Python 3.8+
-   SSH access to your ebook server (Unraid, Synology, VPS, etc.)
-   An `.epub` collection

### Setup

1.  **Clone the repo**
    ```bash
    git clone https://github.com/Aloosli/promptfish.git
    cd promptfish
    ```

2.  **Install dependencies**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```

3.  **Configure environment**
    Create a `.env` file in the root directory:
    ```bash
    cp .env.example .env  # Or create new
    ```
    
    Fill it with your server details:
    ```ini
    UNRAID_HOST=100.x.x.x           # Tailscale IP or Local IP
    UNRAID_USER=root                # SSH User
    UNRAID_KEY_PATH=/path/to/key    # Path to SSH private key (Recommended)
    # UNRAID_PASSWORD=secret        # Or use password
    UNRAID_BOOK_PATH=/mnt/user/books # Path to your library
    ```

---

## 🎣 Usage

Just run the script and let it fish:

```bash
python main.py
```

### Example Output

```text
 ╔══════════════════════════════════════════════════════════════╗
 ║                 🎣 P R O M P T F I S H                       ║
 ╚══════════════════════════════════════════════════════════════╝

✔ Found 142 books.
  Selected: The Dark Forest - Cixin Liu.epub

╭─────────────────────────── 🎣 Your Writing Prompt ───────────────────────────╮
│                                                                              │
│       “The universe is a dark forest. Every civilization is an armed         │
│        hunter stalking through the trees like a ghost.”                      │
│                                                                              │
╰────────────── from The Dark Forest - Cixin Liu.epub ─────────────────────────╯
```

---

## 🛠️ Configuration

You can tweak the "net" size (sentence length filters) in `main.py`:

```python
# Filter out short garbage and huge blobs
if len(sentence) > 30 and len(sentence) < 400:
```

---

## 🤝 Contributing

Got a better way to extract sentences? Want to add genre filtering?
Fork it, fix it, ship it. PRs welcome!

---
*Built with ❤️ for writers.*
