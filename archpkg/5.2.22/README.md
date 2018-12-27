# VirtualBox debug build (Arch Linux)

This is a simple Arch Linux PKGBUILD to build a vulnerable version of
VirtualBox. It is actually 5.2.18 with the 3D acceleration security patches
from July 2018 reverted (see `015-revertogl.patch`).

## Usage

```bash
$ makepkg -sf
$ sudo pacman -U virtualbox{,-host-dkms}-5.2.18-*.pkg.tar.*
```

Then make sure to reload all drivers etc.
