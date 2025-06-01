#!/bin/bash
# Test script for 1inch Fusion+ proxy endpoints

# Set the base URL for your local server
BASE_URL="http://localhost:8000"

# Colors for better readability
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Testing 1inch Fusion+ Proxy Endpoints ===${NC}\n"

# Function to print dividers
divider() {
  echo -e "\n${BLUE}----------------------------------------${NC}\n"
}

# 1. Test GET request - Get supported chains
echo -e "${GREEN}GET Request: Fetch supported chains${NC}"
curl -v "${BASE_URL}/fusion-plus/v1.0/supported-chains" \
  -H "Accept: application/json" 2>&1 | grep -E "^(<|>)|HTTP/"

divider

# 2. Test GET request - Get tokens
echo -e "${GREEN}GET Request: Fetch tokens for Ethereum (chain ID 1)${NC}"
curl -v "${BASE_URL}/fusion-plus/v1.0/1/tokens" \
  -H "Accept: application/json" 2>&1 | grep -E "^(<|>)|HTTP/"

divider

# 3. Test POST request - Get quote
echo -e "${GREEN}POST Request: Get swap quote${NC}"
curl -v "${BASE_URL}/fusion-plus/v1.0/quote" \
  -X POST \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "sourceChainId": 1,
    "destinationChainId": 1,
    "sourceTokenAmount": "1000000000000000000",
    "sourceTokenAddress": "0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE",
    "destinationTokenAddress": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "walletAddress": "0x0000000000000000000000000000000000000001"
  }' 2>&1 | grep -E "^(<|>)|HTTP/"

divider

# 4. Test GET request - Check preset configs
echo -e "${GREEN}GET Request: Check preset configs${NC}"
curl -v "${BASE_URL}/fusion-plus/v1.0/1/presets" \
  -H "Accept: application/json" 2>&1 | grep -E "^(<|>)|HTTP/"

divider

# 5. Test GET request - Check health endpoint
echo -e "${GREEN}GET Request: Check health${NC}"
curl -v "${BASE_URL}/fusion-plus/v1.0/health" \
  -H "Accept: application/json" 2>&1 | grep -E "^(<|>)|HTTP/"

divider

# 6. Test endpoints with query parameters
echo -e "${GREEN}GET Request: Testing with query parameters${NC}"
curl -v "${BASE_URL}/fusion-plus/v1.0/1/approve/target?tokenAddress=0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" \
  -H "Accept: application/json" 2>&1 | grep -E "^(<|>)|HTTP/"

echo -e "\n${GREEN}All tests completed!${NC}" 