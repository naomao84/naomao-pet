# 3D Model Assets

Place your Meshy.ai exported `ppong.glb` file here (`assets/ppong.glb`) or in the project root (`./ppong.glb`).

- **Supported Embedded Clips**: `Idle`, `Walk`, `Jump`, `Wave`, `Talk` (case-insensitive fuzzy matched, with automatic skeletal `THREE.AnimationClip` synthesis for any clip not embedded in the GLB).
- **Fallback Rig**: If `ppong.glb` is not yet placed on disk, `index.html` automatically builds a rigged 3D procedural **Ppong-ppong-i** matching the character turnaround sheet so the application runs immediately out of the box.

