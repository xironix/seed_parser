from typing import Dict, List, Tuple
import binascii
from hdwallet import HDWallet
from hdwallet.symbols import BTC, LTC, BCH, BSV, BNB, DOGE, DASH, ZEC, TRX
from hdwallet.cryptocurrencies import get_cryptocurrency
from eth_account import Account
import os
import secrets
from eth_utils import to_checksum_address

# Enable unaudited HD wallet features for eth-account
Account.enable_unaudited_hdwallet_features()

def generate_wallet_for_coin(mnemonic: str, symbol: str, path: str) -> Dict[str, str]:
    """Generate wallet for a specific coin using hdwallet"""
    try:
        hdwallet = HDWallet(symbol=symbol)
        hdwallet.from_mnemonic(mnemonic)
        hdwallet.from_path(path)
        return {
            'address': hdwallet.address(),
            'private_key': hdwallet.private_key(),
            'public_key': hdwallet.public_key(),
            'path': path
        }
    except Exception as e:
        return {
            'address': f"Error: {str(e)}",
            'private_key': '',
            'public_key': '',
            'path': path
        }

def generate_eth_wallet(mnemonic: str, path: str, chain_id: int = 1) -> Dict[str, str]:
    """Generate Ethereum wallet using eth-account
    
    Args:
        mnemonic: The mnemonic seed phrase
        path: The derivation path
        chain_id: The chain ID (1 for ETH mainnet, 61 for ETC)
    """
    try:
        account = Account.from_mnemonic(mnemonic, account_path=path)
        address = account.address
        # If it's Ethereum Classic, we keep the same address format
        return {
            'address': address,
            'private_key': account.key.hex(),
            'path': path
        }
    except Exception as e:
        return {
            'address': f"Error: {str(e)}",
            'private_key': '',
            'path': path
        }

def generate_wallets_bip(mnemonic: str):
    """Generate wallets for multiple cryptocurrencies"""
    bitcoin_result = {}
    eth_result = {}
    altcoin_result = {}
    altcoin2_result = {}

    # Bitcoin and variants
    for acc in range(5):
        bitcoin_result.setdefault('bitcoin', {})[acc] = []
        for i in range(10):
            path = f"m/44'/0'/{acc}'/0/{i}"  # BIP44
            path49 = f"m/49'/0'/{acc}'/0/{i}"  # BIP49
            path84 = f"m/84'/0'/{acc}'/0/{i}"  # BIP84
            
            wallet44 = generate_wallet_for_coin(mnemonic, BTC, path)
            wallet49 = generate_wallet_for_coin(mnemonic, BTC, path49)
            wallet84 = generate_wallet_for_coin(mnemonic, BTC, path84)
            
            item = {
                'p2pkh': wallet44['address'],
                'p2sh': wallet49['address'],
                'p2wkh': wallet84['address'],
                'wif': wallet44['private_key']
            }
            bitcoin_result['bitcoin'][acc].append(item)

    # Litecoin
    for acc in range(3):
        bitcoin_result.setdefault('litecoin', {})[acc] = []
        for i in range(5):
            path = f"m/44'/2'/{acc}'/0/{i}"
            wallet = generate_wallet_for_coin(mnemonic, LTC, path)
            item = {
                'p2pkh': wallet['address'],
                'p2sh': wallet['address'],
                'p2wkh': wallet['address'],
                'wif': wallet['private_key']
            }
            bitcoin_result['litecoin'][acc].append(item)

    # Bitcoin Cash, Bitcoin SV, Binance Chain
    for coin, symbol in [('bitcoin_cash', BCH), ('bitcoin_sv', BSV), ('binance_chain', BNB)]:
        altcoin_result[coin] = {}
        for acc in range(3):
            altcoin_result[coin][acc] = []
            for i in range(3):
                path = f"m/44'/{get_cryptocurrency(symbol).BIP44_PATH}/{acc}'/0/{i}"
                wallet = generate_wallet_for_coin(mnemonic, symbol, path)
                item = {
                    'p2pkh': wallet['address'],
                    'wif': wallet['private_key']
                }
                altcoin_result[coin][acc].append(item)

    # Other altcoins
    coin_map = {
        'dogecoin': DOGE,
        'dash': DASH,
        'zcash': ZEC,
        'tron': TRX
    }

    for coin_name, symbol in coin_map.items():
        altcoin2_result[coin_name] = []
        path = f"m/44'/{get_cryptocurrency(symbol).BIP44_PATH}/0'/0/0"
        wallet = generate_wallet_for_coin(mnemonic, symbol, path)
        item = {
            'p2pkh': wallet['address'],
            'wif': wallet['private_key']
        }
        altcoin2_result[coin_name].append(item)

    # Handle Ethereum and Ethereum Classic using eth-account
    eth_chains = {
        'ethereum': {'path_prefix': "60", 'chain_id': 1},
        'ethereum_classic': {'path_prefix': "61", 'chain_id': 61}
    }

    for chain_name, chain_info in eth_chains.items():
        if chain_name == 'ethereum':
            result_dict = eth_result
        else:
            altcoin2_result[chain_name] = []
            result_dict = {'default': []}

        path_prefix = chain_info['path_prefix']
        chain_id = chain_info['chain_id']

        if chain_name == 'ethereum':
            derive_path = f"Ethereum m/44'/{path_prefix}'/0'/0"
            result_dict[derive_path] = {}
            
            for acc in range(5):
                result_dict[derive_path][acc] = []
                for i in range(10):
                    path = f"m/44'/{path_prefix}'/{acc}'/0/{i}"
                    wallet = generate_eth_wallet(mnemonic, path, chain_id)
                    item = {
                        'EthAddr': wallet['address'],
                        'private_key': wallet['private_key']
                    }
                    result_dict[derive_path][acc].append(item)

            derive_path = f"Ethereum m/44'/{path_prefix}'/0'"
            result_dict[derive_path] = {}
            
            for acc in range(3):
                result_dict[derive_path][acc] = []
                for i in range(5):
                    path = f"m/44'/{path_prefix}'/{acc}'/{i}"
                    wallet = generate_eth_wallet(mnemonic, path, chain_id)
                    item = {
                        'EthAddr': wallet['address'],
                        'private_key': wallet['private_key']
                    }
                    result_dict[derive_path][acc].append(item)
        else:
            # For ETC, just generate one address
            path = f"m/44'/{path_prefix}'/0'/0/0"
            wallet = generate_eth_wallet(mnemonic, path, chain_id)
            item = {
                'p2pkh': wallet['address'],
                'wif': wallet['private_key']
            }
            result_dict['default'].append(item)
            altcoin2_result[chain_name] = result_dict['default']

    return bitcoin_result, eth_result, altcoin_result, altcoin2_result

def print_wallets_bip(seed_phrase: str) -> Tuple[str, Dict[str, List[str]]]:
    """Generate wallet addresses from a seed phrase."""
    addresses = []
    coin_addresses: Dict[str, List[str]] = {}
    
    # BIP44 addresses (Legacy)
    for i in range(5):
        path = f"m/44'/0'/0'/0/{i}"
        wallet = generate_wallet_for_coin(seed_phrase, BTC, path)
        addr = wallet['address']
        addresses.append(f"BIP44 {i}: {addr}")
        coin_addresses.setdefault("BTC44", []).append(addr)
    
    # BIP49 addresses (SegWit-Compatible)
    for i in range(5):
        path = f"m/49'/0'/0'/0/{i}"
        wallet = generate_wallet_for_coin(seed_phrase, BTC, path)
        addr = wallet['address']
        addresses.append(f"BIP49 {i}: {addr}")
        coin_addresses.setdefault("BTC49", []).append(addr)
    
    # BIP84 addresses (Native SegWit)
    for i in range(5):
        path = f"m/84'/0'/0'/0/{i}"
        wallet = generate_wallet_for_coin(seed_phrase, BTC, path)
        addr = wallet['address']
        addresses.append(f"BIP84 {i}: {addr}")
        coin_addresses.setdefault("BTC84", []).append(addr)
    
    # Generate Ethereum address using eth-account
    wallet = generate_eth_wallet(seed_phrase, "m/44'/60'/0'/0/0")
    eth_address = wallet['address']
    addresses.append(f"ETH: {eth_address}")
    coin_addresses["ETH"] = [eth_address]
    
    return "\n".join(addresses), coin_addresses

def ext_addr(private_key: str) -> str:
    """Extract Ethereum address from private key using eth-account."""
    try:
        account = Account.from_key(private_key)
        return account.address
    except Exception as e:
        return f"Error: {str(e)}"





