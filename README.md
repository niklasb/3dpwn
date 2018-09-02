# VirtualBox 3D PoCs & exploits

*Author*: Niklas Baumstark ([@_niklasb](https://twitter.com/_niklasb))

[Overview article](https://phoenhex.re/2018-07-27/better-slow-than-sorry).

## Exploits

See the subdirectories other than `lib`.

## Library

`lib/hgcm.py` and `lib/chromium.py` provide high-level access to the HGCM interface and
to the `VBoxSharedCrOpenGL` service, via `VBoxGuest` IOCTLs.
`chromium.py` can be used to very easily experiment with Chromium from Python
inside the guest. I used it to build a very simple, completely dumb fuzzer that
found multiple trivial crashes in minutes.
