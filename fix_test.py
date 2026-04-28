#!/usr/bin/env python3
"""Fix indentation in SSML test file."""

with open(r'backend\tests\test_ssml_injector.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Fix lines 163-164 (indices 162-163)
if len(lines) > 163:
    # Replace the badly indented lines
    if '            # All matches' in lines[162]:
        lines[162] = '        # All matches should be variations of "magic" (case-insensitive)\n'
    if '            assert all(tag' in lines[163]:
        lines[163] = '        assert all(tag["term"].lower() == "magic" for tag in phoneme_tags)\n'

with open(r'backend\tests\test_ssml_injector.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed!")
