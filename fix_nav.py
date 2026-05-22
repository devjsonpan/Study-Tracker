import os
import glob
import re

css_files = glob.glob('static/*.css')

for file in css_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Define the old patterns (they might vary slightly in spacing)
    # So we'll use a regex to replace the entire side-panel block under @media (max-width: 768px)
    
    pattern = re.compile(r'\.side-panel\s*\{[^}]+\}\s*\.side-panel-logo\s*\{[^}]+\}\s*\.side-panel\s*\.button\s*\{[^}]+\}')
    
    new_css = """    .side-panel {
        width: 100%;
        height: auto;
        position: relative;
        flex-direction: row;
        flex-wrap: nowrap;
        overflow-x: auto;
        align-items: center;
        padding: 10px 15px;
        box-sizing: border-box;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none; /* Firefox */
    }
    .side-panel::-webkit-scrollbar {
        display: none; /* Chrome/Safari */
    }

    .side-panel-logo {
        width: auto;
        margin-bottom: 0;
        padding-bottom: 0;
        margin-right: 15px;
        flex-shrink: 0;
        border-bottom: none;
    }
    .side-panel-logo h2 {
        font-size: 18px;
        margin: 0;
    }

    .side-panel .button {
        padding: 8px 14px;
        font-size: 13px;
        flex: 0 0 auto;
        max-width: none;
        white-space: nowrap;
        margin: 0 5px 0 0;
        justify-content: center;
    }"""

    if pattern.search(content):
        content = pattern.sub(new_css, content)
        with open(file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {file}")
    else:
        print(f"Pattern not found in {file}")
