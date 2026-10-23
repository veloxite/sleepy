"""Build an allowlisted source release, never copying user data or credentials."""
from datetime import datetime
from pathlib import Path
import re
import shutil
import zipfile

BASE=Path(__file__).resolve().parent
FILES=['README.md','PRIVACY.md','CROSS_PLATFORM_TESTING.md','LICENSE','THIRD_PARTY_NOTICES.md','.gitignore','.env.example',
       'requirements.txt','requirements-build.txt','VERSION','Sleepy.spec','build_app.py',
       'app_paths.py','platform_capture.py','package_smoke.py','DISTRIBUTION.md','desktop_agent.py','sleepy_app.py','focus_overlay.py','agent_core.py',
       'api_connections.py','github_plugin.py','local_store.py',
       'Create Sleepy Shortcut.ps1','fetch_frontend.py','build_source.py',
       'windows_integration.py','unix_windows.py','system_access.py','study_tools.py','provider_usage.py','provider_adapters.py',
       'assistant_features.py','desktop_actions.py','voice_input.py','music_player.py','web_media.py']
SECRET=re.compile(rb'(?:gsk_[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{30,}|sk-proj-[A-Za-z0-9_-]{20,})')

def build():
    sources=[BASE/name for name in FILES]
    for directory in ('ui','assets','.github','tests','packaging'):
        sources.extend(p for p in (BASE/directory).rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix!='.pyc')
    for source in sources:
        if source.is_symlink() or not source.resolve().is_relative_to(BASE):
            raise ValueError('A source path leaves the project: '+str(source.name))
        if not source.is_file():
            raise ValueError('Missing source file: '+source.name)
        if SECRET.search(source.read_bytes()):
            raise ValueError('Possible credential found in '+str(source.relative_to(BASE))+'. Release stopped.')
    target=BASE/'release'/('Sleepy-source-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
    target.mkdir(parents=True,exist_ok=False)
    for source in sources:
        destination=target/source.relative_to(BASE)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,destination)
    archive=target.with_suffix('.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for source in sorted(target.rglob('*')):
            if source.is_file():z.write(source,source.relative_to(target))
    print('Source folder:',target)
    print('Source ZIP:',archive)
    print(f'Included {len(sources)} files. No data, .env, virtual environment, logs, or local shortcuts included.')
    return target

if __name__=='__main__':build()
