import glob
import re

css_files = glob.glob('static/*.css')

new_mobile_nav = """    .side-panel {
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
        justify-content: flex-start;
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

for file in css_files:
    with open(file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    if '@media' in content:
        parts = content.split('@media', 1)
        desktop_part = parts[0]
        mobile_part = '@media' + parts[1]
        
        pattern = re.compile(r'\.side-panel\s*\{[^}]+\}\s*\.side-panel-logo\s*\{[^}]+\}\s*\.side-panel\s*\.button\s*\{[^}]+\}')
        if pattern.search(mobile_part):
            mobile_part = pattern.sub(new_mobile_nav, mobile_part)
            
            with open(file, 'w', encoding='utf-8') as f:
                f.write(desktop_part + mobile_part)
            print(f"Updated {file}")
        else:
            print(f"Pattern not found in mobile section of {file}")
    else:
        print(f"No media queries in {file}")
