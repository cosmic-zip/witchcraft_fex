#! /bin/bash
echo "[x] Setup Build"
nuitka --onefile \
       --static-libpython=yes \
       --include-package=auxiliary \
       --lto=yes \
       --remove-output \
       main.py \
       && mv main.bin witchcraftfex

echo "[x] Setup dist"
mkdir dist temp
mv spellbook/models/ temp/
mv spellbook/ dist/
mv witchcraftfex dist/
tar -czvf witchcraft_lite.tar.gz dist/
mv temp/models/ dist/spellbook/
tar -czvf witchcraft_full.tar.gz dist/

echo "[x] Cleanup"
mv dist/spellbook/ ./
rm -r temp/
mv witchcraft_lite.tar.gz dist/
mv witchcraft_full.tar.gz dist/
mv dist/witchcraftfex ./