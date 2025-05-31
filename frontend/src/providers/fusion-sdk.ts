import { SDK } from "@1inch/cross-chain-sdk";
import { Web3 } from "web3";
import { PrivateKeyProviderConnector } from './private-key-connector';
import { Web3Like } from "./web3-provider";

const web3 = new Web3(process.env.RPC_URL);

const sdk = new SDK({  
    url: process.env.BACKEND_URL as string,  
    authKey: process.env.ONE_INCH_API_KEY,  
    blockchainProvider: new PrivateKeyProviderConnector(process.env.PRIVATE_KEY as string, web3 as Web3Like)  
}) 

export default sdk;