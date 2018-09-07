# VirtualBox 3D PoCs & exploits

*Author*: [@_niklasb](https://twitter.com/_niklasb)

[Overview article](https://phoenhex.re/2018-07-27/better-slow-than-sorry).

[License](https://github.com/niklasb/3dpwn/blob/master/LICENSE)

## Exploits

See the subdirectories other than `lib`.

## Debug build

For Arch Linux, you can use the provided PKGBUILD in `archpkg` to get a debug version of
5.2.18, with the 3D security fixes from July 2018 reverted.

## Library

`lib/hgcm.py` and `lib/chromium.py` provide high-level access to the HGCM interface and
to the `VBoxSharedCrOpenGL` service, via `VBoxGuest` IOCTLs.
`chromium.py` can be used to very easily experiment with Chromium from Python
inside the guest. I used it to build a very simple, completely dumb fuzzer that
found multiple trivial crashes in minutes.
