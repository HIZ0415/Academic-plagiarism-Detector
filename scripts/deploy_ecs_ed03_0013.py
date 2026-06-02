import os
import posixpath
import socket
import stat
import sys
import tarfile
import time
from getpass import getpass
from pathlib import Path

import paramiko

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(errors="replace")


HOST = os.getenv("ECS_HOST", "114.116.204.131")
USER = os.getenv("ECS_USER", "root")
PASSWORD = os.getenv("ECS_PASSWORD") or getpass("ECS password: ")
PROJECT = "/data/Academic-plagiarism-Detector"
RELEASE = "/data/Academic-plagiarism-Detector-release.tar.gz"

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / ".runlogs" / "deploy_ecs_ed03_0013.tar.gz"

EXCLUDE_NAMES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".cache",
    "node_modules",
    "dist",
}


def should_exclude(path: Path) -> bool:
    rel = path.relative_to(ROOT)
    if set(rel.parts) & EXCLUDE_NAMES:
        return True
    if path.name.endswith((".pyc", ".pyo", ".log")):
        return True
    if path.name.startswith("deploy_bundle") and path.name.endswith(".tar.gz"):
        return True
    return False


def make_archive() -> None:
    ARCHIVE.parent.mkdir(exist_ok=True)
    if ARCHIVE.exists():
        ARCHIVE.unlink()
    with tarfile.open(ARCHIVE, "w:gz", dereference=False, format=tarfile.PAX_FORMAT) as tar:
        for path in ROOT.rglob("*"):
            if path == ARCHIVE or should_exclude(path):
                continue
            tar.add(path, arcname=Path("Academic-plagiarism-Detector") / path.relative_to(ROOT), recursive=False)
    print(f"ARCHIVE {ARCHIVE} {ARCHIVE.stat().st_size / 1024 / 1024:.1f} MB")


def connect() -> paramiko.SSHClient:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(
        HOST,
        username=USER,
        password=PASSWORD,
        timeout=20,
        banner_timeout=20,
        auth_timeout=20,
        look_for_keys=False,
        allow_agent=False,
    )
    return client


def run(client: paramiko.SSHClient, command: str, timeout: int = 900) -> str:
    print(f"\n$ {command}")
    _, stdout, stderr = client.exec_command(command, timeout=timeout, get_pty=True)
    chunks: list[str] = []
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            data = stdout.channel.recv(65535).decode("utf-8", errors="replace")
            chunks.append(data)
            print(data, end="")
        if stdout.channel.recv_stderr_ready():
            data = stdout.channel.recv_stderr(65535).decode("utf-8", errors="replace")
            chunks.append(data)
            print(data, end="", file=sys.stderr)
        time.sleep(0.2)
    while stdout.channel.recv_ready():
        data = stdout.channel.recv(65535).decode("utf-8", errors="replace")
        chunks.append(data)
        print(data, end="")
    while stdout.channel.recv_stderr_ready():
        data = stdout.channel.recv_stderr(65535).decode("utf-8", errors="replace")
        chunks.append(data)
        print(data, end="", file=sys.stderr)
    code = stdout.channel.recv_exit_status()
    output = "".join(chunks)
    if code != 0:
        raise RuntimeError(f"command failed ({code}): {command}\n{output[-4000:]}")
    return output


def sftp_mkdirs(sftp: paramiko.SFTPClient, path: str) -> None:
    parts = []
    while path not in ("", "/"):
        parts.append(path)
        path = posixpath.dirname(path)
    for current in reversed(parts):
        try:
            sftp.stat(current)
        except FileNotFoundError:
            sftp.mkdir(current)


def upload(client: paramiko.SSHClient) -> None:
    sftp = client.open_sftp()
    try:
        sftp_mkdirs(sftp, "/data")
        print(f"UPLOAD {ARCHIVE} -> {RELEASE}")
        sftp.put(str(ARCHIVE), RELEASE)
        sftp.chmod(RELEASE, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
    finally:
        sftp.close()


REMOTE_SCRIPT = r"""#!/usr/bin/env bash
set -euo pipefail

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PIP_PROGRESS_BAR=off
export npm_config_progress=false

PROJECT=/data/Academic-plagiarism-Detector
RELEASE=/data/Academic-plagiarism-Detector-release.tar.gz
BACKUP=/data/Academic-plagiarism-Detector.backup.$(date +%Y%m%d%H%M%S)
PUBLIC_HOST=114.116.204.131
API_URL=http://114.116.204.131
WS_URL=ws://114.116.204.131/ws/notifications/

echo "== system =="
cat /etc/os-release || true
uname -a

if command -v dnf >/dev/null 2>&1; then
  PKG=dnf
elif command -v yum >/dev/null 2>&1; then
  PKG=yum
elif command -v apt-get >/dev/null 2>&1; then
  PKG=apt-get
else
  echo "No supported package manager found" >&2
  exit 1
fi

echo "== install system packages =="
if [ "$PKG" = "apt-get" ]; then
  apt-get update
  DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv python3-pip python3-dev build-essential default-libmysqlclient-dev pkg-config nginx redis-server curl tar gzip mariadb-server
else
  $PKG install -y epel-release || true
  $PKG install -y gcc gcc-c++ make python3 python3-devel python3-pip nginx redis mariadb-server curl tar gzip
  $PKG install -y MariaDB-devel || $PKG install -y mariadb-devel || $PKG install -y mysql-devel || true
fi

if ! command -v node >/dev/null 2>&1 || ! node -e 'process.exit(Number(process.versions.node.split(".")[0]) >= 18 ? 0 : 1)' >/dev/null 2>&1; then
  echo "== install nodejs =="
  if [ "$PKG" = "apt-get" ]; then
    DEBIAN_FRONTEND=noninteractive apt-get install -y nodejs npm
  else
    $PKG install -y nodejs npm
  fi
fi

systemctl enable --now nginx || true
systemctl enable --now redis || systemctl enable --now redis-server || true
systemctl enable --now mariadb || systemctl enable --now mysql || true

echo "== replace project =="
mkdir -p /data
if [ -d "$PROJECT" ]; then
  mv "$PROJECT" "$BACKUP"
  echo "backup: $BACKUP"
fi
tar -xzf "$RELEASE" -C /data

echo "== backend environment =="
cd "$PROJECT/代码/后端/后端代码"
PYBASE=python3
if command -v python3.11 >/dev/null 2>&1; then
  PYBASE=python3.11
elif command -v python3.10 >/dev/null 2>&1; then
  PYBASE=python3.10
elif command -v python3.9 >/dev/null 2>&1; then
  PYBASE=python3.9
fi
$PYBASE --version
$PYBASE -m venv .venv
. .venv/bin/activate
python -m pip install -U pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install -r requirements.local.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

echo "== database =="
mysql -uroot <<'SQL'
CREATE DATABASE IF NOT EXISTS academic_plagiarism_detector CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
SQL

export DJANGO_SETTINGS_MODULE=fake_image_detector.cloud_settings
export DB_NAME=academic_plagiarism_detector
export DB_USER=root
export DB_PASSWORD=
export DB_HOST=127.0.0.1
export DB_PORT=3306
export CORS_ALLOWED_ORIGINS=http://114.116.204.131,http://114.116.204.131:81
python manage.py migrate --noinput
python manage.py shell <<'PY'
from datetime import timedelta
from django.utils import timezone
from core.models import DetectionTask, InvitationCode, Organization, ReviewRequest, User

admin, _ = User.objects.get_or_create(email="admin@mail.com", defaults={"username": "admin"})
admin.username = "admin"
admin.role = "admin"
admin.is_staff = True
admin.is_superuser = True
admin.permission = 1111
admin.set_password("Admin@123456")
admin.save()

org, _ = Organization.objects.get_or_create(name="默认测试组织", defaults={"email": "demo-org@example.com"})
if not org.email:
    org.email = "demo-org@example.com"
org.save()

seed_users = [
    ("org_admin@example.com", "org_admin", "admin", "OrgAdmin123!", 1111, True, False),
    ("publisher_test@example.com", "publisher_test", "publisher", "Publisher123!", 1110, False, False),
    ("reviewer_test@example.com", "reviewer_test", "reviewer", "Reviewer123!", 1001, False, False),
    ("publisher@mail.com", "publisher", "publisher", "Publisher@123456", 1110, False, False),
    ("reviewer@mail.com", "reviewer", "reviewer", "Reviewer@123456", 1001, False, False),
]
for email, username, role, password, permission, is_staff, is_superuser in seed_users:
    user, _ = User.objects.get_or_create(email=email, defaults={"username": username})
    user.username = username
    user.role = role
    user.organization = org
    user.permission = permission
    user.is_staff = is_staff
    user.is_superuser = is_superuser
    user.set_password(password)
    user.save()

org_admin = User.objects.get(email="org_admin@example.com")
if org.admin_user_id != org_admin.id:
    org.admin_user = org_admin
    org.save(update_fields=["admin_user"])

demo_emails = [email for email, *_ in seed_users]
DetectionTask.objects.filter(user__email__in=demo_emails).exclude(organization=org).update(organization=org)
ReviewRequest.objects.filter(user__email__in=demo_emails).exclude(organization=org).update(organization=org)

expires = timezone.now() + timedelta(days=3650)
for code, role in (("PUB001", "publisher"), ("REV001", "reviewer")):
    obj, _ = InvitationCode.objects.get_or_create(code=code, defaults={"organization": org, "role": role, "expires_at": expires})
    obj.organization = org
    obj.role = role
    obj.is_used = False
    obj.expires_at = expires
    obj.save()
print("initialized admin, org admin, demo users, and invitation codes")
PY
python manage.py collectstatic --noinput || true

echo "== frontend build =="
export npm_config_registry=https://registry.npmmirror.com
for APP in "前端用户端:/data/vue-project" "前端管理端:/data/vue-project2"; do
  NAME="${APP%%:*}"
  TARGET="${APP#*:}"
  cd "$PROJECT/代码/前端/$NAME"
  cat > .env.production <<EOF
VITE_API_URL=$API_URL
VITE_WS_URL=$WS_URL
EOF
  if [ -f package-lock.json ]; then
    npm ci --registry=https://registry.npmmirror.com
  else
    npm install --registry=https://registry.npmmirror.com
  fi
  npm run build-only
  rm -rf "$TARGET"
  mkdir -p "$TARGET"
  cp -a dist/. "$TARGET/"
  if grep -R "127.0.0.1:8000" "$TARGET" >/dev/null 2>&1; then
    echo "$NAME production bundle still contains 127.0.0.1:8000" >&2
    exit 1
  fi
done

echo "== systemd services =="
cat >/etc/systemd/system/fake-backend.service <<EOF
[Unit]
Description=Academic Plagiarism Detector Django ASGI
After=network.target redis.service mariadb.service

[Service]
Type=simple
WorkingDirectory=$PROJECT/代码/后端/后端代码
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
Environment=AI_SERVICE_URL=http://127.0.0.1:8010
Environment=AI_SERVICE_TIMEOUT=1200
Environment=DJANGO_SETTINGS_MODULE=fake_image_detector.cloud_settings
Environment=DB_NAME=academic_plagiarism_detector
Environment=DB_USER=root
Environment=DB_PASSWORD=
Environment=DB_HOST=127.0.0.1
Environment=DB_PORT=3306
Environment=CORS_ALLOWED_ORIGINS=http://114.116.204.131,http://114.116.204.131:81
ExecStart=$PROJECT/代码/后端/后端代码/.venv/bin/daphne -b 127.0.0.1 -p 9000 fake_image_detector.asgi:application
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/fake-celery-ai.service <<EOF
[Unit]
Description=Academic Plagiarism Detector Celery AI Queue
After=network.target redis.service mariadb.service fake-backend.service

[Service]
Type=simple
WorkingDirectory=$PROJECT/代码/后端/后端代码
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
Environment=AI_SERVICE_URL=http://127.0.0.1:8010
Environment=AI_SERVICE_TIMEOUT=1200
Environment=DJANGO_SETTINGS_MODULE=fake_image_detector.cloud_settings
Environment=DB_NAME=academic_plagiarism_detector
Environment=DB_USER=root
Environment=DB_PASSWORD=
Environment=DB_HOST=127.0.0.1
Environment=DB_PORT=3306
ExecStart=$PROJECT/代码/后端/后端代码/.venv/bin/celery -A fake_image_detector.celery worker -Q ai --concurrency 1 --prefetch-multiplier 1 -n ai@%%h --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/fake-celery-cpu.service <<EOF
[Unit]
Description=Academic Plagiarism Detector Celery CPU Queue
After=network.target redis.service mariadb.service fake-backend.service

[Service]
Type=simple
WorkingDirectory=$PROJECT/代码/后端/后端代码
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
Environment=AI_SERVICE_URL=http://127.0.0.1:8010
Environment=AI_SERVICE_TIMEOUT=1200
Environment=DJANGO_SETTINGS_MODULE=fake_image_detector.cloud_settings
Environment=DB_NAME=academic_plagiarism_detector
Environment=DB_USER=root
Environment=DB_PASSWORD=
Environment=DB_HOST=127.0.0.1
Environment=DB_PORT=3306
ExecStart=$PROJECT/代码/后端/后端代码/.venv/bin/celery -A fake_image_detector.celery worker -Q cpu --concurrency 4 -n cpu@%%h --loglevel=info
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

cat >/etc/systemd/system/fake-ai-http.service <<EOF
[Unit]
Description=Academic Plagiarism Detector AI HTTP Service
After=network.target

[Service]
Type=simple
WorkingDirectory=$PROJECT/代码/AI服务/AI服务器代码
Environment=LANG=C.UTF-8
Environment=LC_ALL=C.UTF-8
ExecStart=$PROJECT/代码/后端/后端代码/.venv/bin/python ai_http_service.py --host 127.0.0.1 --port 8010
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

echo "== nginx =="
cat >/etc/nginx/conf.d/academic-plagiarism-detector.conf <<'EOF'
upstream django_academic_detector {
    server 127.0.0.1:9000;
}

server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    client_max_body_size 100M;
    root /data/vue-project;
    index index.html;

    location /static/ { alias /data/allstatic/; }
    location /media/ { alias /data/media/; }

    location ^~ /api/ {
        proxy_pass http://django_academic_detector;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 1200s;
        proxy_send_timeout 1200s;
    }

    location ^~ /admin/ {
        proxy_pass http://django_academic_detector;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://django_academic_detector;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 1200s;
    }

    location / { try_files $uri $uri/ /index.html; }
}

server {
    listen 81;
    server_name _;
    client_max_body_size 100M;
    root /data/vue-project2;
    index index.html;

    location ^~ /api/ {
        proxy_pass http://django_academic_detector;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 1200s;
        proxy_send_timeout 1200s;
    }

    location ^~ /admin/ {
        proxy_pass http://django_academic_detector;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://django_academic_detector;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 1200s;
    }

    location / { try_files $uri $uri/ /index.html; }
}
EOF

rm -f /etc/nginx/sites-enabled/default /etc/nginx/conf.d/default.conf /etc/nginx/conf.d/fake_image_detector.conf || true
nginx -t

echo "== restart services =="
systemctl daemon-reload
systemctl enable fake-ai-http fake-backend fake-celery-ai fake-celery-cpu
systemctl restart fake-ai-http
systemctl restart fake-backend
systemctl restart fake-celery-ai
systemctl restart fake-celery-cpu
systemctl restart nginx
sleep 5

echo "== status =="
systemctl --no-pager --full status fake-ai-http fake-backend fake-celery-ai fake-celery-cpu nginx | sed -n '1,240p' || true

echo "== health checks =="
curl -I --max-time 15 http://127.0.0.1/ | head
curl -I --max-time 15 http://127.0.0.1:81/ | head
curl -sS --max-time 15 http://127.0.0.1:8010/health || true
echo
curl -sS --max-time 20 http://127.0.0.1/api/admin-login/ -H 'Content-Type: application/json' -d '{"email":"admin@mail.com","password":"Admin@123456"}' | head -c 500 || true
echo
"""


def main() -> None:
    socket.setdefaulttimeout(30)
    make_archive()
    client = connect()
    try:
        run(client, "hostname; whoami; pwd; ls -la /data || true", timeout=60)
        upload(client)
        remote_script = "/tmp/deploy_academic_plagiarism_detector.sh"
        sftp = client.open_sftp()
        try:
            with sftp.file(remote_script, "w") as f:
                f.write(REMOTE_SCRIPT)
            sftp.chmod(remote_script, 0o755)
        finally:
            sftp.close()
        run(client, f"bash {remote_script}", timeout=3600)
    finally:
        client.close()


if __name__ == "__main__":
    main()
