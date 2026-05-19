import glob

for f in glob.glob('templates/*.html'):
    with open(f, 'r', encoding='utf-8') as file:
        content = file.read()
    if 'window.USERNAME' not in content:
        content = content.replace('<script src="/static/dropdown.js"></script>', '<script>window.USERNAME = "{{ session.get(\'username\', \'\') }}";</script>\n    <script src="/static/dropdown.js"></script>')
        with open(f, 'w', encoding='utf-8') as file:
            file.write(content)
