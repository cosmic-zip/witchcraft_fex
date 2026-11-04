echo "Install buildroot"
git clone https://gitlab.com/buildroot.org/buildroot.git --depth=1 --branch=master

echo "Install dependencies"
sudo apt update && sudo apt install -y which sed make binutils build-essential diffutils \
gcc g++ bash patch gzip bzip2 perl tar cpio unzip rsync file bc findutils gawk wget -y


for i in "$@"
do
case $i in
    -c=*|--copy=*)
	echo "This command will copy de default Cosmic OS config"
        cd buildroot && cp ../configs/nt_defconfig ./
    ;;
esac
done
