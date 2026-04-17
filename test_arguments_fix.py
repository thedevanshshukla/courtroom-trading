#!/usr/bin/env python3
from src.courtroom_trading.contracts import MemoryRecord, Argument, AgentOutput
from dataclasses import asdict

print("=" * 60)
print("DIAGNOSTIC TEST FOR BULL/BEAR ARGUMENTS FIX")
print("=" * 60)
print()

# Test 1: Old record without new fields
print("TEST 1: Old record deserialization")
print("-" * 60)
old_record_data = {
    'user_id': 'test_user',
    'features_hash': 'test_hash',
    'decision': 'TRADE',
    'bull_score': 1.5,
    'bear_score': 0.8,
    'winning_side': 'BULL',
    'confidence': 0.75,
    'feature_snapshot': {'price': 100, 'rsi': 75},
    'signal_snapshot': {'rsi_signal': 'OVERBOUGHT'},
}

try:
    record = MemoryRecord(**old_record_data)
    print('✓ Old record deserialized successfully')
    print(f'  bull_args: {record.bull_args}')
    print(f'  bear_args: {record.bear_args}')
    print(f'  reasoning: "{record.reasoning}"')
except Exception as e:
    print(f'✗ Error: {type(e).__name__}: {e}')

print()

# Test 2: New record with new fields
print("TEST 2: New record with all fields")
print("-" * 60)
new_record_data = {
    'user_id': 'test_user',
    'features_hash': 'test_hash',
    'decision': 'TRADE',
    'bull_score': 1.5,
    'bear_score': 0.8,
    'winning_side': 'BULL',
    'confidence': 0.75,
    'feature_snapshot': {'price': 100, 'rsi': 75},
    'signal_snapshot': {'rsi_signal': 'OVERBOUGHT'},
    'bull_args': ['Bull arg 1', 'Bull arg 2'],
    'bear_args': ['Bear arg 1'],
    'reasoning': 'Bull case is stronger',
}

try:
    record = MemoryRecord(**new_record_data)
    print('✓ New record deserialized successfully')
    print(f'  bull_args: {record.bull_args}')
    print(f'  bear_args: {record.bear_args}')
    print(f'  reasoning: "{record.reasoning}"')
except Exception as e:
    print(f'✗ Error: {type(e).__name__}: {e}')

print()

# Test 3: Argument extraction like in orchestrator
print("TEST 3: Argument extraction")
print("-" * 60)
try:
    arg1 = Argument(claim='Test claim 1', evidence='Evidence 1', rule_used='RULE_1', strength=0.8)
    arg2 = Argument(claim='Test claim 2', evidence='Evidence 2', rule_used='RULE_2', strength=0.7)
    bull_output = AgentOutput(stance='BULL', arguments=[arg1, arg2])
    
    extracted = [arg.claim for arg in bull_output.arguments]
    print(f'✓ Arguments extracted successfully')
    print(f'  Extracted claims: {extracted}')
except Exception as e:
    print(f'✗ Error: {type(e).__name__}: {e}')

print()
print("=" * 60)
print("DIAGNOSTIC COMPLETE")
print("=" * 60)
