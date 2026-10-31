# SPDX-License-Identifier: GPL-2.0-or-later
"""Package already-audited firmware, notices, runtime data and corresponding source.

No USB access, image rebuilding, vendor executables or private recovery data.
Run from the clean source commit to be tagged; dependencies must already be cached.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1]

def git(repo,*args):
    return subprocess.check_output(['git','-C',str(repo),*args])

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def tracked(repo):
    return [Path(p.decode()) for p in git(repo,'ls-files','-z').split(b'\0') if p]

def tree(archive,folder,prefix,paths=None):
    paths=paths if paths is not None else (p.relative_to(folder) for p in folder.rglob('*') if p.is_file())
    for relative in sorted(set(paths)):
        if any(p in {'.git','target','__pycache__'} for p in relative.parts):continue
        path=folder/relative
        if path.is_file():archive.write(path,(Path(prefix)/relative).as_posix())

def notice_files(archive):
    for name in ('COPYING','LICENSE','THIRD_PARTY_NOTICES.md'):
        archive.write(ROOT/name,name)
    tree(archive,ROOT/'notices','notices')
    tree(archive,ROOT/'vendor/dmc100-doom/LICENSES','notices/dmc100-doom')
    archive.write(ROOT/'vendor/dmc100-doom/CREDITS.md','notices/dmc100-doom/CREDITS.md')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant',choices=('pc','mini'),required=True)
    parser.add_argument('--tag',required=True)
    parser.add_argument('--metadata',type=Path,default=ROOT/'artifacts/release/cargo-metadata.json')
    args=parser.parse_args()
    if any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._' for c in args.tag):
        parser.error('Use a simple release tag')
    assert not git(ROOT,'status','--porcelain').strip(),'Commit source and docs before packaging'
    mini=args.variant=='mini'
    version='kws-x1-mini-wide-v3' if mini else 'kws-x1-doom-wide-v7r2'
    image=ROOT/('artifacts/mini' if mini else 'artifacts')/(version+'.X1C')
    expected='acc8b85c2ec24a51b43a9348eac16ab68fda019c512fb74537a577dc15285d4f' if mini else 'dd8fb79765193f8ae55286d20730f6b2e936b994141f9ba7efabc0464ad67c18'
    assert digest(image)==expected,'Unexpected firmware image'
    out=ROOT/'artifacts/releases'/args.tag
    out.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(image,out/image.name)
    for src,dst in [('docs/FIRMWARE.md','README.EN.md'),('docs/FIRMWARE.ja.md','README.JA.md')]:
        shutil.copyfile(ROOT/src,out/dst)
    with zipfile.ZipFile(out/'licenses.zip','w',zipfile.ZIP_DEFLATED) as archive:notice_files(archive)
    commit=git(ROOT,'rev-parse','HEAD').decode().strip()
    metadata=json.loads(args.metadata.read_text(encoding='utf-8-sig'))
    packages=[p for p in metadata['packages'] if p.get('source')]
    manifest={'tag':args.tag,'source_commit':commit,'firmware_sha256':expected,'variant':args.variant,
              'packages':[{'name':p['name'],'version':p['version'],'source':p['source']} for p in packages]}
    with zipfile.ZipFile(out/'corresponding-source.zip','w',zipfile.ZIP_DEFLATED) as archive:
        with zipfile.ZipFile(io.BytesIO(git(ROOT,'archive','--format=zip','HEAD'))) as project:
            for name in project.namelist():
                if not name.endswith('/'):archive.writestr('project/'+name,project.read(name))
        engine=ROOT/'vendor/dmc100-doom'
        tree(archive,engine,'project/vendor/dmc100-doom',tracked(engine))
        tree(archive,engine/'gen','project/vendor/dmc100-doom/gen')
        oracle=engine/'oracle/src/doomgeneric-repo'
        tree(archive,oracle,'project/vendor/dmc100-doom/oracle/src/doomgeneric-repo',tracked(oracle))
        board=ROOT/('artifacts/mini/board' if mini else 'vendor/kws-x1-standalone-rs')
        state=ROOT/('artifacts/staged-mini-hashes.json' if mini else 'artifacts/staged-hashes.json')
        managed=json.loads(state.read_text())
        for name,sha in managed.items():assert digest(board/name)==sha,(name,'staged source changed')
        tree(archive,board,'project/vendor/kws-x1-standalone-rs',tracked(board)+list(map(Path,managed)))
        if mini:
            tree(archive,ROOT/'artifacts/mini/gen','project/artifacts/mini/gen')
            for name in ('DOOM.DAT','mini-arena.wad'):
                archive.write(ROOT/'artifacts/mini'/name,'project/artifacts/mini/'+name)
        archive.write(engine/'build/packs/E1M1/DOOM.DAT','project/vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT')
        git_roots=set()
        for package in packages:
            path=Path(package['manifest_path']).parent
            if package['source'].startswith('registry+'):
                tree(archive,path,'dependencies/registry/'+package['name']+'-'+package['version'])
            else:
                while not (path/'.git').exists():
                    assert path!=path.parent,'Git dependency checkout not found'
                    path=path.parent
                git_roots.add(path)
        for path in sorted(git_roots):
            revision=git(path,'rev-parse','HEAD').decode().strip()
            tree(archive,path,'dependencies/git/'+path.parent.name+'-'+revision,tracked(path))
        archive.writestr('SOURCE-MANIFEST.json',json.dumps(manifest,indent=2)+'\n')
        archive.writestr('SOURCE-README.md',
            '# Corresponding source\n\nSource commit: '+commit+'\n\n'
            'project/ contains the tagged project and prepared, patched board/engine sources, '
            'the pinned doomgeneric tree, generated C inputs and matching E1M1 pack. '
            'dependencies/ contains cached registry packages and complete pinned Git dependency source trees with their original notices. '
            'SOURCE-MANIFEST.json identifies every resolved dependency. Compilers/toolchains are not included.\n\n'
            'Normal reconstruction: clone the release tag, then follow project/docs/BUILD.md '
            '(and project/standalone/README.md for mini); these commands fetch pinned source revisions. '
            'Prepared sources here have no .git metadata; skip prepare-sources.py/stage-port.py when using them directly. '
            'Run scripts/build-engine.py from project/ (mini: --generated artifacts/mini/gen), '
            'set KWS_ENGINE_LIB to the resulting artifacts/engine directory, then cargo build --release --locked '
            '-p firmware --target thumbv7em-none-eabihf in project/vendor/kws-x1-standalone-rs. '
            'Its Cargo.lock fixes dependency versions; Cargo may fetch them unless an appropriate local source replacement is configured. '
            'The source trees needed for that are supplied under dependencies/. Use firmware-pack as in scripts/build.ps1 to package/audit.\n\n'
            'Keep COPYING and all original per-file notices. No manufacturer firmware, updater executable, bootloader, '
            'calibration dump, credentials or local machine configuration is included.\n')
    if not mini:
        with zipfile.ZipFile(out/'pc-runtime.zip','w',zipfile.ZIP_DEFLATED) as archive:
            for name in ('scripts/play.ps1','scripts/env.ps1','scripts/pc-controller.py','scripts/usb_link.py','requirements.txt'):
                archive.write(ROOT/name,name)
            tree(archive,ROOT/'web','web')
            tree(archive,ROOT/'docs','docs')
            for name in ('README.md','README.ja.md'):archive.write(ROOT/name,name)
            archive.write(ROOT/'SOURCE_LOCK.json','SOURCE_LOCK.json')
            archive.write(engine/'build/packs/E1M1/DOOM.DAT','vendor/dmc100-doom/build/packs/E1M1/DOOM.DAT')
            notice_files(archive)
    for path in out.glob('*.zip'):
        with zipfile.ZipFile(path) as archive:
            assert archive.testzip() is None,path
            assert not any(name.startswith('/') or '..' in Path(name).parts for name in archive.namelist())
    (out/'SHA256SUMS').write_text(''.join(f'{digest(p)}  {p.name}\n' for p in sorted(out.iterdir()) if p.is_file()),encoding='ascii')
    print(json.dumps({'directory':str(out),'source_commit':commit,'files':[{ 'name':p.name,'bytes':p.stat().st_size} for p in sorted(out.iterdir())]},indent=2),flush=True)

if __name__=='__main__':main()
