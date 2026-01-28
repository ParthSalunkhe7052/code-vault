# Competitive Research

| Competitor | URL | Pricing | Key Features | Strengths | Weaknesses |
|------------|-----|---------|--------------|-----------|------------|
| **PyArmor** | [pyarmor.dashingsoft.com](https://pyarmor.dashingsoft.com/) | Free (limited), Pro ($99/dev), Group ($299) | Obfuscation, HWID locking, Expiration, Time bombs, JIT protection | Industry standard for Python obfuscation, extremely powerful, one-time purchase. | CLI only (hard to use for beginners), minimal licensing server support (mostly offline/static), "Pro" license is per-developer. |
| **Keygen.sh** | [keygen.sh](https://keygen.sh/) | Free tier, then usage-based ($199/mo+) | Licensing API, Entitlements, Device limits, Analytic | Best-in-class licensing API/manageability, language agnostic, enterprise ready. | Does **NOT** protect code (no compilation/obfuscation), expensive for small devs. |
| **Codeclose** | [codeclose.com](https://codeclose.com/) | Unknown (likely paid) | Obfuscation + Encryption + Licensing | Integrated solution similar to License Wrapper. | Less known, effectiveness of protection unclear compared to Nuitka. |
| **SourceDefender** | [sourcedefender.co.uk](https://sourcedefender.co.uk/) | Paid | Encrypts to .pyd/.so, Expiration | Strong protection (encryption), supports multiple platforms. | Licensing features are basic (time-based), less "SaaS-like" management. |
| **Nuitka / PyInstaller** | Open Source | Free | Compilation (Nuitka), Bundling (PyInstaller) | Free, widely used, Nuitka offers good protection (compilation to C). | **NO** built-in licensing/locking system. Developers must build their own auth/hwid logic. |

## Competitive Differentiation

**License Wrapper vs. Competitors**

1.  **Vs. PyArmor**: PyArmor is a tool, not a platform. You run it on your machine. License Wrapper is a "SaaS Platform" (with a self-hosted option) that manages the *clients* and *licenses* for you, while also handling the compilation. PyArmor protects the code well but doesn't give you a dashboard to see "User X just logged in". License Wrapper does.
2.  **Vs. Keygen.sh**: Keygen handles the licenses perfectly but leaves code protection to you. License Wrapper does **both**: Protections (Nuitka + injection) AND Licensing (Dashboard/API).
3.  **Vs. DIY (Nuitka + Custom DB)**: This is what License Wrapper automates. It saves the developer 2-3 weeks of building their own auth server, HWID checker, and build script.

**Verdict**: License Wrapper occupies a "Niche Sweet Spot": **Integrated Compilation + Licensing for Python**. It's easier than PyArmor for licensing, and more protective than Keygen for code.
