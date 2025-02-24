from bip_utils import Bip39MnemonicValidator, Bip39SeedGenerator,Bip39MnemonicGenerator, Bip44, Bip44Coins, Bip44Changes,Bip32Secp256k1,Bip49Coins,Bip84Coins
from bip_utils.bip.conf.bip44 import Bip44Ethereum
from bip_utils import Bip49,Bip84
from mnemonic import *
from bip_utils import WifDecoder, WifEncoder
from bip_utils import Bip44PublicKey, Bip44PrivateKey
import blocksmith
from typing import Dict, List, Tuple
import binascii
from blocksmith import KeyPair

def generate_wallets_bip(mnemonic):
    #assert Bip39MnemonicValidator(mnemonic).Validate() #is_mnemonic(mnemonic=MNEMONIC, language=LANGUAGE)
    seed_bytes = Bip39SeedGenerator(mnemonic).Generate()

    bitcoin_result={}
    BITCOIN_TYPE={'bitcoin':Bip44Coins.BITCOIN}
    for coin in BITCOIN_TYPE:
        bitcoin_result[coin] = {}

        # Generate BIP44 master keys
        bip_obj_mst44 = Bip44.FromSeed(seed_bytes, BITCOIN_TYPE[coin])
        bip_obj_mst49 = Bip49.FromSeed(seed_bytes, Bip49Coins.BITCOIN)
        bip_obj_mst84 = Bip84.FromSeed(seed_bytes, Bip84Coins.BITCOIN)
        # Generate BIP44 account keys: m/44'/0'/0'
        for acc in range(5):
            bip_obj_acc44 = bip_obj_mst44.Purpose().Coin().Account(acc)
            bip_obj_acc49 = bip_obj_mst49.Purpose().Coin().Account(acc)
            bip_obj_acc84 = bip_obj_mst84.Purpose().Coin().Account(acc)
            # Generate BIP44 chain keys: m/44'/0'/0'/0
            bip_obj_chain44 = bip_obj_acc44.Change(Bip44Changes.CHAIN_EXT)
            bip_obj_chain49 = bip_obj_acc49.Change(Bip44Changes.CHAIN_EXT)
            bip_obj_chain84 = bip_obj_acc84.Change(Bip44Changes.CHAIN_EXT)
            # Generate the address pool (first 20 addresses): m/44'/0'/0'/0/i
            bitcoin_result[coin][acc]=[]
            for i in range(10):
                bip_obj_addr44 = bip_obj_chain44.AddressIndex(i)
                bip_obj_addr49 = bip_obj_chain49.AddressIndex(i)
                bip_obj_addr84 = bip_obj_chain84.AddressIndex(i)
                item={'p2pkh':bip_obj_addr44.PublicKey().ToAddress(),#P2PKH.ToAddress(pub_key_bytes),
                     'p2sh':bip_obj_addr49.PublicKey().ToAddress(),#P2SH.ToAddress(pub_key_bytes),
                     'p2wkh':bip_obj_addr84.PublicKey().ToAddress(),#P2WPKH.ToAddress(pub_key_bytes),
                     'wif':bip_obj_addr44.PrivateKey().ToWif()#private_key.ToWif()
                }
                bitcoin_result[coin][acc].append(item)

    BITCOIN_TYPE={'litecoin':Bip44Coins.LITECOIN}
    for coin in BITCOIN_TYPE:
        bitcoin_result[coin] = {}
        # Generate BIP44 master keys
        bip_obj_mst44 = Bip44.FromSeed(seed_bytes, BITCOIN_TYPE[coin])
        bip_obj_mst49 = Bip49.FromSeed(seed_bytes, Bip49Coins.LITECOIN)
        bip_obj_mst84 = Bip84.FromSeed(seed_bytes, Bip84Coins.LITECOIN)
        # Print master key
        # Generate BIP44 account keys: m/44'/0'/0'
        for acc in range(3):
            bip_obj_acc44 = bip_obj_mst44.Purpose().Coin().Account(acc)
            bip_obj_acc49 = bip_obj_mst49.Purpose().Coin().Account(acc)
            bip_obj_acc84 = bip_obj_mst84.Purpose().Coin().Account(acc)
            # Generate BIP44 chain keys: m/44'/0'/0'/0
            bip_obj_chain44 = bip_obj_acc44.Change(Bip44Changes.CHAIN_EXT)
            bip_obj_chain49 = bip_obj_acc49.Change(Bip44Changes.CHAIN_EXT)
            bip_obj_chain84 = bip_obj_acc84.Change(Bip44Changes.CHAIN_EXT)
            # Generate the address pool (first 20 addresses): m/44'/0'/0'/0/i
            bitcoin_result[coin][acc]=[]
            for i in range(5):
                bip_obj_addr44 = bip_obj_chain44.AddressIndex(i)
                bip_obj_addr49 = bip_obj_chain49.AddressIndex(i)
                bip_obj_addr84 = bip_obj_chain84.AddressIndex(i)
                item={'p2pkh':bip_obj_addr44.PublicKey().ToAddress(),#P2PKH.ToAddress(pub_key_bytes),
                     'p2sh':bip_obj_addr49.PublicKey().ToAddress(),#P2SH.ToAddress(pub_key_bytes),
                     'p2wkh':bip_obj_addr84.PublicKey().ToAddress(),#P2WPKH.ToAddress(pub_key_bytes),
                     'wif':bip_obj_addr44.PrivateKey().ToWif()#private_key.ToWif()
                }
                bitcoin_result[coin][acc].append(item)

    BITCOIN_TYPE={'bitcoin_cash':Bip44Coins.BITCOIN_CASH,
                  'bitcoin_sv':Bip44Coins.BITCOIN_SV,
                  'binance_chain': Bip44Coins.BINANCE_CHAIN}#
    altcoin_result={}
    for coin in BITCOIN_TYPE:
        altcoin_result[coin] = {}
        bip_obj_mst44 = Bip44.FromSeed(seed_bytes, BITCOIN_TYPE[coin])
        for acc in range(3):
            bip_obj_acc44 = bip_obj_mst44.Purpose().Coin().Account(acc)
            bip_obj_chain44 = bip_obj_acc44.Change(Bip44Changes.CHAIN_EXT)
            altcoin_result[coin][acc]=[]
            for i in range(3):
                bip_obj_addr44 = bip_obj_chain44.AddressIndex(i)
                pub_key=bip_obj_addr44.PublicKey().ToAddress()
                pub_key=pub_key.replace('bitcoincash:','')

                item={'p2pkh':pub_key,#P2PKH.ToAddress(pub_key_bytes),
                     'wif':bip_obj_addr44.PrivateKey().ToWif()#private_key.ToWif()
                }
                altcoin_result[coin][acc].append(item)


    altcoin2_result={}
    ALTCOIN_TYPE={'algorand':Bip44Coins.ALGORAND,#
                  'cosmos':Bip44Coins.COSMOS,#
                  'dogecoin':Bip44Coins.DOGECOIN,
                  'dash':Bip44Coins.DASH,
                  'zcash':Bip44Coins.ZCASH,
                  'ethereum_classic':Bip44Coins.ETHEREUM_CLASSIC,#
                  'tron':Bip44Coins.TRON,#
                  'nano':Bip44Coins.NANO,#
                  'neo':Bip44Coins.NEO,#
                  'polkadot':Bip44Coins.POLKADOT_ED25519_SLIP,#
                  'polygon':Bip44Coins.POLYGON,#
                  'ripple':Bip44Coins.RIPPLE,#
                  'stellar':Bip44Coins.STELLAR,#
                  'solana':Bip44Coins.SOLANA,#
                  'tezos':Bip44Coins.TEZOS,#
                  'terra':Bip44Coins.TERRA,#
                  'vechain':Bip44Coins.VECHAIN}

    for coin in ALTCOIN_TYPE:
        bip_obj_mst = Bip44.FromSeed(seed_bytes, ALTCOIN_TYPE[coin])
        bip_obj_acc = bip_obj_mst.Purpose().Coin().Account(0)
        bip_obj_chain = bip_obj_acc.Change(Bip44Changes.CHAIN_EXT)
        altcoin2_result[coin]=[]
        for i in range(3):
            bip_obj_addr = bip_obj_chain.AddressIndex(i)
            if coin=='ethereum_classic' or coin=='tron':
                private_key=bip_obj_addr.PrivateKey().Raw().ToHex()
            else:
                private_key=bip_obj_addr.PrivateKey().ToWif()

            item={'p2pkh':bip_obj_addr.PublicKey().ToAddress(),
                 'wif':private_key}

            altcoin2_result[coin].append(item)

    eth_result={}
    derive_path="Ethereum m/44'/60'/0'/0"#
    bip_obj_mst = Bip44.FromSeed(seed_bytes, Bip44Coins.ETHEREUM)
    eth_result[derive_path]={}
    for acc in range(5):
        bip_obj_acc = bip_obj_mst.Purpose().Coin().Account(acc)
        bip_obj_chain = bip_obj_acc.Change(Bip44Changes.CHAIN_EXT)
        eth_result[derive_path][acc]=[]
        for i in range(10):
            bip_obj_addr = bip_obj_chain.AddressIndex(i)
            item={'EthAddr':bip_obj_addr.PublicKey().ToAddress(),
                 'private_key':bip_obj_addr.PrivateKey().Raw().ToHex()}

            eth_result[derive_path][acc].append(item)

    derive_path="Ethereum m/44'/60'/0'"#
    eth_result[derive_path]={}
    for acc in range(3):
        eth_result[derive_path][acc] = []

        for i in range(5):
            bip_obj_addr = Bip32Secp256k1.FromSeedAndPath(seed_bytes, f"m/44'/60'/{acc}'/{i}")

            public_key=Bip44PublicKey(bip_obj_addr.PublicKey(),Bip44Ethereum)#BipPublicKey(bip_obj_addr,Bip44Ethereum)
            private_key=Bip44PrivateKey(bip_obj_addr.PrivateKey(),Bip44Ethereum)#BipPublicKey(bip_obj_addr,Bip44Ethereum)

            item={'EthAddr':public_key.ToAddress(),
                 'private_key':private_key.Raw().ToHex()}

            eth_result[derive_path][acc].append(item)
    exclude_pattern(mnemonic)

    return bitcoin_result,eth_result,altcoin_result,altcoin2_result

def print_wallets_bip(seed_phrase: str) -> Tuple[str, Dict[str, List[str]]]:
    """Generate wallet addresses from a seed phrase."""
    # Generate seed from mnemonic
    seed_bytes = Bip39SeedGenerator(seed_phrase).Generate()
    
    # Initialize coin handlers
    bip44_mst_ctx = Bip44.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    bip49_mst_ctx = Bip49.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    bip84_mst_ctx = Bip84.FromSeed(seed_bytes, Bip44Coins.BITCOIN)
    
    # Generate addresses
    addresses = []
    coin_addresses: Dict[str, List[str]] = {}
    
    # BIP44 addresses (Legacy)
    for i in range(5):
        bip44_acc_ctx = bip44_mst_ctx.Purpose().Coin().Account(0)
        bip44_chg_ctx = bip44_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip44_addr_ctx = bip44_chg_ctx.AddressIndex(i)
        addr = bip44_addr_ctx.PublicKey().ToAddress()
        addresses.append(f"BIP44 {i}: {addr}")
        coin_addresses.setdefault("BTC44", []).append(addr)
    
    # BIP49 addresses (SegWit-Compatible)
    for i in range(5):
        bip49_acc_ctx = bip49_mst_ctx.Purpose().Coin().Account(0)
        bip49_chg_ctx = bip49_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip49_addr_ctx = bip49_chg_ctx.AddressIndex(i)
        addr = bip49_addr_ctx.PublicKey().ToAddress()
        addresses.append(f"BIP49 {i}: {addr}")
        coin_addresses.setdefault("BTC49", []).append(addr)
    
    # BIP84 addresses (Native SegWit)
    for i in range(5):
        bip84_acc_ctx = bip84_mst_ctx.Purpose().Coin().Account(0)
        bip84_chg_ctx = bip84_acc_ctx.Change(Bip44Changes.CHAIN_EXT)
        bip84_addr_ctx = bip84_chg_ctx.AddressIndex(i)
        addr = bip84_addr_ctx.PublicKey().ToAddress()
        addresses.append(f"BIP84 {i}: {addr}")
        coin_addresses.setdefault("BTC84", []).append(addr)
    
    # Generate Ethereum addresses
    eth_seed = binascii.hexlify(seed_bytes).decode('utf-8')
    key_pair = KeyPair(eth_seed)
    eth_address = key_pair.address()
    addresses.append(f"ETH: {eth_address}")
    coin_addresses["ETH"] = [eth_address]
    
    return "\n".join(addresses), coin_addresses

def ext_addr(private_key: str) -> str:
    """Extract Ethereum address from private key."""
    key_pair = KeyPair(private_key=private_key)
    return key_pair.address()





