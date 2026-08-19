# Verified Working VRChat Compatibility Configurations

This document tracks verified configurations that have been empirically validated to pass video decoding and stream playback tests in VRChat under Linux / Bazzite.

---

## 1. Verified Working Combination: `GE-Proton9-25` + HW Decoding

- **Proton Compatibility Tool**: `GE-Proton9-25`
- **VRChat Launch Command**: `WINEDLLOVERRIDES="iyuv_32=" %command% --enable-hw-video-decoding`
- **Verified Result**: `PASS (Latency: 2015.4ms | HRESULT: 0x00000000)`
- **Container Runtime**: `SteamLinuxRuntime_sniper` (Steam Linux Runtime 3.0 - Sniper / AppId 1628350)
- **Note**: Confirmed working in live VRChat sessions.
