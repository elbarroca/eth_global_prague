#!/bin/bash

# Test script for 1inch Fusion+ endpoints
echo "1inch Fusion+ API Test Script"
echo "=============================="

# Set the base URL
BASE_URL="http://localhost:8000"

# Start the FastAPI server in the background
echo "Starting FastAPI server..."
cd backend
uvicorn main:app --reload > server.log 2>&1 &
SERVER_PID=$!
sleep 3  # Wait for server to start

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    echo -e "\n${GREEN}Testing $1...${NC}"
    RESPONSE=$(curl -s -X POST "$BASE_URL$2" \
        -H "Content-Type: application/json" \
        -d "$3")
    
    echo -e "Response:\n$RESPONSE\n"
    
    # Return the response for potential reuse
    echo "$RESPONSE"
}

# Sample data - update with valid addresses for your chains
SRC_CHAIN_ID=1  # Ethereum
DST_CHAIN_ID=137  # Polygon
SRC_TOKEN="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"  # USDC on Ethereum
DST_TOKEN="0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174"  # USDC on Polygon
WALLET="0x742d35Cc6634C0532925a3b844Bc454e4438f44e"  # Example wallet
AMOUNT="1000000000"  # 1000 USDC with 6 decimals

# 1. Test the quote endpoint
QUOTE_DATA='{
    "src_chain_id": '$SRC_CHAIN_ID',
    "dst_chain_id": '$DST_CHAIN_ID',
    "src_token_address": "'$SRC_TOKEN'",
    "dst_token_address": "'$DST_TOKEN'",
    "amount_wei": "'$AMOUNT'",
    "wallet_address": "'$WALLET'",
    "enable_estimate": true
}'

echo "Quote Request:"
echo "$QUOTE_DATA"

QUOTE_RESPONSE=$(test_endpoint "Get Fusion+ Quote" "/fusion/quote" "$QUOTE_DATA")

# Save the quote response to a temporary file
echo "$QUOTE_RESPONSE" > /tmp/fusion_quote.json

# 2. Test the build order endpoint (using the quote from previous step)
BUILD_DATA='{
    "quote": '$QUOTE_RESPONSE',
    "wallet_address": "'$WALLET'",
    "preset_name": "fast"
}'

ORDER_RESPONSE=$(test_endpoint "Build Fusion+ Order" "/fusion/build_order" "$BUILD_DATA")

# Save the order data to a temporary file
echo "$ORDER_RESPONSE" > /tmp/fusion_order.json

# 3. Test the submit order endpoint
# Note: In a real scenario, this order would need to be signed by the user's wallet
# This is just a simplified example that will likely fail without a valid signature
SUBMIT_DATA='{
    "src_chain_id": '$SRC_CHAIN_ID',
    "signed_order_payload": {
        "chainId": '$SRC_CHAIN_ID',
        "order": '$ORDER_RESPONSE',
        "quoteId": "example-quote-id"
    }
}'

test_endpoint "Submit Fusion+ Order" "/fusion/submit_order" "$SUBMIT_DATA"

# Clean up
echo -e "\n${GREEN}Stopping server...${NC}"
kill $SERVER_PID
echo "Server stopped. Test complete."
echo "Response data saved to /tmp/fusion_quote.json and /tmp/fusion_order.json"

# Instructions for manual testing with a real wallet
echo -e "\n${GREEN}For real testing with wallet signatures:${NC}"
echo "1. Start the server with: cd backend && uvicorn main:app --reload"
echo "2. Use Postman or a web app with web3 integration to get quotes"
echo "3. Sign the orders with a wallet like MetaMask"
echo "4. Submit the signed orders back to the API"