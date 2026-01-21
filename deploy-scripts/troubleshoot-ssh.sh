#!/bin/bash
# ============================================================================
# SSH Connection Troubleshooting Script for Digital Ocean Droplet
# ============================================================================
# This script helps diagnose SSH connectivity issues
# ============================================================================

set -e

echo "============================================================================"
echo "  SSH Connection Troubleshooting for CodeVault Deployment"
echo "============================================================================"
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

DROPLET_IP="165.227.76.219"
SSH_KEY="$HOME/.ssh/id_ed25519"
DOMAIN="api.codevault.parth7.me"

# ============================================================================
# Test 1: Network Connectivity
# ============================================================================
echo "Test 1: Checking basic network connectivity..."
if command -v ping &> /dev/null; then
    if timeout 5 ping -c 3 "$DROPLET_IP" &> /dev/null 2>&1; then
        echo -e "${GREEN}✓ Droplet is reachable via ping${NC}"
    else
        echo -e "${RED}✗ Droplet is NOT reachable via ping${NC}"
        echo "  This could mean:"
        echo "  - Droplet is powered off"
        echo "  - Firewall is blocking ICMP"
        echo "  - Network issue"
    fi
else
    echo -e "${YELLOW}⚠ Ping command not available (Windows limitation)${NC}"
fi
echo ""

# ============================================================================
# Test 2: Port 22 (SSH) Accessibility
# ============================================================================
echo "Test 2: Checking if SSH port (22) is open..."
if timeout 10 bash -c "cat < /dev/null > /dev/tcp/$DROPLET_IP/22" 2>/dev/null; then
    echo -e "${GREEN}✓ Port 22 is OPEN and accepting connections${NC}"
else
    echo -e "${RED}✗ Port 22 is CLOSED or unreachable${NC}"
    echo "  This means:"
    echo "  - SSH service is not running"
    echo "  - Droplet is powered off"
    echo "  - Firewall is blocking port 22"
    echo ""
    echo -e "${YELLOW}Solution: Use Digital Ocean web console to start SSH${NC}"
fi
echo ""

# ============================================================================
# Test 3: SSH Key Exists
# ============================================================================
echo "Test 3: Checking SSH key..."
if [ -f "$SSH_KEY" ]; then
    echo -e "${GREEN}✓ SSH private key found at $SSH_KEY${NC}"
    
    if [ -f "${SSH_KEY}.pub" ]; then
        echo -e "${GREEN}✓ SSH public key found${NC}"
        echo ""
        echo "Your public key (add this to droplet):"
        echo "----------------------------------------"
        cat "${SSH_KEY}.pub"
        echo "----------------------------------------"
    else
        echo -e "${YELLOW}⚠ Public key not found at ${SSH_KEY}.pub${NC}"
    fi
else
    echo -e "${RED}✗ SSH key NOT found at $SSH_KEY${NC}"
    echo "  Generate a new key with:"
    echo "  ssh-keygen -t ed25519 -C 'your_email@example.com'"
fi
echo ""

# ============================================================================
# Test 4: SSH Connection Attempt
# ============================================================================
echo "Test 4: Attempting SSH connection..."
echo "Running: ssh -i $SSH_KEY -o ConnectTimeout=10 -o BatchMode=yes root@$DROPLET_IP echo 'Connected'"
if ssh -i "$SSH_KEY" -o ConnectTimeout=10 -o BatchMode=yes root@"$DROPLET_IP" echo 'Connected' 2>/dev/null; then
    echo -e "${GREEN}✓ SSH connection SUCCESSFUL!${NC}"
    echo ""
    echo "Getting server information..."
    ssh -i "$SSH_KEY" root@"$DROPLET_IP" "echo 'Hostname: \$(hostname)'; echo 'OS: \$(lsb_release -d | cut -f2)'; echo 'Uptime: \$(uptime -p)'"
else
    ERROR_MSG=$(ssh -i "$SSH_KEY" -o ConnectTimeout=10 root@"$DROPLET_IP" echo 'Connected' 2>&1 || true)
    echo -e "${RED}✗ SSH connection FAILED${NC}"
    echo ""
    echo "Error message:"
    echo "----------------------------------------"
    echo "$ERROR_MSG"
    echo "----------------------------------------"
    echo ""
    
    if echo "$ERROR_MSG" | grep -q "Connection refused"; then
        echo -e "${YELLOW}Diagnosis: SSH service is not running or not configured${NC}"
        echo ""
        echo "Solutions:"
        echo "1. Use Digital Ocean web console to access the droplet"
        echo "2. Start SSH service: systemctl start ssh"
        echo "3. Add your SSH key to ~/.ssh/authorized_keys"
        
    elif echo "$ERROR_MSG" | grep -q "Connection timed out"; then
        echo -e "${YELLOW}Diagnosis: Droplet is unreachable (powered off or firewall)${NC}"
        echo ""
        echo "Solutions:"
        echo "1. Check Digital Ocean dashboard if droplet is powered on"
        echo "2. Check firewall settings (allow port 22)"
        
    elif echo "$ERROR_MSG" | grep -q "Permission denied"; then
        echo -e "${YELLOW}Diagnosis: SSH key not authorized${NC}"
        echo ""
        echo "Solutions:"
        echo "1. Use Digital Ocean web console"
        echo "2. Add your public key to ~/.ssh/authorized_keys on the server"
        
    else
        echo -e "${YELLOW}Diagnosis: Unknown error${NC}"
    fi
fi
echo ""

# ============================================================================
# Test 5: DNS Resolution (if configured)
# ============================================================================
echo "Test 5: Checking DNS configuration..."
if command -v nslookup &> /dev/null; then
    DNS_RESULT=$(nslookup "$DOMAIN" 2>&1 || true)
    if echo "$DNS_RESULT" | grep -q "$DROPLET_IP"; then
        echo -e "${GREEN}✓ DNS configured correctly${NC}"
        echo "  $DOMAIN → $DROPLET_IP"
    else
        echo -e "${YELLOW}⚠ DNS not configured or not propagated yet${NC}"
        echo "  Expected: $DOMAIN → $DROPLET_IP"
        echo "  Current result:"
        echo "$DNS_RESULT" | grep -A2 "answer" || echo "  No DNS record found"
    fi
else
    echo -e "${YELLOW}⚠ nslookup not available${NC}"
fi
echo ""

# ============================================================================
# Test 6: HTTP/HTTPS Connectivity (future test)
# ============================================================================
echo "Test 6: Checking HTTP/HTTPS endpoints (future)..."
if command -v curl &> /dev/null; then
    if timeout 5 curl -s -o /dev/null -w "%{http_code}" "http://$DROPLET_IP" | grep -q "200\|301\|302"; then
        echo -e "${GREEN}✓ HTTP endpoint responding${NC}"
    else
        echo -e "${YELLOW}⚠ HTTP endpoint not responding (expected - backend not deployed yet)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ curl not available${NC}"
fi
echo ""

# ============================================================================
# Summary and Recommendations
# ============================================================================
echo "============================================================================"
echo "  Summary and Recommendations"
echo "============================================================================"
echo ""

# Try to determine primary issue
if ! timeout 10 bash -c "cat < /dev/null > /dev/tcp/$DROPLET_IP/22" 2>/dev/null; then
    echo -e "${RED}PRIMARY ISSUE: Port 22 is not accessible${NC}"
    echo ""
    echo "IMMEDIATE ACTION REQUIRED:"
    echo "1. Go to: https://cloud.digitalocean.com/droplets"
    echo "2. Find your droplet and click on it"
    echo "3. Check if it shows 'Active' (green indicator)"
    echo "4. If OFF: Click 'Power On' button"
    echo "5. Click 'Console' button (top right) to access web terminal"
    echo "6. Run these commands in the console:"
    echo ""
    echo "   mkdir -p ~/.ssh"
    echo "   echo 'YOUR_PUBLIC_KEY' >> ~/.ssh/authorized_keys"
    echo "   chmod 700 ~/.ssh"
    echo "   chmod 600 ~/.ssh/authorized_keys"
    echo "   systemctl start ssh"
    echo "   systemctl enable ssh"
    echo "   ufw allow 22/tcp"
    echo ""
elif [ ! -f "$SSH_KEY" ]; then
    echo -e "${YELLOW}Issue: SSH key not found${NC}"
    echo ""
    echo "Generate SSH key with:"
    echo "  ssh-keygen -t ed25519 -C 'your_email@example.com'"
else
    echo -e "${YELLOW}Issue: SSH key not authorized on droplet${NC}"
    echo ""
    echo "Add your public key to the droplet:"
    echo "1. Use Digital Ocean web console"
    echo "2. Copy your public key (shown above)"
    echo "3. Add to ~/.ssh/authorized_keys on the server"
fi

echo ""
echo "============================================================================"
echo "For detailed deployment instructions, see:"
echo "  - CodeVaultV1/deploy-scripts/DEPLOYMENT_GUIDE.md"
echo "  - CodeVaultV1/deploy-scripts/QUICKSTART.md"
echo "============================================================================"
