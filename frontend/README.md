# DeFi Portfolio Optimizer Frontend

This is the frontend for the DeFi Portfolio Optimizer built with Next.js.

## Environment Setup

To enable 1inch cross-chain functionality, create a `.env.local` file in the frontend directory with the following variables:

```bash
# Next.js Environment Variables
NEXT_PUBLIC_API_URL=http://localhost:8000

# 1inch SDK Configuration (required for cross-chain transactions)
RPC_URL=https://mainnet.infura.io/v3/your-infura-key
BACKEND_URL=https://api.1inch.dev
ONE_INCH_API_KEY=your-1inch-api-key
PRIVATE_KEY=your-private-key-here
```

**Important Security Notes:**
- Never commit `.env.local` to version control
- Use test/development private keys only
- In production, use proper secret management

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Set up environment variables (see above)

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Features

- Portfolio optimization across multiple chains
- Real-time asset analysis
- Cross-chain transaction execution (with 1inch SDK)
- Portfolio liquidation and bridging
- Interactive charts and analytics

## Development

The app will work without the 1inch SDK configuration, but cross-chain transaction features will be disabled.

To enable full functionality:
1. Get a 1inch API key from [1inch Developer Portal](https://portal.1inch.dev/)
2. Set up an Infura or similar RPC provider
3. Configure the environment variables as shown above

## Learn More

To learn more about this stack, take a look at the following resources:

- [RainbowKit Documentation](https://rainbowkit.com) - Learn how to customize your wallet connection flow.
- [wagmi Documentation](https://wagmi.sh) - Learn how to interact with Ethereum.
- [Next.js Documentation](https://nextjs.org/docs) - Learn how to build a Next.js application.

You can check out [the RainbowKit GitHub repository](https://github.com/rainbow-me/rainbowkit) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out the [Next.js deployment documentation](https://nextjs.org/docs/deployment) for more details.
