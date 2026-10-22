"""Vendor official npm browser builds so rendering works without a CDN at runtime."""
import io
import json
import tarfile
import urllib.request
from pathlib import Path

DEST = Path(__file__).parent / 'ui' / 'vendor'

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'Sleepy-setup'})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()

def main():
    DEST.mkdir(parents=True, exist_ok=True)
    packages = {'marked': ('lib/marked.umd.js', 'marked.js'),
                'dompurify': ('dist/purify.min.js', 'purify.js'),
                '@highlightjs/cdn-assets': ('highlight.min.js', 'highlight.js'),
                'katex': ('dist/katex.min.js', 'katex.js'),
                'mermaid': ('dist/mermaid.min.js', 'mermaid.js')}
    versions = {}
    for package, (source, target) in packages.items():
        metadata = json.loads(get('https://registry.npmjs.org/' + package + '/latest'))
        versions[package] = metadata['version']
        archive = tarfile.open(fileobj=io.BytesIO(get(metadata['dist']['tarball'])), mode='r:gz')
        data = archive.extractfile('package/' + source).read()
        (DEST / target).write_bytes(data)
        if package == 'katex':
            for member in archive.getmembers():
                name = member.name.removeprefix('package/dist/')
                if name == 'katex.min.css' or (name.startswith('fonts/') and name.endswith('.woff2')):
                    path = DEST / name
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(archive.extractfile(member).read())
        license_files = [m for m in archive.getmembers() if m.name.lower() in ('package/license', 'package/license.md', 'package/license.txt')]
        if license_files:
            (DEST / (package.replace('/', '-') + '-LICENSE.txt')).write_bytes(archive.extractfile(license_files[0]).read())
        print(package, metadata['version'])
    (DEST / 'versions.json').write_text(json.dumps(versions, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
