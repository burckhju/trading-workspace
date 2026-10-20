# Playwright-Seccomp-Profil mit gezielter Chromium-Korrektur

Basis: Microsoft Playwright 1.63.0, Apache-2.0 (LICENSE.Playwright).
https://raw.githubusercontent.com/microsoft/playwright/v1.63.0/utils/docker/seccomp_profile.json

Original-SHA-256: cc3e61cabda6bbc1e53e54d27ba4d55a9d3be829b6dd1a596f4a7b31b1cc7849
Korrigierte SHA-256: ee5b24e7c69e303e8291aec15119661c6f6658dba5bddfd86d9579b83f872518
Änderungsdatum: 29.09.2026; Paket issuer-renderer-chroot-fix-v1.

Die einzige funktionale Änderung ist die Entfernung der Capability-Bedingung
CAP_SYS_CHROOT aus der vorhandenen SCMP_ACT_ALLOW-Regel für den Syscall chroot.
Chromium benötigt diesen Aufruf für ChrootToSafeEmptyDir in seiner Namespace-Sandbox.
Mit cap_drop: ALL wird die bisherige bedingte Regel vom Containerprofil nicht aktiviert.
Kernel-Capability- und Namespace-Prüfungen bleiben wirksam.

Alle übrigen Regeln bleiben unverändert. cap_drop: ALL, pwuser, read_only,
no-new-privileges und chromium_sandbox=True bleiben gesetzt. Es werden keine zusätzlichen
Container-Capabilities und kein SYS_ADMIN eingeräumt. Das Profil bleibt standardmäßig
SCMP_ACT_ERRNO; es wird weder auf unconfined noch auf no-sandbox umgestellt.

Bei Änderung dieses Profils den Renderer-Container beim Deployment ausdrücklich
neu erstellen, damit Docker den geänderten Profilinhalt lädt. Ein bloßer
Prozessneustart genügt dafür nicht. Siehe ISSUER_MONITORING_OPERATIONS.md.

Quellen:
https://chromium.googlesource.com/chromium/src/sandbox/+/refs/heads/main/linux/services/credentials.cc
https://docs.docker.com/engine/security/seccomp/
