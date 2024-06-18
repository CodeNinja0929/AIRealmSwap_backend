const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const Web3 = require('web3');
const { randomFloat } = require('random-float');
require('dotenv').config();

const app = express();
app.use(cors());
app.use(bodyParser.json());

// Initialize web3
const infuraUrl = `https://mainnet.infura.io/v3/${process.env.INFURA_PROJECT_ID}`; // Use your Infura Project ID
const web3 = new Web3(new Web3.providers.HttpProvider(infuraUrl));

// Uniswap V1 exchange contract ABI and address
const uniswapV1ExchangeAbi = [
  {
    constant: true,
    inputs: [],
    name: 'getReserves',
    outputs: [
      { name: 'reserve0', type: 'uint112' },
      { name: 'reserve1', type: 'uint112' },
      { name: 'blockTimestampLast', type: 'uint32' },
    ],
    payable: false,
    stateMutability: 'view',
    type: 'function',
  },
  {
    constant: false,
    inputs: [
      { name: 'min_tokens', type: 'uint256' },
      { name: 'deadline', type: 'uint256' },
    ],
    name: 'ethToTokenSwapOutput',
    outputs: [],
    payable: true,
    stateMutability: 'payable',
    type: 'function',
  },
];

// Replace with the actual contract address obtained from the factory contract
const uniswapV1ExchangeAddress = '0x1F98431c8aD98523631AE4a59f267346ea31F984'; // Example exchange address

// Create contract instance
const uniswapV1Exchange = new web3.eth.Contract(uniswapV1ExchangeAbi, uniswapV1ExchangeAddress);

// Endpoint to fetch reserves
app.get('/reserves', async (req, res) => {
  try {
    const reserves = await uniswapV1Exchange.methods.getReserves().call();
    res.json({
      tokenReserve: reserves[0],
      ethReserve: reserves[1],
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to generate a random value
app.get('/api/value', (req, res) => {
  const value = parseFloat(randomFloat(0.343, 0.5334).toFixed(4));
  res.json({ value });
});

// Endpoint to calculate minimum output amount based on slippage
app.post('/calculate_min_amount_out', async (req, res) => {
  try {
    const { amountIn, slippage } = req.body;

    const reserves = await uniswapV1Exchange.methods.getReserves().call();
    const tokenReserve = reserves[0];
    const ethReserve = reserves[1];

    const amountOut = getOutputAmount(amountIn, ethReserve, tokenReserve);
    const slippageAmount = amountOut * (slippage / 100);
    const minAmountOut = amountOut - slippageAmount;

    res.json({
      minAmountOut,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Endpoint to perform the swap
app.post('/swap', async (req, res) => {
  try {
    const { amountIn, minAmountOut, userAddress, privateKey } = req.body;

    const nonce = await web3.eth.getTransactionCount(userAddress);
    const transaction = uniswapV1Exchange.methods.ethToTokenSwapOutput(
      minAmountOut,
      Math.floor(Date.now() / 1000) + 60
    ).encodeABI();

    const tx = {
      from: userAddress,
      to: uniswapV1ExchangeAddress,
      gas: 2000000,
      gasPrice: web3.utils.toWei('50', 'gwei'),
      nonce: nonce,
      value: amountIn,
      data: transaction,
    };

    const signedTx = await web3.eth.accounts.signTransaction(tx, privateKey);
    const txHash = await web3.eth.sendSignedTransaction(signedTx.rawTransaction);

    res.json({
      txHash: txHash.transactionHash,
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Helper function to calculate output amount
function getOutputAmount(inputAmount, inputReserve, outputReserve) {
  const inputAmountWithFee = inputAmount * 997;
  const numerator = inputAmountWithFee * outputReserve;
  const denominator = inputReserve * 1000 + inputAmountWithFee;
  return Math.floor(numerator / denominator);
}

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server is running on port ${PORT}`);
});
