import os, glob
for f in glob.glob('templates/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if '/static/dark_mode.css' not in content:
        content = content.replace('</head>', '    <link rel="stylesheet" href="/static/dark_mode.css">\n</head>')
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
