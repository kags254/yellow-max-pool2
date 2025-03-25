# YELLOW MAX POOL Trading Bot

A sophisticated trading bot web application for binary options that combines statistical analysis and real-time market data from Binary/Deriv API.

![Trading Bot Dashboard](static/img/dashboard-preview.png)

## Features

- **Real-time Market Analysis**: Monitors and analyses market data in real-time
- **Multiple Contract Types**: Supports various binary options contracts (matches, differs, over/under, even/odd)
- **Advanced Backtesting**: Test your strategies against historical data
- **Martingale Strategy Support**: Configurable martingale progression for risk management
- **Digit Analysis**: Statistical analysis of last digit patterns
- **Interactive Dashboard**: Real-time charts and visual indicators
- **Trade Execution**: Automated and manual trade execution
- **User Authentication**: Secure API token-based authentication

## Project Structure

```
yellow_max_pool/
├── app.py                # Flask app configuration
├── main.py               # Entry point
├── models.py             # Database models
├── routes.py             # API routes
├── trading_bot.py        # Bot logic
├── static/               # Frontend assets
│   ├── css/
│   ├── js/
│   └── images/
├── templates/            # HTML templates
│   └── index.html
└── utils/                # Utility modules
    ├── backtester.py
    ├── digit_analysis.py
    └── ml_models.py
```

## Getting Started

### Prerequisites

- Python 3.9+
- PostgreSQL database
- Binary.com/Deriv.com API token

### Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/yellow-max-pool.git
   cd yellow-max-pool
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Configure environment variables:
   ```
   export DATABASE_URL="postgresql://username:password@localhost/database"
   export SESSION_SECRET="your-secret-key"
   ```

4. Initialize the database:
   ```
   python
   >>> from app import app, db
   >>> with app.app_context():
   >>>     db.create_all()
   ```

5. Run the application:
   ```
   python main.py
   ```

6. Open your browser and navigate to `http://localhost:5000`

## Usage

1. Log in with your Binary.com/Deriv.com API token
2. Select a market to trade (R_10, R_25, R_50, R_100)
3. Configure your trading parameters:
   - Contract type (matches, differs, over/under, even/odd)
   - Stake amount
   - Target profit and stop loss
   - Martingale settings
4. Start automated trading or execute trades manually
5. Monitor results in real-time on the dashboard
6. Use the backtesting feature to test strategies before live trading

## Backtesting Module

The backtesting module allows you to test trading strategies against historical data:

1. Navigate to the Backtesting section in the dashboard
2. Configure strategy parameters:
   - Contract type
   - Stake amount
   - Martingale settings
   - Confidence threshold
3. Run the backtest to see detailed results including:
   - Win rate
   - Profit/loss
   - Maximum drawdown
   - Profit factor
   - Equity curve

## Deployment

See the [Deployment Guide](deployment_guide.md) for instructions on deploying to various platforms.

## Security Notes

- Never share your API token
- The application stores your token securely for session purposes only
- Always set reasonable stop loss limits
- Start with small stake amounts until you're confident in your strategy

## Disclaimer

Trading binary options involves substantial risk of loss and is not suitable for all investors. This software is for educational and entertainment purposes only. Past performance is not indicative of future results.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Binary.com/Deriv.com for their WebSocket API
- The Flask and SQLAlchemy communities
- Chart.js and Plotly.js for visualization components