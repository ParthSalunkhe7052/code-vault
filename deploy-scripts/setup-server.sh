#!/bin/bash
# ============================================================================
# CodeVault Server Setup Script for Digital Ocean Droplet
# ============================================================================
# This script sets up a fresh Ubuntu 22.04 droplet with everything needed
# to run the CodeVault backend API server.
#
# Usage: bash setup-server.sh
# ============================================================================

set -e  # Exit on any error

echo "============================================================================"
echo "  CodeVault Server Setup - Starting Installation"
echo "============================================================================"

# Color codes for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

log_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

log_info() {
    echo -e "${YELLOW}➜ $1${NC}"
}

log_error() {
    echo -e "${RED}✗ $1${NC}"
}

# ============================================================================
# Step 1: System Updates
# ============================================================================
log_info "Updating system packages..."
apt update -y
apt upgrade -y
log_success "System packages updated"

# ============================================================================
# Step 2: Install Essential Tools
# ============================================================================
log_info "Installing essential tools..."
apt install -y \
    curl \
    wget \
    git \
    vim \
    nano \
    htop \
    net-tools \
    ufw \
    ca-certificates \
    gnupg \
    lsb-release
log_success "Essential tools installed"

# ============================================================================
# Step 3: Install Docker
# ============================================================================
log_info "Installing Docker..."

# Remove old Docker versions if any
apt remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# Add Docker's official GPG key
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
chmod a+r /etc/apt/keyrings/docker.gpg

# Set up Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
apt update -y
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker
systemctl start docker
systemctl enable docker

# Verify Docker installation
docker --version
log_success "Docker installed successfully"

# ============================================================================
# Step 4: Configure Firewall (UFW)
# ============================================================================
log_info "Configuring firewall..."

# Reset UFW to default settings
ufw --force reset

# Default policies
ufw default deny incoming
ufw default allow outgoing

# Allow SSH (CRITICAL - don't lock yourself out!)
ufw allow 22/tcp comment 'SSH'

# Allow HTTP and HTTPS
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'

# Allow Docker API port (only needed for development, comment out in production)
# ufw allow 8000/tcp comment 'Docker API'

# Enable firewall
ufw --force enable

# Show status
ufw status numbered

log_success "Firewall configured"

# ============================================================================
# Step 5: Install Nginx
# ============================================================================
log_info "Installing Nginx..."
apt install -y nginx
systemctl start nginx
systemctl enable nginx
log_success "Nginx installed"

# ============================================================================
# Step 6: Install Certbot for SSL
# ============================================================================
log_info "Installing Certbot..."
apt install -y certbot python3-certbot-nginx
log_success "Certbot installed"

# ============================================================================
# Step 7: Install Python (for utility scripts)
# ============================================================================
log_info "Installing Python..."
apt install -y python3 python3-pip python3-venv
log_success "Python installed"

# ============================================================================
# Step 8: Create Application Directory Structure
# ============================================================================
log_info "Creating application directories..."
mkdir -p /opt/codevault
mkdir -p /var/log/codevault
mkdir -p /etc/codevault
log_success "Application directories created"

# ============================================================================
# Step 9: Set up Docker log rotation
# ============================================================================
log_info "Configuring Docker log rotation..."
cat > /etc/docker/daemon.json <<EOF
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
EOF
systemctl restart docker
log_success "Docker log rotation configured"

# ============================================================================
# Step 10: Create helper scripts
# ============================================================================
log_info "Creating helper scripts..."

# Deployment script
cat > /usr/local/bin/deploy-codevault <<'DEPLOY_SCRIPT'
#!/bin/bash
set -e

echo "Deploying CodeVault..."

# Navigate to repository
cd /root/codevault/CodeVaultV1

# Pull latest changes
git pull origin main

# Stop and remove old container
docker stop codevault-backend 2>/dev/null || true
docker rm codevault-backend 2>/dev/null || true

# Build new image
docker build -t codevault-backend:latest -f Dockerfile .

# Run new container
docker run -d \
  --name codevault-backend \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file /etc/codevault/.env \
  -v /opt/codevault/uploads:/app/server/uploads \
  codevault-backend:latest

# Wait for container to be healthy
sleep 5

# Check if container is running
if docker ps | grep -q codevault-backend; then
    echo "✓ CodeVault deployed successfully!"
    docker logs --tail 50 codevault-backend
else
    echo "✗ Deployment failed! Check logs:"
    docker logs codevault-backend
    exit 1
fi
DEPLOY_SCRIPT

chmod +x /usr/local/bin/deploy-codevault

# Logs script
cat > /usr/local/bin/codevault-logs <<'LOGS_SCRIPT'
#!/bin/bash
docker logs -f --tail 100 codevault-backend
LOGS_SCRIPT

chmod +x /usr/local/bin/codevault-logs

# Status script
cat > /usr/local/bin/codevault-status <<'STATUS_SCRIPT'
#!/bin/bash
echo "=== CodeVault Status ==="
echo ""
echo "Container Status:"
docker ps -a --filter name=codevault-backend --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "Resource Usage:"
docker stats codevault-backend --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}"
echo ""
echo "Recent Logs:"
docker logs --tail 20 codevault-backend
STATUS_SCRIPT

chmod +x /usr/local/bin/codevault-status

log_success "Helper scripts created"

# ============================================================================
# Final Summary
# ============================================================================
echo ""
echo "============================================================================"
echo -e "${GREEN}  Server Setup Complete!${NC}"
echo "============================================================================"
echo ""
echo "Next Steps:"
echo "  1. Configure DNS: Point api.codevault.parth7.me to this server's IP"
echo "  2. Create .env file: /etc/codevault/.env"
echo "  3. Clone repository: git clone <repo-url> /root/codevault"
echo "  4. Deploy application: deploy-codevault"
echo "  5. Configure SSL: certbot --nginx -d api.codevault.parth7.me"
echo ""
echo "Useful Commands:"
echo "  - deploy-codevault    : Deploy/redeploy the application"
echo "  - codevault-logs      : View application logs"
echo "  - codevault-status    : Check application status"
echo ""
echo "============================================================================"
