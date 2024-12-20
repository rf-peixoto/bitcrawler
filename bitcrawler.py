#!/usr/bin/env python3
import sys
import json
import time
import re
import requests
from datetime import datetime
from colorama import init, Fore, Style

# Setup
REQUEST_DELAY = 2.0           # Delay (seconds) between requests to respect API usage limits.
RECENT_TX_COUNT = 5           # Number of recent transactions to display for an address.
LOG_FILE = "bexplorer_errors.log"  # Log file for error messages.
BASE_URL = "https://blockstream.info/api"  # Blockstream API base URL.
visited_chain = {}  # Stores visited transactions.
init(autoreset=True)  # Initialize colorama for cross-platform colored output.

# Logging and Error Handling
def log_error(msg, code=1):
    """Log an error message to the LOG_FILE and print it in red."""
    timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    error_entry = f"[{timestamp}] ERROR CODE {code}: {msg}\n"
    with open(LOG_FILE, 'a') as f:
        f.write(error_entry)
    print(Fore.RED + f"Error: {msg} (Code: {code})")

def delay_request():
    """Wait for a fixed duration before making the next request."""
    time.sleep(REQUEST_DELAY)

# Utility Functions for Navigation
def check_special_commands(user_input):
    """
    Check if user_input is 'm' or 'exit'. 
    'm' returns user to main menu.
    'exit' quits the program.
    Otherwise, returns the original input.
    """
    if user_input.lower() == 'm':
        main_menu()
        return None  # main_menu will handle navigation
    if user_input.lower() == 'exit':
        print(Fore.YELLOW + "\nExiting gracefully...")
        sys.exit(0)
    return user_input

# Banner and Menus
def print_banner():
    print(Fore.YELLOW + Style.BRIGHT + " _     _ _                          _           ")
    print(Fore.YELLOW + Style.BRIGHT + "| |   (_) |                        | |          ")
    print(Fore.YELLOW + Style.BRIGHT + "| |__  _| |_ ___ _ __ __ ___      _| | ___ _ __ ")
    print(Fore.YELLOW + Style.BRIGHT + "| '_ \| | __/ __| '__/ _` \ \ /\ / / |/ _ \ '__|")
    print(Fore.YELLOW + Style.BRIGHT + "| |_) | | || (__| | | (_| |\ V  V /| |  __/ |")
    print(Fore.YELLOW + Style.BRIGHT + "|_.__/|_|\__\___|_|  \__,_| \_/\_/ |_|\___|_|")
    print(Fore.YELLOW + Style.BRIGHT + "\n")
    print(Fore.YELLOW + Style.BRIGHT + "                            v1.0.0" + Style.RESET_ALL)

def main_menu():
    """Main menu loop for user interaction."""
    while True:
        print(Fore.YELLOW + "MAIN MENU")
        print("----------")
        print("1. Query Address")
        print("2. Query Transaction")
        print("3. Load Previously Dumped Chain")
        print("4. Exit")
        print("----------")
        print("Type 'm' anytime to return here, or 'exit' to quit." + Style.RESET_ALL)

        choice = input(Fore.YELLOW + "Enter option: " + Style.RESET_ALL).strip().lower()
        choice = check_special_commands(choice)
        if choice is None:
            # User chose 'm' or 'exit', handled already
            continue
        if choice == "1":
            addr = input(Fore.YELLOW + "Enter wallet address: " + Style.RESET_ALL).strip()
            addr = check_special_commands(addr)
            if addr is None:
                continue
            handle_address_input(addr)
        elif choice == "2":
            txid = input(Fore.YELLOW + "Enter transaction ID: " + Style.RESET_ALL).strip()
            txid = check_special_commands(txid)
            if txid is None:
                continue
            handle_transaction_input(txid)
        elif choice == "3":
            load_chain_menu()
        elif choice == "4":
            print(Fore.YELLOW + "\nExiting gracefully...")
            sys.exit(0)
        else:
            print(Fore.RED + "Invalid option.")

# Input Handling
def is_transaction_id(input_str):
    """Check if input looks like a txid (64 hex chars)."""
    return bool(re.match(r"^[0-9a-fA-F]{64}$", input_str))

def handle_address_input(address):
    """Handle address queries."""
    addr_data = fetch_address_data(address)
    if not addr_data:
        return

    # Display basic address info (balance, tx_count)
    display_address_info(address, addr_data)

    # Fetch recent transactions and display them once
    recent_txs = fetch_address_txs(address)
    if recent_txs:
        print(Fore.YELLOW + f"\nRecent Transactions (up to {RECENT_TX_COUNT}):")
        for i, tx in enumerate(recent_txs[:RECENT_TX_COUNT]):
            status = tx.get("status", {})
            confirmed = status.get("confirmed", False)
            conf_str = "Confirmed" if confirmed else "Unconfirmed"
            print(f"{i+1}. {Fore.GREEN}{tx.get('txid','N/A')}{Style.RESET_ALL} - {conf_str}")

        user_prompt = Fore.YELLOW + f"Enter a transaction number to explore or press ENTER to skip (type 'm' for menu, 'exit' to quit): " + Style.RESET_ALL
        choice = input(user_prompt).strip()
        choice = check_special_commands(choice)
        if choice is None:
            return
        if choice.isdigit():
            c_idx = int(choice)-1
            if 0 <= c_idx < len(recent_txs[:RECENT_TX_COUNT]):
                chosen_txid = recent_txs[c_idx].get("txid")
                tx_data = fetch_transaction_data(chosen_txid)
                if tx_data:
                    add_to_chain(tx_data, path="from address", source_txid=None)
                    display_transaction_info(tx_data)
                    follow_transaction(tx_data)
                else:
                    log_error("Could not fetch chosen transaction.", code=102)
    else:
        print("No recent transactions or unable to fetch.")

def handle_transaction_input(txid):
    """Handle transaction queries."""
    if not is_transaction_id(txid):
        print(Fore.RED + "Invalid transaction ID format.")
        return
    tx_data = fetch_transaction_data(txid)
    if tx_data:
        add_to_chain(tx_data, path="initial query", source_txid=None)
        display_transaction_info(tx_data)
        follow_transaction(tx_data)
    # If not found, error already logged

# Data Fetching
def fetch_address_data(address):
    """Fetch address data from Blockstream API."""
    try:
        delay_request()
        resp = requests.get(f"{BASE_URL}/address/{address}")
        if resp.status_code != 200:
            log_error(f"Received status code {resp.status_code} for address data", code=201)
            return None
        return resp.json()
    except Exception as e:
        log_error(f"Exception fetching address data: {e}", code=202)
        return None

def fetch_address_txs(address):
    """Fetch a list of recent transactions for the address."""
    try:
        delay_request()
        resp = requests.get(f"{BASE_URL}/address/{address}/txs")
        if resp.status_code != 200:
            log_error(f"Received status code {resp.status_code} for address transactions", code=203)
            return []
        return resp.json()
    except Exception as e:
        log_error(f"Exception fetching address transactions: {e}", code=204)
        return []

def fetch_transaction_data(txid):
    """Fetch transaction details."""
    try:
        delay_request()
        resp = requests.get(f"{BASE_URL}/tx/{txid}")
        if resp.status_code != 200:
            log_error(f"Received status code {resp.status_code} for transaction data", code=205)
            return None
        return resp.json()
    except Exception as e:
        log_error(f"Exception fetching transaction: {e}", code=206)
        return None

def fetch_transaction_outspends(txid):
    """Fetch outspends of a transaction's outputs to determine if they are spent."""
    try:
        delay_request()
        resp = requests.get(f"{BASE_URL}/tx/{txid}/outspends")
        if resp.status_code != 200:
            log_error(f"Received status code {resp.status_code} for outspends", code=207)
            return None
        return resp.json()
    except Exception as e:
        log_error(f"Exception fetching outspends: {e}", code=208)
        return None

# Display Information
def display_address_info(address, address_data):
    chain_stats = address_data.get("chain_stats", {})
    balance = chain_stats.get("funded_txo_sum", 0) - chain_stats.get("spent_txo_sum", 0)
    tx_count = chain_stats.get("tx_count", 0)

    print(Fore.GREEN + f"\nAddress: {address}")
    print(f"Balance: {balance} satoshis")
    print(f"Total Transactions: {tx_count}")

def display_transaction_info(tx_data):
    txid = tx_data.get("txid")
    status = tx_data.get("status", {})
    confirmed = status.get("confirmed", False)
    block_time = status.get("block_time", None)
    confirmations = "Confirmed" if confirmed else "Unconfirmed"
    date_str = datetime.utcfromtimestamp(block_time).strftime('%Y-%m-%d %H:%M:%S UTC') if block_time else "N/A"

    print(Fore.BLUE + f"\nTransaction: {txid}")
    print(f"Status: {confirmations}")
    print(f"Timestamp: {date_str}")

    vin = tx_data.get("vin", [])
    print(Fore.YELLOW + f"Inputs ({len(vin)}):" + Style.RESET_ALL)
    for i, inp in enumerate(vin):
        prev_txid = inp.get("txid", "Coinbase")
        vout_index = inp.get("vout", "N/A")
        print(f"  Input {i+1}: from {Fore.GREEN}{prev_txid}{Style.RESET_ALL}, vout: {vout_index}")

    vout = tx_data.get("vout", [])
    print(Fore.YELLOW + f"Outputs ({len(vout)}):" + Style.RESET_ALL)
    for i, out in enumerate(vout):
        value = out.get("value", 0)
        scriptpubkey = out.get("scriptpubkey_address", "N/A")
        print(f"  Output {i+1}: {Fore.GREEN}{value}{Style.RESET_ALL} sat to {Fore.GREEN}{scriptpubkey}{Style.RESET_ALL}")


# Chain and Navigation
def add_to_chain(tx_data, path=None, source_txid=None):
    txid = tx_data.get("txid")
    visited_chain[txid] = {
        "data": tx_data,
        "from": source_txid,
        "path": path
    }

def follow_transaction(tx_data):
    """
    Command-based navigation:
    - 'iN': follow input N backward
    - 'oN': follow output N forward
    - 'dump': dump the chain to JSON
    - 'm': return to main menu
    - 'exit': quit
    """
    while True:
        print(Fore.YELLOW + "\nTRANSACTION NAVIGATION")
        print("----------")
        print("Commands:")
        print("  iN  - Follow input N backward (e.g., i3)")
        print("  oN  - Follow output N forward (e.g., o2)")
        print("  dump - Dump the chain to JSON")
        print("  m - Return to main menu")
        print("  exit - Quit")
        print("----------" + Style.RESET_ALL)

        cmd = input(Fore.YELLOW + "Enter command: " + Style.RESET_ALL).strip()
        cmd = check_special_commands(cmd)
        if cmd is None:
            # 'm' or 'exit' handled
            continue
        if cmd == '':
            # Just press enter does nothing, continue
            continue
        elif cmd == 'dump':
            dump_chain()
        elif cmd.startswith('i'):
            # iN command
            num_str = cmd[1:]
            if num_str.isdigit():
                idx = int(num_str)-1
                follow_input_by_index(tx_data, idx)
            else:
                print(Fore.RED + "Invalid input command format.")
        elif cmd.startswith('o'):
            # oN command
            num_str = cmd[1:]
            if num_str.isdigit():
                idx = int(num_str)-1
                follow_output_by_index(tx_data, idx)
            else:
                print(Fore.RED + "Invalid output command format.")
        else:
            print(Fore.RED + "Invalid command.")

def follow_output_by_index(tx_data, idx):
    vout = tx_data.get("vout", [])
    if idx < 0 or idx >= len(vout):
        print(Fore.RED + "Invalid output number.")
        return
    if not vout:
        print(Fore.RED + "No outputs to follow.")
        return

    outspends = fetch_transaction_outspends(tx_data.get("txid"))
    if outspends is None:
        return  # Error logged
    chosen_outspend = outspends[idx]
    if chosen_outspend is not None:
        next_txid = chosen_outspend.get("txid")
        next_tx_data = fetch_transaction_data(next_txid)
        if next_tx_data:
            add_to_chain(next_tx_data, path=f"followed output {idx+1} of {tx_data.get('txid')}", source_txid=tx_data.get('txid'))
            display_transaction_info(next_tx_data)
            follow_transaction(next_tx_data)
        else:
            log_error("Could not fetch the spending transaction.", code=301)
    else:
        print("This output is unspent. No further transaction.")

def follow_input_by_index(tx_data, idx):
    vin = tx_data.get("vin", [])
    if idx < 0 or idx >= len(vin):
        print(Fore.RED + "Invalid input number.")
        return
    if not vin:
        print(Fore.RED + "No inputs (possibly a coinbase transaction).")
        return

    inp_chosen = vin[idx]
    prev_txid = inp_chosen.get("txid", None)
    if prev_txid is None:
        print("This is a coinbase input, no previous transaction.")
        return

    prev_tx_data = fetch_transaction_data(prev_txid)
    if prev_tx_data:
        add_to_chain(prev_tx_data, path=f"followed input {idx+1} of {tx_data.get('txid')}", source_txid=tx_data.get('txid'))
        display_transaction_info(prev_tx_data)
        follow_transaction(prev_tx_data)
    else:
        log_error("Could not fetch the previous transaction.", code=302)


# Dumping and Loading Chains
def dump_chain():
    filename = f"chain_dump_{int(time.time())}.json"
    try:
        with open(filename, 'w') as f:
            json.dump(visited_chain, f, indent=4)
        print(Fore.GREEN + f"Chain dumped to {filename}")
    except Exception as e:
        log_error(f"Failed to dump chain: {e}", code=401)

def load_chain_menu():
    print(Fore.YELLOW + "\nLOAD PREVIOUSLY DUMPED CHAIN")
    print("----------")
    print("Type 'm' to return to main menu, 'exit' to quit.")
    print("----------" + Style.RESET_ALL)
    filename = input(Fore.YELLOW + "Enter the path to the JSON file: " + Style.RESET_ALL).strip()
    filename = check_special_commands(filename)
    if filename is None:
        return
    load_chain(filename)

def load_chain(filename):
    global visited_chain
    try:
        with open(filename, 'r') as f:
            loaded_data = json.load(f)
        visited_chain = loaded_data
        print(Fore.GREEN + f"Chain loaded from {filename}.")
        if visited_chain:
            print(Fore.YELLOW + "\nTransactions in loaded chain:")
            txids = list(visited_chain.keys())
            for i, tid in enumerate(txids):
                print(f"{i+1}. {tid} (from: {visited_chain[tid].get('from')}, path: {visited_chain[tid].get('path')})")
            user_prompt = Fore.YELLOW + "Select a transaction number to explore or press ENTER to skip (type 'm' for menu, 'exit' to quit): " + Style.RESET_ALL
            choice = input(user_prompt).strip()
            choice = check_special_commands(choice)
            if choice is None:
                return
            if choice.isdigit():
                c_idx = int(choice)-1
                if 0 <= c_idx < len(txids):
                    chosen_txid = txids[c_idx]
                    tx_data = visited_chain[chosen_txid].get("data")
                    if tx_data:
                        display_transaction_info(tx_data)
                        follow_transaction(tx_data)
                    else:
                        print(Fore.RED + "No transaction data found in chain for that txid.")
        else:
            print("Loaded chain is empty.")
    except FileNotFoundError:
        log_error(f"File not found: {filename}", code=501)
    except json.JSONDecodeError as e:
        log_error(f"JSON decode error: {e}", code=502)
    except Exception as e:
        log_error(f"Failed to load chain: {e}", code=503)

# Main
def main():
    print_banner()
    try:
        main_menu()
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\nSupport this project! bc1q8sptfr88g886xpxtjkmh26cvvf8sfm782yu5yp")
        sys.exit(0)

if __name__ == "__main__":
    main()
