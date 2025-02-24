#!/usr/bin/env python3

import datetime
import logging
import os
from pathlib import Path
import sqlite3
import re
import sys
import argparse
import multiprocessing as mp
from multiprocessing.synchronize import RLock
from typing import Dict, List, Optional, Set, Tuple
from mnemonic import Mnemonic
import signal
import threading
from contextlib import contextmanager
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeRemainingColumn,
)
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
import time
from collections import Counter

from seed_parser.wallet import *

# Initialize rich console
console = Console()

# Configuration
PARSE_ETH = False  # Fixed typo from PARCE to PARSE
LOG_DIR = Path('./logs')
BASE_DIR = Path(__file__).parent / 'data'  # Updated to point to package data directory
SOURCE_DIR = Path('D:/')  # Configurable via CLI

# Statistics tracking
stats = {
    'files_processed': 0,
    'bytes_processed': 0,
    'phrases_found': 0,
    'eth_keys_found': 0,
    'errors': 0
}
stats_lock = threading.Lock()

# File filtering configuration
BAD_EXTENSIONS: Set[str] = {
    '.jpg', '.png', '.jpeg', '.ico', '.gif', '.iso',
    '.dll', '.sys', '.zip', '.rar', '.7z', '.cab', '.dat'
}

BAD_DIRS: List[str] = [
    'ololololz'  # Add more as needed
]

BAD_FILES: List[str] = [
    'ololololo'  # Add more as needed
]

ENABLE_LANG: List[str] = ['english']  # hdwallet only supports English mnemonics

WORDS_CHAIN_SIZES: Set[int] = {12, 15, 18, 24}
EXWORDS: int = 2
CHUNK_SIZE: int = 1024 * 1024  # 1MB chunks for file reading

# Set up logging with rich handler
LOG_DIR.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)]
)
logger = logging.getLogger(__name__)

# Initialize mnemonic validator
MNEMONIC_VALIDATOR = Mnemonic("english")

class DBController:
    def __init__(self, in_memory: bool = False) -> None:
        """Initialize database controller with optional in-memory storage."""
        if in_memory:
            self.conn = sqlite3.connect(":memory:", detect_types=sqlite3.PARSE_DECLTYPES)
        else:
            db_path = LOG_DIR / 'phrases.db'
            self.conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
        
        self.conn.execute("PRAGMA journal_mode=WAL")  # Better concurrent access
        self.conn.execute("PRAGMA synchronous=NORMAL")  # Better performance
        self.conn.execute("CREATE TABLE IF NOT EXISTS phrases (phrase VARCHAR(500) PRIMARY KEY, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_phrases_created ON phrases(created_at)")
        self._lock = threading.Lock()
        self.batch_size = 1000
        self.phrase_buffer: List[str] = []

    @contextmanager
    def transaction(self):
        """Context manager for database transactions."""
        with self._lock:
            try:
                yield
                self.conn.commit()
            except Exception as e:
                self.conn.rollback()
                logger.error(f"Database transaction failed: {e}")
                raise

    def insert_phrase(self, phrase: str) -> None:
        """Insert a phrase into the database with batching."""
        self.phrase_buffer.append(phrase)
        if len(self.phrase_buffer) >= self.batch_size:
            self.flush_buffer()

    def flush_buffer(self) -> None:
        """Flush the phrase buffer to the database."""
        if not self.phrase_buffer:
            return
            
        with self.transaction():
            self.conn.executemany(
                "INSERT OR IGNORE INTO phrases (phrase) VALUES (?)",
                [(p,) for p in self.phrase_buffer]
            )
        self.phrase_buffer.clear()

    def phrase_in_db(self, phrase: str) -> bool:
        """Check if a phrase exists in the database."""
        with self._lock:
            cursor = self.conn.execute(
                "SELECT EXISTS(SELECT 1 FROM phrases WHERE phrase = ? LIMIT 1)",
                (phrase,)
            )
            return bool(cursor.fetchone()[0])

    def __del__(self) -> None:
        """Cleanup database resources."""
        try:
            self.flush_buffer()
            self.conn.close()
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")

def update_stats(key: str, value: int = 1) -> None:
    """Thread-safe update of statistics."""
    with stats_lock:
        stats[key] += value

def create_stats_table() -> Table:
    """Create a rich table for statistics display."""
    table = Table(title="Scan Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    with stats_lock:
        table.add_row("Files Processed", str(stats['files_processed']))
        table.add_row("Data Processed", f"{stats['bytes_processed'] / 1024 / 1024:.2f} MB")
        table.add_row("Phrases Found", str(stats['phrases_found']))
        table.add_row("ETH Keys Found", str(stats['eth_keys_found']))
        table.add_row("Errors", str(stats['errors']), style="red")
    
    return table

def valid_phrase(words: List[str]) -> bool:
    """Validate if a phrase meets the word repetition criteria."""
    if EXWORDS == 0:
        return True
    return max(words.count(w) for w in words) < EXWORDS

def write_log(log_name: str, data: str) -> None:
    """Write data to a log file with proper locking."""
    log_path = LOG_DIR / log_name
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"{data}\n")
    except Exception as e:
        logger.error(f"Error writing to log {log_name}: {e}")

def get_phrase_arr(raw: List[str]) -> List[List[str]]:
    """Get possible phrase arrays from raw word list."""
    raw_len = len(raw)
    if raw_len in WORDS_CHAIN_SIZES:
        return [raw]
    elif raw_len < min(WORDS_CHAIN_SIZES):
        return []
    
    phrase_arr = []
    for m in sorted(s for s in WORDS_CHAIN_SIZES if s < raw_len):
        for i in range(raw_len - m + 1):
            p = raw[i:i + m]
            if len(p) == m:
                phrase_arr.append(p)
    return phrase_arr

def validate_mnemonic(mnemonic: str) -> bool:
    """Validate a mnemonic phrase."""
    try:
        return MNEMONIC_VALIDATOR.check(mnemonic)
    except Exception:
        return False

def find_in_file(path: str, log_lock: RLock, log_files: Dict[str, str]) -> None:
    """Process a single file looking for seed phrases."""
    try:
        file_path = Path(path)
        if not file_path.is_file():
            return

        # Read file in chunks to handle large files
        words_chain: List[str] = []
        db = DBController()
        file_size = file_path.stat().st_size
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                try:
                    update_stats('bytes_processed', len(chunk))
                    
                    # Try different encodings
                    for encoding in ('UTF-8', 'CP437', 'ISO-8859-1'):
                        try:
                            data = chunk.decode(encoding)
                            break
                        except UnicodeDecodeError:
                            continue
                    else:
                        continue  # Skip if no encoding works

                    # Process words in the chunk
                    for word in re.finditer(r'\b[a-z]+\b', data.lower()):
                        word = word.group(0)
                        # Only add words that could be part of a BIP39 mnemonic
                        if 3 <= len(word) <= 8:  # BIP39 words are typically 3-8 characters
                            words_chain.append(word)
                        
                        # Process chain when it reaches maximum size
                        if len(words_chain) >= max(WORDS_CHAIN_SIZES):
                            process_word_chain(words_chain, path, db, log_lock, log_files)
                            words_chain = words_chain[1:]  # Keep a sliding window

                    # Process any remaining chain
                    if len(words_chain) >= min(WORDS_CHAIN_SIZES):
                        process_word_chain(words_chain, path, db, log_lock, log_files)

                except Exception as e:
                    logger.error(f"Error processing chunk in {path}: {e}")
                    update_stats('errors')
                    continue

        update_stats('files_processed')

    except Exception as e:
        logger.error(f"Error processing file {path}: {e}")
        update_stats('errors')

def process_word_chain(
    words_chain: List[str],
    path: str,
    db: DBController,
    log_lock: RLock,
    log_files: Dict[str, str]
) -> None:
    """Process a chain of words for potential seed phrases."""
    if not words_chain:
        return

    for phrase in get_phrase_arr(words_chain):
        words_str = ' '.join(phrase)
        if not valid_phrase(phrase):
            continue

        if not validate_mnemonic(words_str) or db.phrase_in_db(words_str):
            continue

        try:
            full_log, coin_log = print_wallets_bip(words_str)
            db.insert_phrase(words_str)
            update_stats('phrases_found')
            
            with log_lock:
                write_log('found.log', f"File: {path}")
                write_log('found.log', f"Phrase: {words_str}")
                write_log('found.log', full_log)
                write_log('found.log', "-" * 80)
                
                for coin, addresses in coin_log.items():
                    if coin in log_files:
                        write_log(log_files[coin], f"File: {path}")
                        write_log(log_files[coin], f"Phrase: {words_str}")
                        for addr in addresses:
                            write_log(log_files[coin], addr)
                        write_log(log_files[coin], "-" * 80)
                
                # Print to console with color
                console.print(f"[green]Found seed phrase in:[/green] [cyan]{path}[/cyan]")
                console.print(f"[yellow]Phrase:[/yellow] {words_str}")
        except Exception as e:
            logger.error(f"Error processing phrase from {path}: {e}")
            update_stats('errors')

def process_eth_addresses(
    data: str,
    path: str,
    log_lock: RLock,
    log_files: Dict[str, str]
) -> None:
    """Process potential Ethereum addresses in the data."""
    for match in re.finditer(r"(?:[^\w/\\]|^)([a-f0-9]{64})(?:\W|$)", data, re.I):
        try:
            private_key = match[1]
            address = ext_addr(private_key)
            update_stats('eth_keys_found')
            
            log_entry = (
                f"{path}\n"
                f"ETH-Privkey:{private_key}\n"
                f"ETH-Address:{address}\n"
                f"{'-'*24}\n"
            )

            if log_files['ETH_FULL_LOG']:
                with log_lock:
                    write_log(log_files['ETH_FULL_LOG'], log_entry)
                    write_log(log_files['ETH_A_LOG'], address)
                    write_log(log_files['ETH_P_LOG'], f"{address}:{private_key}")
                    
                    # Print to console with color
                    console.print(f"[green]Found ETH key in:[/green] [cyan]{path}[/cyan]")
                    console.print(f"[yellow]Address:[/yellow] {address}")
        except Exception as e:
            logger.error(f"Error processing ETH address: {e}")
            update_stats('errors')

def thread_fun(
    directory: str,
    log_lock: RLock,
    log_files: Dict[str, str]
) -> str:
    """Worker function for processing directories."""
    try:
        # Process files in directory
        dir_path = Path(directory)
        for item in dir_path.rglob('*'):
            if not item.is_file():
                continue
                
            if any(bad_dir.lower() in str(item).lower() for bad_dir in BAD_DIRS):
                continue

            if item.suffix.lower() in BAD_EXTENSIONS:
                continue
                
            if any(bad_file.lower() in item.stem.lower() for bad_file in BAD_FILES):
                continue

            try:
                find_in_file(str(item), log_lock, log_files)
            except Exception as e:
                logger.error(f"Error processing file {item}: {e}")
                update_stats('errors')

    except Exception as e:
        logger.error(f"Error in thread processing directory {directory}: {e}")
        update_stats('errors')
    
    return directory

def validate_directory(directory: Path) -> None:
    """Validate the input directory and raise appropriate exceptions."""
    try:
        if not directory.exists():
            raise FileNotFoundError(f"Directory does not exist: {directory}")
        if not directory.is_dir():
            raise NotADirectoryError(f"Path exists but is not a directory: {directory}")
        if not os.access(directory, os.R_OK):
            raise PermissionError(f"No read permission for directory: {directory}")
        
        # Check if directory is empty
        try:
            next(directory.iterdir())
        except StopIteration:
            raise ValueError(f"Directory is empty: {directory}")
    except Exception as e:
        # Catch any other potential errors during validation
        raise ValueError(f"Error validating directory {directory}: {str(e)}")

def main() -> None:
    """Main entry point for the seed phrase parser."""
    # Show startup banner
    console.print(Panel.fit(
        "[bold green]Cryptocurrency Seed Phrase Parser[/bold green]\n"
        "[yellow]A high-performance tool for finding and validating cryptocurrency wallets[/yellow]",
        border_style="blue"
    ))

    parser = argparse.ArgumentParser(
        description='Cross-platform cryptocurrency seed phrase and private key extractor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -d /path/to/scan -t 8 -w
  %(prog)s -d /path/to/scan --no-eth
  %(prog)s -d /path/to/scan --memory-db

For more information, visit: https://github.com/yourusername/seed_parser
        """
    )
    parser.add_argument('-w', '--write-logs', action='store_true', default=True,
                        help='Enable logging (default: True)')
    parser.add_argument('-t', '--threads', type=int, default=mp.cpu_count(),
                        help='Number of threads (default: CPU count)')
    parser.add_argument('-d', '--directory', type=str, required=True,
                        help='Source directory to scan')
    parser.add_argument('--no-eth', action='store_true',
                        help='Disable Ethereum private key scanning')
    parser.add_argument('--memory-db', action='store_true',
                        help='Use in-memory database (faster but higher memory usage)')

    args = parser.parse_args()

    try:
        # Create logs directory
        LOG_DIR.mkdir(exist_ok=True, mode=0o700)  # Secure permissions for logs

        # Set up logging before anything else
        if args.write_logs:
            timestamp = datetime.datetime.now().strftime('%d-%m-%Y_%H-%M-%S')
            log_files = {
                'SEED_LOG': f'seed-{timestamp}.txt',
                'ADDR_log': f'-addresses-{timestamp}.txt',
                'FULL_LOG': f'full-log-{timestamp}.txt',
                'ETH_FULL_LOG': f'eth-full-log-{timestamp}.txt',
                'ETH_A_LOG': f'eth-a-log-{timestamp}.txt',
                'ETH_P_LOG': f'eth-p-log-{timestamp}.txt'
            }
        else:
            log_files = dict.fromkeys(
                ['SEED_LOG', 'ADDR_log', 'FULL_LOG', 'ETH_FULL_LOG', 'ETH_A_LOG', 'ETH_P_LOG']
            )

        # Validate source directory
        source_dir = Path(args.directory).resolve()
        validate_directory(source_dir)
        
        # Validate thread count
        if args.threads < 1:
            logger.warning(f"Invalid thread count {args.threads}, using 1 thread")
            args.threads = 1
        elif args.threads > mp.cpu_count() * 2:
            logger.warning(
                f"Thread count {args.threads} is more than 2x CPU count, "
                f"limiting to {mp.cpu_count() * 2} threads"
            )
            args.threads = mp.cpu_count() * 2

        # Initialize database
        try:
            db = DBController(in_memory=args.memory_db)
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            sys.exit(1)

        # Set up multiprocessing
        manager = mp.Manager()
        log_lock = manager.RLock()
        
        # Configure process pool with maxtasksperchild to prevent memory leaks
        work_pool = mp.Pool(
            processes=args.threads,
            maxtasksperchild=100  # Restart workers periodically to prevent memory leaks
        )

        try:
            # Process directories
            directories = [d for d in source_dir.iterdir() if d.is_dir()]
            if not directories:
                logger.warning(f"No subdirectories found in {source_dir}")
                # Still process the root directory itself
                directories = [source_dir]

            params = [(str(d), log_lock, log_files) for d in directories]
            
            console.print(f"[bold cyan]Starting scan with {args.threads} threads...[/bold cyan]")
            console.print(f"[cyan]Scanning directory:[/cyan] {source_dir}")
            console.print(f"[cyan]Found {len(directories)} directories to process[/cyan]")
            
            # Create progress display
            progress = Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                expand=True,
                transient=True  # Allow the progress bar to be part of other displays
            )

            # Create a layout that combines progress and stats
            def make_layout():
                layout = Table.grid(expand=True)
                layout.add_row(progress)
                layout.add_row(create_stats_table())
                return layout

            # Create the progress task before entering Live context
            scan_task = progress.add_task(
                "[cyan]Scanning directories...", 
                total=len(directories)
            )

            # Single Live display for both progress and stats
            with Live(make_layout(), console=console, refresh_per_second=1):
                for i, result in enumerate(work_pool.starmap(thread_fun, params)):
                    progress.update(scan_task, advance=1)
                    # No need to manually update layout, Live will refresh automatically
            
            # Show final statistics
            console.print("\n[bold green]Scan completed![/bold green]")
            console.print(create_stats_table())
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Received interrupt signal, cleaning up...[/yellow]")
            work_pool.terminate()
        except Exception as e:
            logger.error(f"Error during processing: {e}")
            raise
        finally:
            work_pool.close()
            work_pool.join()
            db.flush_buffer()  # Ensure all phrases are written

    except (FileNotFoundError, NotADirectoryError, PermissionError) as e:
        logger.error(str(e))
        sys.exit(1)
    except ValueError as e:
        logger.error(str(e))
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

def signal_handler(signum: int, frame) -> None:
    """Handle interrupt signals gracefully."""
    console.print("\n[yellow]Received shutdown signal. Cleaning up...[/yellow]")
    try:
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    main()
