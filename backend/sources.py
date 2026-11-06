"""Read local documents without modifying their source files."""
import hashlib
from html.parser import HTMLParser
from pathlib import Path

class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.hidden = 0
    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}: self.hidden += 1
        if tag in {'h1','h2','h3','p','pre','li','br'}: self.parts.append('\n')
    def handle_endtag(self, tag):
        if tag in {'script','style'}: self.hidden = max(0,self.hidden-1)
        if tag in {'h1','h2','h3','p','pre','li'}: self.parts.append('\n')
    def handle_data(self, data):
        if not self.hidden: self.parts.append(data)

def directory_files(root):
    root = Path(root).resolve()
    if not root.is_dir(): raise ValueError('Source directory does not exist')
    for path in sorted(root.rglob('*')):
        if path.is_symlink() or not path.is_file(): continue
        relative = path.relative_to(root)
        if any(part.startswith('.') for part in relative.parts): continue
        if path.suffix.lower() not in {'.md','.txt','.c','.h','.s','.html'}: continue
        content = path.read_text(encoding='utf-8',errors='replace')
        digest = hashlib.sha256(content.encode()).hexdigest()
        if path.suffix.lower() == '.html':
            parser = HTMLText(); parser.feed(content)
            content = ''.join(parser.parts)
        yield relative.as_posix(), content, digest
