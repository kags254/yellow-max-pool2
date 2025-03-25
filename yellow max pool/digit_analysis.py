import numpy as np
from collections import Counter

def analyze_digits(digits):
    """
    Analyze a list of last digits to provide insights
    
    Args:
        digits: List of last digits (0-9)
        
    Returns:
        Dictionary with analysis results
    """
    if not digits:
        return {
            'frequency': {i: 0 for i in range(10)},
            'most_common': None,
            'least_common': None,
            'streaks': [],
            'patterns': [],
            'missing': list(range(10))
        }
    
    # Calculate frequency
    frequency = Counter(digits)
    
    # Find most and least common digits
    most_common = frequency.most_common(1)[0][0] if frequency else None
    least_common = frequency.most_common()[-1][0] if len(frequency) == 10 else next(i for i in range(10) if i not in frequency)
    
    # Find streaks (consecutive same digits)
    streaks = []
    current_streak = {'digit': digits[0], 'count': 1, 'start': 0}
    
    for i in range(1, len(digits)):
        if digits[i] == current_streak['digit']:
            current_streak['count'] += 1
        else:
            if current_streak['count'] >= 3:  # Only record streaks of 3 or more
                streaks.append(current_streak)
            current_streak = {'digit': digits[i], 'count': 1, 'start': i}
    
    # Add the last streak if it's significant
    if current_streak['count'] >= 3:
        streaks.append(current_streak)
    
    # Find missing digits
    missing = [i for i in range(10) if i not in frequency]
    
    # Find patterns (repeating sequences) with more sophisticated detection
    patterns = []
    
    # Look for exact repetitions
    for length in range(2, min(6, len(digits) // 2)):  # Look for patterns up to length 5
        for start in range(len(digits) - length * 2):
            pattern = digits[start:start+length]
            next_seq = digits[start+length:start+length*2]
            if pattern == next_seq:
                # Check how many times this pattern repeats
                repeat_count = 2  # We already found 2 occurrences
                pos = start + length*2
                
                while pos + length <= len(digits):
                    if digits[pos:pos+length] == pattern:
                        repeat_count += 1
                        pos += length
                    else:
                        break
                
                patterns.append({
                    'pattern': pattern,
                    'length': length,
                    'start': start,
                    'repeats': repeat_count,
                    'type': 'exact',
                    'confidence': min(0.9, 0.5 + (repeat_count / 10))
                })
    
    # Look for arithmetic progressions (like 2,4,6,8 or 9,7,5,3)
    for window in range(3, min(8, len(digits))):
        for start in range(len(digits) - window):
            seq = digits[start:start+window]
            diffs = [seq[i+1] - seq[i] for i in range(len(seq)-1)]
            
            # Check if all diffs are the same (arithmetic progression)
            if len(set(diffs)) == 1 and diffs[0] != 0:  # Avoid sequences like 5,5,5
                diff = diffs[0]
                # Handle wraparound (e.g., 8,9,0,1 has a consistent +1 pattern with wraparound at 10)
                adjusted_diffs = [(d + 10) % 10 if d < -5 else d % 10 if d > 5 else d for d in diffs]
                
                if len(set(adjusted_diffs)) == 1:
                    patterns.append({
                        'pattern': seq,
                        'length': window,
                        'start': start,
                        'type': 'arithmetic',
                        'difference': adjusted_diffs[0],
                        'confidence': min(0.8, 0.4 + (window / 10))
                    })
    
    # Look for alternating patterns (like high-low-high-low or odd-even-odd-even)
    for start in range(len(digits) - 6):  # Need at least 6 digits to confirm alternating pattern
        seq = digits[start:start+6]
        
        # Check odd-even alternation
        odd_even_alternating = True
        for i in range(5):
            if seq[i] % 2 == seq[i+1] % 2:  # Both odd or both even
                odd_even_alternating = False
                break
                
        # Check high-low alternation (digits 0-4 vs 5-9)
        high_low_alternating = True
        for i in range(5):
            if (seq[i] < 5 and seq[i+1] < 5) or (seq[i] >= 5 and seq[i+1] >= 5):
                high_low_alternating = False
                break
        
        if odd_even_alternating:
            patterns.append({
                'pattern': seq,
                'length': 6,
                'start': start,
                'type': 'odd_even_alternation',
                'confidence': 0.75
            })
            
        if high_low_alternating:
            patterns.append({
                'pattern': seq,
                'length': 6,
                'start': start,
                'type': 'high_low_alternation',
                'confidence': 0.75
            })
    
    return {
        'frequency': {i: frequency.get(i, 0) for i in range(10)},
        'most_common': most_common,
        'least_common': least_common,
        'streaks': streaks,
        'patterns': patterns,
        'missing': missing
    }

def get_digit_indicators(digits, window_size=20):
    """
    Generate indicators based on digit analysis to help predict future digits
    
    Args:
        digits: List of last digits (0-9)
        window_size: Size of the window to analyze for short-term trends
        
    Returns:
        Dictionary with indicator values
    """
    if len(digits) < window_size:
        return {
            'hot_digits': [],
            'cold_digits': [],
            'due_digits': [],
            'trending_up': [],
            'trending_down': []
        }
    
    # Get overall frequency
    overall_freq = Counter(digits)
    
    # Get recent frequency (last window_size digits)
    recent_freq = Counter(digits[-window_size:])
    
    # Calculate expected frequency for each digit in a uniform distribution
    expected_freq = len(digits) / 10
    recent_expected = window_size / 10
    
    # Hot digits: appearing more frequently in recent window
    hot_digits = []
    for digit in range(10):
        overall_rate = overall_freq.get(digit, 0) / len(digits)
        recent_rate = recent_freq.get(digit, 0) / window_size
        if recent_rate > overall_rate * 1.5 and recent_freq.get(digit, 0) >= 2:
            hot_digits.append({
                'digit': digit,
                'recent_rate': recent_rate,
                'overall_rate': overall_rate,
                'score': recent_rate / overall_rate if overall_rate > 0 else recent_rate * 10
            })
    
    # Cold digits: appearing less frequently in recent window
    cold_digits = []
    for digit in range(10):
        overall_rate = overall_freq.get(digit, 0) / len(digits)
        recent_rate = recent_freq.get(digit, 0) / window_size
        if recent_rate < overall_rate * 0.5 and overall_freq.get(digit, 0) >= 2:
            cold_digits.append({
                'digit': digit,
                'recent_rate': recent_rate,
                'overall_rate': overall_rate,
                'score': overall_rate / recent_rate if recent_rate > 0 else overall_rate * 10
            })
    
    # Due digits: not appeared for a long time
    all_positions = {digit: [] for digit in range(10)}
    for i, digit in enumerate(digits):
        all_positions[digit].append(i)
    
    due_digits = []
    for digit in range(10):
        positions = all_positions[digit]
        if not positions:  # Digit never appeared
            due_digits.append({
                'digit': digit,
                'absent_count': len(digits),
                'score': len(digits) / 10
            })
        else:
            last_pos = positions[-1]
            absent_count = len(digits) - 1 - last_pos
            if absent_count > expected_freq:
                due_digits.append({
                    'digit': digit,
                    'absent_count': absent_count,
                    'score': absent_count / expected_freq
                })
    
    # Trending analysis
    trending_up = []
    trending_down = []
    
    # Split the window into two halves and compare frequencies
    half_size = window_size // 2
    first_half = Counter(digits[-window_size:-half_size])
    second_half = Counter(digits[-half_size:])
    
    for digit in range(10):
        first_rate = first_half.get(digit, 0) / half_size
        second_rate = second_half.get(digit, 0) / half_size
        
        if second_rate > first_rate * 1.5:
            trending_up.append({
                'digit': digit,
                'first_rate': first_rate,
                'second_rate': second_rate,
                'score': second_rate / first_rate if first_rate > 0 else second_rate * 10
            })
        elif first_rate > second_rate * 1.5:
            trending_down.append({
                'digit': digit,
                'first_rate': first_rate,
                'second_rate': second_rate,
                'score': first_rate / second_rate if second_rate > 0 else first_rate * 10
            })
    
    # Sort all indicators by score in descending order
    hot_digits.sort(key=lambda x: x['score'], reverse=True)
    cold_digits.sort(key=lambda x: x['score'], reverse=True)
    due_digits.sort(key=lambda x: x['score'], reverse=True)
    trending_up.sort(key=lambda x: x['score'], reverse=True)
    trending_down.sort(key=lambda x: x['score'], reverse=True)
    
    return {
        'hot_digits': hot_digits[:3],  # Top 3 of each category
        'cold_digits': cold_digits[:3],
        'due_digits': due_digits[:3],
        'trending_up': trending_up[:3],
        'trending_down': trending_down[:3]
    }

def get_digit_prediction(digits, indicators):
    """
    Predict the next digit based on analysis and indicators
    
    Args:
        digits: List of last digits (0-9)
        indicators: Dictionary of indicators from get_digit_indicators()
        
    Returns:
        Dictionary with predictions and confidence scores
    """
    # Simple baseline prediction using the most recent pattern
    if len(digits) < 3:
        return {
            'matches': 5,  # Default prediction
            'differs': 5,
            'over': 5,
            'under': 5,
            'even': True,
            'odd': False,
            'confidence': 0.3
        }
    
    # Check for immediate patterns
    last_three = digits[-3:]
    
    # Check for repeats (e.g., 3,3,3 -> predict 3)
    if last_three[0] == last_three[1] == last_three[2]:
        repeat_confidence = 0.7
        return {
            'matches': last_three[0],
            'differs': (last_three[0] + 5) % 10,  # Pick a digit far from the match
            'over': 5 if last_three[0] >= 5 else 4,
            'under': 4 if last_three[0] < 5 else 5,
            'even': last_three[0] % 2 == 0,
            'odd': last_three[0] % 2 != 0,
            'confidence': repeat_confidence
        }
    
    # Check for arithmetic sequences (e.g., 2,4,6 -> predict 8)
    if last_three[1] - last_three[0] == last_three[2] - last_three[1]:
        diff = last_three[1] - last_three[0]
        next_in_seq = (last_three[2] + diff) % 10  # Loop around base 10
        seq_confidence = 0.6
        return {
            'matches': next_in_seq,
            'differs': (next_in_seq + 5) % 10,
            'over': 5 if next_in_seq >= 5 else 4,
            'under': 4 if next_in_seq < 5 else 5,
            'even': next_in_seq % 2 == 0,
            'odd': next_in_seq % 2 != 0,
            'confidence': seq_confidence
        }
    
    # Use the hot/cold/due indicators for more complex predictions
    matches_candidates = []
    differs_candidates = []
    
    # Hot digits are likely to repeat
    for hot in indicators.get('hot_digits', []):
        matches_candidates.append((hot['digit'], hot['score'] * 1.2))
    
    # Due digits might be coming soon
    for due in indicators.get('due_digits', []):
        matches_candidates.append((due['digit'], due['score']))
    
    # Cold digits are good candidates for "differs" prediction
    for cold in indicators.get('cold_digits', []):
        differs_candidates.append((cold['digit'], cold['score']))
    
    # Trending up digits are more likely to appear
    for trend in indicators.get('trending_up', []):
        matches_candidates.append((trend['digit'], trend['score'] * 1.1))
    
    # Trending down digits are less likely to appear
    for trend in indicators.get('trending_down', []):
        differs_candidates.append((trend['digit'], trend['score'] * 1.1))
    
    # Select the best candidates
    best_match = max(matches_candidates, key=lambda x: x[1])[0] if matches_candidates else 5
    best_differ = max(differs_candidates, key=lambda x: x[1])[0] if differs_candidates else 5
    
    # Calculate an overall confidence score (0.3 to 0.8 range)
    confidence = 0.3
    if matches_candidates:
        confidence += min(0.5, max(matches_candidates, key=lambda x: x[1])[1] / 10)
    
    return {
        'matches': best_match,
        'differs': best_differ,
        'over': 5 if indicators.get('hot_digits', []) and sum(h['digit'] >= 5 for h in indicators['hot_digits']) > len(indicators['hot_digits']) // 2 else 4,
        'under': 4 if indicators.get('hot_digits', []) and sum(h['digit'] < 5 for h in indicators['hot_digits']) > len(indicators['hot_digits']) // 2 else 5,
        'even': best_match % 2 == 0,
        'odd': best_match % 2 != 0,
        'confidence': confidence
    }
