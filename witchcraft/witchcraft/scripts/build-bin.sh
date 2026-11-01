nuitka --onefile \
       --static-libpython=yes \
       --include-package=auxiliary \
       --lto=yes \
       --remove-output \
       main.py \
       && mv nettraveler.bin nettraveler