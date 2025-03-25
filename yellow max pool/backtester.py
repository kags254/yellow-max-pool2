import json
import logging
from datetime import datetime
from collections import Counter, defaultdict

from utils.digit_analysis import analyze_digits
from utils.ml_models import build_simple_prediction_model

logger = logging.getLogger('backtester')

class BackTester:
    """Class for backtesting trading strategies on historical data"""
    
    def __init__(self, historical_data=None):
        """
        Initialize the backtester
        
        Args:
            historical_data: Optional list of historical price data
        """
        self.historical_data = historical_data or []
        self.digit_data = []
        self.last_digits = []
        self.prediction_model = build_simple_prediction_model()
        self.results = {
            'trades': [],
            'summary': {},
            'equity_curve': []
        }
    
    def load_data(self, historical_data):
        """
        Load historical data into the backtester
        
        Args:
            historical_data: List of price data points or price dictionaries
        """
        self.historical_data = historical_data
        
        # Extract last digits from prices
        self.last_digits = []
        for p in self.historical_data:
            if isinstance(p, dict) and 'digit' in p:
                # If the data already contains digit information, use it
                self.last_digits.append(p['digit'])
            elif isinstance(p, dict) and 'price' in p:
                # If it's a dictionary with a price field
                price_value = p['price']
                self.last_digits.append(int(str(float(price_value))[-1]))
            else:
                # Assume it's a raw price value
                self.last_digits.append(int(str(float(p))[-1]))
        
        self.digit_data = self._prepare_digit_data()
        
        logger.info(f"Loaded {len(self.historical_data)} data points for backtesting")
    
    def _prepare_digit_data(self):
        """Convert raw price data to structured digit data for analysis"""
        digit_data = []
        for i, data_point in enumerate(self.historical_data):
            timestamp = datetime.now().timestamp() - (len(self.historical_data) - i)
            
            if isinstance(data_point, dict):
                if 'digit' in data_point and 'price' in data_point:
                    # If the data already has both digit and price
                    digit_data.append({
                        'digit': data_point['digit'],
                        'price': data_point['price'],
                        'timestamp': data_point.get('timestamp', timestamp)
                    })
                elif 'digit' in data_point:
                    # If it has digit but no price
                    digit_data.append({
                        'digit': data_point['digit'],
                        'price': 0.0,  # Default price
                        'timestamp': data_point.get('timestamp', timestamp)
                    })
                elif 'price' in data_point:
                    # If it has price but no digit
                    price_value = data_point['price']
                    digit = int(str(float(price_value))[-1])
                    digit_data.append({
                        'digit': digit,
                        'price': price_value,
                        'timestamp': data_point.get('timestamp', timestamp)
                    })
            else:
                # Raw price value
                digit = int(str(float(data_point))[-1])
                digit_data.append({
                    'digit': digit,
                    'price': float(data_point),
                    'timestamp': timestamp
                })
        
        return digit_data
    
    def run_backtest(self, config):
        """
        Run a backtest with the specified configuration
        
        Args:
            config: Dictionary containing test parameters
                - contract_type: Type of contract ('matches', 'differs', 'over_under', 'even_odd')
                - stake_amount: Amount to stake on each trade
                - martingale_enabled: Whether to use martingale strategy
                - martingale_start: Number of consecutive losses to start martingale
                - max_martingale: Maximum martingale level
                - min_confidence: Minimum confidence threshold to execute a trade
                - window_size: Size of the sliding window for prediction
                
        Returns:
            Dictionary with backtest results
        """
        if not self.historical_data or len(self.historical_data) < config.get('window_size', 20):
            return {'error': 'Not enough historical data for backtesting'}
        
        # Initialize results
        self.results = {
            'trades': [],
            'summary': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'profit_loss': 0,
                'max_consecutive_wins': 0,
                'max_consecutive_losses': 0,
                'max_drawdown': 0,
                'max_drawdown_percentage': 0,
                'profit_factor': 0,
                'sharpe_ratio': 0,
                'average_win': 0,
                'average_loss': 0,
                'largest_win': 0,
                'largest_loss': 0
            },
            'equity_curve': [{'x': 0, 'y': 0}]  # Start with zero
        }
        
        # Extract configuration parameters
        contract_type = config.get('contract_type', 'matches')
        stake_amount = config.get('stake_amount', 10)
        martingale_enabled = config.get('martingale_enabled', False)
        martingale_start = config.get('martingale_start', 1)
        max_martingale = config.get('max_martingale', 5)
        min_confidence = config.get('min_confidence', 0.6)
        window_size = config.get('window_size', 20)
        
        # Simulation state variables
        current_stake = stake_amount
        balance = 0
        consecutive_losses = 0
        consecutive_wins = 0
        max_consecutive_wins = 0
        max_consecutive_losses = 0
        current_drawdown = 0
        max_drawdown = 0
        max_drawdown_percentage = 0
        peak_balance = 0
        winning_trades = []
        losing_trades = []
        
        # Martingale level
        current_martingale_level = 0
        
        # Run simulation over historical data
        # We start at window_size to have enough data for initial prediction
        for i in range(window_size, len(self.last_digits) - 1):
            # Current window of data
            window = self.last_digits[i-window_size:i]
            
            # Target (next digit)
            next_digit = self.last_digits[i]
            
            # Make prediction using our statistical model
            predicted_digit = self.prediction_model(window)
            
            # Calculate digit statistics
            digit_frequency = Counter(window)
            total_ticks = len(window)
            
            # Calculate probabilities for different contract types
            probabilities = {}
            
            # Matches probability (specific digit)
            most_common_digit = digit_frequency.most_common(1)[0][0] if digit_frequency else 5
            matches_count = digit_frequency.get(most_common_digit, 0)
            probabilities['matches'] = matches_count / total_ticks
            
            # Differs probability (not a specific digit)
            least_common_digit = digit_frequency.most_common()[-1][0] if len(digit_frequency) > 0 else 0
            differs_count = total_ticks - digit_frequency.get(least_common_digit, 0)
            probabilities['differs'] = differs_count / total_ticks
            
            # Over/Under probability
            over_count = sum(digit_frequency.get(d, 0) for d in range(5, 10))
            under_count = sum(digit_frequency.get(d, 0) for d in range(0, 5))
            probabilities['over'] = over_count / total_ticks
            probabilities['under'] = under_count / total_ticks
            
            # Even/Odd probability
            even_count = sum(digit_frequency.get(d, 0) for d in [0, 2, 4, 6, 8])
            odd_count = sum(digit_frequency.get(d, 0) for d in [1, 3, 5, 7, 9])
            probabilities['even'] = even_count / total_ticks
            probabilities['odd'] = odd_count / total_ticks
            
            # Calculate confidence for the selected contract type
            confidence = 0
            trade_details = {}
            
            if contract_type == 'matches':
                confidence = probabilities['matches']
                target_digit = most_common_digit
                # Check if actual next digit matches our target
                is_win = next_digit == target_digit
                payout_if_win = 9  # Typical payout for digit match
                trade_details = {
                    'target_digit': target_digit,
                    'contract_type': 'DIGITMATCH'
                }
                
            elif contract_type == 'differs':
                confidence = probabilities['differs']
                avoid_digit = least_common_digit
                # Check if actual next digit is different from what we want to avoid
                is_win = next_digit != avoid_digit
                payout_if_win = 0.9  # Typical payout for digit differ
                trade_details = {
                    'avoid_digit': avoid_digit,
                    'contract_type': 'DIGITDIFF'
                }
                
            elif contract_type == 'over_under':
                if probabilities['over'] > probabilities['under']:
                    confidence = probabilities['over']
                    is_win = next_digit >= 5  # Check if over
                    trade_details = {
                        'barrier': 4,
                        'contract_type': 'DIGITOVER'
                    }
                else:
                    confidence = probabilities['under']
                    is_win = next_digit < 5  # Check if under
                    trade_details = {
                        'barrier': 5,
                        'contract_type': 'DIGITUNDER'
                    }
                payout_if_win = 1.0  # Typical payout for over/under
                
            elif contract_type == 'even_odd':
                if probabilities['even'] > probabilities['odd']:
                    confidence = probabilities['even']
                    is_win = next_digit % 2 == 0  # Check if even
                    trade_details = {
                        'contract_type': 'DIGITEVEN'
                    }
                else:
                    confidence = probabilities['odd']
                    is_win = next_digit % 2 == 1  # Check if odd
                    trade_details = {
                        'contract_type': 'DIGITODD'
                    }
                payout_if_win = 1.0  # Typical payout for even/odd
            
            # Calculate current stake based on martingale strategy
            if martingale_enabled and consecutive_losses >= martingale_start:
                current_martingale_level = min(consecutive_losses - martingale_start + 1, max_martingale)
                current_stake = stake_amount * (2 ** current_martingale_level)
            else:
                current_stake = stake_amount
            
            # Only execute the trade if confidence exceeds minimum threshold
            if confidence >= min_confidence:
                # Calculate profit/loss for this trade
                if is_win:
                    profit = current_stake * payout_if_win
                    consecutive_wins += 1
                    consecutive_losses = 0
                    winning_trades.append(profit)
                    
                    # Update max consecutive wins
                    max_consecutive_wins = max(max_consecutive_wins, consecutive_wins)
                    
                    # Reset martingale level
                    current_martingale_level = 0
                else:
                    profit = -current_stake
                    consecutive_losses += 1
                    consecutive_wins = 0
                    losing_trades.append(abs(profit))
                    
                    # Update max consecutive losses
                    max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
                
                # Update balance
                balance += profit
                
                # Update peak balance and drawdown
                if balance > peak_balance:
                    peak_balance = balance
                    current_drawdown = 0
                else:
                    current_drawdown = peak_balance - balance
                    if current_drawdown > max_drawdown:
                        max_drawdown = current_drawdown
                        if peak_balance > 0:
                            max_drawdown_percentage = (max_drawdown / peak_balance) * 100
                
                # Record the trade
                trade = {
                    'index': i,
                    'window': window[-10:],  # Just show last 10 digits for brevity
                    'prediction': predicted_digit,
                    'actual': next_digit,
                    'is_win': is_win,
                    'stake': current_stake,
                    'profit': profit,
                    'balance': balance,
                    'confidence': confidence,
                    'martingale_level': current_martingale_level,
                    **trade_details  # Include contract-specific details
                }
                
                self.results['trades'].append(trade)
                
                # Add point to equity curve
                self.results['equity_curve'].append({
                    'x': len(self.results['trades']),
                    'y': balance
                })
        
        # Calculate summary statistics
        total_trades = len(self.results['trades'])
        wins = sum(1 for trade in self.results['trades'] if trade['is_win'])
        losses = total_trades - wins
        
        total_profit = sum(trade['profit'] for trade in self.results['trades'] if trade['profit'] > 0)
        total_loss = sum(abs(trade['profit']) for trade in self.results['trades'] if trade['profit'] < 0)
        
        # Prevent division by zero and handle special cases
        win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
        
        # Handle profit factor with special cases
        if total_loss == 0:
            if total_profit > 0:
                profit_factor = float('inf')  # All wins, no losses
            else:
                profit_factor = 0  # No trades or all break-even
        else:
            profit_factor = total_profit / total_loss
        
        average_win = total_profit / wins if wins > 0 else 0
        average_loss = total_loss / losses if losses > 0 else 0
        
        # Calculate Sharpe ratio
        if total_trades > 0:
            returns = [trade['profit'] / trade['stake'] for trade in self.results['trades']]
            avg_return = sum(returns) / len(returns)
            std_dev = (sum((r - avg_return) ** 2 for r in returns) / len(returns)) ** 0.5
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
        
        # Update summary
        self.results['summary'] = {
            'total_trades': total_trades,
            'wins': wins,
            'losses': losses,
            'win_rate': win_rate,
            'profit_loss': balance,
            'max_consecutive_wins': max_consecutive_wins,
            'max_consecutive_losses': max_consecutive_losses,
            'max_drawdown': max_drawdown,
            'max_drawdown_percentage': max_drawdown_percentage,
            'profit_factor': profit_factor,
            'sharpe_ratio': sharpe_ratio,
            'average_win': average_win,
            'average_loss': average_loss,
            'largest_win': max(winning_trades) if winning_trades else 0,
            'largest_loss': max(losing_trades) if losing_trades else 0
        }
        
        return self.results
    
    def get_results(self):
        """Get the results of the last backtest"""
        return self.results