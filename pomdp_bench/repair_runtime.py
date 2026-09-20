"""Run an untrusted source snapshot with no host mounts, network or credentials."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import threading
import uuid

from .model_io import strict_json

STATUSES = {"completed", "runtime_error", "timeout", "output_limit", "process_error", "invalid_response"}


def validate_image(image):
    if not isinstance(image, str) or not re.fullmatch(r"sha256:[0-9a-f]{64}", image):
        raise ValueError("Use an immutable local Docker image ID (sha256), not a mutable tag")


class DockerExecutor:
    def __init__(self, image):
        validate_image(image)
        self.image = image

    def run(self, files, requests):
        if not shutil.which("docker"):
            return {"status": "runtime_error"}
        name = "pomdp-repair-" + uuid.uuid4().hex
        worker = Path(__file__).with_name("repair_worker.py").read_text(encoding="utf-8")
        command = ["docker", "run", "--rm", "--pull=never", "--name", name, "-i",
                   "--network=none", "--read-only", "--user=65534:65534", "--cap-drop=ALL",
                   "--security-opt=no-new-privileges", "--pids-limit=32", "--memory=256m", "--cpus=1",
                   "--tmpfs=/work:rw,nosuid,nodev,noexec,size=32m,uid=65534,gid=65534",
                   self.image, "python", "-I", "-S", "-c", worker]
        payload = json.dumps({"files": files, "requests": requests}, ensure_ascii=False).encode()
        if len(payload) > 4_000_000:
            raise ValueError("Repair snapshot exceeds its fixed input allowance")
        chunks, overflow = [], threading.Event()
        process, reader = None, None
        try:
            with tempfile.TemporaryFile() as source:
                source.write(payload)
                source.seek(0)
                process = subprocess.Popen(command, stdin=source, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                def read_output():
                    total = 0
                    while chunk := process.stdout.read(8192):
                        total += len(chunk)
                        if total > 262_144:
                            overflow.set()
                            process.kill()
                            return
                        chunks.append(chunk)

                reader = threading.Thread(target=read_output, daemon=True)
                reader.start()
                try:
                    returncode = process.wait(timeout=20)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
                    return {"status": "timeout"}
                reader.join(timeout=5)
                if reader.is_alive():
                    return {"status": "runtime_error"}
                if overflow.is_set():
                    return {"status": "output_limit"}
                if returncode:
                    return {"status": "process_error"}
                try:
                    values = strict_json(b"".join(chunks).decode("utf-8"))
                except (ValueError, UnicodeError):
                    return {"status": "invalid_response"}
                return {"status": "completed", "values": values}
        except (OSError, subprocess.SubprocessError):
            return {"status": "runtime_error"}
        finally:
            if process is not None and process.poll() is None:
                process.kill()
            # Killing the client is not assumed to stop the container.
            try:
                subprocess.run(["docker", "rm", "-f", name], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            except (OSError, subprocess.SubprocessError):
                pass
            if reader is not None:
                reader.join(timeout=1)
            if process is not None and process.stdout is not None:
                process.stdout.close()
