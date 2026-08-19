# VRCVideoTester (`vrcvt`)

[![GitHub Release](https://img.shields.io/github/v/release/Bluscream/vrcvt?style=flat-square)](https://github.com/Bluscream/vrcvt)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**`vrcvt` (VRCVideoTester)** is an out-of-the-box, comprehensive diagnostic tool and benchmark suite for testing **VRChat video player compatibility on Linux (Proton)**.

It measures, tests, and diagnoses video playback across installed Proton compatibility tools, environment variables, launch flags, and stream types without requiring you to launch VRChat or join game worlds manually.

---

## Key Features

- **Multi-Stream Testing**:
  - Bundled local 720p H.264 + AAC MP4 asset (`assets/sample.mp4`)
  - YouTube Video streams
  - YouTube Music / Audio streams
  - Real-Time Streaming Protocol (VRCDN `rtspt://`)
  - HTTP Live Streaming (`.m3u8` HLS)
  - Direct HTTPS MP4 streams
- **VRChat Mimicry**:
  - Passes VRChat's exact `yt-dlp` headers (`User-Agent`, `--no-check-certificates`, format selectors).
  - Invokes Windows Media Foundation (`IMFSourceResolver`, `IMFSourceReader`) directly via C++ harness (`wmf_test.exe`).
- **Timing & Retry Metrics**:
  - High-precision execution timings (in milliseconds) for `yt-dlp` resolution, WMF startup, and stream creation.
- **DNS & SSL Error Diagnostics & Solution Generator**:
  - Detects missing shared libraries (`libbz2.so.1.0`, `libavcodec.so.58`), GnuTLS TLS errors (`%COMPAT`), DNS resolution failures (`0x80072EE7`), and SSL certificate errors (`0x80072F8F`), automatically recommending actionable fixes.

---

## Quick Start

```bash
# Clone repository
git clone https://github.com/Bluscream/vrcvt.git
cd vrcvt

# Run quick diagnostic matrix
./vrcvt --quick

# Run full comprehensive matrix across all installed Proton versions
./vrcvt --all

# Test a custom video or stream URL
./vrcvt --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

## Building `wmf_test.exe` (Optional)

`assets/wmf_test.exe` comes pre-compiled in the repository. To recompile it from source:

```bash
x86_64-w64-mingw32-g++ src/wmf_test.cpp -o assets/wmf_test.exe -lmfplat -lmfreadwrite -lmfuuid -lole32
```

---

## Recommended Launch Options for VRChat on Linux

Based on empirical testing on Bazzite / Arch / Fedora:

```bash
WINEDLLOVERRIDES="iyuv_32=" G_TLS_GNUTLS_PRIORITY=NORMAL %command% --enable-avpro-in-proton --disable-hw-video-decoding
```

---

## License

MIT License. See `LICENSE` for details.
