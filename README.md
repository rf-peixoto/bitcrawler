# Bitcrawler
Bitcrawler is a simple blockchain explorer via terminal. It allows you to analyze the transactions of a wallet, follow the inputs and outputs, dump a chain of outputs to your current wallet.

## Features

- **Query Address**:  
  View the address balance, transaction count, and recent transactions.
  
- **Query Transaction**:  
  Display details about a specific transaction, including inputs, outputs, confirmation status, and timestamp.

- **Trace Transactions**:  
  Navigate through transactions by following outputs forward (to see where funds were spent) and inputs backward (to see where funds came from). This tool helps in tracing the flow of satoshis from wallet to wallet, allowing users to identify the provenance of "dirty" coins or suspicious funds.

- **Chain Dumping and Loading**:  
  Save the traced chain data to a JSON file for later analysis. Load a previously dumped chain to continue tracing from where you left off.
- **Command-Based Navigation**:  
  Use commands like:
  - `oN` to follow output N forward (e.g., `o2`)
  - `iN` to follow input N backward (e.g., `i3`)
  - `dump` to dump the chain
  - `m` to return to the main menu
  - `exit` to quit

- **Return to Main Menu Anytime**:  
  Typing `m` in any prompt returns you to the main menu.  
  Typing `exit` at any prompt quits the application.

## Support

- You can help this project by donating some sats to `bc1q8sptfr88g886xpxtjkmh26cvvf8sfm782yu5yp`
