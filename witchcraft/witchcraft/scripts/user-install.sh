#!/usr/bin/env bash
set -e

# Create installation directory
sudo mkdir -p /opt/witchcraft
sudo chown -R $USER:$USER /opt/witchcraft

# Locate and extract tar.gz file
TAR_FILE=""
if [[ -f witchcraft_lite.tar.gz ]]; then
    TAR_FILE="witchcraft_lite.tar.gz"
elif [[ -f witchcraft_full.tar.gz ]]; then
    TAR_FILE="witchcraft_full.tar.gz"
else
    echo "[!] No Witchcraft tar.gz file found in current directory."
    exit 1
fi

echo "[+] Extracting $TAR_FILE to /opt/witchcraft..."
tar -xzvf "$TAR_FILE" -C /opt/witchcraft

# Move binary to /usr/local/bin (better than /bin)
sudo mv /opt/witchcraft/dist/witchcraftfex /usr/local/bin/

# Environment instruction
echo "[+] Installation complete."
echo "Add the following to your shell configuration to set NT_DATAROOT:" 
echo "    export NT_DATAROOT=/opt/witchcraft/dist/spellbook"
