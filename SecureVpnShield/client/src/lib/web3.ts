import Web3 from 'web3';
import { AbiItem } from 'web3-utils';
import { Contract } from 'web3-eth-contract';

const contractAddress = import.meta.env.VITE_CONTRACT_ADDRESS as string;
const contractABI: AbiItem[] = [
  {
    "inputs": [
      {
        "internalType": "string",
        "name": "plan",
        "type": "string"
      }
    ],
    "name": "purchaseSubscription",
    "outputs": [],
    "stateMutability": "payable",
    "type": "function"
  },
  {
    "inputs": [
      {
        "internalType": "address",
        "name": "user",
        "type": "address"
      }
    ],
    "name": "checkSubscription",
    "outputs": [
      {
        "internalType": "bool",
        "name": "active",
        "type": "bool"
      },
      {
        "internalType": "string",
        "name": "plan",
        "type": "string"
      },
      {
        "internalType": "uint256",
        "name": "expires",
        "type": "uint256"
      }
    ],
    "stateMutability": "view",
    "type": "function"
  }
];

export async function initWeb3() {
  if (typeof window.ethereum !== 'undefined') {
    const web3 = new Web3(window.ethereum);
    try {
      await window.ethereum.request({ method: 'eth_requestAccounts' });
      const contract = new web3.eth.Contract(contractABI, contractAddress);
      return { web3, contract };
    } catch (error) {
      console.error('User denied account access');
      throw error;
    }
  } else {
    throw new Error('Please install MetaMask or another Web3 wallet');
  }
}

export async function purchaseSubscription(plan: string, price: number) {
  const { web3, contract } = await initWeb3();
  const accounts = await web3.eth.getAccounts();
  
  return contract.methods.purchaseSubscription(plan).send({
    from: accounts[0],
    value: web3.utils.toWei(price.toString(), 'ether')
  });
}

export async function checkSubscription(address: string) {
  const { contract } = await initWeb3();
  return contract.methods.checkSubscription(address).call();
}

declare global {
  interface Window {
    ethereum: any;
  }
}
