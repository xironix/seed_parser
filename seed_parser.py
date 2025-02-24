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
from typing import Dict, List, Optional, Set, Tuple
from mnemonic import Mnemonic
import signal
import threading
from contextlib import contextmanager

from gen_wallet import *

# Configuration
PARSE_ETH = False  # Fixed typo from PARCE to PARSE
LOG_DIR = Path('./logs')
BASE_DIR = Path(__file__).parent.absolute()
SOURCE_DIR = Path('D:/')  # Configurable via CLI

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

ENABLE_LANG: List[str] = [
    'english', 'chinese_simplified', 'chinese_traditional',
    'french', 'italian', 'japanese', 'korean',
    'portuguese', 'spanish'
]

WORDS_CHAIN_SIZES: Set[int] = {12, 15, 18, 24}
EXWORDS: int = 2
CHUNK_SIZE: int = 1024 * 1024  # 1MB chunks for file reading

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'parser.log')
    ]
)
logger = logging.getLogger(__name__)

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

    def create_tables(self) -> None:
        """Create necessary database tables."""
        with self.transaction():
            self.conn.executescript("""
                CREATE TABLE IF NOT EXISTS phrases (
                    phrase VARCHAR(500) PRIMARY KEY,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                CREATE INDEX IF NOT EXISTS idx_phrases_created ON phrases(created_at);
            """)

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

def find_in_file(path: str, log_lock: mp.synchronize.RLock, log_files: Dict[str, str]) -> None:
    """Process a single file looking for seed phrases."""
    try:
        file_path = Path(path)
        if not file_path.is_file():
            return

        # Read file in chunks to handle large files
        words_chain: List[str] = []
        lang = ''
        db = DBController()
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                try:
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
                    for match in re.finditer('[a-z]+', data, re.I):
                        word = match.group(0)
                        
                        if not words_chain:
                            # Try to start a new chain
                            for k, word_data in words_arr.items():
                                if word in word_data['words']:
                                    words_chain.append(word)
                                    lang = k
                                    break
                            continue

                        if word in words_arr[lang]['words']:
                            words_chain.append(word)
                            continue

                        # Process completed chains
                        process_word_chain(words_chain, lang, path, db, log_lock, log_files)
                        words_chain = []

                    # Process any remaining chain
                    if words_chain:
                        process_word_chain(words_chain, lang, path, db, log_lock, log_files)

                    # Parse ETH addresses if enabled
                    if PARSE_ETH:
                        process_eth_addresses(data, path, log_lock, log_files)

                except Exception as e:
                    logger.error(f"Error processing chunk in {path}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error processing file {path}: {e}")

def process_word_chain(
    words_chain: List[str],
    lang: str,
    path: str,
    db: DBController,
    log_lock: mp.synchronize.RLock,
    log_files: Dict[str, str]
) -> None:
    """Process a chain of words for potential seed phrases."""
    if not words_chain:
        return

    mnemo = words_arr[lang]['mnemo']
    for phrase in get_phrase_arr(words_chain):
        words_str = ' '.join(phrase)
        if not valid_phrase(phrase):
            continue

        if not mnemo.check(words_str) or db.phrase_in_db(words_str):
            continue

        try:
            full_log, coin_log = print_wallets_bip(words_str)
            db.insert_phrase(words_str)
            
            log_entry = f"{path}\n{words_str}\n{full_log}"
            logger.info(log_entry)

            if log_files['SEED_LOG']:
                with log_lock:
                    write_log(f"{lang}_{log_files['SEED_LOG']}", words_str)
                    write_log(log_files['SEED_LOG'], words_str)
                    write_log(log_files['FULL_LOG'], log_entry)
                    for coin, addresses in coin_log.items():
                        write_log(f"{coin}{log_files['ADDR_log']}", '\n'.join(addresses))
        except Exception as e:
            logger.error(f"Error processing phrase '{words_str}': {e}")

def process_eth_addresses(
    data: str,
    path: str,
    log_lock: mp.synchronize.RLock,
    log_files: Dict[str, str]
) -> None:
    """Process potential Ethereum addresses in the data."""
    for match in re.finditer(r"(?:[^\w/\\]|^)([a-f0-9]{64})(?:\W|$)", data, re.I):
        try:
            private_key = match[1]
            address = ext_addr(private_key)
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
        except Exception as e:
            logger.error(f"Error processing ETH address: {e}")

def thread_fun(
    directory: str,
    log_lock: mp.synchronize.RLock,
    log_files: Dict[str, str]
) -> str:
    """Worker function for processing directories."""
    global words_arr
    words_arr = {}
    
    try:
        # Initialize word lists
        wordlist_dir = BASE_DIR / 'wordlist'
        
        if 'english' in ENABLE_LANG:
            with open(wordlist_dir / 'english.txt', 'r', encoding='utf-8') as f:
                words_arr['english'] = {
                    'words': set(f.read().splitlines()),
                    'mnemo': Mnemonic("english")
                }

        other_dir = wordlist_dir / 'Other'
        for lang_file in other_dir.glob('*.txt'):
            lang = lang_file.stem
            if lang in ENABLE_LANG:
                with open(lang_file, 'r', encoding='utf-8') as f:
                    words_arr[lang] = {
                        'words': set(f.read().splitlines()),
                        'mnemo': Mnemonic(f"Other/{lang}")
                    }

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

    except Exception as e:
        logger.error(f"Error in thread processing directory {directory}: {e}")
    
    return directory

def main() -> None:
    """Main entry point for the seed phrase parser."""
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

    # Create logs directory
    LOG_DIR.mkdir(exist_ok=True)

    # Initialize logging
    log_files = {}
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

    # Set up source directory
    source_dir = Path(args.directory)
    if not source_dir.exists():
        logger.error(f"Error: Source directory {source_dir} does not exist")
        sys.exit(1)

    # Initialize database
    db = DBController(in_memory=args.memory_db)
    db.create_tables()

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
        params = [(str(d), log_lock, log_files) for d in directories]
        
        logger.info(f"Starting scan with {args.threads} threads...")
        results = work_pool.starmap(thread_fun, params)
        
        logger.info(f"Scan completed. Processed {len(results)} directories:")
        for r in results:
            logger.info(f"- {r}")
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, cleaning up...")
        work_pool.terminate()
    except Exception as e:
        logger.error(f"Error during processing: {e}")
    finally:
        work_pool.close()
        work_pool.join()
        db.flush_buffer()  # Ensure all phrases are written
        Mnemonic.free_sources()

def signal_handler(signum: int, frame) -> None:
    """Handle interrupt signals gracefully."""
    logger.info("\nReceived shutdown signal. Cleaning up...")
    try:
        Mnemonic.free_sources()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Error during cleanup: {e}")
        sys.exit(1)

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == '__main__':
    main()
