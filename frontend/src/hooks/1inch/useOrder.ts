import {  
    HashLock,  
    SupportedChain,  
    OrderParams,
    PresetEnum,
    OrderStatus,  
} from '@1inch/cross-chain-sdk';
import initializeSDK from "@/providers/fusion-sdk";
import { getRandomBytes32 } from "@/utils/get-random-bytes";
import { sleep } from "@/utils/sleep";

export const TOKEN_ADDRESS = "0x4200000000000000000000000000000006"; //wETH on base
export const SPENDER = "0x111111125421ca6dc452d289314280a0f8842a65";

export interface quoteParams {
    srcChainId: SupportedChain;
    dstChainId: SupportedChain;
    srcTokenAddress: string;
    dstTokenAddress: string;
    amount: string;
    enableEstimate: boolean;
    walletAddress: string;
}

// const params = {
//     srcChainId: NetworkEnum.COINBASE,
//     dstChainId: NetworkEnum.ARBITRUM,
//     srcTokenAddress: "0xc5fecC3a29Fb57B5024eEc8a2239d4621e111CBE", //1inch on base
//     dstTokenAddress: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", //usdc on arbitrum
//     amount: "10000000000000000000", // 10 1inch
//     enableEstimate: true,
//     walletAddress: makerAddress,
//   };
  
const source = "sdk-tutorial";

export async function getActiveOrders() {
    const sdk = await initializeSDK();
    if (!sdk) {
        throw new Error('1inch SDK not available. Please check environment configuration.');
    }
    const orders = await sdk.getActiveOrders({ page: 1, limit: 2 });
    return orders;
}

export async function getQuoteAndExecuteOrder(params: quoteParams) {
  try {
    const sdk = await initializeSDK();

    if (!sdk) {
      throw new Error('1inch SDK not available. Please check environment configuration.');
    }

    const quote = await sdk.getQuote(params);
    const secretsCount = quote.getPreset().secretsCount;

    const secrets = Array.from({ length: secretsCount }).map(() =>
      getRandomBytes32()
    );
    const secretHashes = secrets.map((x) => HashLock.hashSecret(x));

    const hashLock =  
        secrets.length === 1  
            ? HashLock.forSingleFill(secrets[0])  
            : HashLock.forMultipleFills(HashLock.getMerkleLeaves(secrets)) 

    try {
      const { hash, quoteId, order } = await sdk.createOrder(quote, {
        walletAddress: params.walletAddress,
        hashLock,
        preset: PresetEnum.fast,
        source,
        secretHashes,
      } as OrderParams);
      console.log({ hash, quoteId, order }, "order created");

      try {
        const orderInfo = await sdk.submitOrder(
          quote.srcChainId,
          order,
          quoteId,
          secretHashes
        );

        // return { success: true, orderInfo, hash, quoteId, order };
        
        while (true) {  
            const secretsToShare = await sdk.getReadyToAcceptSecretFills(hash)  
      
            if (secretsToShare.fills.length) {  
                for (const {idx} of secretsToShare.fills) {  
                    await sdk.submitSecret(hash, secrets[idx])  
      
                    console.log({idx}, 'shared secret')  
                }  
            }  
      
            // check if order finished  
            const {status} = await sdk.getOrderStatus(hash)  
      
            if (  
                status === OrderStatus.Executed ||  
                status === OrderStatus.Expired ||  
                status === OrderStatus.Refunded  
            ) {  
                break  
            }  
      
            await sleep(1000)  
        }  
      
        const statusResponse = await sdk.getOrderStatus(hash)  
      
        console.log(statusResponse)  
        
      } catch (submitError: any) {
        if (submitError.response?.data) {
          console.error("Response data:", submitError.response.data);
        } else {
          console.error("Error details:", submitError);
        }
        return { success: false, error: submitError };
      }
    } catch (error: any) {
      if (error.response?.data) {
        console.error("Response data:", error.response.data);
      } else {
        console.error("Error details:", error);
      }
      return { success: false, error };
    }
  } catch (err: any) {
    console.error("Error inside async block:", err);
    return { success: false, error: err };
  }
}

export function useOrder() {
  return {
    getQuoteAndExecuteOrder
  };
}

