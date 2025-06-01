const BLOCKSCOUT_API_BASE_URL = 'https://eth.blockscout.com/api/v2';

async function fetchData<T>(endpoint: string, params?: Record<string, string | number | boolean>): Promise<T> {
  const url = new URL(`${BLOCKSCOUT_API_BASE_URL}${endpoint}`);
  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined && value !== null) { // Only append if value is present
        url.searchParams.append(key, String(value));
      }
    });
  }

  try {
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: {
        'Accept': 'application/json',
      },
    });

    if (!response.ok) {
      // Attempt to get more detailed error info from response body
      let errorBody = '';
      try {
        errorBody = await response.text();
      } catch (e) {
        // ignore if can't read body
      }
      throw new Error(`HTTP error ${response.status} for ${url.toString()}: ${response.statusText}. Body: ${errorBody}`);
    }
    return response.json() as Promise<T>;
  } catch (error) {
    console.error(`Failed to fetch data from ${url.toString()}:`, error);
    throw error; // Re-throw the error after logging
  }
}

// --- Type Definitions based on Blockscout API responses (these might need adjustments based on actual API output) ---

// For /stats/chart/transactions
export interface TransactionChartPoint {
  date: string; // e.g., "2023-10-26"
  tx_count: number;
  // There might be other fields like gas_used, new_addresses, etc.
}
export type TransactionStatsChartResponse = TransactionChartPoint[];


// For /tokens
export interface TokenInfo {
  address: string;
  circulating_market_cap: string | null;
  decimals: string | null; // Usually string, can be null if not ERC20 standard
  exchange_rate: string | null;
  holders: string | null; // Count of holders
  icon_url: string | null;
  name: string | null;
  symbol: string | null;
  total_supply: string | null;
  type: 'ERC-20' | 'ERC-721' | 'ERC-1155' | string; // Or other token types
  volume_24h: string | null;
}
export interface PaginationParams {
  block_number: number | null;
  index: number | null;
  items_count: number | null;
  transaction_index: number | null;
  // ... other pagination fields Blockscout might use
}
export interface TokensResponse {
  items: TokenInfo[];
  next_page_params: PaginationParams | null;
}


// For /tokens/{address_hash}/transfers
export interface AddressDetails {
  ens_domain_name: string | null;
  hash: string;
  implementation_name: string | null;
  is_contract: boolean;
  is_verified: boolean | null;
  name: string | null;
  private_tags: any[]; // Define more specifically if needed
  public_tags: any[];  // Define more specifically if needed
  watchlist_names: any[];// Define more specifically if needed
}
export interface TokenTransferTokenInfo {
  address: string;
  circulating_market_cap: string | null;
  decimals: string | null;
  exchange_rate: string | null;
  holders: string | null;
  icon_url: string | null;
  name: string | null;
  symbol: string | null;
  total_supply: string | null;
  type: string;
}
export interface TokenTransferValue {
  value: string; // Amount of token transferred
  decimals: string | null; // Token's decimals
}
export interface TokenTransfer {
  block_hash: string;
  from: AddressDetails;
  log_index: string;
  method: string | null; // e.g., "transfer", "mint"
  timestamp: string; // ISO 8601 date string
  to: AddressDetails;
  token: TokenTransferTokenInfo;
  total: TokenTransferValue; // For ERC-20, represents amount. For ERC-721/1155, might be token_id related.
  tx_hash: string;
  type: 'token_transfer' | string; // or 'NFT transfer' etc.
  // For ERC-721/1155, there might be a 'token_id' field
  token_id?: string;
  // There might be an 'amount' field for ERC-1155
  amount?: string;
}
export interface TokenTransfersResponse {
  items: TokenTransfer[];
  next_page_params: PaginationParams | null;
}


// For /tokens/{address_hash}/holders
export interface TokenHolder {
  address: AddressDetails;
  token: TokenTransferTokenInfo; // Re-using the token info from transfers
  value: string; // The balance of the token for this holder
  // Blockscout might also include percentage_relative_to_total_supply
  percentage_relative_to_total_supply?: number | null;
}
export interface TokenHoldersResponse {
  items: TokenHolder[];
  next_page_params: PaginationParams | null;
}


// --- API Function Implementations ---

/**
 * 1. Fetches transaction statistics chart data.
 * Endpoint: /stats/chart/transactions
 */
export async function getTransactionStatsChart(): Promise<TransactionStatsChartResponse> {
  return fetchData<TransactionStatsChartResponse>('/stats/chart/transactions');
}

/**
 * 2. Fetches a list of tokens.
 * Endpoint: /tokens
 * @param params Optional query parameters like q (search), type, page, offset.
 * Refer to Blockscout docs for all available query params.
 */
export interface GetTokensParams {
  q?: string; // Search query for token name or symbol
  type?: 'ERC-20' | 'ERC-721' | 'ERC-1155'; // Filter by token type
  // Blockscout uses a custom pagination with `next_page_params` from previous responses.
  // For initial call, these might be specific like:
  items_count?: number; // How many items to return
  // Or other params Blockscout might use for pagination like 'page' and 'offset' if supported directly
  page?: number;
  offset?: number;
  // You'll need to pass the `next_page_params` object from a previous response to get the next page.
  // For simplicity, this example doesn't deeply integrate complex cursor pagination.
  // If Blockscout uses specific keys in `next_page_params` directly as query params, add them here.
  // e.g., if next_page_params contains { block_number: 123, index: 10 }
  block_number?: number;
  index?: number;
}
export async function getTokens(params?: GetTokensParams): Promise<TokensResponse> {
  return fetchData<TokensResponse>('/tokens', params);
}

/**
 * 3. Fetches transfers for a specific token.
 * Endpoint: /tokens/{address_hash}/transfers
 * @param tokenAddressHash The contract address of the token.
 * @param params Optional query parameters for pagination (e.g., items_count, or specific keys from next_page_params).
 */
export interface GetTokenTransfersParams {
  // Similar to GetTokensParams, for pagination.
  items_count?: number;
  block_number?: number;
  index?: number;
  // Add other params if Blockscout uses them for this endpoint's pagination
}
export async function getTokenTransfers(
  tokenAddressHash: string,
  params?: GetTokenTransfersParams
): Promise<TokenTransfersResponse> {
  if (!tokenAddressHash) throw new Error("Token address hash is required.");
  return fetchData<TokenTransfersResponse>(`/tokens/${tokenAddressHash}/transfers`, params);
}

/**
 * 4. Fetches holders for a specific token.
 * Endpoint: /tokens/{address_hash}/holders
 * @param tokenAddressHash The contract address of the token.
 * @param params Optional query parameters for pagination.
 */
export interface GetTokenHoldersParams {
  // Similar to GetTokensParams, for pagination.
  items_count?: number;
  // Add other params if Blockscout uses them for this endpoint's pagination
}
export async function getTokenHolders(
  tokenAddressHash: string,
  params?: GetTokenHoldersParams
): Promise<TokenHoldersResponse> {
  if (!tokenAddressHash) throw new Error("Token address hash is required.");
  return fetchData<TokenHoldersResponse>(`/tokens/${tokenAddressHash}/holders`, params);
}
