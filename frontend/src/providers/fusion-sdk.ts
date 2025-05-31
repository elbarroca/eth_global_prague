import { SDK } from "@1inch/cross-chain-sdk";
import { Web3 } from "web3";
import { PrivateKeyProviderConnector } from './private-key-connector';
import { Web3Like } from "./web3-provider";

// Check if we're in a browser environment and if all required env vars are available
const isServer = typeof window === 'undefined';
const hasRequiredEnvVars = process.env.RPC_URL && 
                          process.env.BACKEND_URL && 
                          process.env.ONE_INCH_API_KEY && 
                          process.env.PRIVATE_KEY;

let sdk: SDK | null = null;

// Only initialize SDK if we have all required environment variables
if (hasRequiredEnvVars) {
    try {
        const web3 = new Web3(process.env.RPC_URL);
        
        sdk = new SDK({  
            url: process.env.BACKEND_URL as string,  
            authKey: process.env.ONE_INCH_API_KEY,  
            blockchainProvider: new PrivateKeyProviderConnector(process.env.PRIVATE_KEY as string, web3 as Web3Like)  
        });
    } catch (error) {
        console.warn('Failed to initialize 1inch SDK:', error);
        sdk = null;
    }
} else {
    console.warn('1inch SDK not initialized: Missing required environment variables (RPC_URL, BACKEND_URL, ONE_INCH_API_KEY, PRIVATE_KEY)');
}

export default sdk;