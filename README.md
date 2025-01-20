# Seed Phrase Extractor

## 🔍 Description

This Python 3.x program performs a recursive search for secret phrases from crypto wallets inside files. It checks their validity (i.e., prints only those phrases that comply with the BIP39 standard) and displays the passphrase along with the path to the file in which it was found. 

Validation of phrases for compliance with the BIP39 standard is performed using the library from the repository of the Trezor hardware crypto wallet. 
🔗 [trezor/python-mnemonic](https://github.com/trezor/python-mnemonic)

---

## 🖥 Sample Output

```
/home/zzzzz/zzzzzz/Files/wallety/New text document.txt
rude cool annual mango hazard stable affair payment kingdom naive crush cancel

/home/zzzzz/zzzzzz/Files/wallety/tron.txt
awake window awful off hero coach salmon deer medal bleak crisp noodle

/home/zzzzzzz/FileGrabber/Users/aliraza/Documents/atomic backup pharse wallet.txt
focus city expand planet upon power stick begin usual cereal spring damage

/home/zzzzzzz/FileGrabber/Users/tunas/Desktop/torrrez codes.txt
sketch swift bronze stadium monster agent office error lock spare split frown

/home/zzzzz/zzzzzz/Files/wallety/ark wallet.txt
rude cool annual mango hazard stable affair payment kingdom naive crush cancel
```

---

## 🛠 Installation

1. Download and install **Python 3.8+** from (https://www.python.org/).  
2. During installation, select the checkboxes:  
   - ✅ "Install Launcher for all users"  
   - ✅ "Add Python3.8 to PATH"  
3. At the end of installation, select:  
   - ✅ "Disable PATH length limit"  
4. Install **Visual C++ Build Tools** from (https://visualstudio.microsoft.com/visual-cpp-build-tools/).  
   - [Installation Guide](https://prnt.sc/XUQAJLvWtrU-)  
5. After completing the above steps, run :  

   ```
   install_libs.cmd
   ```

---

## ⚙ Configuration

Edit `seed_parser_v*.py` and modify the following settings as needed:

```python
SOURCE_DIR = 'd:/__dd2/'  # Path to logs (use '/' for Windows)

PARCE_ETH = False  # Enable/disable Ethereum private key extraction
                   # If enabled, set up exclusion files/folders to avoid excessive garbage

BAD_DIRS = ['ololololz']  # List of folders to ignore

BAD_FILES = ['ololololo']  # List of files to ignore

WORDS_CHAIN_SIZES = {12, 15, 18, 24}  # Supported seed phrase lengths

EXWORDS = 2  # Filters out non-unique phrases (phrases with more than 2 repeated words)
```

---

## 🚀 Running the Script

To execute the script, use `run.bat`.  

1. Open the script directory in the terminal:  

   ```
   cd C:\Users\administrator\Desktop\seed_parser_v2.2
   ```

2. Run the script:  

   ```
   run.bat
   ```

---

📌 **Ensure all necessary dependencies are installed before running the script!**

