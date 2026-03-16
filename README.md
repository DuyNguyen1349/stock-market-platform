# 📈 Stock Market Platform & Big Data Engine

This is a comprehensive, enterprise-grade Stock Market Tracking and AI Analysis platform. It functions as a mini **Bloomberg Terminal** or **TradingView**, providing technical charts, real-time news sentiment analysis, portfolio optimization, and AI-driven price prediction.

The project incorporates **Big Data** processing using **PySpark** and real-time streaming via **Apache Kafka** deployed on AWS EC2.

![Stock Market Dashboard](frontend/public/favicon.ico) *(Replace with actual screenshot link if available)*

---

## 🏗 System Architecture

The project consists of three independent microservices that need to be run concurrently:

1. **Frontend (`/frontend`)**: A modern React-based UI built with Next.js, serving as the main dashboard and interactive interface.
2. **Backend API (`/backend`)**: A Node.js/Express server acting as a bridge, utilizing Google Gemini AI for deep natural language financial summaries.
3. **Data Engine (`/data_engine`)**: A Python/Flask service acting as the heavy-lifter. It scrapes financial news, cleans data via **PySpark** pipelines, streams NLP analytics through **Kafka**, and forecasts future stock prices using Facebook **Prophet**.

---

## 🚀 Prerequisites

To run this project on your local machine, you must have the following installed:
* **Node.js** (v18 or higher) & **npm**
* **Python** (3.9 to 3.11 recommended)
* **Git**

*(Optional for Big Data):* An active Kafka Broker (e.g., on AWS EC2) and Java 17 for PySpark/Kafka interactions. The system will automatically fallback to local PySpark if Kafka is unreachable.

---

## 🛠️ Installation & Setup

Follow these steps to get a local copy up and running.

### 1. Clone the repository
```bash
git clone https://github.com/DuyNguyen1349/stock-market-platform.git
cd stock-market-platform
```

### 2. Setup the Data Engine (Python)
This engine requires heavy libraries like PySpark, Pandas, and Prophet. It is highly recommended to use a virtual environment.

```bash
cd data_engine

# Install Python dependencies
pip install -r requirements.txt

# Start the Flask Data Engine (Runs on http://localhost:5000)
python run.py
```

### 3. Setup the Backend API (Node.js)
Open a **new terminal window**.

```bash
cd stock-market-platform/backend

# Install Node modules
npm install

# Start the Node.js Express Server (Runs on http://localhost:5001)
npm run dev
```
*(Note: Ensure you have your `GEMINI_API_KEY` configured in a `.env` file for AI features to work).*

### 4. Setup the Frontend (Next.js)
Open a **third terminal window**.

```bash
cd stock-market-platform/frontend

# Install Node modules
npm install

# Start the Next.js React App (Runs on http://localhost:3000)
npm run dev
```

---

## 🌐 Usage

Once all three servers are running:
1. Open your web browser.
2. Navigate to **`http://localhost:3000`**
3. Use the search bar to enter a stock ticker (e.g., `AAPL`, `TSLA`, `NVDA`).
4. Explore the interactive UI tools:
   - **Market Sentiment**: Analyzed in real-time leveraging big data pipelines.
   - **AI Predictor**: View Prophet model 90-day trajectory.
   - **Portfolio Optimizer**: Allocate capital efficiently via Markowitz models.

---

## 👨‍💻 Tech Stack

* **Frontend:** Next.js, React, Tailwind CSS, TypeScript
* **Backend:** Node.js, Express, Prisma
* **Data Engine/AI:** Python, Flask, PySpark, Kafka-Python, NLTK/VADER, Prophet, yfinance
* **Infrastructure:** AWS EC2 (Apache Kafka Message Broker)

## 👤 Author
Developed by **Duy Nguyen**
