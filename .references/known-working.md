# Verified Working VRChat Compatibility Configurations

This document tracks verified configurations that have been empirically validated to pass video decoding and stream playback tests in VRChat under Linux / Bazzite.

---

## 1. Verified Working Combination: `Proton-GE RTSP Latest` (Out-of-the-Box)

- **Proton Compatibility Tool**: `Proton-GE RTSP Latest`
- **Environment Variables**: *None required (Clean environment)*
- **VRChat Launch Command**: `%command% --enable-avpro-in-proton`
- **Verified Result**: `PASS (Player Latency: 264.1ms | YouTube HLS Latency: 1356ms)`
- **Container Runtime**: `SteamLinuxRuntime_4` (Steam Linux Runtime 4.0 / AppId 4183110)
- **Note**: Confirmed 100% working in live VRChat sessions and verified in 1:1 Unity Standalone Harness (`VRChatVideoTester.exe`). Bundles patched AVPro GStreamer video shims.

---

## 2. Verified Working Combination: `GE-Proton9-25` + HW Decoding

- **Proton Compatibility Tool**: `GE-Proton9-25`
- **Environment Variables**: `WINEDLLOVERRIDES="iyuv_32="`
- **VRChat Launch Command**: `%command% --enable-hw-video-decoding`
- **Verified Result**: `PASS (Latency: 2015.4ms | HRESULT: 0x00000000)`
- **Container Runtime**: `SteamLinuxRuntime_sniper` (Steam Linux Runtime 3.0 - Sniper / AppId 1628350)
- **Note**: Confirmed working in live VRChat sessions.
