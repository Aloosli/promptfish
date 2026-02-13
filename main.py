import os
import random
import tempfile
import paramiko
from dotenv import load_dotenv
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import sys
import warnings

# Suppress ebooklib warnings
warnings.filterwarnings('ignore')

def connect_to_server():
    """Establishes an SSH connection to the Unraid server."""
    host = os.getenv("UNRAID_HOST")
    user = os.getenv("UNRAID_USER", "root")
    password = os.getenv("UNRAID_PASSWORD")
    key_path = os.getenv("UNRAID_KEY_PATH")
    
    if not host:
        print("Error: UNRAID_HOST not set in .env")
        sys.exit(1)

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        connect_kwargs = {"hostname": host, "username": user}
        if key_path:
            connect_kwargs["key_filename"] = key_path
        elif password:
            connect_kwargs["password"] = password
        else:
            # Try default agent/keys
            pass
            
        ssh.connect(**connect_kwargs)
        return ssh
    except Exception as e:
        print(f"Failed to connect to {host}: {e}")
        sys.exit(1)

def get_epub_list(ssh, remote_path):
    """Finds all .epub files recursively using the 'find' command."""
    print(f"Searching for epubs in {remote_path}...")
    # Using 'find' is much faster than walking SFTP
    stdin, stdout, stderr = ssh.exec_command(f'find "{remote_path}" -type f -name "*.epub"')
    
    file_list = []
    for line in stdout:
        file_list.append(line.strip())
        
    error = stderr.read().decode().strip()
    if error:
        # Some permission denied errors are normal, but let's log if list is empty
        if not file_list:
             print(f"Warning: 'find' command stderr: {error}")
             
    return file_list

def extract_sentences_from_epub(epub_path):
    """Reads epub and extracts valid sentences."""
    book = epub.read_epub(epub_path)
    sentences = []
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text = soup.get_text(separator=' ')
            
            # Basic cleaning and splitting
            # Split by period followed by space, or newline
            start = 0
            for i in range(len(text)):
                if text[i] in ['.', '?', '!'] and (i+1 >= len(text) or text[i+1].isspace()):
                    sentence = text[start:i+1].strip()
                    if len(sentence) > 20 and len(sentence) < 500: # Filter out short garbage and huge blobs
                        sentences.append(sentence)
                    start = i + 1
                    
    return sentences

def main():
    load_dotenv()
    
    remote_path = os.getenv("UNRAID_BOOK_PATH")
    if not remote_path:
        print("Error: UNRAID_BOOK_PATH not set in .env")
        sys.exit(1)

    ssh = connect_to_server()
    
    try:
        epubs = get_epub_list(ssh, remote_path)
        if not epubs:
            print("No epub files found.")
            return

        print(f"Found {len(epubs)} books.")
        
        # Pick a random book
        chosen_book = random.choice(epubs)
        print(f"Selected: {os.path.basename(chosen_book)}")
        
        # Download to temp file
        sftp = ssh.open_sftp()
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            print("Downloading...")
            sftp.get(chosen_book, tmp.name)
            tmp_path = tmp.name
            
        sftp.close()
        
        # Process
        print("Extracting text...")
        try:
            sentences = extract_sentences_from_epub(tmp_path)
            if sentences:
                print("\n" + "="*40)
                print("YOUR WRITING PROMPT:")
                print("="*40 + "\n")
                print(random.choice(sentences))
                print("\n" + "="*40)
            else:
                print("Could not extract any valid sentences from this book.")
        except Exception as e:
            print(f"Error reading epub: {e}")
        finally:
            os.remove(tmp_path)

    finally:
        ssh.close()

if __name__ == "__main__":
    main()
