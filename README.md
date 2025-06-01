<p align="center">
  <img src="https://github.com/user-attachments/assets/quantumleap-banner.png" alt="QuantumLeap Engine Banner" width="800"/>
</p>

<h1 align="center">QuantumLeap Engine</h1>

<p align="center">
  <strong>Unlock Cross-Chain Alpha. Intelligently.</strong>
  <br />
  <em>Your Automated Edge: From Multi-Chain Data to Optimized DeFi Portfolios.</em>
  <br />
  <br />
  Built in <strong>36 hours</strong> for <strong>ETHGlobal Prague</strong>! 🚀
</p>

<p align="center">
  <a href="#-live-demo">Live Demo</a> •
  <a href="#-how-it-works">How It Works</a> •
  <a href="#-key-features">Features</a> •
  <a href="#-technology-stack">Tech Stack</a> •
  <a href="#-getting-started">Getting Started</a> •
  <a href="#-api-documentation">API Docs</a>
</p>

---

## ✨ Project Overview

In today's dynamic DeFi landscape, finding a true investment edge across multiple blockchains is a complex puzzle. **QuantumLeap Engine** cuts through the noise, offering a sophisticated yet intuitive platform for discovering and constructing high-potential, risk-adjusted portfolios.

We automate the journey from raw, multi-chain data to actionable investment strategies, empowering you to navigate the DeFi markets with greater confidence and precision.

---

## 💡 How It Works: The QuantumLeap Pipeline

QuantumLeap employs a systematic, multi-stage process to generate its insights:

<p align="center">
  <img src="https://github.com/user-attachments/assets/architecture-diagram.png" alt="QuantumLeap Architecture Diagram" width="900"/>
  <br/>
  <em>Figure 1: QuantumLeap's Core Data and Logic Flow.</em>
</p>

### 1. 🌍 **Multi-Chain Data Aggregation**
   - Continuously ingests token information and detailed OHLCV (Open, High, Low, Close, Volume) price history from 1inch APIs
   - Spans **8 leading EVM-compatible chains**, ensuring comprehensive market coverage
   - Data is meticulously cleaned, standardized, and stored in our high-performance MongoDB database

### 2. 🧠 **Intelligent Forecasting Engine**
   - **Quantitative Models:** Proprietary algorithms leveraging advanced statistical methods:
     - Fourier analysis for cyclical pattern detection
     - GARCH models for volatility forecasting
     - Structural break detection for regime changes
   - **Technical Analysis (TA):** Complementary insights from proven indicators:
     - RSI, MACD, Bollinger Bands
     - Moving averages and momentum indicators
   - Outputs actionable **buy/sell/hold signals** with confidence scores

### 3. 📈 **Asset Ranking & Strategic Selection**
   - Assets intelligently scored based on collective signal strength
   - Multi-factor ranking considering both quantitative and technical signals
   - Only the most promising candidates advance to portfolio construction

### 4. ⚖️ **Optimized Portfolio Construction (MVO)**
   - Implements Nobel Prize-winning Modern Portfolio Theory
   - Three optimization objectives available:
     - **Maximize Sharpe Ratio:** Best risk-adjusted returns
     - **Minimize Volatility:** For specified target returns
     - **Maximize Return:** Within acceptable risk parameters
   - Ensures portfolios align with sound risk management principles

### 5. 🚀 **Actionable Insights & Future Execution**
   - Clear, data-backed portfolio suggestions with performance metrics
   - *Vision:* Direct integration with 1inch Fusion+ for one-click portfolio execution
   - Backend services prepared for seamless cross-chain trading

---

## 🌟 Key Features

- **🌐 Cross-Chain Supremacy:** Analyze and optimize across 8 major EVM networks for unparalleled diversification
- **🤖 Hybrid Intelligence:** Combines cutting-edge quantitative finance with time-tested technical analysis
- **🛡️ Smart Risk Management:** Modern Portfolio Theory (MVO) for intelligent risk-reward balance
- **⚡ Performance-Optimized:** MongoDB caching for OHLCV data and portfolio results ensures lightning-fast responses
- **🔧 Modular Architecture:** Clean, service-oriented design for future enhancements
- **📡 API-First Design:** Robust FastAPI backend with comprehensive documentation
- **💱 DeFi Native Integration:** 1inch Fusion+ integration for direct on-chain execution (in development)

---

## 🔗 Supported Chains

<p align="center">
  <img src="https://img.shields.io/badge/Ethereum-3C3C3D?style=for-the-badge&logo=ethereum&logoColor=white" />
  <img src="https://img.shields.io/badge/BNB_Chain-F0B90B?style=for-the-badge&logo=binance&logoColor=white" />
  <img src="https://img.shields.io/badge/Arbitrum-28A0F0?style=for-the-badge&logo=arbitrum&logoColor=white" />
  <img src="https://img.shields.io/badge/Polygon-8247E5?style=for-the-badge&logo=polygon&logoColor=white" />
  <img src="https://img.shields.io/badge/Optimism-FF0420?style=for-the-badge&logo=optimism&logoColor=white" />
  <img src="https://img.shields.io/badge/Avalanche-E84142?style=for-the-badge&logo=avalanche&logoColor=white" />
  <img src="https://img.shields.io/badge/Fantom-1969FF?style=for-the-badge&logo=fantom&logoColor=white" />
  <img src="https://img.shields.io/badge/Base-0052FF?style=for-the-badge&logo=coinbase&logoColor=white" />
</p>

---

## 🛠️ Technology Stack

### Backend
- **Language:** Python 3.10+
- **Framework:** FastAPI with Pydantic validation
- **Database:** MongoDB with Motor for async operations
- **Data Science:** Pandas, NumPy, Scikit-learn, Statsmodels
- **Portfolio Optimization:** Custom MVO implementation
- **External APIs:** 1inch (data & Fusion+), Blockscout

### Frontend
- **Framework:** Next.js 15 with React 19
- **Language:** TypeScript
- **Styling:** Tailwind CSS with Radix UI components
- **Charts:** Recharts for data visualization
- **Web3:** RainbowKit, Wagmi, Viem for wallet connections
- **State Management:** Zustand

### DevOps & Tools
- **Package Management:** npm/yarn (frontend), pip/conda (backend)
- **Server:** Uvicorn for ASGI
- **Version Control:** Git/GitHub

---

## 📂 Project Structure

ETH_GLOBAL_PRAGUE_HACK/
├── backend/
│ ├── forecast/ # Core forecasting algorithms
│ │ ├── quant_forecast.py # Quantitative analysis models
│ │ ├── ta_forecast.py # Technical analysis indicators
│ │ ├── mvo_portfolio.py # Mean-Variance Optimization
│ │ └── main_pipeline.py # Orchestration logic
│ ├── services/ # External integrations
│ │ ├── one_inch_data_service.py # 1inch data fetching
│ │ ├── one_inch_fusion_service.py # 1inch Fusion+ trading
│ │ ├── mongo_service.py # Database operations
│ │ └── blockscout_service.py # Blockchain explorer
│ ├── main.py # FastAPI application
│ ├── models.py # Pydantic data models
│ └── configs.py # Configuration management
├── frontend/
│ ├── src/
│ │ ├── components/ # React UI components
│ │ ├── hooks/ # Custom React hooks
│ │ └── pages/ # Next.js page routes
│ └── lib/ # Utility functions
└── README.md


---

## 🚀 Getting Started

### Prerequisites
- **Python 3.10+** with pip
- **Node.js 18+** with npm/yarn
- **MongoDB** instance (local or cloud)
- **1inch API Key** ([Get it here](https://portal.1inch.dev/))

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
echo "MONGO_URI=mongodb://localhost:27017" >> .env
echo "DATABASE_NAME=alphastream" >> .env
echo "ONEINCH_API_KEY=your_api_key_here" >> .env

# Start the backend server
./start.sh  # Or: uvicorn main:app --reload --port 8000
```

📚 **API Documentation:** http://localhost:8000/docs

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install  # or yarn install

# Create environment configuration
echo "NEXT_PUBLIC_API_URL=http://localhost:8000" >> .env.local

# Start the development server
npm run dev  # or yarn dev
```

🎨 **Application:** http://localhost:3000

---

## 📊 Live Demo

🔗 **Live Application:** [alphastream.demo.com](#) *(Coming Soon)*

### Demo Credentials
- **Test Wallet:** Connect any wallet (read-only demo)
- **Sample Portfolios:** Pre-computed results available

---

## 📡 API Documentation

### Key Endpoints

#### Portfolio Optimization
```http
POST /api/cross-chain-portfolio-optimization
```
Generates optimized portfolio across multiple chains.

**Request Body:**
```json
{
  "chain_ids": [10, 137, 42161],
  "timeframe": "day",
  "max_tokens_per_chain": 20,
  "mvo_objective": "max_sharpe",
  "risk_free_rate": 0.02
}
```

#### Forecast Signals
```http
GET /api/signals/{chain_id}
```
Retrieves forecasting signals for assets on a specific chain.

#### OHLCV Data
```http
GET /api/ohlcv/{chain_id}/{token_address}
```
Fetches historical price data for analysis.

---

## 🔮 Future Vision

QuantumLeap Engine is just the beginning. Our roadmap includes:

- **⚙️ Integration of Pectra's EIP-7702:** Improving UX, user only signs once for full portfolio rebalancing
- **✅ One-Click Execution:** Complete 1inch Fusion+ integration for seamless portfolio rebalancing
- **👤 User Accounts:** Personalized strategies and performance tracking
- **📊 Enhanced Data Sources:** On-chain sentiment analysis and governance activity
- **🤖 Advanced ML Models:** Deep learning for improved price predictions
- **📱 Mobile App:** Trade and monitor portfolios on the go
- **🔄 Auto-Rebalancing:** Set it and forget it portfolio management

---

## 👥 The Team @ ETHGlobal Prague

Built with ❤️ and ☕ by passionate DeFi enthusiasts during an intense 36-hour hackathon sprint.

- **Pedro Rosalba** - Smart Contract Developer 
- **Ricardo Barroca** - Quantitative Strategy & Financial Modeling
- **Diogo Melo** - Frontend Development & UI/UX Design

---

## 🏆 Hackathon Achievements

- **⚡ Rapid Prototyping:** From concept to functional multi-chain application in 36 hours
- **🔗 Complex Integration:** Successfully orchestrated 4 external APIs with advanced financial modeling
- **📈 Data Pipeline:** Built end-to-end pipeline from raw market data to optimized portfolios
- **🌍 Cross-Chain Innovation:** Tackled multi-chain portfolio optimization challenge
- **🎯 User-Centric Design:** Created intuitive interface for complex financial operations

---

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  <strong>Built at ETHGlobal Prague 2024</strong>
  <br/>
  <em>Empowering the next generation of DeFi portfolio management</em>
  <br/>
  <br/>
  <a href="https://github.com/elbarroca/eth_global_prague">GitHub</a>
</p>
