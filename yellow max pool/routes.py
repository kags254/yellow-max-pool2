from app import app, db
from flask import render_template, request, jsonify, session as flask_session, redirect, url_for
from models import User, Trade, TradingSession, DigitHistory
from trading_bot import AdvancedTradingBot
from utils.backtester import BackTester
import logging
import asyncio
import json
import os
import math

# Custom JSON encoder to handle special values like Infinity
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, float) and math.isinf(obj):
            return "Infinity"  # Convert to string representation
        return super().default(obj)

# Function to handle serialization of special values
def custom_json_handler(obj):
    """Custom handler for JSON serialization"""
    if isinstance(obj, float) and math.isinf(obj):
        return "Infinity"
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

# Override Flask's jsonify to handle special values
def _jsonify(*args, **kwargs):
    """Custom jsonify function that handles special values"""
    return app.response_class(
        json.dumps(dict(*args, **kwargs), default=custom_json_handler),
        mimetype="application/json"
    )

# Global bot instance
trading_bot = None

@app.route('/')
def index():
    """Render the main dashboard page"""
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    """Handle user login with API token"""
    data = request.json
    api_token = data.get('api_token')
    
    if not api_token:
        return jsonify({'success': False, 'message': 'API token is required'})
    
    try:
        # Initialize the trading bot with the API token
        global trading_bot
        trading_bot = AdvancedTradingBot(api_token)
        
        # Create or update user in the database
        user = User.query.filter_by(api_token=api_token).first()
        if not user:
            # Create new user
            user = User(username=f"user_{len(User.query.all()) + 1}", api_token=api_token)
            db.session.add(user)
            db.session.commit()  # Commit immediately to get the user ID
            
        # Ensure user exists before creating session
        if user and user.id:
            flask_session['user_id'] = user.id
            flask_session['api_token'] = api_token
            
            # Create trading session
            trading_session = TradingSession(
                user_id=user.id,
                start_balance=1000.0,
                current_balance=1000.0
            )
            db.session.add(trading_session)
            db.session.commit()
            
            flask_session['trading_session_id'] = trading_session.id
        
        # Store user info in Flask session
        flask_session['user_id'] = user.id
        flask_session['api_token'] = api_token
        
        # Create a new trading session
        trading_session = TradingSession(
            user_id=user.id,
            start_balance=1000.0,  # This will be updated with real balance later
            current_balance=1000.0
        )
        db.session.add(trading_session)
        db.session.commit()
        
        # Store trading session ID in Flask session
        flask_session['trading_session_id'] = trading_session.id
        
        return jsonify({'success': True, 'message': 'Login successful'})
    except Exception as e:
        logging.error(f"Login error: {str(e)}")
        return jsonify({'success': False, 'message': f'Login failed: {str(e)}'})

@app.route('/logout', methods=['POST'])
def logout():
    """Handle user logout"""
    try:
        # Update trading session end time
        if 'trading_session_id' in flask_session:
            trading_session = TradingSession.query.get(flask_session['trading_session_id'])
            if trading_session:
                from datetime import datetime
                trading_session.end_time = datetime.utcnow()
                db.session.commit()
        
        # Clear session data
        flask_session.clear()
        global trading_bot
        trading_bot = None
        
        return jsonify({'success': True, 'message': 'Logout successful'})
    except Exception as e:
        logging.error(f"Logout error: {str(e)}")
        return jsonify({'success': False, 'message': f'Logout failed: {str(e)}'})

@app.route('/market_data', methods=['POST'])
def market_data():
    """Get market data for the selected market"""
    if not trading_bot:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        market = request.json.get('market', 'R_100')
        # Use synchronous methods instead of async
        # Return mock data for now
        return jsonify({
            'success': True,
            'data': {
                'last_digits': [1, 2, 3, 4, 5, 6, 7, 8, 9, 0],
                'indicators': {
                    'best_match': 5,
                    'best_differ': 8,
                    'confidence': 0.75,
                    'next_prediction': 5
                }
            },
            'digit_frequency': {"0": 10, "1": 12, "2": 9, "3": 11, "4": 8, "5": 14, "6": 10, "7": 9, "8": 8, "9": 9}
        })
    except Exception as e:
        logging.error(f"Market data error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get market data: {str(e)}'})

@app.route('/execute_trade', methods=['POST'])
def execute_trade():
    """Execute a trade with the specified parameters"""
    if not trading_bot:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        data = request.json
        contract_type = data.get('contract_type')
        stake_amount = float(data.get('stake_amount', 10))
        target_profit = float(data.get('target_profit', 5))
        stop_loss = float(data.get('stop_loss', 2))
        martingale_start = int(data.get('martingale_start', 1))
        max_martingale = int(data.get('max_martingale', 5))
        market = data.get('market', 'R_100')
        
        # Configure the trading bot with these parameters
        trading_bot.configure_trade(
            contract_type=contract_type,
            stake_amount=stake_amount,
            target_profit=target_profit,
            stop_loss=stop_loss,
            martingale_start=martingale_start,
            max_martingale=max_martingale,
            market=market
        )
        
        # Record the trade in the database
        if 'user_id' in flask_session:
            trade = Trade(
                user_id=flask_session['user_id'],
                market=market,
                contract_type=contract_type,
                stake_amount=stake_amount,
                outcome='pending'
            )
            db.session.add(trade)
            db.session.commit()
        
        # Return mock result
        result = {
            "contract_id": "mock_contract_123",
            "status": "pending",
            "contract_type": contract_type,
            "stake_amount": stake_amount,
            "market": market
        }
        
        return jsonify({
            'success': True,
            'message': 'Trade executed successfully',
            'result': result
        })
    except Exception as e:
        logging.error(f"Trade execution error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to execute trade: {str(e)}'})

@app.route('/account_info', methods=['GET'])
def account_info():
    """Get account information"""
    if not trading_bot or 'api_token' not in flask_session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        # Provide mock account info for demonstration
        info = {
            'balance': 1000.00,
            'currency': 'USD',
            'wins': 5,
            'losses': 3,
            'profit_rate': 62.5
        }
        
        # Update trading session in the database
        if 'trading_session_id' in flask_session:
            trading_session = TradingSession.query.get(flask_session['trading_session_id'])
            if trading_session:
                trading_session.current_balance = info['balance']
                trading_session.profit_loss = info['balance'] - trading_session.start_balance
                trading_session.wins = info['wins']
                trading_session.losses = info['losses']
                db.session.commit()
        
        return jsonify({
            'success': True,
            'data': info
        })
    except Exception as e:
        logging.error(f"Account info error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get account info: {str(e)}'})

@app.route('/pause_trading', methods=['POST'])
def pause_trading():
    """Pause the trading bot"""
    if not trading_bot:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        trading_bot.pause()
        return jsonify({'success': True, 'message': 'Trading paused'})
    except Exception as e:
        logging.error(f"Pause error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to pause trading: {str(e)}'})

@app.route('/resume_trading', methods=['POST'])
def resume_trading():
    """Resume the trading bot"""
    if not trading_bot:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        trading_bot.resume()
        return jsonify({'success': True, 'message': 'Trading resumed'})
    except Exception as e:
        logging.error(f"Resume error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to resume trading: {str(e)}'})

@app.route('/break_after_win', methods=['POST'])
def break_after_win():
    """Set the bot to break after a win"""
    if not trading_bot:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        trading_bot.break_after_win = True
        return jsonify({'success': True, 'message': 'Bot will break after win'})
    except Exception as e:
        logging.error(f"Break after win error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to set break after win: {str(e)}'})

@app.route('/backtest', methods=['POST'])
def run_backtest():
    """Run a backtest with the specified configuration"""
    try:
        data = request.json
        
        # Create a backtester instance
        backtester = BackTester()
        
        # Generate sample historical data for testing
        import random
        sample_data = []
        for i in range(1000):
            sample_data.append({
                'price': 100 + random.uniform(-5, 5),
                'timestamp': i,
                'digit': random.randint(0, 9)
            })
        
        backtester.load_data(sample_data)
        
        # Run the backtest
        config = {
            'contract_type': data.get('contract_type', 'matches'),
            'stake_amount': float(data.get('stake_amount', 10)),
            'martingale_enabled': bool(data.get('martingale_enabled', False)),
            'martingale_start': int(data.get('martingale_start', 1)),
            'max_martingale': int(data.get('max_martingale', 5)),
            'min_confidence': float(data.get('min_confidence', 0.6)),
            'window_size': int(data.get('window_size', 20))
        }
        
        results = backtester.run_backtest(config)
        
        # Save backtest results to database if logged in
        if 'user_id' in flask_session:
            # TODO: Add backtest results to database if needed
            pass
        
        # Transform results to match frontend expectations
        frontend_results = {
            'total_trades': results['summary']['total_trades'],
            'win_rate': results['summary']['win_rate'] / 100 if isinstance(results['summary']['win_rate'], (int, float)) else 0,
            'profit_loss': results['summary']['profit_loss'],
            'max_consecutive_wins': results['summary']['max_consecutive_wins'],
            'max_consecutive_losses': results['summary']['max_consecutive_losses'],
            'max_drawdown': results['summary']['max_drawdown'],
            'profit_factor': results['summary']['profit_factor'],
            'avg_win': results['summary']['average_win'],
            'avg_loss': results['summary']['average_loss'],
            'trades': []
        }
        
        # Handle special case for profit_factor (Infinity)
        if isinstance(frontend_results['profit_factor'], float) and math.isinf(frontend_results['profit_factor']):
            frontend_results['profit_factor'] = "Infinity"
        
        # Transform trade data
        for trade in results['trades']:
            frontend_results['trades'].append({
                'prediction': trade['prediction'],
                'actual': trade['actual'],
                'result': 'win' if trade['is_win'] else 'loss',
                'stake': trade['stake'],
                'profit_loss': trade['profit'],
                'balance': trade['balance'],
                'confidence': trade['confidence']
            })
        
        # Use manual JSON serialization with our custom handler to handle special values
        response_data = {
            'success': True,
            'results': frontend_results
        }
        
        return app.response_class(
            json.dumps(response_data, default=custom_json_handler),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f"Backtest error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to run backtest: {str(e)}'})

@app.route('/saved_backtests', methods=['GET'])
def get_saved_backtests():
    """Get a list of saved backtests for the current user"""
    if 'user_id' not in flask_session:
        return jsonify({'success': False, 'message': 'Not logged in'})
    
    try:
        # TODO: Fetch saved backtests from database when we implement that feature
        saved_backtests = []
        
        return jsonify({
            'success': True,
            'backtests': saved_backtests
        })
        
    except Exception as e:
        logging.error(f"Get saved backtests error: {str(e)}")
        return jsonify({'success': False, 'message': f'Failed to get saved backtests: {str(e)}'})
