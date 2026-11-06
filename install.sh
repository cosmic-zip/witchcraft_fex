#!/bin/bash
echo "Install all packages for debian"
sudo apt update && sudo apt install -y \
  python3 \
  python3-pip \
  p7zip-full \
  build-essential \
  chromium \
  coreutils \
  curl \
  dirb \
  dnsenum \
  dnsutils \
  file \
  foremost \
  freeglut3-dev \
  git \
  htop \
  iftop \
  iproute2 \
  iptables \
  iputils-ping \
  kakoune \
  libc-bin \
  libatm1t64 \
  libatomic1 \
  libayatana-appindicator3-dev \
  libclang-dev \
  libclang1-18 \
  libglu1-mesa \
  libimage-exiftool-perl \
  libllvm15t64 \
  liboss4-salsa-asound2 \
  libssl-dev \
  libwebkit2gtk-4.1-dev \
  libxdo-dev \
  librsvg2-dev \
  lsof \
  lua5.4 \
  ngrep \
  nmap \
  openssh-server \
  openssl \
  pkg-config \
  qemu-system-x86 \
  qemu-utils \
  ruby \
  steghide \
  tor \
  traceroute \
  tree \
  virt-manager \
  wget \
  whois \
  xattr \
  xxd \
  bash \
  dc3dd \
  macchanger \
  bluez \
  tcpdump \
  hashcat \
  foremost \
  iptables \
  ftp \
  smbclient \
  wipe \
  ssh \
  sshpass \
  jq \
  hydra \
  john \
  sqlmap \
  nikto \
  gobuster \
  docker.io \
  docker-compose \
  clamav \
  clamav-daemon \
  cmake \
  gcc \
  make \
  net-tools \
  postgresql-client \
  mariadb-client \
  redis-tools \
  sqlite3 \
  ca-certificates \
  gnupg \
  lsb-release \
  systemd \
  cron \
  procps \
  psmisc \
  arp-scan \
  netcat-openbsd

echo ""
echo "============================================="
echo "Base packages installation completed!"
echo "============================================="
echo ""

# ─── Instalações adicionais ──────────────────────────────────────────

echo "Installing additional tools manually..."

# Nuclei (via go)
echo ""
echo "Installing nuclei via go..."
if command -v go &> /dev/null; then
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
    echo "nuclei installed in ~/go/bin/ - add to PATH if needed"
else
    echo "Go not found. Install Go first: sudo apt install golang-go"
fi

# WPScan (via gem)
echo ""
echo "Installing wpscan via gem..."
sudo gem install wpscan

# Metasploit (via snap ou curl)
echo ""
echo "Metasploit:"
echo "  Option 1 (snap): sudo snap install metasploit-framework"
echo "  Option 2 (curl): curl https://raw.githubusercontent.com/rapid7/metasploit-omnibus/master/config/templates/metasploit-framework-wrappers/msfupdate.erb > msfinstall && chmod 755 msfinstall && ./msfinstall"

# hcxpcapngtool / hcxtools
echo ""
echo "Installing hcxtools (includes hcxpcapngtool)..."
sudo apt install -y hcxtools 2>/dev/null || {
    echo "hcxtools not in repos, installing from source..."
    git clone https://github.com/ZerBea/hcxtools.git /tmp/hcxtools
    cd /tmp/hcxtools
    make -j$(nproc)
    sudo make install
    cd -
}

# ngrok
echo ""
echo "ngrok needs manual installation:"
echo "  wget https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-linux-amd64.tgz"
echo "  tar xvzf ngrok-*.tgz -C /usr/local/bin"
echo "  Or use snap: sudo snap install ngrok"

sudo snap install docker metasploit-framework ngrok --assume-yes

echo ""
echo "============================================="
echo "All installations completed!"
echo "Check the messages above for tools that need manual steps."
echo "============================================="

