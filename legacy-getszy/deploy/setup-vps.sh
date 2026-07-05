#!/usr/bin/env bash
# One-shot VPS bootstrap for getszy.com on AlmaLinux 9
# Run as root.  curl -fsSL <url>/setup-vps.sh | bash
# Or: ssh root@<vps> 'bash -s' < setup-vps.sh

set -euo pipefail

echo "==> Updating system"
dnf -y update

echo "==> Installing base tools"
dnf -y install epel-release
dnf -y install git curl wget vim htop firewalld unzip tar policycoreutils-python-utils

echo "==> Enabling firewall + opening 22, 80, 443"
systemctl enable --now firewalld
firewall-cmd --permanent --add-service=ssh
firewall-cmd --permanent --add-service=http
firewall-cmd --permanent --add-service=https
firewall-cmd --reload

echo "==> Installing Docker CE"
dnf -y install dnf-plugins-core
dnf config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker

echo "==> Adding swap (8GB) if missing (helps when models load)"
if ! swapon --show | grep -q .; then
  fallocate -l 8G /swapfile
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "==> Installing Ollama (native, will run on host:11434)"
curl -fsSL https://ollama.com/install.sh | sh
systemctl enable --now ollama

echo "==> Pulling light models (background — large downloads)"
ollama pull llama3.2:3b   || true
ollama pull qwen2.5:7b    || true
# Optional heavy code model (slow on CPU): ollama pull qwen2.5-coder:7b

echo "==> Done. Reboot recommended (optional)."
echo ""
echo "NEXT STEPS:"
echo "  1) cd /opt && git clone <your-repo>.git getszy && cd getszy"
echo "  2) cp .env.example .env  &&  vim .env   # fill secrets"
echo "  3) docker compose up -d --build"
echo "  4) Point getszy.com DNS A record to this server's IP"
echo "  5) Caddy will fetch SSL automatically once DNS resolves."
