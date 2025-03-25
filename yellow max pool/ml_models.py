import random
import collections

def build_simple_prediction_model():
    """
    Build a simple statistical model for digit prediction
    
    Returns:
        A function that can predict the next digit
    """
    def predict_next_digit(digit_history):
        # If no history, return a random digit
        if not digit_history:
            return 5
        
        # Count frequency of each digit
        counter = collections.Counter(digit_history)
        
        # Find the most common digit
        most_common = counter.most_common(1)
        if most_common:
            return most_common[0][0]
        else:
            return random.randint(0, 9)
    
    return predict_next_digit

# For compatibility with existing code
def build_lstm_model():
    """Stub function for backward compatibility"""
    return build_simple_prediction_model()

def build_rf_model():
    """Stub function for backward compatibility"""
    return build_simple_prediction_model()

def train_lstm_model(model, historical_data, target_type='over_under', window_size=60):
    """
    Stub function for compatibility
    """
    return model

def train_rf_model(model, historical_data, window_size=10):
    """
    Stub function for compatibility
    """
    return model

def predict_next_digit(lstm_model, rf_model, last_digits, window_size=60, rf_window=10):
    """
    Simple statistical prediction of next digit
    
    Args:
        lstm_model: Function from build_simple_prediction_model
        rf_model: Function from build_simple_prediction_model
        last_digits: List of most recent last digits
        
    Returns:
        Dictionary with predictions
    """
    if not last_digits:
        return {
            'lstm_over': 0.5,
            'rf_prediction': 5,
            'rf_probabilities': {i: 0.1 for i in range(10)},
            'combined_prediction': 5,
            'confidence': 0.3
        }
    
    # Use our simple model function to predict
    next_digit = lstm_model(last_digits)
    
    # Calculate basic statistics
    from collections import Counter
    digit_counts = Counter(last_digits)
    total = len(last_digits)
    probabilities = {digit: count/total for digit, count in digit_counts.items()}
    
    # Fill in missing digits
    for d in range(10):
        if d not in probabilities:
            probabilities[d] = 0.01
    
    # Determine if it's likely to be over or under
    over_count = sum(digit_counts.get(d, 0) for d in range(5, 10))
    under_count = sum(digit_counts.get(d, 0) for d in range(0, 5))
    lstm_over = over_count / total if total > 0 else 0.5
    
    # Determine confidence based on how skewed the distribution is
    max_count = max(digit_counts.values()) if digit_counts else 0
    confidence = max_count / total if total > 0 else 0.3
    confidence = min(0.9, 0.3 + confidence * 0.5)  # Scale and cap
    
    return {
        'lstm_over': float(lstm_over),
        'rf_prediction': int(next_digit),
        'rf_probabilities': probabilities,
        'combined_prediction': int(next_digit),
        'confidence': confidence
    }
