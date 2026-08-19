# Verified Working VRChat Compatibility Configurations

This document tracks verified configurations that have been empirically validated to pass video decoding and stream playback tests in VRChat under Linux / Bazzite.

---

## 1. Verified Working Combination: `GE-Proton9-25` + HW Decoding

- **Proton Compatibility Tool**: `GE-Proton9-25`
- **Environment Variables**: `WINEDLLOVERRIDES="iyuv_32="`
- **VRChat Launch Arguments**: `%command% --enable-hw-video-decoding`
- **Verified Result**: `PASS (Latency: 2015.4ms | HRESULT: 0x00000000)`
- **Container Runtime**: `SteamLinuxRuntime_4` (Steam Linux Runtime 4.0 - Debian 12)
- **Note**: Confirmed working in live VRChat sessions and verified in `vrcvt` test harness.

---

## 2. Verified Working Combination: `Proton-GE RTSP Latest`

- **Proton Compatibility Tool**: `Proton-GE RTSP Latest`
- **Environment Variables**: `WINEDLLOVERRIDES="iyuv_32=" G_TLS_GNUTLS_PRIORITY=NORMAL`
- **VRChat Launch Arguments**: `%command% --enable-avpro-in-proton --disable-hw-video-decoding`
- **Verified Result**: `PASS (Latency: 3370.7ms | HRESULT: 0x00000000)`
- **Container Runtime**: `SteamLinuxRuntime_4` / `SteamLinuxRuntime_sniper`
- **Note**: Bundles patched GStreamer and WMF libraries for AVPro video stream decoding.
