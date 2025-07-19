from web3 import Web3
from eth_account import Account
from colorama import Fore, init
import time
from web3.exceptions import TimeExhausted

# Inisialisasi colorama
init(autoreset=True)

# Konfigurasi
RPC_URL = "https://mainnet.crosstoken.io:22001"  # RPC dari bot fee
CHAIN_ID = 612055  # Chain ID dari bot fee
CONTRACT_ADDRESS = "0xc22ee14d61a5FE3D02dE17Ad876749638fcD905b"
PK_FILE = "pk.txt"
AMOUNT_TO_CLAIM = 20000000000000000000  # 20 ETH dalam wei
FALLBACK_AMOUNT = 10000000000000000000  # 10 ETH dalam wei
GAS_PRICE_GWEI = 26.4  # Dari transaksi contoh
TIMEOUT_SECONDS = 10  # Timeout per transaksi
DELAY_SECONDS = 0.3  # Delay antar transaksi

# ABI untuk fungsi claimETH
ABI = [
    {
        "constant": False,
        "inputs": [{"name": "amount", "type": "uint256"}],
        "name": "claimETH",
        "outputs": [],
        "payable": False,
        "stateMutability": "nonpayable",
        "type": "function"
    }
]

# Koneksi ke jaringan Cross chain
w3 = Web3(Web3.HTTPProvider(RPC_URL))
print(f"{Fore.YELLOW}🔍 Cek koneksi RPC...")
start_rpc = time.time()
try:
    block_number = w3.eth.get_block_number()
    print(f"{Fore.GREEN}🔗 Terkoneksi ke Cross chain, blok: {block_number}, waktu: {(time.time() - start_rpc) * 1000:.0f}ms")
except Exception as e:
    print(f"{Fore.RED}❌ Gagal konek ke RPC: {str(e)}")
    exit()

# Baca private key dari pk.txt
def get_private_keys():
    try:
        with open(PK_FILE, "r") as f:
            keys = [line.strip() for line in f if line.strip()]
            for i, key in enumerate(keys):
                if not key.startswith("0x"):
                    keys[i] = "0x" + key
            return keys
    except FileNotFoundError:
        print(f"{Fore.RED}❌ File {PK_FILE} tidak ditemukan.")
        exit()
    except Exception as e:
        print(f"{Fore.RED}❌ Gagal baca {PK_FILE}: {str(e)}")
        exit()

# Fungsi untuk melakukan klaim
def claim_rewards(private_key, amount):
    try:
        # Inisialisasi akun
        wallet = Account.from_key(private_key)
        wallet_address = wallet.address

        # Inisialisasi kontrak
        contract = w3.eth.contract(address=CONTRACT_ADDRESS, abi=ABI)

        # Cek saldo dompet
        balance = w3.eth.get_balance(wallet_address)
        print(f"{Fore.CYAN}🔹 Wallet: {wallet_address} | Saldo: {w3.from_wei(balance, 'ether')} CROSS | Kla adding: {w3.from_wei(amount, 'ether')} ETH")

        # Estimasi gas
        gas_estimate = contract.functions.claimETH(amount).estimate_gas({
            'from': wallet_address
        })
        print(f"{Fore.YELLOW}⛽ Estimasi gas: {gas_estimate}")

        # Buat transaksi
        tx = contract.functions.claimETH(amount).build_transaction({
            'chainId': CHAIN_ID,
            'from': wallet_address,
            'nonce': w3.eth.get_transaction_count(wallet_address, 'pending'),
            'gas': gas_estimate,
            'maxFeePerGas': w3.to_wei(GAS_PRICE_GWEI, 'gwei'),
            'maxPriorityFeePerGas': w3.to_wei(GAS_PRICE_GWEI - 1, 'gwei')  # Priority fee sedikit lebih rendah
        })

        # Tanda tangani Ascend
        signed_tx = w3.eth.account.sign_transaction(tx, private_key)
        print(f"{Fore.YELLOW}✅ TX Dikirim: {signed_tx.hash.hex()} -> Klaim: {w3.from_wei(amount, 'ether')} ETH")

        # Kirim transaksi
        start = time.time()
        tx_hash = w3.eth.send_raw_transaction(signed_tx.raw_transaction)

        # Tunggu konfirmasi
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=TIMEOUT_SECONDS)
        gas_used = receipt['gasUsed']
        gas_price = receipt.get('effectiveGasPrice', tx['maxFeePerGas'])
        fee = gas_used * gas_price / 1e18
        print(f"{Fore.GREEN}✅ TX Selesai: {tx_hash.hex()} (Blok: {receipt['blockNumber']})")
        print(f"{Fore.CYAN}⛽ Gas: {gas_used}, Harga: {gas_price / 1e9} Gwei, Biaya: {fee} CROSS")
        print(f"{Fore.YELLOW}⏳ Waktu: {(time.time() - start) * 1000:.0f}ms")
        return True
    except TimeExhausted:
        print(f"{Fore.RED}❌ Gagal klaim untuk {wallet_address}: Transaksi timeout setelah {TIMEOUT_SECONDS} detik")
        return False
    except Exception as e:
        print(f"{Fore.RED}❌ Gagal klaim untuk {wallet_address}: {str(e)}")
        return False

def main():
    print(f"{Fore.BLUE}🚀 Mulai Bot Klaim 20 ETH dengan Fallback 10 ETH...")
    # Baca private key
    private_keys = get_private_keys()
    print(f"{Fore.CYAN}📌 Ada {len(private_keys)} wallet untuk klaim")

    # Proses klaim satu per satu
    success_count = 0
    for idx, pk in enumerate(private_keys, 1):
        print(f"\n{Fore.BLUE}🔄 Memproses wallet {idx}/{len(private_keys)}...")
        # Coba klaim 20 ETH
        if claim_rewards(pk, AMOUNT_TO_CLAIM):
            success_count += 1
        else:
            # Kalau gagal, coba klaim 10 ETH
            print(f"{Fore.YELLOW}🔄 Mencoba fallback klaim 10 ETH untuk wallet {idx}...")
            if claim_rewards(pk, FALLBACK_AMOUNT):
                success_count += 1
        if len(private_keys) > 1:
            time.sleep(DELAY_SECONDS)

    print(f"\n{Fore.GREEN}✅ Selesai! {success_count} dari {len(private_keys)} wallet berhasil diklaim")

if __name__ == "__main__":
    main()