# Desktop applications pack

- Choose cross-platform/runtime only after assessing OS target, offline needs, installer/updates and native APIs.
- For Electron/Tauri, separate renderer from privileged processes. Apply least privilege and safe IPC.
- Test packaging, file-system permissions, migration/backup restore, multi-language UI, and Windows path behavior.
- Never store user secrets unencrypted in client-visible files.
