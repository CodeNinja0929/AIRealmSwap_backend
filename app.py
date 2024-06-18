from flask import Flask, request, jsonify
from flask_cors import CORS
import random
from web3 import Web3

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize web3
infura_url = 'https://mainnet.infura.io/v3/YOUR_INFURA_PROJECT_ID'  # Replace with your Infura Project ID
web3 = Web3(Web3.HTTPProvider(infura_url))

# Uniswap V1 exchange contract ABI and address
uniswap_v1_exchange_abi = [
    {
        "constant": True,
        "inputs": [],
        "name": "getReserves",
        "outputs": [
            {"name": "reserve0", "type": "uint112"},
            {"name": "reserve1", "type": "uint112"},
            {"name": "blockTimestampLast", "type": "uint32"}
        ],
        "payable": False,
        "stateMutability": "view",
        "type": "function"
    },
    {
        "constant": False,
        "inputs": [
            {"name": "min_tokens", "type": "uint256"},
            {"name": "deadline", "type": "uint256"}
        ],
        "name": "ethToTokenSwapOutput",
        "outputs": [],
        "payable": True,
        "stateMutability": "payable",
        "type": "function"
    }
]

# Replace with the actual contract address obtained from the factory contract
uniswap_v1_exchange_address = '0x1F98431c8aD98523631AE4a59f267346ea31F984'  # Example exchange address

# Create contract instance
uniswap_v1_exchange = web3.eth.contract(address=uniswap_v1_exchange_address, abi=uniswap_v1_exchange_abi)

# Endpoint to fetch reserves
@app.route('/reserves', methods=['GET'])
def get_reserves():
    reserves = uniswap_v1_exchange.functions.getReserves().call()
    return jsonify({
        'tokenReserve': reserves[0],
        'ethReserve': reserves[1]
    })

# Endpoint to generate a random value
@app.route('/api/value', methods=['GET'])
def get_value():
    value = round(random.uniform(0.343, 0.5334), 4)
    return jsonify({'value': value})

# Endpoint to calculate minimum output amount based on slippage
@app.route('/calculate_min_amount_out', methods=['POST'])
def calculate_min_amount_out():
    data = request.get_json()
    amount_in = int(data['amountIn'])
    slippage = float(data['slippage'])

    reserves = uniswap_v1_exchange.functions.getReserves().call()
    token_reserve = reserves[0]
    eth_reserve = reserves[1]

    amount_out = get_output_amount(amount_in, eth_reserve, token_reserve)
    slippage_amount = amount_out * (slippage / 100)
    min_amount_out = amount_out - slippage_amount

    return jsonify({
        'minAmountOut': min_amount_out
    })

# Endpoint to perform the swap
@app.route('/swap', methods=['POST'])
def swap():
    data = request.get_json()
    amount_in = int(data['amountIn'])
    min_amount_out = int(data['minAmountOut'])
    user_address = data['userAddress']
    private_key = data['privateKey']  # Private key of the user for signing the transaction

    nonce = web3.eth.getTransactionCount(user_address)
    transaction = uniswap_v1_exchange.functions.ethToTokenSwapOutput(
        min_amount_out,
        web3.eth.getBlock('latest')['timestamp'] + 60
    ).buildTransaction({
        'chainId': 1,
        'gas': 2000000,
        'gasPrice': web3.toWei('50', 'gwei'),
        'nonce': nonce,
        'value': amount_in
    })

    signed_txn = web3.eth.account.signTransaction(transaction, private_key)
    tx_hash = web3.eth.sendRawTransaction(signed_txn.rawTransaction)

    return jsonify({
        'txHash': web3.toHex(tx_hash)
    })

# Helper function to calculate output amount
def get_output_amount(input_amount, input_reserve, output_reserve):
    input_amount_with_fee = input_amount * 997
    numerator = input_amount_with_fee * output_reserve
    denominator = (input_reserve * 1000) + input_amount_with_fee
    return numerator // denominator

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
