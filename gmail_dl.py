import imaplib
import email
import os
import logging
from getpass import getpass
from datetime import datetime, timedelta
import email.utils
import argparse
from email.header import decode_header
import base64
import re
from typing import Tuple, List, Optional, Union

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def decode_gmail_label(label: str) -> str:
    def decode_modified_utf7(s: str) -> str:
        if not s.startswith('&'):
            return s
        s = s[1:-1]  # Remove & and -
        pad = len(s) % 4
        if pad:
            s += '=' * (4 - pad)
        try:
            decoded = base64.b64decode(s)
            # According to Claude:
            # UTF-16BE is used here because it's what Gmail's IMAP implementation historically chose for encoding
            # non-ASCII mailbox names. This choice was made when UTF-16 was more common for internationalization
            return decoded.decode('utf-16be')
        except:
            return s

    # Handle escaped quotes and dashes
    label = label.replace('\\"', '"')

    # Split encoded/plain segments
    parts = re.findall(r'(&[^-]+-)|([^&]+)', label)
    decoded_parts: List[str] = []

    for encoded, plain in parts:
        if encoded:
            decoded_parts.append(decode_modified_utf7(encoded))
        if plain:
            decoded_parts.append(plain)

    return ''.join(decoded_parts)

def decode_mime_words(s: str) -> str:
    return ''.join(
        word.decode(encoding or 'utf8') if isinstance(word, bytes) else word
        for word, encoding in decode_header(s)
    )

def get_month_range(current_month: bool = False) -> Tuple[datetime, datetime]:
    today = datetime.now()
    first_day_of_current_month = today.replace(day=1)

    if current_month:
        last_day = (first_day_of_current_month + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        return first_day_of_current_month, last_day

    last_day_of_previous_month = first_day_of_current_month - timedelta(days=1)
    first_day_of_previous_month = last_day_of_previous_month.replace(day=1)
    return first_day_of_previous_month, last_day_of_previous_month

def get_year_range(current_year: bool = False) -> Tuple[datetime, datetime]:
    year = datetime.now().year - (0 if current_year else 1)
    return (
        datetime(year, 1, 1),
        datetime(year, 12, 31)
    )

def download_attachments(
        email_address: str,
        password: str,
        output_dir: str,
        label: str,
        from_: str,
        month: bool = True,
        year: bool = False,
        current: bool = False,
        dry_run: bool = False
) -> None:

    if month == year:
        raise ValueError(f"Either month or year must be selected (but only one), month={month}, year={year}")

    imap_server = "imap.gmail.com"
    imap_port = 993
    # Create an IMAP4 client encrypted with SSL
    mail = imaplib.IMAP4_SSL(imap_server, imap_port)
    try:
        # Login to the account
        mail.login(email_address, password)

        list_labels(mail)

        # Select the mailbox (label) you want to search in
        label_to_search = f'"{label}"'
        logging.info(f"Selecting label: {label_to_search}")
        status, messages = mail.select(label_to_search)

        if status != "OK":
            logging.error(f"Error selecting label {label_to_search}. Please check if the label exists.")
            mail.logout()
            return

        # Get date range for the previous or current month
        if month:
            start_date, end_date = get_month_range(current)
        else:
            start_date, end_date = get_year_range(current)

        # Format dates for IMAP search
        since_date = start_date.strftime("%d-%b-%Y")
        before_date = (end_date + timedelta(days=1)).strftime("%d-%b-%Y")

        # Search for emails from the specific sender within the date range
        search_criteria = f'(FROM "{from_}" SINCE "{since_date}" BEFORE "{before_date}")'
        logging.info(f"Search criteria: {search_criteria}")
        _, message_numbers = mail.search(None, search_criteria)
        logging.info(f"Number of messages found: {len(message_numbers[0].split())}")

        if not message_numbers[0]:
            logging.info("No messages found.")
            return

        duplicate_count = 0
        for num in message_numbers[0].split():
            _, msg = mail.fetch(num, "(RFC822)")
            email_body = msg[0][1]
            email_message = email.message_from_bytes(email_body)

            # Get email date, subject, and sender
            date_tuple = email.utils.parsedate_tz(email_message['Date'])
            subject = decode_mime_words(email_message['Subject'])
            sender = decode_mime_words(email_message['From'])

            if date_tuple:
                email_date = datetime.fromtimestamp(email.utils.mktime_tz(date_tuple))
                logging.info(f"\nProcessing email from: {email_date.strftime('%Y-%m-%d')}")
                logging.info(f"Subject: {subject}")
                logging.info(f"From: {sender}")

            # Process attachments
            attachments_found = save_email_attachments(email_message, output_dir, dry_run, duplicate_count)

            if not attachments_found:
                logging.info("No matching attachments found in this email.")
    finally:
        # Close the connection
        mail.close()
        mail.logout()



def save_email_attachments(email_message, output_dir, dry_run, duplicate_count):
    attachments_found = False
    for part in email_message.walk():
        # email_message(multipart / mixed)
        # ├── text_part(text / plain)
        # ├── html_part(text / html)
        # └── attachment_part(application / pdf)
        if part.get_content_maintype() == "multipart":
            continue

        #  The Content-Disposition header is specifically used to indicate whether a MIME part
        #  should be displayed inline in the email or treated as an attachment.
        if part.get("Content-Disposition") is None:
            continue

        filename = part.get_filename()
        if filename:
            filename = decode_mime_words(filename)
            filepath = output_filepath(filename, output_dir)

            if dry_run:
                logging.info(f"Would download: {filename} and save to {filepath}")
            else:
                try:
                    payload = part.get_payload(decode=True)
                    if payload:
                        with open(filepath, "wb") as f:
                            f.write(payload)
                        logging.info(f"Downloaded: {filename} and saved to {filepath}")
                        attachments_found = True
                    else:
                        logging.warning(f"Empty payload for attachment: {filename}")
                except Exception as e:
                    logging.error(f"Error saving attachment {filename}: {str(e)}")
    return attachments_found


def output_filepath(filename, output_dir):
    orig_filepath = os.path.join(output_dir, filename)
    filepath = orig_filepath
    duplicate_count = 0
    while os.path.exists(filepath):
        duplicate_count += 1
        split_filepath = os.path.splitext(orig_filepath)
        filepath = f"{split_filepath[0]}_{duplicate_count}{split_filepath[1]}"
    return filepath


def list_labels(mail):
    # List all available labels/folders
    _, mailboxes = mail.list()
    logging.info("Available labels:")
    for mailbox in mailboxes:
        logging.info(mailbox.decode())
        logging.info(decode_gmail_label(mailbox.decode().split(' "/" ')[-1].strip('"')))


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Gett receipt attachments from Gmail")
    parser.add_argument("--dry-run", action="store_true", help="Run in dry mode without saving attachments")
    parser.add_argument("--label", default="Bills", help="Gmail label to search in (default: Bills)")
    parser.add_argument("--from", dest="from_", default="do-not-reply@gett.com",
                        help="Email address to filter by")
    parser.add_argument("--month", action="store_true", help="True for one month range (default: False)")
    parser.add_argument("--year", action="store_true", help="True for one year range (default: False)")
    parser.add_argument("--current", action="store_true",
                        help="True for current month/year range otherwise previous month/year range (default: False")
    args = parser.parse_args()
    email_address = input("Enter your Gmail address: ")
    password = getpass("Enter your password: ")
    output_dir = input("Enter the directory to save attachments: ")
    if not args.dry_run and not os.path.exists(output_dir):
        os.makedirs(output_dir)
    download_attachments(email_address, password, output_dir, args.label, args.from_,
                         month=args.month, year=args.year, current=args.current, dry_run=args.dry_run)
    logging.info("\nAttachment download completed.")


if __name__ == "__main__":
    main()
