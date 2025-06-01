# QuantumLeap Frontend

A Next.js application for DeFi portfolio optimization across multiple chains.

## 🚀 Quick Start

### Local Development

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment variables:**
   Create a `.env.local` file in the frontend directory:
   ```bash
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

4. **Open your browser:**
   Navigate to [http://localhost:3000](http://localhost:3000)

## 🌐 Vercel Deployment

### Prerequisites
- Vercel account
- Backend API deployed and accessible

### Deployment Steps

1. **Connect your repository to Vercel:**
   - Go to [vercel.com](https://vercel.com)
   - Import your GitHub repository
   - Select the `frontend` folder as the root directory

2. **Configure environment variables in Vercel:**
   In your Vercel project settings, add the following environment variables:
   
   ```
   NEXT_PUBLIC_API_URL=https://your-backend-api-url.com
   ```

3. **Build settings:**
   Vercel should automatically detect Next.js. If needed, configure:
   - **Framework Preset:** Next.js
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`
   - **Install Command:** `npm install`

4. **Deploy:**
   - Push your changes to the main branch
   - Vercel will automatically deploy

### Environment Variables

| Variable | Description | Required | Example |
|----------|-------------|----------|---------|
| `NEXT_PUBLIC_API_URL` | Backend API base URL | Yes | `https://api.yourapp.com` |

### Troubleshooting

**Build Errors:**
- Ensure all TypeScript errors are resolved
- Check that all imports are correct
- Verify environment variables are set

**Runtime Errors:**
- Check browser console for errors
- Verify API endpoints are accessible
- Ensure wallet connection is working

## 🛠 Tech Stack

- **Framework:** Next.js 15
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** Radix UI
- **Web3:** Wagmi + RainbowKit
- **Charts:** Recharts
- **Forms:** React Hook Form + Zod

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/     # Reusable UI components
│   ├── hooks/          # Custom React hooks
│   ├── pages/          # Next.js pages
│   ├── stores/         # State management
│   ├── types/          # TypeScript type definitions
│   └── utils/          # Utility functions
├── public/             # Static assets
└── package.json        # Dependencies and scripts
```

## 🔧 Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## 🌟 Features

- **Multi-chain Portfolio Optimization:** Optimize portfolios across Ethereum, Polygon, Arbitrum, and more
- **Real-time Data:** Live market data and price feeds
- **Wallet Integration:** Connect with MetaMask, WalletConnect, and other popular wallets
- **Interactive Charts:** Visualize portfolio performance and efficient frontiers
- **Cross-chain Bridging:** Execute portfolio rebalancing across chains
- **Responsive Design:** Works on desktop and mobile devices

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
