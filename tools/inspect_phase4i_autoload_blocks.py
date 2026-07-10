from pathlib import Path
p = Path('ki_system') / 'autonomous.py'
print('file:', p.resolve())
for i, line in enumerate(p.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
    if 'PHASE4I' in line or line.strip() in {'<<<','>>>','===','<<<<<<<','>>>>>>>'}:
        print(f'{i}: {line}')
