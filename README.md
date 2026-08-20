# VRCVideoTester (`vrcvt`)

[![GitHub Release](https://img.shields.io/github/v/release/Bluscream/vrcvt?style=flat-square)](https://github.com/Bluscream/vrcvt)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)

**`vrcvt` (VRCVideoTester)** is a comprehensive, out-of-the-box diagnostic tool and compatibility benchmark suite for **VRChat video player playback on Linux (Proton)**.

It automatically measures, tests, and ranks video playback compatibility across all installed Proton tools, Steam Linux Runtime container environments, launch parameters, and video stream types without requiring you to launch VRChat or join game worlds manually.

---

## Quick VRChat Diagnostic Inspector (`check_vrc.sh`)

Run the standalone diagnostic inspector directly in your terminal from GitHub to inspect active VRChat processes, Proton tool matches, blacklisted environment variables, and log video status:

```bash
bash <(curl -sSL https://raw.githubusercontent.com/Bluscream/vrcvt/main/bin/check_vrc.sh)
```

---

## Key Features

- **Multi-Layered Compatibility Matrix**:
  - Tests permutations across `[Proton Tools] x [Steam Container Runtimes] x [Steam Launch Command Profiles] x [Test Streams]`
  - Supports `SteamLinuxRuntime_4` (Steam Linux Runtime 4.0 - Debian 12), `SteamLinuxRuntime_sniper` (Runtime 3.0), `soldier` (Runtime 2.0), and `HostNative`
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
  - Automatically evaluates all permutations and ranks them from **#1 BEST** to worst based on Pass Rate and Average Execution Time (fastest first).
- **Desktop Mode Try Mode (`--try`)**:
  - Benchmark matrix runs dynamically rank the best setup and can automatically trigger VRChat launch in **1024x768 (4:3) Desktop Debug Mode** directly into test world `wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1`.
- **Instant Launch Option (`--no-tests`)**:
  - Bypass the benchmark testing phase and directly trigger the `--try` VRChat desktop mode launch instantly.
- **Matrix Filtering Capabilities**:
  - Pass `--tool`, `--env`, `--cmd`, or `--url` to filter benchmark execution to specific configurations.

---

## Usage

```bash
# Clone repository
git clone https://github.com/Bluscream/vrcvt.git
cd vrcvt

# Run full multi-layered diagnostic matrix across all installed Proton versions and Container Runtimes
./bin/vrcvt

# Run a single compatibility test with exact Steam launch options string and container runtime
./bin/vrcvt --single --tool "GE-Proton9-25" --env "SteamLinuxRuntime_4" --cmd 'WINEDLLOVERRIDES="iyuv_32=" %command% --enable-hw-video-decoding' --url "ASSET_LOCAL"

# Run benchmark matrix filtered to a specific Proton tool and Container Runtime
./bin/vrcvt --tool "GE-Proton9-25" --env "SteamLinuxRuntime_4" --url "ASSET_LOCAL"

# Run benchmark matrix AND launch VRChat using #1 ranked configuration
./bin/vrcvt --try

# Launch VRChat using a specific rank number (e.g. #2 or #3 from saved results.json)
./bin/vrcvt --try 2
./bin/vrcvt --no-tests --try 3

# Skip benchmark tests and launch VRChat directly in Desktop Debug Mode
./bin/vrcvt --no-tests

# Output raw JSON results for automated tools
./bin/vrcvt --single --tool "GE-Proton9-25" --json
```

---

## CLI Options

| Argument | Description |
| :--- | :--- |
| *(default)* | Run multi-layered diagnostic matrix across all installed Proton tools, container runtimes, and test streams, saving ranked combinations to `results.json` |
| `--single` | Run a single stream compatibility test instead of the full diagnostic matrix |
| `--cmd <STRING>` | Specify or filter Steam launch command line string (e.g. `'WINEDLLOVERRIDES="iyuv_32=" %command% --enable-hw-video-decoding'`) |
| `--env <NAME>` | Specify or filter Steam Linux Runtime container environment (e.g. `'SteamLinuxRuntime_4'`, `'SteamLinuxRuntime_sniper'`, `'HostNative'`) |
| `--tool <NAME>` | Specify or filter Proton compatibility tools (e.g. `'GE-Proton9-25'`, `'Proton-GE RTSP Latest'`) |
| `--try [RANK]` | Launch VRChat in 1024x768 (4:3) Desktop Debug mode into test world (`wrld_a2fd9533-5c69-400b-a34e-ae0c11df99e1`) using target ranking (e.g. `--try 1`, `--try 2`) |
| `--no-tests` | Skip the benchmark testing phase and trigger direct `--try` VRChat desktop launch immediately |
| `--url <URL>` | Benchmark or filter target video stream URL |
| `--json` | Output results in raw JSON format |

---

## License

MIT License. See `LICENSE` for details.
