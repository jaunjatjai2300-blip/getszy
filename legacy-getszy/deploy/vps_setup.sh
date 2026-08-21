#!/bin/bash
set -e

echo "🚀 Starting Getszy Production Deployment..."

# 1. Install Docker & Docker Compose if missing
if ! command -v docker &> /dev/null; then
    echo "📦 Installing Docker..."
    curl -fsSL https://get.docker.com -o get-docker.sh
    sudo sh get-docker.sh
    sudo usermod -aG docker $USER
fi

if ! command -v docker compose &> /dev/null; then
    echo "📦 Installing Docker Compose..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
fi

# 2. Setup Directory
DEPLOY_DIR="$HOME/getszy-production"
mkdir -p "$DEPLOY_DIR"
cd "$DEPLOY_DIR"

# 3. Clone or Update Repository
if [ ! -d ".git" ]; then
    echo "📥 Cloning repository..."
    git clone -b release/getszy-production-hardening https://github.com/jaunjatjai2300-blip/getszy.git .
else
    echo "🔄 Updating repository..."
    git fetch origin
    git checkout release/getszy-production-hardening
    git pull origin release/getszy-production-hardening
fi

# 4. Environment Configuration
if [ ! -f ".env" ]; then
    echo "📝 Creating .env template..."
    cat > .env <<EOF
DOMAIN=yourdomain.com
PUBLIC_URL=https://yourdomain.com
JWT_SECRET=$(openssl rand -hex 32)
INTEGRATION_ENCRYPTION_KEY=$(openssl rand -base64 32)
BACKUP_ENCRYPTION_KEY=$(openssl rand -base64 32)
GRAFANA_PASSWORD=$(openssl rand -hex 12)
ALERT_WEBHOOK_URL=https://your-alert-sink.com/webhook

SEED_ADMIN_EMAIL=admin@yourdomain.com
SEED_ADMIN_PASSWORD=$(openssl rand -hex 12)
SEED_CUSTOMER_EMAIL=customer@yourdomain.com
SEED_CUSTOMER_PASSWORD=$(openssl rand -hex 12)

# AI Providers
LLM_PROVIDER=groq
GROQ_API_KEY=your_groq_key_here
EOF
    echo "⚠️  Action Required: Please edit the .env file and add your real API keys!"
    echo "    Command: nano .env"
fi

# 5. Launch Services
echo "🏗️  Building and launching services..."
sudo docker compose pull
sudo docker compose up -d --build --remove-orphans

# 6. Launch Monitoring
echo "📊 Launching monitoring stack..."
sudo docker compose -f docker-compose.monitoring.yml up -d --remove-orphans

echo "✅ Deployment complete!"
echo "🔍 Check status with: sudo docker compose ps"
echo "🌐 Your API should be live at: https://yourdomain.com/api/health"
