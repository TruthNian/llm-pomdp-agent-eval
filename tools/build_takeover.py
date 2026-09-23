"""Build and bind a local Docker runtime; config contains argv, never credentials."""
import argparse
import io
import json
from pathlib import Path
import subprocess
import tarfile

from pomdp_bench.takeover_runtime import asset_hashes

BASE = 'postgres@sha256:3725f4e2499eef5134592b3b4ab79a543ed7f8e533b05b5b637af926630f6650'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('config', type=Path, help='JSON with docker_command and optional keepalive_command argv')
    args = parser.parse_args()
    cfg = json.loads(args.config.read_text(encoding='utf-8'))
    command = cfg.get('docker_command',['docker'])
    root = Path(__file__).resolve().parents[1] / 'pomdp_bench/takeover_data'
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf,mode='w:gz',format=tarfile.USTAR_FORMAT) as archive:
        for file in sorted(root.iterdir()):
            if file.is_file():
                data = file.read_bytes().replace(b'\r\n',b'\n')
                info = tarfile.TarInfo(file.name)
                info.size, info.mode = len(data), 0o644
                archive.addfile(info,io.BytesIO(data))
    subprocess.run(command+['build','--build-arg','BASE='+BASE,'-t','pomdp-takeover:local','-'],
                   input=buf.getvalue(),check=True)
    cfg.update(image=subprocess.check_output(command+['image','inspect','pomdp-takeover:local','--format','{{.Id}}']).decode().strip(),
               base_image=BASE,assets_sha256=asset_hashes())
    args.config.write_text(json.dumps(cfg,indent=2)+'\n',encoding='utf-8')
    print('Built immutable image:',cfg['image'])


if __name__ == '__main__':
    main()
