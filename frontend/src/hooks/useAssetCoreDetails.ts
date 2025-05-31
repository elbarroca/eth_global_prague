import { useState, useEffect, useCallback } from 'react';

export interface AssetCoreDetails {
  name: string;
  symbol: string;
  decimals: number;
  logo_uri?: string;
  address: string;
  chain_id: number;
}

interface UseAssetCoreDetailsParams {
  chainId: number | null;
  tokenAddress: string | null;
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const useAssetCoreDetails = ({
  chainId,
  tokenAddress,
}: UseAssetCoreDetailsParams) => {
  const [data, setData] = useState<AssetCoreDetails | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    if (!chainId || !tokenAddress) {
      setData(null);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // For now, we'll create a mock response since this endpoint doesn't exist yet
      // In a real implementation, you would call your backend API
      // const response = await fetch(`${API_BASE_URL}/api/token_details?chain_id=${chainId}&address=${tokenAddress}`);
      
      // Mock data for now - you can replace this with actual API call
      const mockData: AssetCoreDetails = {
        name: "Token",
        symbol: "TOKEN",
        decimals: 18,
        logo_uri: undefined,
        address: tokenAddress,
        chain_id: chainId,
      };

      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      setData(mockData);
    } catch (err: any) {
      setError(err.message || 'An unknown error occurred');
      setData(null);
    } finally {
      setIsLoading(false);
    }
  }, [chainId, tokenAddress]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  return { data, isLoading, error, refetch: fetchData };
};

// Example Usage:
// import { useAssetCoreDetails } from './hooks/useAssetCoreDetails';
//
// const TokenInfoComponent = ({ chainId, tokenAddress }) => {
//   const { data, isLoading, error } = useAssetCoreDetails({ chainId, tokenAddress });
//
//   if (isLoading) return <p>Loading token details...</p>;
//   if (error) return <p>Error: {error}</p>;
//   if (!data) return <p>No token details found.</p>;
//
//   return (
//     <div>
//       <h3>{data.name} ({data.symbol})</h3>
//       <p>Decimals: {data.decimals}</p>
//       {data.logo_uri && <img src={data.logo_uri} alt={data.name} />}
//     </div>
//   );
// }; 