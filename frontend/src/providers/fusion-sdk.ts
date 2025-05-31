import { SDK } from "@1inch/cross-chain-sdk";

const sdk = new SDK({  
    url: 'https://localhost:5000/fusion-plus',  
    authKey: process.env.ONE_INCH_API_KEY,  
    blockchainProvider: new WagmiProviderConnector(connection)  
})  