# Third-party software

Sleepy's own code and original face icon use the MIT license in `LICENSE`.
Dependencies retain their respective licenses. This source release vendors only
frontend libraries and fonts; Python/Qt dependencies are installed separately.

## Vendored UI libraries

- Mermaid: MIT — `ui/vendor/mermaid-LICENSE.txt`; loaded only on diagram request.

- Marked: MIT â€” `ui/vendor/marked-LICENSE.txt`
- DOMPurify: Apache-2.0 OR MPL-2.0 â€” `ui/vendor/dompurify-LICENSE.txt`
- highlight.js CDN assets: BSD-3-Clause â€” `ui/vendor/@highlightjs-cdn-assets-LICENSE.txt`
- KaTeX: MIT, with bundled font notices â€” `ui/vendor/katex-LICENSE.txt`

Versions are recorded in `ui/vendor/versions.json`. Keep these license files and
all copyright/font notices when redistributing the frontend.

## Installed dependencies

See the installed distributions and upstream projects for complete license terms:

- [PySide6 / Qt for Python](https://doc.qt.io/qtforpython-6/licenses.html):
  LGPLv3/GPLv3/commercial options; Qt modules and bundled third-party components
  have their own notices. A future binary installer must include the appropriate
  Qt and third-party notices and satisfy the chosen distribution license.
- [OpenAI Python SDK](https://github.com/openai/openai-python): Apache-2.0.
- [python-dotenv](https://github.com/theskumar/python-dotenv): BSD-3-Clause.
- [Pillow](https://github.com/python-pillow/Pillow): MIT-CMU and bundled notices.
- [keyring](https://github.com/jaraco/keyring): MIT and dependency notices.
- [pypdf](https://github.com/py-pdf/pypdf): BSD-3-Clause.
- [edge-tts](https://github.com/rany2/edge-tts): LGPL-3.0; optional online neural voice service client.
- [yt-dlp](https://github.com/yt-dlp/yt-dlp): Unlicense for the Python source distribution; dependencies have their own licenses.

Web images come from Wikimedia Commons with source/creator/license information
displayed beside each image. Each image retains its own license. YouTube and
SoundCloud content remains subject to its source's terms and availability.

No third-party branding implies sponsorship or affiliation. Provider/API usage
is subject to each provider's terms and account limits.
