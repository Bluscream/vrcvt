# VRCVideoTester (`vrcvt`)

[![GitHub Release](https://img.shields.io/github/v/release/Bluscream/vrcvt?style=flat-square)](https://github.com/Bluscream/vrcvt)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**`vrcvt` (VRCVideoTester)** is a comprehensive, out-of-the-box diagnostic tool and compatibility benchmark suite for **VRChat video player playback on Linux (Proton)**.

It automatically measures, tests, and ranks video playback compatibility across all installed Proton tools, launch parameters, environment flags, and video stream types without requiring you to launch VRChat or join game worlds manually.

---

## Key Features

- **Exhaustive Multi-Stream Diagnostic Matrix**:
  - Bundled local 720p H.264 + AAC MP4 asset (`assets/sample.mp4`)
  - YouTube Video streams (`https://www.youtube.com/...`)
  - YouTube Music / Audio streams (`https://music.youtube.com/...`)
  - Real-Time Streaming Protocol (VRCDN `rtspt://...`)
  - HTTP Live Streaming (`.m3u8` HLS)
  - Direct HTTPS MP4 streams
- **Automatic H.264 Payload Unlock**:
  - Verifies presence of Steam's H.264 codec payload (`mfh264enc.dll`) and auto-triggers `steam://unlockh264/` if missing.
- **Dynamic Configuration Ranking Engine**:
  - Automatically evaluates all `(Proton, Env)` permutations and ranks them from **#1 BEST** to worst based on Pass Rate and Average Execution Time (fastest first).
- **Desktop Mode Try Mode (`--try`)**:
  - Benchmark matrix runs dynamically rank the best setup and can automatically trigger VRChat launch in **1024x768 (4:3) Desktop Debug Mode** directly into test world `wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1`.
- **Instant Launch Option (`--no-tests`)**:
  - Bypass the benchmark testing phase and directly trigger the `--try` VRChat desktop mode launch instantly.
- **Detailed Suite Timing & Bottleneck Analysis**:
  - High-precision split timing for `yt-dlp` stream pre-resolution vs MediaFoundation C++ decoder execution (`WMF`) and container overhead.
- **Isolated Sandbox Prefix**:
  - Executes test harness inside `/tmp/vrcvt_sandbox_prefix` so Proton tool switches **never** touch or modify your real VRChat prefix data or Windows registry.
- **VRChat Native Mimicry**:
  - Passes VRChat's exact `yt-dlp` headers (`User-Agent: VRChat/2024.3.2`, format selectors).
  - Invokes Windows Media Foundation (`IMFSourceResolver`, `IMFSourceReader`) directly via C++ harness (`wmf_test.exe`).

---

## Usage

```bash
# Clone repository
git clone https://github.com/Bluscream/vrcvt.git
cd vrcvt

# Run full diagnostic benchmark matrix across all installed Proton versions
./bin/vrcvt

# Run benchmark matrix AND launch VRChat using #1 ranked configuration
./bin/vrcvt --try

# Launch VRChat using a specific rank number (e.g. #2 or #3 from saved results.json)
./bin/vrcvt --try 2
./bin/vrcvt --no-tests --try 3

# Run a single compatibility test with custom Proton tool and environment variables
./bin/vrcvt --single --tool "Proton-GE RTSP Latest" --env "WINEDLLOVERRIDES=iyuv_32=" --url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Skip benchmark tests and launch VRChat directly in Desktop Debug Mode
./bin/vrcvt --no-tests

# Output raw JSON results for automated tools
./bin/vrcvt --single --tool "GE-Proton9-25" --json
```

---

## CLI Options

| Argument | Description |
| :--- | :--- |
| *(default)* | Run mandatory diagnostic matrix across all installed Proton tools and test streams, saving ranked combinations to `results.json` |
| `--single` | Run a single stream compatibility test instead of the full diagnostic matrix |
| `--tool <NAME>` | Specify a target Proton tool name or path (e.g. `'Proton-GE RTSP Latest'`, `'GE-Proton9-25'`) |
| `--env <KEY=VAL>` | Pass custom environment variables (e.g. `--env WINEDLLOVERRIDES=iyuv_32= --env G_TLS_GNUTLS_PRIORITY=NORMAL`) |
| `--try [RANK]` | Launch VRChat in 1024x768 (4:3) Desktop Debug mode into test world (`wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1`) using target ranking (e.g. `--try 1`, `--try 2`, `--try 3`) |
| `--no-tests` | Skip the benchmark testing phase and trigger direct `--try` VRChat desktop launch immediately |
| `--url <URL>` | Benchmark a specific custom stream or video URL |
| `--json` | Output results in raw JSON format |

---

## Building `wmf_test.exe` (Optional)

`assets/wmf_test.exe` comes pre-compiled in the repository. To recompile it from source:

```bash
x86_64-w64-mingw32-g++ src/wmf_test.cpp -o assets/wmf_test.exe -lmfplat -lmfreadwrite -lmfuuid -lole32
```

---

## License

MIT License. See `LICENSE` for details.
