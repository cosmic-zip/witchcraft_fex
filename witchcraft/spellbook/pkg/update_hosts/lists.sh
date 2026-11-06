echo "updating ip reputation lists"
wget -O spellbook/hosts/adware_plus_malware.hosts https://raw.githubusercontent.com/StevenBlack/hosts/master/hosts
wget -O spellbook/hosts/fakenews.hosts https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/fakenews-only/hosts
wget -O spellbook/hosts/gambling.hosts https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/gambling-only/hosts
wget -O spellbook/hosts/porn.hosts https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/porn-only/hosts
wget -O spellbook/hosts/social.hosts https://raw.githubusercontent.com/StevenBlack/hosts/master/alternates/social-only/hosts

echo "updating baguys lists"
wget -O spellbook/osint/ip/ci-badguys.txt https://cinsscore.com/list/ci-badguys.txt

echo "downloading tldr pages"
wget -qO tldr-main.zip https://github.com/tldr-pages/tldr/archive/refs/heads/main.zip

# echo "unziping tldr pages and deleting tldr-main.zip"
# unzip -q tldr-main.zip "*pages*" && rm -rf tldr-main.zip 
# echo "creating new folder called tldr"
# mkdir -p spellbook/tldr
# echo "moving tldr-main to spellbook/tldr"
# mv tldr-main spellbook/tldr 
