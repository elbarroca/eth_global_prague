import { Button } from "@/components/ui/button"
import { useApproveTransfer } from "@/hooks/erc20/useApproveTransfer"
import { useOrder, TOKEN_ADDRESS } from "@/hooks/1inch/useOrder";
import { SupportedChain } from "@1inch/cross-chain-sdk";
import { useAccount } from "wagmi";

export default function TestButton() {
    const { address: walletAddress } = useAccount();
    const { approveTransfer } = useApproveTransfer();
    const { getQuoteAndExecuteOrder } = useOrder();

    // Define chain IDs according to 1inch cross-chain SDK
    const CHAIN_IDS = {
        ETHEREUM: 1 as SupportedChain,
        BASE: 8453 as SupportedChain,
        ARBITRUM: 42161 as SupportedChain
    };

    const amount = "196800000000000" // ≈0.0001968 ETH ≈\$0.50 at \$2,540.66/ETH

    const approve = async () => {
        // Use BigInt constructor instead of literal for compatibility
        const result = await approveTransfer(BigInt(amount));
        console.log(result);
    }

    const sendTx = async () => {
        if (!walletAddress) {
            console.error("Wallet not connected");
            return;
        }

        const result = await getQuoteAndExecuteOrder({
            srcChainId: CHAIN_IDS.BASE,
            dstChainId: CHAIN_IDS.ARBITRUM,
            srcTokenAddress: TOKEN_ADDRESS,
            dstTokenAddress: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", //usdc on arbitrum
            amount: amount, // 10 tokens
            enableEstimate: true, 
            walletAddress: walletAddress 
        });
        
        console.log(result);
    }
    
    return (
        <div className="flex gap-3">
            <Button onClick={approve}>Test Approve</Button>
            <Button onClick={sendTx} className="bg-emerald-600 hover:bg-emerald-700">Test Cross-Chain Tx</Button>
        </div>
    )
}
