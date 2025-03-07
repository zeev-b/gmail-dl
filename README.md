# Gmail Attachment Downloader

## Overview
This Python script allows users to download attachments from their Gmail inbox based on specific search criteria such as sender email, label, and date range. It connects to Gmail via IMAP, searches for emails within a defined period, and downloads any attachments found in those emails.

## Features
- Connects to Gmail using IMAP.
- Searches emails based on:
  - Sender email address.
  - Gmail label (folder).
  - Date range (previous or current month/year).
- Decodes and downloads attachments from matching emails.
- Supports a dry-run mode to preview downloads without saving files.
- Handles duplicate filenames by renaming them appropriately.

## Prerequisites
- Python 3.7+
- A Gmail account with IMAP access enabled.

## Installation
1. Clone this repository or download the script.
2. Ensure you have Python installed (3.7 or higher).
3. Install any required dependencies (if needed, though this script only uses built-in modules).

```sh
python -m venv venv  # Optional virtual environment setup
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate  # On Windows
pip install -r requirements.txt  # If external dependencies are added in the future
```

## Usage
Run the script using the command line:

```sh
python gmail_dl.py
```

You will be prompted to enter your Gmail credentials and output directory.

Alternatively, you can use command-line arguments:

```sh
python gmail_dl.py --label "Bills" --from "example@domain.com" --month --current
```

### Command-Line Arguments
| Argument      | Description |
|--------------|-------------|
| `--dry-run`  | Runs the script without downloading attachments (preview mode). |
| `--label`    | Specifies the Gmail label to search (default: "Bills"). |
| `--from`     | Filters emails by sender's email address. |
| `--month`    | Searches emails within the last or current month. |
| `--year`     | Searches emails within the last or current year. |
| `--current`  | Specifies whether to search in the current month/year instead of the previous one. |

## Enabling IMAP in Gmail
To use this script, you must enable IMAP access in your Gmail account:
1. Open Gmail.
2. Go to **Settings** > **See all settings**.
3. Navigate to the **Forwarding and POP/IMAP** tab.
4. Under "IMAP access," select "Enable IMAP" and save changes.

## Security Considerations
- It is **not** recommended to enter your password directly in the terminal. Consider using [App Passwords](https://support.google.com/accounts/answer/185833) instead.
- Avoid storing your credentials in plaintext.

## License
This project is licensed under the **GNU GENERAL PUBLIC LICENSE Version 3, 29 June 2007**.

## Contributing
Feel free to submit issues and pull requests to improve this script!



