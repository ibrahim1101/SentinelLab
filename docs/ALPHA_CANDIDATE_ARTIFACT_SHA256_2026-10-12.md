# SentinelLab alpha candidate — verified artifact SHA-256 (2026-10-12)

**Status: technical checksum evidence only, not release approval.** Hashes below were computed from the installer payloads *inside downloaded GitHub Actions artifact ZIP files*. They do not represent the currently attached draft release assets unless independently matched.

| Target | Actions run / source commit | Artifact ID | Installer path inside artifact | SHA-256 |
| --- | --- | --- | --- | --- |
| Windows x64 | [38289907035](https://github.com/ibrahim1101/SentinelLab/actions/runs/38289907035) / `d2966620` | `11764609407` | `SentinelLab_0.1.0_x64-setup.exe` | `f283a60452f9f78c71a279bfe2d06f770cfcd02d5def5227b74f9306ee9221a8` |
| Linux x64 AppImage | [38289916624](https://github.com/ibrahim1101/SentinelLab/actions/runs/38289916624) / `efb43f43` | `11765541240` | `appimage/SentinelLab_0.1.0_amd64.AppImage` | `35d227a7d36970b39cacc89d89e1c0f0a6c066be9c5cf7f535844f2613b74b05` |
| Linux x64 DEB | same Linux/macOS run / `efb43f43` | `11765541240` | `deb/SentinelLab_0.1.0_amd64.deb` | `5d20a3d8298f9fcc7779382ca407bb73775e4f64023d13b5a8c3daa5872db729` |
| macOS Intel | same Linux/macOS run / `efb43f43` | `11766640882` | `dmg/SentinelLab_0.1.0_x64.dmg` | `033b8fc046a9f78c43b1d8029a2656d155e1df2fc2be8fde991b03f227070a10` |
| macOS Apple Silicon | same Linux/macOS run / `efb43f43` | `11764584236` | `dmg/SentinelLab_0.1.0_aarch64.dmg` | `9fbd961051b5ec6ade6885f2bc76777d43d7997ca408c4d39e167b9ec4ab15e0` |

**Important:** These are from two distinct source commits (Windows vs Linux/macOS). Before release, prefer a frozen commit and a full fresh cross-platform build from that exact SHA, with new checksums and a matching release checksum manifest. No claim is made about signing, runtime execution, or third-party licensing.
