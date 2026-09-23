"""Build the real CDC runtime from locally resolved upstream image identities."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def assets():
    root = Path(__file__).resolve().parents[1]/'pomdp_bench/stream_data'
    return root, {p.name:hashlib.sha256(p.read_bytes().replace(b'\r\n',b'\n')).hexdigest()
                  for p in sorted(root.iterdir()) if p.is_file()}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config',type=Path)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    command = config.get('docker_command',['docker'])
    sources = {}
    for name,tag in [('POSTGRES','postgres:17-bookworm'),('CONNECT','quay.io/debezium/connect:3.2.1.Final')]:
        raw = subprocess.check_output(command+['image','inspect',tag])
        item = json.loads(raw)[0]
        sources[name] = {'tag':tag,'image':item['Id'],'repo_digests':item['RepoDigests']}
    root,hashes = assets()
    data = io.BytesIO()
    with tarfile.open(fileobj=data,mode='w:gz',format=tarfile.USTAR_FORMAT) as archive:
        for name in hashes:
            content = (root/name).read_bytes().replace(b'\r\n',b'\n')
            info = tarfile.TarInfo(name)
            info.size,info.mode = len(content),0o644
            archive.addfile(info,io.BytesIO(content))
    arguments = ['build','-t','pomdp-stream:local']
    for name,source in sources.items():
        if not source['repo_digests']:
            raise ValueError('Upstream image has no repository digest: '+source['tag'])
        arguments += ['--build-arg',name+'='+source['repo_digests'][0]]
    subprocess.run(command+arguments+['-'],input=data.getvalue(),check=True)
    config.update(image=subprocess.check_output(command+['image','inspect','pomdp-stream:local','--format','{{.Id}}']).decode().strip(),
                  components=sources,assets_sha256=hashes,
                  debezium_source_commit='003672a405041d45d406ffac5149203b1a9e6471')
    args.config.write_text(json.dumps(config,indent=2)+'\n',encoding='utf-8')
    print('Built CDC runtime:',config['image'])


if __name__ == '__main__':
    main()
