#!/bin/bash
# ONE-TIME SERVER SETUP for AuthApp on Ubuntu 24.04 LTS.
#
# Easiest way: paste this whole file into the "User data" box when you launch the EC2
# instance (Advanced details). It then runs automatically, once, as root, on first boot.
# Or run it by hand:   sudo bash server_setup.sh
#
# It installs what the app needs, creates a locked-down service user, a private secret
# key, and a systemd service. The first pipeline run then deploys the application itself.
set -euxo pipefail
export DEBIAN_FRONTEND=noninteractive

apt-get update -y
apt-get install -y python3 python3-venv python3-pip unzip curl ca-certificates

# AWS CLI v2 (used by the deploy script to read builds from S3)
if [ ! -x /usr/local/bin/aws ]; then
  cd /tmp
  curl -fsSL "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o awscliv2.zip
  unzip -q awscliv2.zip
  ./aws/install
  rm -rf aws awscliv2.zip
fi

# Service user and folders. The database lives in /opt/authapp/data, outside the releases.
id authapp >/dev/null 2>&1 || useradd --system --home-dir /opt/authapp --shell /usr/sbin/nologin authapp
mkdir -p /opt/authapp/releases /opt/authapp/data /opt/authapp/tmp
chown -R authapp:authapp /opt/authapp/data

# Private settings for the app (created once, never overwritten)
if [ ! -f /etc/authapp.env ]; then
  SECRET="$(python3 -c 'import secrets; print(secrets.token_urlsafe(48))')"
  cat > /etc/authapp.env <<ENVEOF
SECRET_KEY=${SECRET}
AUTH_DB_PATH=/opt/authapp/data/users.db
PYTHONDONTWRITEBYTECODE=1
ENVEOF
  chmod 600 /etc/authapp.env
fi

# systemd service: starts on boot, restarts if it crashes, listens on port 80
cat > /etc/systemd/system/authapp.service <<'UNITEOF'
[Unit]
Description=AuthApp (FastAPI multi-tenant login and registration)
After=network.target

[Service]
Type=simple
User=authapp
Group=authapp
WorkingDirectory=/opt/authapp/current
EnvironmentFile=/etc/authapp.env
ExecStart=/opt/authapp/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 80
Restart=on-failure
RestartSec=3
AmbientCapabilities=CAP_NET_BIND_SERVICE
CapabilityBoundingSet=CAP_NET_BIND_SERVICE
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
UNITEOF

systemctl daemon-reload
systemctl enable authapp   # it starts after the first deployment creates /opt/authapp/current

echo "AuthApp server setup finished at $(date)" > /var/log/authapp-setup-done
