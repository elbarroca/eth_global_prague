import { SDK } from "@1inch/cross-chain-sdk";
import { Web3 } from "web3";
import { PrivateKeyProviderConnector } from './private-key-connector';
import { Web3Like } from "./web3-provider";

async function initializeSDK() {
    const isServer = typeof window === 'undefined';
    const hasRequiredEnvVars = process.env.NEXT_PUBLIC_RPC_URL && 
                              process.env.NEXT_PUBLIC_BACKEND_URL && 
                              process.env.NEXT_PUBLIC_ONE_INCH_API_KEY 
                            //   process.env.PRIVATE_KEY;
    
    let sdk: SDK | null = null;
    
    // Only initialize SDK if we have all required environment variables
    if (hasRequiredEnvVars) {
        try {
            const web3 = new Web3(process.env.NEXT_PUBLIC_RPC_URL);
            
            sdk = new SDK({  
                url: process.env.NEXT_PUBLIC_BACKEND_URL as string,  
                authKey: process.env.NEXT_PUBLIC_ONE_INCH_API_KEY,  
                // blockchainProvider: new PrivateKeyProviderConnector(process.env.PRIVATE_KEY as string, web3 as Web3Like)  
            });
            console.log(sdk);
            console.log('1inch SDK initialized successfully');
        } catch (error) {
            console.warn('Failed to initialize 1inch SDK:', error);
            sdk = null;
        }
    } else {
        console.warn('1inch SDK not initialized: Missing required environment variables (RPC_URL, BACKEND_URL, ONE_INCH_API_KEY, PRIVATE_KEY)');
    }
    
    return sdk;
}
// Check if we're in a browser environment and if all required env vars are available
export default initializeSDK;