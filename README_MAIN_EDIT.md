# main_edit.py - Expert Optimizations Implementation

## Overview
`main_edit.py` is an optimized version of `main.py` that integrates 6 expert trading optimizations while preserving all original functionality.

## Expert Optimizations

### 1. 🎯 Flexible Multi-Timeframe M5 Confirmation
**Problem**: Old logic was too strict - M5 had to exactly match M15
**Solution**: 
- M5 only blocks when clearly opposite to M15
- NEUTRAL M5 is now allowed
- More trades can pass through when M5 is not decisive

**Code**:
```python
# Old: side_m5 == side_m15 (too strict)
# New: 
m5_allows = (side_m5 == side_m15) or (side_m5 == "NEUTRAL")
```

### 2. 📊 Increased Quality Thresholds
**Problem**: Low thresholds allowed too many weak signals
**Solution**: Raised thresholds to filter only high-quality setups

| Parameter | Old Value | New Value | Change |
|-----------|-----------|-----------|--------|
| M15 Score | 9.5 | 15.0 | +5.5 |
| H1 Score | 8.0 | 8.0 | unchanged |
| ADX H1 | 25 | 28 | +3 |
| Heavy Hits | 3 | 3 | unchanged |

### 3. 🔧 ATR Reversal Amplitude Filter
**Problem**: Entering trades too close to previous entry caused noise
**Solution**: Only enter if price differs from last entry by ≥ 0.7 × ATR

**Function**:
```python
def check_atr_reversal_filter(symbol, timeframe, price_now, atr_val, min_atr_mult=0.7):
    """
    Returns (allowed, price_diff):
    - allowed=True if no last entry or |price_now - last_entry| >= 0.7 * ATR
    - allowed=False if too close to last entry
    """
```

### 4. 🕐 M5 Snapshot Requires 3 Candles
**Problem**: Old logic required ALL candles to match exactly
**Solution**: 
- Requires 3 candles to confirm same direction
- Only blocks when ALL 3 are clearly opposite
- Allows mixed signals or NEUTRAL

**Logic**:
```python
# Count same vs opposite direction candles
same_direction_count = sum(1 for v in votes if v == side_m15)
opposite_direction_count = sum(1 for v in votes if v != "NEUTRAL" and v != side_m15)

# Block only if all 3 opposite
if opposite_direction_count >= 3:
    return False  # Block

# Allow if 3+ same direction or mixed
return True
```

### 5. 📉 Entry Difference Threshold: 0.5%
**Problem**: 0.3% was too sensitive, creating signals for tiny price movements
**Solution**: Raised to 0.5% to reduce noise

**Impact**:
- Entry must differ by ≥0.5% from last signal
- Reduces spam from small price fluctuations
- More meaningful signal changes

### 6. 🔄 Reversal Tracking & Logging
**Problem**: No protection against consecutive whipsaws
**Solution**: Track reversals, skip if too frequent

**Features**:
- Counts consecutive reversals
- Logs each reversal with counter
- Blocks after 3+ reversals within 1 hour
- Resets counter when same direction continues

**Output**:
```
[REVERSAL] Đảo chiều lần thứ 1 trong thời gian gần đây: BTC/USDT 15m
🚨 **CẢNH BÁO: ĐẢO CHIỀU #2** BTC/USDT 15m từ LONG sang SHORT
[REVERSAL] BỎ QUA tín hiệu do quá nhiều đảo chiều liên tiếp (3 lần trong 1h)
```

## Usage

### Running the Bot
```bash
# With strict profile
python main_edit.py --profile strict

# With medium profile
python main_edit.py --profile medium

# Default (uses config.json active_profile)
python main_edit.py
```

### Configuration
All optimizations use default values but can be overridden in `config.json`:

```json
{
  "thresholds": {
    "M15": 15.0,
    "H1": 8.0
  },
  "adx_h1_threshold": 28,
  "tight_mode": {
    "heavy_required": 3,
    "anti_chase_atr_mult": 0.7,
    "snapshot_confirmations": 2
  }
}
```

## Testing

Run the optimization tests:
```bash
python /tmp/test_optimizations.py
```

Expected output:
```
✅ All 6 expert optimizations implemented in main_edit.py
```

## Files

- `main_edit.py` - Main optimized trading bot (736 lines)
- `MAIN_EDIT_CHANGES.md` - Detailed technical documentation
- `README_MAIN_EDIT.md` - This file

## Independence

`main_edit.py` is **completely independent** from `main.py`:
- Can run simultaneously
- Can replace main.py
- Uses same config.json structure
- Compatible with all existing modules

## Migration

To migrate from main.py to main_edit.py:

1. **Test first**: Run main_edit.py in parallel with main.py
2. **Monitor**: Compare signal quality and frequency
3. **Switch**: Replace main.py calls with main_edit.py when satisfied
4. **Backup**: Keep main.py as fallback

## Benefits

✅ Higher quality signals (stricter thresholds)  
✅ More flexible M5 confirmation (allows NEUTRAL)  
✅ Better spacing between entries (ATR filter)  
✅ Whipsaw protection (reversal tracking)  
✅ Reduced noise (0.5% threshold)  
✅ More robust M5 confirmation (3 candle logic)  

## Technical Details

See `MAIN_EDIT_CHANGES.md` for:
- Line-by-line code changes
- Function signatures
- Implementation details
- Logic flow diagrams

## Support

For issues or questions about the optimizations:
1. Check `MAIN_EDIT_CHANGES.md` for technical details
2. Review test output in `/tmp/test_optimizations.py`
3. Compare with original `main.py` behavior
