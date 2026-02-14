
import re

def analyze_file(filepath):
    with open(filepath, 'r') as f:
        lines = f.readlines()

    stack = []
    
    # We only care about the script part, roughly. 
    # But strictly speaking, we can just look for { and } in the whole file 
    # assuming mostly valid HTML/JS structure where <style> and <body> don't mess it up too much
    # or better, let's focus on the <script> block.
    
    in_script = False
    script_start_line = 0
    
    for i, line in enumerate(lines):
        if '<script>' in line:
            in_script = True
            script_start_line = i + 1
            print(f"Script starts at line {script_start_line}")
            continue
        if '</script>' in line:
            in_script = False
            print(f"Script ends at line {i+1}")
            
        if in_script:
            # Remove comments/strings to avoid false positives (simple approach)
            # This is a naive parser but usually good enough for "missing brace" debugging
            clean_line = re.sub(r'//.*', '', line) # remove line comments
            clean_line = re.sub(r'".*?"', '""', clean_line) # remove double quoted strings
            clean_line = re.sub(r"'.*?'", "''", clean_line) # remove single quoted strings
            clean_line = re.sub(r"`.*?`", "``", clean_line) # remove backtick strings (naive, multiline issues possible but let's try)

            for char in clean_line:
                if char == '{':
                    stack.append((char, i + 1))
                elif char == '}':
                    if not stack:
                        print(f"ERROR: Extra closing brace }} at line {i+1}")
                    else:
                        last = stack[-1]
                        if last[0] == '{':
                            stack.pop()
                        else:
                            print(f"ERROR: Mismatched brace }} at line {i+1}, expected closing for {last[0]} from line {last[1]}")

    if stack:
        print("\nUNCLOSED BLOCKS:")
        for item in stack:
            print(f"Unclosed {item[0]} from line {item[1]}: {lines[item[1]-1].strip()}")

analyze_file('smart_trading_bot.html')
