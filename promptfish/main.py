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
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text
from rich.align import Align

# Suppress ebooklib warnings
warnings.filterwarnings('ignore')

# Initialize Rich Console
console = Console()

BANNER = """
 [bold cyan]╔══════════════════════════════════════════════════════════════╗[/]
 [bold cyan]║                                                              ║[/]
 [bold cyan]║[/]                 [bold white]🎣 P R O M P T F I S H[/]                       [bold cyan]║[/]
 [bold cyan]║[/]                                                              [bold cyan]║[/]
 [bold cyan]╚══════════════════════════════════════════════════════════════╝[/]
"""

def connect_to_server():
    """Establishes an SSH connection to the Unraid server."""
    host = os.getenv("UNRAID_HOST")
    user = os.getenv("UNRAID_USER", "root")
    password = os.getenv("UNRAID_PASSWORD")
    key_path = os.getenv("UNRAID_KEY_PATH")
    
    if not host:
        console.print("[bold red]Error:[/] UNRAID_HOST not set in .env")
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
        console.print(f"[bold red]Failed to connect to {host}:[/] {e}")
        sys.exit(1)

def get_epub_list(ssh, remote_path):
    """Finds all .epub files recursively using the 'find' command."""
    # Using 'find' is much faster than walking SFTP
    stdin, stdout, stderr = ssh.exec_command(f'find "{remote_path}" -type f -name "*.epub"')
    
    file_list = []
    for line in stdout:
        file_list.append(line.strip())
        
    error = stderr.read().decode().strip()
    if error and not file_list:
             console.print(f"[yellow]Warning: 'find' command stderr: {error}[/]")
             
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
            start = 0
            for i in range(len(text)):
                if text[i] in ['.', '?', '!'] and (i+1 >= len(text) or text[i+1].isspace()):
                    sentence = text[start:i+1].strip()
                    if len(sentence) > 30 and len(sentence) < 400: # Filter out short garbage and huge blobs
                        sentences.append(sentence)
                    start = i + 1
                    
    return sentences

def main():
    console.print(BANNER)
    load_dotenv()
    
    remote_path = os.getenv("UNRAID_BOOK_PATH")
    if not remote_path:
        console.print("[bold red]Error:[/] UNRAID_BOOK_PATH not set in .env")
        sys.exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=False
    ) as progress:
        
        task_connect = progress.add_task("[cyan]Connecting to Unraid...[/]", total=None)
        ssh = connect_to_server()
        progress.update(task_connect, completed=True, visible=False)
        
        try:
            task_search = progress.add_task(f"[cyan]Searching for epubs in {remote_path}...[/]", total=None)
            epubs = get_epub_list(ssh, remote_path)
            progress.update(task_search, completed=True, visible=False)

            if not epubs:
                console.print("[bold red]No epub files found.[/]")
                return

            console.print(f"[green]✔ Found {len(epubs)} books.[/]")
            
            # Pick a random book
            chosen_book_path = random.choice(epubs)
            book_name = os.path.basename(chosen_book_path)
            
            console.print(f"  Selected: [bold yellow]{book_name}[/]")
            
            # Download
            task_download = progress.add_task("[cyan]Downloading book...[/]", total=None)
            sftp = ssh.open_sftp()
            with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
                sftp.get(chosen_book_path, tmp.name)
                tmp_path = tmp.name
            sftp.close()
            progress.update(task_download, completed=True, visible=False)
            
            # Process
            task_process = progress.add_task("[cyan]Extracting text...[/]", total=None)
            try:
                sentences = extract_sentences_from_epub(tmp_path)
                progress.update(task_process, completed=True, visible=False)
                
                if sentences:
                    prompt = random.choice(sentences)
                    
                    console.print("\n")
                    console.print(Panel(
                        Align.center(f"[bold white]{prompt}[/]"),
                        title="[bold cyan]🎣 Your Writing Prompt[/]",
                        border_style="cyan",
                        padding=(1, 2),
                        subtitle=f"[dim]from {book_name}[/]"
                    ))
                    console.print("\n")
                else:
                    console.print("[bold red]Could not extract any valid sentences from this book.[/]")
            except Exception as e:
                console.print(f"[bold red]Error reading epub:[/] {e}")
            finally:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)

        finally:
            ssh.close()

if __name__ == "__main__":
    main()

