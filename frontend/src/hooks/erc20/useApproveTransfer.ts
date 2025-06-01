// async function submit(e: React.FormEvent<HTMLFormElement>) {
//     e.preventDefault()

//     if (!receiverAddress) {
//       alert('Please connect your wallet.');
//       return;
//     }

//     const formData = new FormData(e.target as HTMLFormElement)
//     const asset = formData.get('asset') as string
//     const amount_wei = formData.get('amount_wei') as string
//     const targetAddress: `0x${string}` = formData.get('target_address') as `0x${string}`;
//     const secret = formData.get('secret') as string

//     let token_address = "";
//     if (asset === 'USDT') {
//       token_address = "0xaA8E23Fb1079EA71e0a56F48a2aA51851D8433D0";
//     } else if (asset === 'USDC') {
//       token_address = "0xf08A50178dfcDe18524640EA6618a1f965821715";
//     } else if (asset === 'LINK') {
//       token_address = "0x779877A7B0D9E8603169DdbD7836e478b4624789";
//     } else if (asset === 'UNI') {
//       token_address = "0x41952a7F9247442292410EEa5CC94a0Be3724399";
//     }

//     // Convert amount_wei to BigInt or BigNumber
//     const amountWeiBigInt = BigInt(amount_wei);

//     if (asset === 'eth') {
//       console.log('sending eth');
//       writeContract({
//         address: smartContractAddress,
//         abi,
//         functionName: 'sendEth',
//         args: [targetAddress, secret],//need to also add payable amount
//         value: amountWeiBigInt, // Use amountWeiBN if using BigNumber
//       })
//     } else {
//         console.log('approving token transfer');
//         const result = await writeContract(config, {
//             address: token_address,
//             abi,
//             functionName: 'approve',
//             args: [smartContractAddress, amountWeiBigInt],
//         })
        
//         await waitForTransactionReceipt(
//             config, {
//             hash: result,
//             confirmations: 1, // You can change the number of block confirmations as per your requirement
//         })
        
//         console.log('sending token');
//         const result2 = await writeContract(config, {
//             address: smartContractAddress,
//             abi,
//             functionName: 'sendToken',
//             args: [targetAddress, amountWeiBigInt, secret, token_address],
//         })
//     }
//   }

import erc20Abi from '@/abi/erc20';
import { SPENDER, TOKEN_ADDRESS } from '../1inch/useOrder';
import { useWriteContract } from 'wagmi'

export function useApproveTransfer() {
    const { writeContract } = useWriteContract();
    
    const approveTransfer = async (amount: BigInt) => {
        try {
            const result = await writeContract({
                address: TOKEN_ADDRESS,
                abi: erc20Abi,
                functionName: 'approve',
                args: [SPENDER, amount],
            });

            return result;
        } catch (error) {
            console.error(error);
            return null;
        }
    };

    return {
        approveTransfer
    };
}
