#!/bin/bash

# Test script for 1inch Fusion+ endpoints
echo "1inch Fusion+ API Test Script"
echo "=============================="

# Set the base URL
BASE_URL="http://localhost:8000"

# Check if we're already in the backend directory
if [ -f "main.py" ]; then
  # We're already in the backend directory
  SCRIPT_DIR="."
else
  # We're in the project root, need to go to backend
  SCRIPT_DIR="backend"
  cd $SCRIPT_DIR || { echo "Error: backend directory not found. Make sure you're running this from the project root or backend directory."; exit 1; }
fi

# Start the FastAPI server in the background
echo "Starting FastAPI server..."
uvicorn main:app --reload > server.log 2>&1 &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"
sleep 3  # Wait for server to start

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Test function
test_endpoint() {
    echo -e "\n${GREEN}Testing $1...${NC}"
    echo "Request data:"
    echo "$3" | python -m json.tool 2>/dev/null || echo "$3"
    
    RESPONSE=$(curl -s -X POST "$BASE_URL$2" \
        -H "Content-Type: application/json" \
        -d "$3")
    
    echo -e "Response:\n$RESPONSE\n"
    
    # Return the response for potential reuse
    echo "$RESPONSE"
}

# Create output directory
mkdir -p test_output

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
echo "$QUOTE_DATA" | python -m json.tool 2>/dev/null || echo "$QUOTE_DATA"

QUOTE_RESPONSE=$(test_endpoint "Get Fusion+ Quote" "/fusion/quote" "$QUOTE_DATA")

# Save the quote response to a file
echo "$QUOTE_RESPONSE" > test_output/fusion_quote.json

# Check if the quote response looks valid (contains quoteId)
if [[ "$QUOTE_RESPONSE" == *"quoteId"* ]]; then
    # 2. Test the build order endpoint (using the quote from previous step)
    BUILD_DATA='{
        "quote": '"$QUOTE_RESPONSE"',
        "wallet_address": "'$WALLET'",
        "preset_name": "fast"
    }'

    ORDER_RESPONSE=$(test_endpoint "Build Fusion+ Order" "/fusion/build_order" "$BUILD_DATA")

    # Save the order data to a file
    echo "$ORDER_RESPONSE" > test_output/fusion_order.json

    # 3. Test the submit order endpoint
    # In a real scenario, this order would need to be signed by the user's wallet
    # This is just a simplified example that will likely fail without a valid signature
    SUBMIT_DATA='{
        "src_chain_id": '$SRC_CHAIN_ID',
        "signed_order_payload": {
            "chainId": '$SRC_CHAIN_ID',
            "order": '"$(echo "$ORDER_RESPONSE" | sed 's/"/\\"/g')"',
            "quoteId": "example-quote-id"
        }
    }'

    test_endpoint "Submit Fusion+ Order" "/fusion/submit_order" "$SUBMIT_DATA"
else
    echo -e "${RED}Quote response doesn't contain quoteId. Skipping order build and submit tests.${NC}"
fi

# Clean up
echo -e "\n${GREEN}Stopping server...${NC}"
kill $SERVER_PID 2>/dev/null || echo "Server process not found. It may have already stopped."
echo "Server stopped. Test complete."
echo "Response data saved to /tmp/fusion_quote.json and /tmp/fusion_order.json"
