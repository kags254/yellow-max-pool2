import os
import json
import asyncio
import websockets
import logging
from datetime import datetime
import random
import numpy as np
from collections import Counter
import requests
from utils.digit_analysis import analyze_digits

class AdvancedTradingBot:
    def __init__(self, api_token):
        self.api_url = "wss://ws.binaryws.com/websockets/v3"
        self.api_token = api_token
        self.ws = None
        self.historical_data = []
        self.digit_frequency = Counter()
        self.last_digits = []
        self.connected = False
        self.account_info = {}
        self.paused = False
        self.break_after_win = False
        self.trade_config = {
            'contract_type': 'matches',
            'stake_amount': 10.0,
            'target_profit': 5.0,
            'stop_loss': 2.0,
            'martingale_start': 1,
            'max_martingale': 5,
            'market': 'R_100',
            'current_martingale_level': 0,
            'total_profit_loss': 0.0,
            'consecutive_losses': 0,
            'wins': 0,
            'losses': 0
        }
        self.logger = logging.getLogger('trading_bot')
    
    async def connect(self):
        """Connect to Binary.com WebSocket API with retry logic"""
        if self.connected and self.ws is not None:
            try:
                # Check if the connection is still alive with a ping
                pong = await asyncio.wait_for(self.ws.ping(), timeout=2.0)
                if pong:
                    return True
            except (asyncio.TimeoutError, websockets.exceptions.ConnectionClosed):
                self.logger.info("Connection lost, reconnecting...")
                self.connected = False

        # Connection retry logic with backoff
        max_retries = 3
        base_delay = 1
        
        for attempt in range(max_retries):
            try:
                if self.ws:
                    try:
                        await self.ws.close()
                    except:
                        pass
                
                self.ws = await websockets.connect(self.api_url, ping_interval=20, ping_timeout=10)
                self.connected = True
                
                # Authorize with API token
                auth_request = {
                    "authorize": self.api_token
                }
                await self.ws.send(json.dumps(auth_request))
                response = await self.ws.recv()
                response_data = json.loads(response)
                
                if 'error' in response_data:
                    error_msg = response_data['error']['message']
                    self.logger.error(f"Authorization error: {error_msg}")
                    
                    # Check if it's a token issue
                    if "token" in error_msg.lower():
                        self.logger.critical("Invalid API token. Please check your credentials.")
                        self.connected = False
                        return False
                        
                    # For other errors, retry
                    continue
                    
                self.account_info = response_data.get('authorize', {})
                self.logger.info(f"Connected to Binary.com API. Account: {self.account_info.get('loginid')}")
                return True
                
            except Exception as e:
                self.logger.warning(f"Connection attempt {attempt+1} failed: {str(e)}")
                self.connected = False
                
                # Exponential backoff
                if attempt < max_retries - 1:
                    backoff_time = base_delay * (2 ** attempt)
                    self.logger.info(f"Retrying in {backoff_time} seconds...")
                    await asyncio.sleep(backoff_time)
        
        self.logger.error(f"Failed to connect after {max_retries} attempts.")
        return False
    
    async def fetch_historical_data(self, market, count=500):
        """Fetch historical tick data for a market with caching"""
        if not self.connected:
            connected = await self.connect()
            if not connected:
                self.logger.error("Cannot fetch data: connection failed")
                return []
        
        # Check if we need to update our data
        current_time = datetime.now()
        if hasattr(self, 'last_data_fetch') and hasattr(self, 'cached_market_data'):
            # If we have cached data for this market that's less than 10 seconds old, use it
            time_diff = (current_time - self.last_data_fetch).total_seconds()
            if time_diff < 10 and self.cached_market == market:
                self.logger.debug(f"Using cached market data ({time_diff:.1f}s old)")
                return self.cached_market_data
        
        try:
            # Request tick history
            history_request = {
                "ticks_history": market,
                "count": count,
                "end": "latest",
                "style": "ticks",
                "req_id": f"history_{current_time.timestamp()}"  # Add request ID for tracking
            }
            
            await self.ws.send(json.dumps(history_request))
            response = await self.ws.recv()
            response_data = json.loads(response)
            
            if 'error' in response_data:
                self.logger.error(f"History fetch error: {response_data['error']['message']}")
                return []
                
            history = response_data.get('history', {})
            prices = history.get('prices', [])
            
            if not prices:
                self.logger.warning(f"No price data returned for {market}")
                return []
                
            # Extract last digits and update frequency counter
            self.last_digits = [int(str(float(p))[-1]) for p in prices[-100:]]
            self.digit_frequency = Counter(self.last_digits)
            
            # Update cache
            self.cached_market_data = prices
            self.cached_market = market
            self.last_data_fetch = current_time
            
            # Store historical data for analysis
            self.historical_data = prices
            
            return prices
            
        except Exception as e:
            self.logger.error(f"Fetch historical data error: {str(e)}")
            
            # If we have cached data, return it as fallback
            if hasattr(self, 'cached_market_data') and hasattr(self, 'cached_market') and self.cached_market == market:
                self.logger.info("Using cached data as fallback after error")
                return self.cached_market_data
                
            return []
    
    def configure_trade(self, contract_type, stake_amount, target_profit, stop_loss, 
                       martingale_start, max_martingale, market):
        """Configure trading parameters"""
        self.trade_config['contract_type'] = contract_type
        self.trade_config['stake_amount'] = stake_amount
        self.trade_config['target_profit'] = target_profit
        self.trade_config['stop_loss'] = stop_loss
        self.trade_config['martingale_start'] = martingale_start
        self.trade_config['max_martingale'] = max_martingale
        self.trade_config['market'] = market
        self.trade_config['current_martingale_level'] = 0
        self.logger.info(f"Trade configured: {self.trade_config}")
    
    async def get_account_info(self):
        """Get account information"""
        if not self.connected:
            await self.connect()
        
        try:
            # Request account status
            balance_request = {
                "balance": 1,
                "subscribe": 1
            }
            
            await self.ws.send(json.dumps(balance_request))
            response = await self.ws.recv()
            response_data = json.loads(response)
            
            if 'error' in response_data:
                self.logger.error(f"Account info error: {response_data['error']['message']}")
                return {
                    'balance': 0,
                    'currency': 'USD',
                    'loginid': 'Unknown',
                    'wins': self.trade_config['wins'],
                    'losses': self.trade_config['losses'],
                    'profit_loss': self.trade_config['total_profit_loss']
                }
                
            balance_data = response_data.get('balance', {})
            
            account_info = {
                'balance': balance_data.get('balance', 0),
                'currency': balance_data.get('currency', 'USD'),
                'loginid': self.account_info.get('loginid', 'Unknown'),
                'wins': self.trade_config['wins'],
                'losses': self.trade_config['losses'],
                'profit_loss': self.trade_config['total_profit_loss']
            }
            
            return account_info
            
        except Exception as e:
            self.logger.error(f"Get account info error: {str(e)}")
            return {
                'balance': 0,
                'currency': 'USD',
                'loginid': 'Unknown',
                'wins': 0,
                'losses': 0,
                'profit_loss': 0
            }
    
    async def analyze_market(self, market):
        """Analyze market data and return insights"""
        # Fetch historical data for the market
        historical_data = await self.fetch_historical_data(market)
        
        # Calculate probabilities
        probabilities = await self.calculate_probabilities()
        
        # Get predictions
        predictions = await self.predict_with_ml()
        
        # Get digit analysis
        digit_analysis = analyze_digits(self.last_digits)
        
        # Return comprehensive analysis
        return {
            'probabilities': probabilities,
            'predictions': predictions,
            'digit_analysis': digit_analysis,
            'last_digits': self.last_digits[-20:],  # Last 20 digits for visualization
            'market': market
        }
    
    async def calculate_probabilities(self):
        """Calculate probabilities for various contract types based on digit analysis"""
        # Ensure we have historical data
        if not self.historical_data:
            await self.fetch_historical_data(self.trade_config['market'])
        
        # Analyze the digits
        probabilities = {}
        
        # Matches probability (specific digit)
        most_common_digit = self.digit_frequency.most_common(1)[0][0] if self.digit_frequency else 5
        matches_count = self.digit_frequency.get(most_common_digit, 0)
        total_ticks = sum(self.digit_frequency.values()) or 1
        probabilities['matches'] = matches_count / total_ticks
        
        # Differs probability (not a specific digit)
        least_common_digit = self.digit_frequency.most_common()[-1][0] if len(self.digit_frequency) > 0 else 0
        differs_count = total_ticks - self.digit_frequency.get(least_common_digit, 0)
        probabilities['differs'] = differs_count / total_ticks
        
        # Over/Under probability
        over_count = sum(self.digit_frequency.get(d, 0) for d in range(5, 10))
        under_count = sum(self.digit_frequency.get(d, 0) for d in range(0, 5))
        probabilities['over'] = over_count / total_ticks
        probabilities['under'] = under_count / total_ticks
        
        # Even/Odd probability
        even_count = sum(self.digit_frequency.get(d, 0) for d in [0, 2, 4, 6, 8])
        odd_count = sum(self.digit_frequency.get(d, 0) for d in [1, 3, 5, 7, 9])
        probabilities['even'] = even_count / total_ticks
        probabilities['odd'] = odd_count / total_ticks
        
        return probabilities
    
    async def predict_with_ml(self):
        """Use simple statistics to predict the next digit"""
        # Ensure we have enough historical data
        if len(self.last_digits) < 10:
            await self.fetch_historical_data(self.trade_config['market'])
        
        try:
            # Find the most common digit
            if not self.digit_frequency:
                return {
                    'lstm_confidence': 0.5,
                    'rf_prediction': 5,
                    'rf_probabilities': {i: 0.1 for i in range(10)}
                }
                
            most_common_digit = self.digit_frequency.most_common(1)[0][0]
            total_count = sum(self.digit_frequency.values())
            
            # Calculate probabilities for each digit
            probabilities = {digit: count/total_count for digit, count in self.digit_frequency.items()}
            
            # Fill in missing digits with low probability
            for i in range(10):
                if i not in probabilities:
                    probabilities[i] = 0.01
                    
            # Calculate confidence based on frequency of the most common digit
            confidence = self.digit_frequency[most_common_digit] / total_count
            
            # Return in the same format as the ML version
            return {
                'lstm_confidence': confidence,
                'rf_prediction': most_common_digit,
                'rf_probabilities': probabilities
            }
            
        except Exception as e:
            self.logger.error(f"Prediction error: {str(e)}")
            return {
                'lstm_confidence': 0.5,
                'rf_prediction': 5,
                'rf_probabilities': {i: 0.1 for i in range(10)}
            }
    
    async def get_news_sentiment(self):
        """Get financial news sentiment for additional signal"""
        try:
            # This would be replaced with a real financial news API
            # For now, we'll return a random sentiment
            import random
            sentiment = random.uniform(-1.0, 1.0)
            return sentiment
            
        except Exception as e:
            self.logger.error(f"News sentiment error: {str(e)}")
            return 0.0
    
    async def execute_trade(self):
        """Execute a trade based on configured parameters and predictions"""
        if self.paused:
            return {'success': False, 'message': 'Trading is paused'}
        
        if not self.connected:
            success = await self.connect()
            if not success:
                return {'success': False, 'message': 'Failed to connect to API'}
        
        try:
            # Analyze market data
            await self.fetch_historical_data(self.trade_config['market'])
            
            # Calculate probabilities
            probabilities = await self.calculate_probabilities()
            
            # Get ML predictions
            ml_predictions = await self.predict_with_ml()
            
            # Get news sentiment
            sentiment = await self.get_news_sentiment()
            
            # Determine contract parameters based on contract type
            contract_params = {}
            contract_type = self.trade_config['contract_type']
            
            if contract_type == 'matches':
                target_digit = ml_predictions['rf_prediction']
                contract_params = {
                    "contract_type": "DIGITMATCH",
                    "symbol": self.trade_config['market'],
                    "duration": 5,
                    "duration_unit": "t",
                    "barrier": target_digit,
                    "basis": "stake",
                    "currency": "USD",
                    "amount": self.get_stake_amount()
                }
            elif contract_type == 'differs':
                avoid_digit = ml_predictions['rf_prediction']
                contract_params = {
                    "contract_type": "DIGITDIFF",
                    "symbol": self.trade_config['market'],
                    "duration": 5,
                    "duration_unit": "t",
                    "barrier": avoid_digit,
                    "basis": "stake",
                    "currency": "USD",
                    "amount": self.get_stake_amount()
                }
            elif contract_type == 'over_under':
                if probabilities['over'] > probabilities['under']:
                    barrier = 4  # Predict over 4
                else:
                    barrier = 5  # Predict under 5
                contract_params = {
                    "contract_type": "DIGITOVER" if probabilities['over'] > probabilities['under'] else "DIGITUNDER",
                    "symbol": self.trade_config['market'],
                    "duration": 5,
                    "duration_unit": "t",
                    "barrier": barrier,
                    "basis": "stake",
                    "currency": "USD",
                    "amount": self.get_stake_amount()
                }
            elif contract_type == 'even_odd':
                if probabilities['even'] > probabilities['odd']:
                    contract_params = {
                        "contract_type": "DIGITEVEN",
                        "symbol": self.trade_config['market'],
                        "duration": 5,
                        "duration_unit": "t",
                        "basis": "stake",
                        "currency": "USD",
                        "amount": self.get_stake_amount()
                    }
                else:
                    contract_params = {
                        "contract_type": "DIGITODD",
                        "symbol": self.trade_config['market'],
                        "duration": 5,
                        "duration_unit": "t",
                        "basis": "stake",
                        "currency": "USD",
                        "amount": self.get_stake_amount()
                    }
            
            # Calculate confidence based on probabilities, ML and sentiment
            confidence = 0.0
            if contract_type == 'matches':
                confidence = (probabilities['matches'] * 0.5) + (ml_predictions['lstm_confidence'] * 0.3) + ((sentiment + 1) / 2 * 0.2)
            elif contract_type == 'differs':
                confidence = (probabilities['differs'] * 0.5) + (ml_predictions['lstm_confidence'] * 0.3) + ((sentiment + 1) / 2 * 0.2)
            elif contract_type == 'over_under':
                confidence = (max(probabilities['over'], probabilities['under']) * 0.5) + (ml_predictions['lstm_confidence'] * 0.3) + ((sentiment + 1) / 2 * 0.2)
            elif contract_type == 'even_odd':
                confidence = (max(probabilities['even'], probabilities['odd']) * 0.5) + (ml_predictions['lstm_confidence'] * 0.3) + ((sentiment + 1) / 2 * 0.2)
            
            # Adapt confidence threshold based on market conditions and past performance
            # This makes the bot more conservative during turbulent markets and more aggressive in stable markets
            base_confidence_threshold = 0.6
            
            # Adjust threshold based on win rate
            total_trades = self.trade_config['wins'] + self.trade_config['losses']
            if total_trades > 0:
                win_rate = self.trade_config['wins'] / total_trades
                
                # Lower threshold if win rate is high, increase if low
                if win_rate > 0.6:  # Good performance, can be more aggressive
                    confidence_adjustment = -0.05  # Lower threshold
                elif win_rate < 0.4:  # Poor performance, be more conservative
                    confidence_adjustment = 0.05   # Increase threshold
                else:
                    confidence_adjustment = 0.0    # Default threshold
            else:
                confidence_adjustment = 0.0
                
            # Adjust threshold based on digit volatility
            if len(self.last_digits) >= 20:
                # Check last 20 digits for volatility
                digit_counts = Counter(self.last_digits[-20:])
                unique_digits = len(digit_counts)
                
                if unique_digits <= 3:  # Very stable market, fewer unique digits
                    volatility_adjustment = -0.03  # Can be more aggressive
                elif unique_digits >= 8:  # Volatile market, many different digits
                    volatility_adjustment = 0.03   # Be more conservative
                else:
                    volatility_adjustment = 0.0
            else:
                volatility_adjustment = 0.0
                
            # Apply adjustments
            min_confidence = base_confidence_threshold + confidence_adjustment + volatility_adjustment
            
            # Cap the threshold within reasonable limits
            min_confidence = max(0.5, min(0.75, min_confidence))
                
            self.logger.info(f"Confidence threshold: {min_confidence:.2f} (base: {base_confidence_threshold}, " +
                           f"win rate adj: {confidence_adjustment:.2f}, volatility adj: {volatility_adjustment:.2f})")
                
            if confidence < min_confidence:
                self.logger.info(f"Skipping trade: confidence too low ({confidence:.2f} < {min_confidence:.2f})")
                return {
                    'success': False, 
                    'message': f'Confidence too low: {confidence:.2f} < {min_confidence:.2f}',
                    'confidence': confidence,
                    'threshold': min_confidence,
                    'probabilities': probabilities,
                    'ml_predictions': ml_predictions
                }
            
            # Execute the trade
            trade_request = {
                "buy": 1,
                "parameters": contract_params,
                "price": contract_params['amount']
            }
            
            await self.ws.send(json.dumps(trade_request))
            response = await self.ws.recv()
            response_data = json.loads(response)
            
            if 'error' in response_data:
                self.logger.error(f"Trade execution error: {response_data['error']['message']}")
                return {'success': False, 'message': response_data['error']['message']}
            
            # Get the contract ID and wait for result
            contract_id = response_data.get('buy', {}).get('contract_id')
            if not contract_id:
                return {'success': False, 'message': 'No contract ID received'}
            
            # Subscribe to contract updates
            proposal_open_contract_request = {
                "proposal_open_contract": 1,
                "contract_id": contract_id,
                "subscribe": 1
            }
            
            await self.ws.send(json.dumps(proposal_open_contract_request))
            
            # Wait for the contract to be settled
            while True:
                response = await self.ws.recv()
                response_data = json.loads(response)
                
                if 'proposal_open_contract' in response_data:
                    contract_data = response_data['proposal_open_contract']
                    
                    if contract_data.get('status') == 'sold':
                        # Contract is settled
                        profit = contract_data.get('profit', 0)
                        is_win = profit > 0
                        
                        # Update trade statistics
                        self.trade_config['total_profit_loss'] += profit
                        
                        if is_win:
                            self.trade_config['wins'] += 1
                            self.trade_config['consecutive_losses'] = 0
                            self.trade_config['current_martingale_level'] = 0
                            
                            # Check if we should break after win
                            if self.break_after_win:
                                self.paused = True
                                self.break_after_win = False
                        else:
                            self.trade_config['losses'] += 1
                            self.trade_config['consecutive_losses'] += 1
                            
                            # Increment martingale level if needed
                            if self.trade_config['consecutive_losses'] >= self.trade_config['martingale_start']:
                                self.trade_config['current_martingale_level'] = min(
                                    self.trade_config['current_martingale_level'] + 1,
                                    self.trade_config['max_martingale']
                                )
                        
                        # Check if target profit or stop loss reached
                        if self.trade_config['total_profit_loss'] >= self.trade_config['target_profit']:
                            self.logger.info(f"Target profit reached: {self.trade_config['total_profit_loss']}")
                            self.paused = True
                        elif self.trade_config['total_profit_loss'] <= -self.trade_config['stop_loss']:
                            self.logger.info(f"Stop loss reached: {self.trade_config['total_profit_loss']}")
                            self.paused = True
                        
                        return {
                            'success': True,
                            'is_win': is_win,
                            'profit': profit,
                            'total_profit_loss': self.trade_config['total_profit_loss'],
                            'confidence': confidence,
                            'contract_type': contract_type
                        }
                
                # Check for errors
                if 'error' in response_data:
                    self.logger.error(f"Contract monitoring error: {response_data['error']['message']}")
                    return {'success': False, 'message': response_data['error']['message']}
                
                # Wait a bit before checking again
                await asyncio.sleep(0.1)
            
        except Exception as e:
            self.logger.error(f"Execute trade error: {str(e)}")
            return {'success': False, 'message': f'Trade execution failed: {str(e)}'}
    
    def get_stake_amount(self):
        """Calculate stake amount based on adaptive martingale strategy with risk management"""
        base_stake = self.trade_config['stake_amount']
        
        # If we're not in a martingale sequence, return base stake
        if self.trade_config['current_martingale_level'] == 0:
            return base_stake
            
        # Get basic multiplier (standard martingale uses 2^level)
        standard_multiplier = 2 ** self.trade_config['current_martingale_level']
        
        # Apply risk management based on win/loss ratio and account balance
        if hasattr(self, 'account_info') and 'balance' in self.account_info:
            account_balance = self.account_info.get('balance', 0)
            
            # Calculate win rate
            total_trades = self.trade_config['wins'] + self.trade_config['losses']
            win_rate = self.trade_config['wins'] / total_trades if total_trades > 0 else 0.5
            
            # Adjust multiplier based on win rate
            # Lower win rates use more conservative multipliers
            if win_rate < 0.4 and self.trade_config['current_martingale_level'] > 2:
                # More conservative approach if win rate is low
                multiplier = 1.5 ** self.trade_config['current_martingale_level']
            elif win_rate > 0.6:
                # More aggressive approach if win rate is high
                multiplier = standard_multiplier
            else:
                # Default approach
                multiplier = 1.8 ** self.trade_config['current_martingale_level']
                
            # Apply risk limits - never stake more than X% of account balance
            max_risk_percentage = 0.05  # 5% of account balance
            max_stake = account_balance * max_risk_percentage
            
            # Calculate stake using multiplier, but cap at maximum risk limit
            stake = min(base_stake * multiplier, max_stake)
            
            # Ensure the stake is at least the base amount
            return max(stake, base_stake)
            
        # Fallback to standard martingale if account info is not available
        return base_stake * standard_multiplier
    
    def pause(self):
        """Pause trading"""
        self.paused = True
        self.logger.info("Trading paused")
    
    def resume(self):
        """Resume trading"""
        self.paused = False
        self.logger.info("Trading resumed")
    
    async def close(self):
        """Close the websocket connection"""
        if self.ws:
            await self.ws.close()
            self.connected = False
            self.logger.info("Connection closed")
