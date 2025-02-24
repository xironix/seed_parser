# Cryptocurrency Seed Phrase Parser

A high-performance, multi-threaded tool for scanning directories and extracting cryptocurrency seed phrases and private keys. This tool is designed for security research and recovery of lost cryptocurrency wallets.

## Project Status

🚧 **Beta Version 1.0.0** 🚧

- ✅ Core functionality complete
- ✅ Multi-threading support
- ✅ Memory optimization
- ✅ SQLite integration
- ✅ Multiple cryptocurrency support
- 🔄 Ongoing security improvements
- 🔄 Performance optimizations
- 📝 Documentation updates

## Features

- Multi-threaded directory scanning with automatic CPU core detection
- Support for multiple cryptocurrencies:
  - Bitcoin (BIP44, BIP49, BIP84)
  - Ethereum
  - Litecoin
  - Bitcoin Cash
  - Bitcoin SV
  - Binance Chain
  - And many more altcoins
- Memory-efficient processing of large files:
  - Chunked file reading
  - Batched database operations
  - Worker process recycling
- Comprehensive logging system
- SQLite database with WAL mode for deduplication
- Graceful shutdown handling
- Support for multiple languages:
  - English
  - Chinese (Simplified & Traditional)
  - French
  - Italian
  - Japanese
  - Korean
  - Portuguese
  - Spanish

## Requirements

- Python 3.8+
- uv (modern Python package installer)
- Git

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/seed_parser.git
cd seed_parser
```

2. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Create and activate a virtual environment:
```bash
uv venv
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate  # On Windows
```

4. Install dependencies:
```bash
uv pip install -e .
```

## Project Structure

```
seed_parser/
├── src/
│   └── seed_parser/
│       ├── __init__.py
│       ├── parser.py
│       └── wallet.py
├── tests/
│   └── test_parser.py
├── pyproject.toml
├── README.md
└── .gitignore
```

## Usage

Basic usage:
```bash
python -m seed_parser -d /path/to/scan
```

Advanced options:
```bash
python -m seed_parser -d /path/to/scan -t 8 --memory-db
```

### Command Line Arguments

- `-d, --directory`: Source directory to scan (required)
- `-t, --threads`: Number of threads (default: CPU count)
- `-w, --write-logs`: Enable logging (default: True)
- `--no-eth`: Disable Ethereum private key scanning
- `--memory-db`: Use in-memory database (faster but higher memory usage)

### Output Files

All output files are stored in the `logs` directory with timestamps:

- `seed-{timestamp}.txt`: Found seed phrases
- `-addresses-{timestamp}.txt`: Generated addresses
- `full-log-{timestamp}.txt`: Complete scan results
- `eth-full-log-{timestamp}.txt`: Ethereum-specific results
- `eth-a-log-{timestamp}.txt`: Ethereum addresses
- `eth-p-log-{timestamp}.txt`: Ethereum private keys
- `parser.log`: General program logs

## Performance Optimization

The tool implements several performance optimizations:
- Chunked file reading (1MB chunks) for memory efficiency
- SQLite WAL journal mode for better concurrent access
- Database operation batching (1000 records per batch)
- Automatic worker process recycling (every 100 tasks)
- Multi-threaded processing with configurable thread count

## Security Considerations

⚠️ **Important Security Notes**:
- All output files contain sensitive cryptographic material
- Use appropriate file permissions (600 or stricter)
- Consider encrypting the output directory
- Never share or commit log files
- Use secure storage for results
- Consider using hardware security modules (HSM) for key storage

## Error Handling

The tool implements comprehensive error handling:
- Graceful handling of keyboard interrupts (CTRL+C)
- Proper cleanup of resources on exit
- Detailed logging with timestamps
- Transaction management for database operations
- Worker process error recovery
- File encoding detection and fallback

## Error Handling Examples

The tool provides clear error messages for various failure scenarios:

```text
# Non-existent directory
$ seed-parser -d /path/does/not/exist
2024-03-20 10:15:23 - ERROR - Directory does not exist: /path/does/not/exist

# Not a directory
$ seed-parser -d /path/to/file.txt
2024-03-20 10:15:24 - ERROR - Path exists but is not a directory: /path/to/file.txt

# No permissions
$ seed-parser -d /root/protected
2024-03-20 10:15:25 - ERROR - No read permission for directory: /root/protected

# Empty directory
$ seed-parser -d /path/to/empty/dir
2024-03-20 10:15:26 - ERROR - Directory is empty: /path/to/empty/dir
```

## Usage Examples

The tool handles various edge cases gracefully:

```text
# Invalid thread count
$ seed-parser -d /path -t 0
2024-03-20 10:15:27 - WARNING - Invalid thread count 0, using 1 thread
2024-03-20 10:15:27 - INFO - Starting scan with 1 thread...

# Too many threads
$ seed-parser -d /path -t 100
2024-03-20 10:15:28 - WARNING - Thread count 100 is more than 2x CPU count, limiting to 16 threads
2024-03-20 10:15:28 - INFO - Starting scan with 16 threads...

# No subdirectories
$ seed-parser -d /path/single/dir
2024-03-20 10:15:29 - WARNING - No subdirectories found in /path/single/dir
2024-03-20 10:15:29 - INFO - Processing directory itself...
```

## Development

### Setting up development environment:

```