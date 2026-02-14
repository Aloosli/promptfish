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

FICTION_TAGS = {
    "fiction", "science fiction", "fantasy", "horror", "romance", "mystery",
    "mystery & detective", "crime", "thriller", "thrillers", "suspense",
    "literary", "classics", "dystopian", "cyberpunk", "satire", "absurdist",
    "noir", "paranormal", "magical realism", "dark fantasy", "epic",
    "action & adventure", "historical", "contemporary", "humorous", "humor",
    "litrpg", "litrpg (literary role-playing game)", "science fiction & fantasy",
    "genre fiction", "juvenile fiction", "young adult fiction", "coming of age",
    "alternative history", "apocalyptic", "hard science fiction", "urban",
    "short stories (single author)", "collections & anthologies", "drama",
    "poetry", "vampires", "pirates", "superheroes", "media tie-in",
    "occult & supernatural", "time travel", "alien contact", "space exploration",
    "multiple timelines", "love & romance",
}

DEFAULT_EXCLUDED_SUBJECTS = {
    "cooking", "baking", "courses & dishes", "non-fiction", "nonfiction", "нонфикшн",
    "computers", "python", "programming", "software development & engineering",
    "web programming", "web design", "web services & apis", "javascript",
    "object oriented", "networking", "quality assurance & testing", "salads",
    "diet & nutrition", "vegetables", "vegan", "vegetarian", "quick & easy",
    "herbs; spices; condiments", "soups & stews", "bread", "cakes",
    "ice cream; ices; etc", "appetizers", "comfort food", "canning & preserving",
    "individual chefs & restaurants", "rice & grains", "dairy",
    "specific ingredients", "east asian style", "thai", "vietnamese",
    "indian & south asian", "entertaining", "nutrition", "weight loss", "writing",
    "fiction writing", "creative writing", "authorship", "editing & proofreading",
    "language arts & disciplines", "language arts", "reference", "thesauri",
    "methods", "style manuals", "writing skills", "composition", "book notes",
    "biography & autobiography", "history", "history & surveys",
    "expeditions & discoveries", "medieval", "prehistory", "prehistoric peoples",
    "scandinavia", "russia & the former soviet union", "nordic countries",
    "europe", "united states", "american civil war era", "ancient & classical",
    "self-help", "self help", "personal growth", "self-management", "happiness",
    "motivational", "success", "time management", "memory improvement",
    "journaling", "psychology", "applied psychology",
    "industrial & organizational psychology", "cognitive psychology & cognition",
    "cognitive science", "psychotherapy", "psychoanalysis", "psychopathology",
    "counseling", "post-traumatic stress disorder (ptsd)",
    "attention-deficit disorder (add-adhd)", "attention deficit disorder (add-adhd)",
    "anxieties & phobias", "emotions", "personality", "health & fitness",
    "medical", "internal medicine", "women's health", "alternative therapies",
    "healing", "body; mind & spirit", "spirituality", "mysticism", "religion",
    "psychology of religion", "hallucinogenic drugs and religious experience",
    "ufos & extraterrestrials", "business & economics",
    "business & productivity software", "project management", "careers",
    "education", "education & training", "teaching", "study aids", "study skills",
    "study & test-taking skills", "assessment; testing & measurement",
    "social science", "feminism & feminist theory", "women's studies",
    "activism & social justice", "political", "sustainable development",
    "philosophy", "existentialism", "free will & determinism", "aesthetics",
    "metaphysics", "science", "sports & recreation", "motor sports", "drawing",
    "cartooning", "manga", "art", "comics & graphic novels", "literary criticism",
    "literary collections", "literary figures", "letters", "memoirs",
    "personal memoirs", "essays", "ebook", "book", "non lu",
    "www.it-ebooks.info", "soc035000", "isbn-13: 9780199238293", "subjects",
    "professional", "development", "techniques", "skills", "languages", "technology", "mathematics"
}

DEFAULT_TITLE_KEYWORDS = [
    "recipe", "cookbook", "kefir", "ferment", "nutrition", "diet", "meal prep",
    "python", "javascript", "programming", "mastering", "handbook",
    "learning ipython", "design patterns", "high performance", "unlocked",
    "calibre", "quick start guide", "writer's guide", "emotion amplifiers",
    "save the cat", "novel writing", "how to write", "anatomy of story",
    "emotional craft of fiction", "system for writing", "home learning year",
    "homeschool", "zettelkasten"
]


def get_epub_list(ssh, remote_path):
    """Queries Calibre's metadata.db for all epubs, with optional genre/title filtering.
    Books tagged with any fiction genre are always kept, regardless of other tags."""
    
    # Start with global defaults
    excluded_subjects = DEFAULT_EXCLUDED_SUBJECTS.copy()
    
    # Add any extra from env
    raw = os.getenv("EXCLUDE_SUBJECTS", "")
    if raw.strip():
        extra_subjects = {s.strip().lower() for s in raw.split(",") if s.strip()}
        excluded_subjects.update(extra_subjects)

    # Start with global defaults
    title_keywords = DEFAULT_TITLE_KEYWORDS.copy()
    
    # Add any extra from env
    raw_kw = os.getenv("EXCLUDE_TITLE_KEYWORDS", "")
    if raw_kw.strip():
        extra_keywords = [k.strip().lower() for k in raw_kw.split(",") if k.strip()]
        title_keywords.extend(extra_keywords)

    db_path = os.path.join(remote_path, "metadata.db")
    query = """
        SELECT b.path, d.name, GROUP_CONCAT(t.name, '|')
        FROM books b
        JOIN data d ON b.id = d.book
        LEFT JOIN books_tags_link btl ON b.id = btl.book
        LEFT JOIN tags t ON btl.tag = t.id
        WHERE d.format = 'EPUB'
        GROUP BY b.id, d.name;
    """
    stdin, stdout, stderr = ssh.exec_command(f'sqlite3 "{db_path}" "{query}"')
    raw_output = stdout.read().decode(errors="ignore")

    error = stderr.read().decode().strip()
    if error and not raw_output:
        console.print(f"[yellow]Warning: sqlite3 error: {error}[/]")

    all_epubs = []
    filtered_epubs = []

    for line in raw_output.strip().split("\n"):
        if not line:
            continue
        parts = line.split("|")
        book_path = parts[0]
        file_name = parts[1]
        tags = {p.lower() for p in parts[2:] if p}

        epub_path = f"{remote_path}/{book_path}/{file_name}.epub"
        all_epubs.append(epub_path)

        # If any tag marks it as fiction, always keep it
        if tags & FICTION_TAGS:
            filtered_epubs.append(epub_path)
            continue

        # If it has excluded tags and no fiction tags, skip it
        if excluded_subjects and tags & excluded_subjects:
            continue

        # Untagged books: check title keywords
        if not tags and title_keywords:
            title = file_name.lower()
            if any(kw in title for kw in title_keywords):
                continue

        filtered_epubs.append(epub_path)

    return all_epubs, filtered_epubs


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
            all_epubs, epubs = get_epub_list(ssh, remote_path)
            progress.update(task_search, completed=True, visible=False)

            if not all_epubs:
                console.print("[bold red]No epub files found.[/]")
                return

            console.print(f"[green]✔ Found {len(all_epubs)} books.[/]")

            if len(epubs) < len(all_epubs):
                console.print(f"[green]✔ {len(epubs)} books after filtering.[/]")

            if not epubs:
                console.print("[bold red]No books left after filtering. Check your EXCLUDE_SUBJECTS.[/]")
                return

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

