When using a PKGBUILD with `build_type=DEBUG`, make sure you have `OPTIONS=(!strip ...` in your `/etc/makepkg.conf` or else makepkg will strip the binaries automatically.
