/**
 * Ppong-ppong-i 3D World RPG, Basecamp, Skirmish & Wave Siege Defense Subsystem (v2.0)
 * ====================================================================================
 * Designed by 10 3D Game Design Experts & 10 3D RPG/Defense Engineering Experts:
 *   1. 4 Multi-Worldview Real-Time Theme Engine (Fantasy / Cyberpunk / Sci-Fi / Cozy Island)
 *   2. Persistent 3D Mini Basecamp (4-Stage Growing Farm Plot + Mini Guardian Turret)
 *   3. 4-Tier 3D Evolving Hero Weapon + Crescent Slash Trail + Horn Homing Magic Bolts
 *   4. Procedural 3D Enemy Factory (Slime, Imp, Drone, Boss Golem/Dragon) + InstancedMesh Swarms
 *   5. Intermittent Desktop Skirmish (바탕화면 수호) & Wave Siege Defense Mini-Game (웨이브 디펜스)
 *   6. Mandatory Causality Loop: Auto Battle Bento Buffs (Farming+Fishing) + Turrets/Gear (Mining+Economy)
 *   7. Interactive Mouse Cursor Smite (마우스 협동 벼락 타격)
 */

export const WORLDVIEW_THEMES = {
  fantasy: {
    key: 'fantasy',
    name: '🌿 판타지 왕국 (Fantasy Kingdom)',
    badge: '🌿 판타지 왕국',
    hemiSky: 0xfffcf8,
    hemiGround: 0xd8dee9,
    keyColor: 0xfff8f0,
    rimColor: 0xe0f2fe,
    meadowTint: 0x22543d,
    meadowGlow: 0x86efac,
    portalColor: 0xa855f7,
    coreColor: 0x38bdf8,
    slashColor: 0xfacc15,
    isCozyNonViolent: false,
    enemies: {
      slime: { name: '버그 슬라임', color: 0x22c55e, eye: 0x111827 },
      imp: { name: '스팸 고블린', color: 0xef4444, eye: 0xfde047 },
      drone: { name: '다크 마법구체', color: 0xa855f7, eye: 0x38bdf8 },
      boss5: { name: '👑 트로이 목마 거신', color: 0xd97706, eye: 0xef4444 },
      boss10: { name: '👑 블루스크린 드래곤', color: 0x2563eb, eye: 0x22d3ee },
      boss15: { name: '👑 랜섬웨어 리치 로드', color: 0x7c3aed, eye: 0xf43f5e }
    }
  },
  cyberpunk: {
    key: 'cyberpunk',
    name: '🌃 사이버펑크 네온 (Cyberpunk Neon)',
    badge: '🌃 사이버펑크 네온',
    hemiSky: 0xe0f2fe,
    hemiGround: 0x1e1b4b,
    keyColor: 0xfdf4ff,
    rimColor: 0x22d3ee,
    meadowTint: 0x0f172a,
    meadowGlow: 0x22d3ee,
    portalColor: 0xf43f5e,
    coreColor: 0x22d3ee,
    slashColor: 0x22d3ee,
    isCozyNonViolent: false,
    enemies: {
      slime: { name: '글리치 데이터 블롭', color: 0x06b6d4, eye: 0xf43f5e },
      imp: { name: '넷러너 해커봇', color: 0xf43f5e, eye: 0x22d3ee },
      drone: { name: '바이러스 시큐리티 드론', color: 0xeab308, eye: 0xef4444 },
      boss5: { name: '👑 메가코프 스파이더 탱크', color: 0xec4899, eye: 0x22d3ee },
      boss10: { name: '👑 방화벽 파괴자 드래곤', color: 0x06b6d4, eye: 0xf43f5e },
      boss15: { name: '👑 AI 오버로드 메인프레임', color: 0xa855f7, eye: 0xfacc15 }
    }
  },
  scifi: {
    key: 'scifi',
    name: '🚀 스페이스 오디세이 (Space Odyssey)',
    badge: '🚀 스페이스 오디세이',
    hemiSky: 0xe0e7ff,
    hemiGround: 0x1e293b,
    keyColor: 0xf0f9ff,
    rimColor: 0x818cf8,
    meadowTint: 0x312e81,
    meadowGlow: 0xa5b4fc,
    portalColor: 0x6366f1,
    coreColor: 0x60a5fa,
    slashColor: 0x38bdf8,
    isCozyNonViolent: false,
    enemies: {
      slime: { name: '코스믹 아메바', color: 0x8b5cf6, eye: 0x38bdf8 },
      imp: { name: '제노모프 스카우트', color: 0x10b981, eye: 0xfacc15 },
      drone: { name: 'UFO 인터셉터', color: 0x60a5fa, eye: 0xf43f5e },
      boss5: { name: '👑 아스테로이드 메카 골렘', color: 0x64748b, eye: 0x38bdf8 },
      boss10: { name: '👑 성운 레비아탄', color: 0x4f46e5, eye: 0xf472b6 },
      boss15: { name: '👑 보이드 마더쉽 타이탄', color: 0x9333ea, eye: 0xfde047 }
    }
  },
  cozy: {
    key: 'cozy',
    name: '🌼 코지 힐링 아일랜드 (Cozy Island)',
    badge: '🌼 코지 힐링 아일랜드',
    hemiSky: 0xfffbeb,
    hemiGround: 0xfef3c7,
    keyColor: 0xfff7ed,
    rimColor: 0xfde68a,
    meadowTint: 0x15803d,
    meadowGlow: 0xfef08a,
    portalColor: 0xf472b6,
    coreColor: 0xfbbf24,
    slashColor: 0xf472b6,
    isCozyNonViolent: true,
    enemies: {
      slime: { name: '몽실 먼지뭉치', color: 0xf9a8d4, eye: 0x1f2937 },
      imp: { name: '장난꾸러기 도토리 요정', color: 0xfbbf24, eye: 0x1f2937 },
      drone: { name: '둥실 구름 솜사탕', color: 0xbae6fd, eye: 0xf472b6 },
      boss5: { name: '👑 거대 낮잠 곰인형', color: 0xd97706, eye: 0x1f2937 },
      boss10: { name: '👑 무지개 고래 풍선', color: 0x38bdf8, eye: 0xfde047 },
      boss15: { name: '👑 달콤 케이크 성채', color: 0xf472b6, eye: 0xfacc15 }
    }
  }
};

export function createWorldRPGDefenseSubsystem(ctx) {
  const {
    THREE,
    scene,
    camera,
    characterPivot,
    stageGroup,
    hemiLight,
    keyLight,
    backRimLight,
    pawFootprintMatTemplate,
    getRigBones,
    addBoneEulerOffset,
    playAnimation,
    triggerEmotionEmote,
    soloPlaySys
  } = ctx;

  const fxApi = soloPlaySys ? soloPlaySys.fxApi : null;
  const root = new THREE.Group();
  root.name = 'WorldRPGDefenseRoot';
  scene.add(root);

  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
  const outBack = (x) => { x = clamp01(x); const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const lerp = (a, b, t) => a + (b - a) * t;
  const rand = (a, b) => a + Math.random() * (b - a);
  const mat = (color, rough = 0.42, metal = 0.1, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal, ...extra });
  const glow = (color, opacity = 0.9) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, toneMapped: false });
  const mesh = (geo, m, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); return o; };

  // =========================================================================
  // 1. Global RPG State Mirror (Synced with Python pet_rpg_save.json)
  // =========================================================================
  const rpgState = {
    worldview: 'fantasy',
    workSafeMode: false,
    basecampVisible: true,
    petLevel: 1,
    petXP: 0,
    gold: 200,
    weaponEnhance: 0,
    weaponTier: 1, // 1..4 derived from weaponEnhance
    pickaxeTier: 1,
    rodTier: 1,
    wateringTier: 1,
    turrets: {
      barricade: 1,
      ballista: 0,
      frost: 0,
      arc: 0
    },
    bentos: {
      potato_fish: 1,
      trout_steak: 0,
      carp_stew: 0,
      star_emperor: 0
    },
    farm: {
      planted: true,
      growth: 0.35, // 0.0 -> 1.0
      watered: true,
      cropType: '튼튼 감자'
    },
    highestWave: 0
  };
  window.ppongRPGState = rpgState;

  // =========================================================================
  // 2. Persistent 3D Mini Basecamp (Left: 4-Stage Farm Plot, Right: Mini Turret)
  // =========================================================================
  const baseCampGroup = new THREE.Group();
  baseCampGroup.name = 'MiniBasecamp';
  stageGroup.add(baseCampGroup);

  // 2A. Left Mini Farm Plot (-0.64, 0, 0.24)
  const farmGroup = new THREE.Group();
  farmGroup.position.set(-0.64, 0.01, 0.24);
  baseCampGroup.add(farmGroup);

  const planterRim = mesh(new THREE.BoxGeometry(0.38, 0.06, 0.28), mat(0x92400e, 0.75), 0, 0.03, 0);
  const soilMesh = mesh(new THREE.BoxGeometry(0.34, 0.05, 0.24), mat(0x451a03, 0.95), 0, 0.04, 0);
  farmGroup.add(planterRim, soilMesh);

  const cropStalks = [];
  [-0.10, 0, 0.10].forEach((cx, i) => {
    const cg = new THREE.Group();
    cg.position.set(cx, 0.06, 0);
    const stem = mesh(new THREE.CylinderGeometry(0.008, 0.012, 0.16, 6), mat(0x16a34a, 0.6), 0, 0.08, 0);
    const leafL = mesh(new THREE.SphereGeometry(0.028, 8, 8), mat(0x22c55e, 0.5), -0.025, 0.09, 0);
    leafL.scale.set(1.4, 0.5, 0.8);
    const leafR = mesh(new THREE.SphereGeometry(0.028, 8, 8), mat(0x22c55e, 0.5), 0.025, 0.11, 0);
    leafR.scale.set(1.4, 0.5, 0.8);
    const fruit = mesh(new THREE.SphereGeometry(0.034, 10, 10), mat([0xfacc15, 0xf97316, 0xec4899][i], 0.35), 0, 0.17, 0);
    cg.add(stem, leafL, leafR, fruit);
    farmGroup.add(cg);
    cropStalks.push({ group: cg, fruit });
  });

  // 2B. Right Mini Guardian Turret Preview (+0.64, 0, 0.24)
  const campTurretGroup = new THREE.Group();
  campTurretGroup.position.set(0.64, 0.01, 0.24);
  baseCampGroup.add(campTurretGroup);

  const turretPedestal = mesh(new THREE.CylinderGeometry(0.12, 0.15, 0.08, 12), mat(0x475569, 0.4, 0.7), 0, 0.04, 0);
  const turretPillar = mesh(new THREE.CylinderGeometry(0.05, 0.07, 0.18, 10), mat(0x64748b, 0.35, 0.8), 0, 0.14, 0);
  const turretCrystal = mesh(new THREE.OctahedronGeometry(0.075, 0), new THREE.MeshStandardMaterial({
    color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.85, roughness: 0.15, metalness: 0.8
  }), 0, 0.29, 0);
  const turretRing = mesh(new THREE.TorusGeometry(0.10, 0.01, 6, 20), glow(0x38bdf8, 0.75), 0, 0.29, 0);
  turretRing.rotation.x = Math.PI / 2;
  campTurretGroup.add(turretPedestal, turretPillar, turretCrystal, turretRing);

  function updateBasecampVisuals(dt, elapsed) {
    baseCampGroup.visible = Boolean(rpgState.basecampVisible && !defenseState.active);
    if (!baseCampGroup.visible) return;

    // Update Farm Plot growth stage (0.0 -> 1.0)
    const g = clamp01(rpgState.farm.growth || 0.35);
    soilMesh.material.color.setHex(rpgState.farm.watered ? 0x3f1d0b : 0x78350f);
    cropStalks.forEach((st, idx) => {
      const s = Math.max(0.15, g);
      const readyBob = g >= 0.99 ? Math.sin(elapsed * 5 + idx) * 0.015 : 0;
      st.group.scale.setScalar(s);
      st.group.position.y = 0.06 + readyBob;
      st.fruit.visible = g >= 0.65;
    });

    // Update Mini Turret crystal spin & color based on highest unlocked turret
    turretCrystal.rotation.y = elapsed * 2.2;
    turretCrystal.position.y = 0.29 + Math.sin(elapsed * 3.5) * 0.02;
    turretRing.rotation.z = -elapsed * 1.8;
    const tCol = rpgState.turrets.arc > 0 ? 0xfacc15 : (rpgState.turrets.frost > 0 ? 0x38bdf8 : (rpgState.turrets.ballista > 0 ? 0x22c55e : 0x94a3b8));
    turretCrystal.material.color.setHex(tCol);
    turretRing.material.color.setHex(tCol);
  }

  // =========================================================================
  // 3. Hero 4-Tier 3D Evolving Weapon & Crescent Slash Trail
  // =========================================================================
  const heroWeaponGroup = new THREE.Group();
  heroWeaponGroup.visible = false;
  root.add(heroWeaponGroup);

  const slashArcMesh = mesh(
    new THREE.RingGeometry(0.24, 0.62, 20, 1, -Math.PI * 0.4, Math.PI * 0.85),
    glow(0xfacc15, 0.0),
    0, 0.68, 0.35
  );
  slashArcMesh.rotation.x = -Math.PI / 2 + 0.25;
  slashArcMesh.material.side = THREE.DoubleSide;
  slashArcMesh.visible = false;
  root.add(slashArcMesh);

  let builtWeaponKey = '';
  function rebuildHeroWeapon() {
    const tier = rpgState.weaponEnhance >= 10 ? 4 : (rpgState.weaponEnhance >= 7 ? 3 : (rpgState.weaponEnhance >= 3 ? 2 : 1));
    rpgState.weaponTier = tier;
    const key = `${rpgState.worldview}_${tier}`;
    if (builtWeaponKey === key) return;
    builtWeaponKey = key;

    while (heroWeaponGroup.children.length > 0) {
      heroWeaponGroup.remove(heroWeaponGroup.children[0]);
    }

    const hilt = mesh(new THREE.CylinderGeometry(0.014, 0.016, 0.16, 8), mat(0x78350f, 0.6), 0, 0.06, 0);
    const guard = mesh(new THREE.BoxGeometry(0.14, 0.028, 0.045), mat(0xfbbf24, 0.3, 0.8), 0, 0.14, 0);
    heroWeaponGroup.add(hilt, guard);

    const bladeColors = {
      1: { col: 0x94a3b8, em: 0x000000, len: 0.38, w: 0.032 },
      2: { col: 0xe2e8f0, em: 0x38bdf8, len: 0.46, w: 0.038 },
      3: { col: 0x38bdf8, em: 0x0284c7, len: 0.54, w: 0.045 },
      4: { col: 0xfacc15, em: 0xf43f5e, len: 0.62, w: 0.054 }
    }[tier];

    if (rpgState.worldview === 'cozy') {
      // Magical Star/Bubble Wand for Cozy Island
      const wandPole = mesh(new THREE.CylinderGeometry(0.012, 0.014, bladeColors.len, 10), mat(0xf472b6, 0.3), 0, 0.14 + bladeColors.len * 0.5, 0);
      const starRing = mesh(new THREE.TorusGeometry(0.08, 0.016, 8, 20), mat(0xfacc15, 0.25, 0.6), 0, 0.18 + bladeColors.len, 0);
      const gem = mesh(new THREE.OctahedronGeometry(0.045, 0), glow(0x38bdf8, 0.9), 0, 0.18 + bladeColors.len, 0);
      heroWeaponGroup.add(wandPole, starRing, gem);
    } else {
      const bladeMat = new THREE.MeshStandardMaterial({
        color: bladeColors.col,
        emissive: bladeColors.em,
        emissiveIntensity: tier >= 3 ? 0.85 : (tier === 2 ? 0.35 : 0.0),
        roughness: 0.2,
        metalness: 0.85
      });
      const blade = mesh(new THREE.BoxGeometry(bladeColors.w, bladeColors.len, 0.016), bladeMat, 0, 0.14 + bladeColors.len * 0.5, 0);
      const tip = mesh(new THREE.ConeGeometry(bladeColors.w * 0.72, 0.09, 4), bladeMat, 0, 0.14 + bladeColors.len + 0.045, 0);
      tip.rotation.y = Math.PI / 4;
      heroWeaponGroup.add(blade, tip);

      if (tier >= 3) {
        const auraRing = mesh(new THREE.TorusGeometry(0.075, 0.008, 6, 18), glow(tier === 4 ? 0xfacc15 : 0x38bdf8, 0.85), 0, 0.28, 0);
        auraRing.rotation.x = Math.PI / 2;
        heroWeaponGroup.add(auraRing);
      }
    }
  }
  rebuildHeroWeapon();

  // =========================================================================
  // 4. Procedural 3D Enemy Factory & Wave Defense Structures
  // =========================================================================
  const battlefieldGroup = new THREE.Group();
  battlefieldGroup.name = 'BattlefieldGroup';
  root.add(battlefieldGroup);

  // 4A. Defense Stage Structures (Left Nexus Core, Barricade, 3 Auto-Turrets, Right Portal)
  const defenseStageGroup = new THREE.Group();
  defenseStageGroup.visible = false;
  battlefieldGroup.add(defenseStageGroup);

  // Guardian Sanctuary Nexus Core (x = -1.65) + 3D Health Bar & Top Wave Banner Sprite
  const nexusGroup = new THREE.Group();
  nexusGroup.position.set(-1.65, 0.01, 0.15);
  const nexusBase = mesh(new THREE.CylinderGeometry(0.28, 0.34, 0.14, 8), mat(0x334155, 0.5, 0.7), 0, 0.07, 0);
  const nexusCrystal = mesh(new THREE.OctahedronGeometry(0.22, 0), new THREE.MeshStandardMaterial({
    color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.9, roughness: 0.15, metalness: 0.75
  }), 0, 0.48, 0);
  nexusCrystal.scale.set(0.75, 1.45, 0.75);
  const nexusShieldRing = mesh(new THREE.TorusGeometry(0.32, 0.018, 8, 28), glow(0x38bdf8, 0.8), 0, 0.48, 0);
  nexusShieldRing.rotation.x = Math.PI / 3;
  const nexusHpBg = mesh(new THREE.PlaneGeometry(0.56, 0.065), new THREE.MeshBasicMaterial({ color: 0x0f172a, side: THREE.DoubleSide }), 0, 0.96, 0);
  const nexusHpFill = mesh(new THREE.PlaneGeometry(0.54, 0.048), new THREE.MeshBasicMaterial({ color: 0x38bdf8, side: THREE.DoubleSide }), 0, 0.96, 0.005);
  nexusGroup.add(nexusBase, nexusCrystal, nexusShieldRing, nexusHpBg, nexusHpFill);
  defenseStageGroup.add(nexusGroup);

  // Top 3D Wave Banner Sprite (`waveBannerSprite`)
  let waveBannerSprite = null;
  function updateWaveBannerSprite(waveNum) {
    if (waveBannerSprite) {
      defenseStageGroup.remove(waveBannerSprite);
      waveBannerSprite = null;
    }
    if (fxApi && typeof fxApi.makeSprite === 'function') {
      const isBossWave = waveNum % 5 === 0;
      const bannerTxt = isBossWave ? `👑 BOSS WAVE ${waveNum}` : `🏰 WAVE ${waveNum} DEFENSE`;
      waveBannerSprite = fxApi.makeSprite(bannerTxt, isBossWave ? '#fde047' : '#38bdf8', 0.20);
      waveBannerSprite.position.set(0, 2.02, 0.12);
      defenseStageGroup.add(waveBannerSprite);
    }
  }

  // Barricade at x = -0.68
  const barricadeGroup = new THREE.Group();
  barricadeGroup.position.set(-0.68, 0.01, 0.25);
  for (let i = -1; i <= 1; i++) {
    const post = mesh(new THREE.BoxGeometry(0.08, 0.28, 0.08), mat(0x64748b, 0.4, 0.8), i * 0.11, 0.14, 0);
    barricadeGroup.add(post);
  }
  const crossBeam = mesh(new THREE.BoxGeometry(0.36, 0.07, 0.10), mat(0x94a3b8, 0.3, 0.85), 0, 0.20, 0);
  barricadeGroup.add(crossBeam);
  defenseStageGroup.add(barricadeGroup);

  // 3 Auto-Turret Meshes (Ballista, Frost Tower, Arc Cannon)
  const turretMeshes = {
    ballista: new THREE.Group(),
    frost: new THREE.Group(),
    arc: new THREE.Group()
  };
  // Ballista (-1.15, 0, -0.05)
  turretMeshes.ballista.position.set(-1.15, 0.01, -0.05);
  turretMeshes.ballista.add(
    mesh(new THREE.CylinderGeometry(0.10, 0.13, 0.18, 8), mat(0x78350f, 0.7), 0, 0.09, 0),
    mesh(new THREE.BoxGeometry(0.22, 0.05, 0.06), mat(0xfbbf24, 0.3, 0.8), 0.04, 0.21, 0)
  );
  // Frost Crystal Tower (-1.28, 0, 0.35)
  turretMeshes.frost.position.set(-1.28, 0.01, 0.35);
  turretMeshes.frost.add(
    mesh(new THREE.CylinderGeometry(0.09, 0.12, 0.24, 8), mat(0x1e3a8a, 0.4, 0.6), 0, 0.12, 0),
    mesh(new THREE.OctahedronGeometry(0.09, 0), glow(0x38bdf8, 0.95), 0, 0.32, 0)
  );
  // Orichalcum Arc Cannon (-0.95, 0, 0.38)
  turretMeshes.arc.position.set(-0.95, 0.01, 0.38);
  turretMeshes.arc.add(
    mesh(new THREE.CylinderGeometry(0.11, 0.14, 0.22, 10), mat(0x334155, 0.3, 0.85), 0, 0.11, 0),
    mesh(new THREE.TorusGeometry(0.10, 0.02, 8, 20), glow(0xfacc15, 0.95), 0, 0.30, 0)
  );
  defenseStageGroup.add(turretMeshes.ballista, turretMeshes.frost, turretMeshes.arc);

  // Right Invasion Portal Gate (x = +1.72)
  const portalGroup = new THREE.Group();
  portalGroup.position.set(1.72, 0.45, 0.18);
  const portalOuter = mesh(new THREE.TorusGeometry(0.34, 0.035, 10, 32), glow(0xa855f7, 0.9), 0, 0, 0);
  const portalInner = mesh(new THREE.CircleGeometry(0.31, 24), glow(0x3b0764, 0.65), 0, 0, 0);
  portalOuter.rotation.y = -Math.PI / 3;
  portalInner.rotation.y = -Math.PI / 3;
  portalGroup.add(portalOuter, portalInner);
  battlefieldGroup.add(portalGroup);
  portalGroup.visible = false;

  // 4B. Procedural 3D Enemy Builder
  function buildEnemyMesh(archetype, themeObj, isBoss = false) {
    const g = new THREE.Group();
    const cfg = themeObj.enemies[archetype] || themeObj.enemies.slime;
    const bodyMat = new THREE.MeshStandardMaterial({
      color: cfg.color,
      roughness: 0.35,
      metalness: archetype === 'drone' ? 0.65 : 0.15,
      emissive: 0x000000,
      emissiveIntensity: 0
    });

    if (isBoss) {
      // Articulated 3D Boss Golem / Titan
      const torso = mesh(new THREE.BoxGeometry(0.38, 0.42, 0.28), bodyMat, 0, 0.36, 0);
      const head = mesh(new THREE.BoxGeometry(0.24, 0.22, 0.24), bodyMat, 0, 0.68, 0.02);
      const eyeL = mesh(new THREE.SphereGeometry(0.032, 8, 8), glow(cfg.eye, 1), -0.06, 0.69, 0.14);
      const eyeR = mesh(new THREE.SphereGeometry(0.032, 8, 8), glow(cfg.eye, 1), 0.06, 0.69, 0.14);
      const hornL = mesh(new THREE.ConeGeometry(0.04, 0.16, 6), mat(0xfacc15, 0.3, 0.8), -0.11, 0.84, 0);
      const hornR = mesh(new THREE.ConeGeometry(0.04, 0.16, 6), mat(0xfacc15, 0.3, 0.8), 0.11, 0.84, 0);
      const shoulderL = mesh(new THREE.BoxGeometry(0.16, 0.28, 0.16), bodyMat, -0.28, 0.38, 0);
      const shoulderR = mesh(new THREE.BoxGeometry(0.16, 0.28, 0.16), bodyMat, 0.28, 0.38, 0);
      const crown = mesh(new THREE.TorusGeometry(0.10, 0.018, 6, 16), glow(0xfacc15, 0.95), 0, 0.88, 0);
      crown.rotation.x = Math.PI / 2;
      g.add(torso, head, eyeL, eyeR, hornL, hornR, shoulderL, shoulderR, crown);
      g.userData.bodyMat = bodyMat;
      return g;
    }

    if (archetype === 'slime') {
      const body = mesh(new THREE.SphereGeometry(0.16, 16, 12), bodyMat, 0, 0.15, 0);
      body.scale.set(1.15, 0.88, 1.05);
      const eyeL = mesh(new THREE.SphereGeometry(0.022, 8, 8), mat(cfg.eye), -0.05, 0.17, 0.14);
      const eyeR = mesh(new THREE.SphereGeometry(0.022, 8, 8), mat(cfg.eye), 0.05, 0.17, 0.14);
      g.add(body, eyeL, eyeR);
    } else if (archetype === 'imp') {
      const body = mesh(new THREE.CapsuleGeometry(0.09, 0.14, 6, 10), bodyMat, 0, 0.18, 0);
      const earL = mesh(new THREE.ConeGeometry(0.035, 0.10, 5), bodyMat, -0.08, 0.31, 0);
      earL.rotation.z = 0.45;
      const earR = mesh(new THREE.ConeGeometry(0.035, 0.10, 5), bodyMat, 0.08, 0.31, 0);
      earR.rotation.z = -0.45;
      const eyeL = mesh(new THREE.SphereGeometry(0.018, 8, 8), glow(cfg.eye, 1), -0.035, 0.24, 0.085);
      const eyeR = mesh(new THREE.SphereGeometry(0.018, 8, 8), glow(cfg.eye, 1), 0.035, 0.24, 0.085);
      g.add(body, earL, earR, eyeL, eyeR);
    } else {
      // Drone
      const core = mesh(new THREE.OctahedronGeometry(0.13, 0), bodyMat, 0, 0.38, 0);
      const ring1 = mesh(new THREE.TorusGeometry(0.18, 0.012, 6, 20), glow(cfg.eye, 0.85), 0, 0.38, 0);
      const eye = mesh(new THREE.SphereGeometry(0.035, 8, 8), glow(cfg.eye, 1), 0, 0.38, 0.11);
      g.add(core, ring1, eye);
      g.userData.ring = ring1;
    }
    g.userData.bodyMat = bodyMat;
    return g;
  }

  // =========================================================================
  // 5. Projectiles, Lightning Smite & Combat State
  // =========================================================================
  const activeEnemies = [];
  const activeProjectiles = [];
  const enemiesGroup = new THREE.Group();
  const projectilesGroup = new THREE.Group();
  battlefieldGroup.add(enemiesGroup, projectilesGroup);

  const lightningBoltMesh = mesh(new THREE.CylinderGeometry(0.04, 0.12, 3.2, 8), glow(0xfacc15, 0.0), 0, 1.6, 0);
  lightningBoltMesh.visible = false;
  battlefieldGroup.add(lightningBoltMesh);

  let slashTimer = 0;
  let cameraShake = 0;
  const defaultCamPos = new THREE.Vector3(0, 1.18, 7.6);
  const defenseCamPos = new THREE.Vector3(0, 1.65, 9.6);
  let targetCamMode = 'normal';

  const combatState = {
    mode: 'none', // 'none' | 'skirmish' | 'defense'
    heroHP: 200,
    heroMaxHP: 200,
    coreHP: 1000,
    coreMaxHP: 1000,
    attackCooldown: 0,
    turretCooldowns: { ballista: 0, frost: 0, arc: 0 },
    bentoBuffTimer: 0,
    bentoAtkMult: 1.0,
    bentoSpdMult: 1.0,
    comboStep: 0
  };

  const defenseState = {
    active: false,
    wave: 1,
    totalToSpawn: 0,
    spawnedCount: 0,
    spawnTimer: 0,
    bossSpawned: false,
    waveClearPending: false
  };

  function calcHeroStats() {
    const lv = Math.max(1, rpgState.petLevel || 1);
    const enh = Math.max(0, rpgState.weaponEnhance || 0);
    const baseWep = 12 + rpgState.weaponTier * 10;
    const atk = Math.round((15 + 4 * lv + baseWep * (1 + 0.14 * enh)) * combatState.bentoAtkMult);
    const maxHP = Math.round(140 + 30 * lv + enh * 18);
    const aps = (1.15 + rpgState.weaponTier * 0.12) * combatState.bentoSpdMult;
    return { atk, maxHP, aps };
  }

  function updateMiniHudBadge(text, visible = true) {
    const badge = document.getElementById('status-badge');
    if (!badge) return;
    if (!visible) {
      badge.classList.remove('visible');
      return;
    }
    badge.textContent = text;
    badge.classList.add('visible');
  }

  function spawnProjectile(fromVec, targetEnemy, color, damage, effectType = 'magic') {
    const pMesh = mesh(new THREE.SphereGeometry(0.042, 8, 8), glow(color, 0.95), fromVec.x, fromVec.y, fromVec.z);
    projectilesGroup.add(pMesh);
    activeProjectiles.push({
      mesh: pMesh,
      target: targetEnemy,
      damage,
      color,
      effectType,
      speed: 5.2,
      life: 0
    });
  }

  function clearAllEnemies() {
    while (activeEnemies.length > 0) {
      const e = activeEnemies.pop();
      enemiesGroup.remove(e.mesh);
    }
    while (activeProjectiles.length > 0) {
      const p = activeProjectiles.pop();
      projectilesGroup.remove(p.mesh);
    }
  }

  function spawnEnemy(archetype, xPos, hpScale = 1.0, atkScale = 1.0, isBoss = false) {
    const themeObj = WORLDVIEW_THEMES[rpgState.worldview] || WORLDVIEW_THEMES.fantasy;
    const eMesh = buildEnemyMesh(archetype, themeObj, isBoss);
    const zOff = rand(0.12, 0.38);
    eMesh.position.set(xPos, 0.01, zOff);
    enemiesGroup.add(eMesh);

    const cfg = themeObj.enemies[archetype] || themeObj.enemies.slime;
    const baseHP = isBoss ? 420 : (archetype === 'drone' ? 65 : 55);
    const maxHP = Math.round(baseHP * hpScale);
    const atk = Math.round((isBoss ? 22 : 8) * atkScale);

    // HP Bar Sprite above enemy
    const hpBg = mesh(new THREE.PlaneGeometry(isBoss ? 0.55 : 0.28, 0.038), glow(0x0f172a, 0.8), 0, isBoss ? 0.98 : 0.44, 0);
    const hpFill = mesh(new THREE.PlaneGeometry(isBoss ? 0.53 : 0.26, 0.026), glow(isBoss ? 0xf43f5e : 0x22c55e, 0.95), 0, isBoss ? 0.98 : 0.44, 0.002);
    eMesh.add(hpBg, hpFill);

    if (fxApi) {
      fxApi.ring(xPos, 0.15, zOff, themeObj.portalColor, { size: isBoss ? 1.4 : 0.75, max: 0.45 });
    }

    activeEnemies.push({
      mesh: eMesh,
      hpFill,
      name: cfg.name,
      archetype,
      isBoss,
      hp: maxHP,
      maxHP,
      atk,
      speed: isBoss ? 0.24 : (archetype === 'imp' ? 0.48 : 0.34),
      slowTimer: 0,
      stunTimer: 0,
      flashTimer: 0,
      atkTimer: 0.8,
      vx: 0,
      phase: Math.random() * 6.28
    });
  }

  function damageEnemy(e, rawDmg, isCrit = false, source = 'hero') {
    if (!e || e.hp <= 0) return;
    const dmg = Math.max(1, Math.round(rawDmg));
    e.hp = Math.max(0, e.hp - dmg);
    e.flashTimer = 0.085;
    if (e.mesh.userData.bodyMat) {
      e.mesh.userData.bodyMat.emissive.setHex(0xffffff);
      e.mesh.userData.bodyMat.emissiveIntensity = 0.9;
    }
    e.vx = 0.65 * (e.isBoss ? 0.25 : 1.0); // Knockback right
    const hpRatio = clamp01(e.hp / e.maxHP);
    e.hpFill.scale.x = Math.max(0.01, hpRatio);

    const themeObj = WORLDVIEW_THEMES[rpgState.worldview] || WORLDVIEW_THEMES.fantasy;
    if (fxApi) {
      const ex = e.mesh.position.x, ey = e.mesh.position.y + (e.isBoss ? 0.55 : 0.25), ez = e.mesh.position.z;
      if (themeObj.isCozyNonViolent) {
        fxApi.floatEmoji(isCrit ? `💖정화! ${dmg}` : `🫧+${dmg}`, ex, ey + 0.18, ez + 0.1, {
          size: isCrit ? 0.15 : 0.12,
          color: isCrit ? '#f472b6' : '#bae6fd',
          max: 0.9
        });
        fxApi.burst(ex, ey, ez, 0xf9a8d4, isCrit ? 12 : 6, 1.1, { max: 0.45 });
      } else {
        fxApi.floatEmoji(isCrit ? `💥CRIT ${dmg}!` : `${dmg}`, ex, ey + 0.18, ez + 0.1, {
          size: isCrit ? 0.15 : 0.12,
          color: isCrit ? '#facc15' : '#f8fafc',
          max: 0.85
        });
        fxApi.burst(ex, ey, ez, isCrit ? 0xfacc15 : themeObj.slashColor, isCrit ? 14 : 7, 1.35, { max: 0.45 });
      }
      if (isCrit && source === 'hero') fxApi.hitStop(0.045);
    }

    if (e.hp <= 0) {
      const ex = e.mesh.position.x, ez = e.mesh.position.z;
      if (fxApi) {
        fxApi.ring(ex, 0.05, ez, e.isBoss ? 0xfacc15 : 0x38bdf8, { size: e.isBoss ? 1.8 : 0.95, max: 0.55 });
        fxApi.burst(ex, 0.28, ez, 0xfde047, e.isBoss ? 28 : 14, 1.6);
        fxApi.itemDrop(e.isBoss ? '👑' : '💎', 0.55);
      }
      enemiesGroup.remove(e.mesh);
      const idx = activeEnemies.indexOf(e);
      if (idx >= 0) activeEnemies.splice(idx, 1);

      if (typeof window.emitPpongSync === 'function') {
        window.emitPpongSync({
          type: 'enemy_defeated',
          name: e.name,
          isBoss: e.isBoss,
          mode: combatState.mode,
          wave: defenseState.wave,
          goldReward: e.isBoss ? 120 * defenseState.wave : 18 + defenseState.wave * 4,
          xpReward: e.isBoss ? 85 : 22,
          coreDrop: e.isBoss ? 3 : 1
        });
      }
    }
  }

  // =========================================================================
  // 6. Auto Battle Bento Consumption (Farming + Fishing -> Cooking Causality!)
  // =========================================================================
  function tryConsumeBattleBento(reason = 'hp') {
    const b = rpgState.bentos || {};
    let chosen = null;
    if (b.star_emperor > 0) {
      b.star_emperor--;
      chosen = { key: 'star_emperor', name: '🍱 별빛 해산물 황제 도시락', heal: 500, atkMult: 1.45, spdMult: 1.35 };
    } else if (b.carp_stew > 0) {
      b.carp_stew--;
      chosen = { key: 'carp_stew', name: '🍲 황금 잉어 매운탕', heal: 280, atkMult: 1.35, spdMult: 1.20 };
    } else if (b.trout_steak > 0) {
      b.trout_steak--;
      chosen = { key: 'trout_steak', name: '🍣 무지개 송어 스테이크', heal: 180, atkMult: 1.20, spdMult: 1.28 };
    } else if (b.potato_fish > 0) {
      b.potato_fish--;
      chosen = { key: 'potato_fish', name: '🥔 감자 생선구이', heal: 120, atkMult: 1.12, spdMult: 1.10 };
    }
    if (!chosen) return false;

    combatState.heroHP = Math.min(combatState.heroMaxHP, combatState.heroHP + chosen.heal);
    combatState.bentoAtkMult = chosen.atkMult;
    combatState.bentoSpdMult = chosen.spdMult;
    combatState.bentoBuffTimer = 45.0;

    if (fxApi) {
      fxApi.pillar();
      fxApi.floatText(`${chosen.name} 섭취! (HP+${chosen.heal} / 화력 UP!)`, '#a3e635', 1.85, 0.14, 2.2);
    }
    if (typeof window.emitPpongSync === 'function') {
      window.emitPpongSync({
        type: 'bento_consumed',
        bentoKey: chosen.key,
        bentoName: chosen.name,
        reason
      });
    }
    return true;
  }

  // =========================================================================
  // 7. Skirmish Mode (간헐적 바탕화면 수호) & Wave Defense Mode (웨이브 디펜스)
  // =========================================================================
  function startSkirmish(customArchetype = null) {
    if (soloPlaySys && soloPlaySys.isSoloPlayingActive()) {
      soloPlaySys.stopSoloAction();
    }
    clearAllEnemies();
    rebuildHeroWeapon();

    combatState.mode = 'skirmish';
    defenseState.active = false;
    defenseStageGroup.visible = false;
    portalGroup.visible = true;
    portalGroup.position.set(0.92, 0.35, 0.25);
    heroWeaponGroup.visible = true;
    targetCamMode = 'normal';

    const stats = calcHeroStats();
    combatState.heroMaxHP = stats.maxHP;
    combatState.heroHP = stats.maxHP;

    const types = ['slime', 'imp', 'drone'];
    const arch1 = customArchetype || types[Math.floor(Math.random() * types.length)];
    const lvScale = 1 + (rpgState.petLevel - 1) * 0.18;
    spawnEnemy(arch1, 0.88, lvScale, lvScale, false);
    if (Math.random() < 0.45) {
      spawnEnemy(types[Math.floor(Math.random() * types.length)], 1.12, lvScale * 0.85, lvScale, false);
    }

    const themeObj = WORLDVIEW_THEMES[rpgState.worldview] || WORLDVIEW_THEMES.fantasy;
    const eName = themeObj.enemies[arch1]?.name || '침입자';
    if (fxApi) {
      fxApi.floatEmoji('⚔️ 바탕화면 수호!', 0, 1.65, 0.2, { size: 0.16, color: '#facc15', max: 1.5 });
    }
    updateMiniHudBadge(`🛡️ 바탕화면 수호 교전 중! (${eName}) — 클릭 시 ⚡벼락 지원!`, true);
    triggerEmotionEmote && triggerEmotionEmote('excited');
    return { enemyName: eName };
  }

  function startWaveDefense(waveNumber = 1) {
    if (soloPlaySys && soloPlaySys.isSoloPlayingActive()) {
      soloPlaySys.stopSoloAction();
    }
    clearAllEnemies();
    rebuildHeroWeapon();

    const w = Math.max(1, Number(waveNumber) || 1);
    combatState.mode = 'defense';
    defenseState.active = true;
    defenseState.wave = w;
    defenseState.totalToSpawn = 4 + Math.min(10, Math.floor(w * 1.2));
    defenseState.spawnedCount = 0;
    defenseState.spawnTimer = 0.4;
    defenseState.bossSpawned = false;
    defenseState.waveClearPending = false;

    const stats = calcHeroStats();
    combatState.heroMaxHP = stats.maxHP;
    combatState.heroHP = stats.maxHP;
    const barLv = rpgState.turrets.barricade || 1;
    combatState.coreMaxHP = 500 + barLv * 250 + rpgState.petLevel * 60;
    combatState.coreHP = combatState.coreMaxHP;

    defenseStageGroup.visible = true;
    barricadeGroup.visible = (rpgState.turrets.barricade || 0) > 0;
    turretMeshes.ballista.visible = (rpgState.turrets.ballista || 0) > 0;
    turretMeshes.frost.visible = (rpgState.turrets.frost || 0) > 0;
    turretMeshes.arc.visible = (rpgState.turrets.arc || 0) > 0;

    portalGroup.visible = true;
    portalGroup.position.set(1.68, 0.42, 0.18);
    heroWeaponGroup.visible = true;
    targetCamMode = 'defense';
    nexusHpFill.scale.x = 1.0;
    updateWaveBannerSprite(w);

    // If Boss Wave (Wave 5, 10, 15...), auto-consume Battle Bento at start if available!
    if (w % 5 === 0) {
      tryConsumeBattleBento('boss_wave');
    }

    if (fxApi) {
      fxApi.floatText(`🏰 WAVE ${w} 디펜스 개시!`, '#38bdf8', 1.88, 0.16, 2.2);
    }
    updateMiniHudBadge(`🏰 [WAVE ${w}] Core HP: ${combatState.coreHP}/${combatState.coreMaxHP} | ⚡적 클릭 시 마우스 벼락!`, true);
    return { wave: w, coreMaxHP: combatState.coreMaxHP };
  }

  function stopCombatAndDefense() {
    clearAllEnemies();
    combatState.mode = 'none';
    defenseState.active = false;
    defenseStageGroup.visible = false;
    portalGroup.visible = false;
    heroWeaponGroup.visible = false;
    slashArcMesh.visible = false;
    targetCamMode = 'normal';
    characterPivot.position.set(0, 0, 0);
    updateMiniHudBadge('', false);
  }

  // =========================================================================
  // 8. Interactive Cursor Smite (마우스 클릭 협동 벼락 타격)
  // =========================================================================
  function triggerCursorSmite(normX = 0, normY = 0) {
    if (combatState.mode === 'none' || activeEnemies.length === 0) return false;
    // Find enemy closest to clicked horizontal screen position or frontmost enemy
    const approxWorldX = normX * (targetCamMode === 'defense' ? 2.2 : 1.1);
    let bestEnemy = activeEnemies[0];
    let bestDist = 999;
    for (const e of activeEnemies) {
      const d = Math.abs(e.mesh.position.x - approxWorldX);
      if (d < bestDist) {
        bestDist = d;
        bestEnemy = e;
      }
    }
    if (!bestEnemy) return false;

    const tx = bestEnemy.mesh.position.x;
    const tz = bestEnemy.mesh.position.z;
    lightningBoltMesh.position.set(tx, 1.5, tz);
    lightningBoltMesh.visible = true;
    lightningBoltMesh.material.opacity = 0.95;
    setTimeout(() => { lightningBoltMesh.visible = false; }, 160);

    cameraShake = 0.06;
    const stats = calcHeroStats();
    const smiteDmg = Math.round(stats.atk * 1.45 + bestEnemy.maxHP * (bestEnemy.isBoss ? 0.08 : 0.25));
    bestEnemy.stunTimer = 1.1;
    damageEnemy(bestEnemy, smiteDmg, true, 'cursor_smite');

    if (fxApi) {
      fxApi.ring(tx, 0.04, tz, 0xfacc15, { size: 1.5, max: 0.45 });
      fxApi.floatEmoji('⚡천벌 벼락!', tx, 0.95, tz, { size: 0.15, color: '#fde047', max: 0.85 });
    }
    return true;
  }

  // =========================================================================
  // 9. Multi-Worldview Theme Swap Engine (Fantasy / Cyberpunk / Sci-Fi / Cozy)
  // =========================================================================
  function applyWorldviewTheme(themeKey) {
    const theme = WORLDVIEW_THEMES[themeKey] || WORLDVIEW_THEMES.fantasy;
    rpgState.worldview = theme.key;

    if (hemiLight) {
      hemiLight.color.setHex(theme.hemiSky);
      hemiLight.groundColor.setHex(theme.hemiGround);
    }
    if (keyLight) keyLight.color.setHex(theme.keyColor);
    if (backRimLight) backRimLight.color.setHex(theme.rimColor);
    if (pawFootprintMatTemplate && pawFootprintMatTemplate.uniforms) {
      pawFootprintMatTemplate.uniforms.uTint.value.setHex(theme.meadowTint);
      pawFootprintMatTemplate.uniforms.uGlow.value.setHex(theme.meadowGlow);
    }
    portalOuter.material.color.setHex(theme.portalColor);
    nexusCrystal.material.color.setHex(theme.coreColor);
    nexusShieldRing.material.color.setHex(theme.coreColor);
    slashArcMesh.material.color.setHex(theme.slashColor);

    rebuildHeroWeapon();
    if (fxApi) {
      fxApi.ring(0, 0.05, 0, theme.coreColor, { size: 2.1, max: 0.65 });
      fxApi.floatText(`🌌 세계관 전환: ${theme.badge}`, '#f8fafc', 1.82, 0.14, 2.0);
    }
    return theme;
  }

  // =========================================================================
  // 10. Real-Time Frame Update (60 FPS Combat, Turrets, Projectiles & Camera)
  // =========================================================================
  const tmpHand = new THREE.Vector3();
  const tmpHorn = new THREE.Vector3();

  function updateWorldRPGDefense(dt, elapsed) {
    updateBasecampVisuals(dt, elapsed);

    // Smooth camera transition for Wave Defense vs Normal
    const desiredCam = targetCamMode === 'defense' ? defenseCamPos : defaultCamPos;
    camera.position.lerp(desiredCam, 1 - Math.exp(-5.5 * dt));
    if (cameraShake > 0.001) {
      camera.position.x += (Math.random() - 0.5) * cameraShake;
      camera.position.y += (Math.random() - 0.5) * cameraShake;
      cameraShake = Math.max(0, cameraShake - dt * 0.28);
    }

    if (combatState.bentoBuffTimer > 0) {
      combatState.bentoBuffTimer = Math.max(0, combatState.bentoBuffTimer - dt);
      if (combatState.bentoBuffTimer <= 0) {
        combatState.bentoAtkMult = 1.0;
        combatState.bentoSpdMult = 1.0;
      }
    }

    if (combatState.mode === 'none') return;

    // Attach Hero Weapon to Right Hand Bone
    if (heroWeaponGroup.visible && fxApi) {
      fxApi.handPos('R', tmpHand);
      heroWeaponGroup.position.copy(tmpHand);
      const swingAng = slashTimer > 0 ? Math.sin((slashTimer / 0.22) * Math.PI) * 1.45 : 0;
      heroWeaponGroup.rotation.set(0.35 - swingAng, 0, -0.45 - swingAng * 0.5);
    }

    if (slashTimer > 0) {
      slashTimer = Math.max(0, slashTimer - dt);
      slashArcMesh.visible = true;
      slashArcMesh.material.opacity = (slashTimer / 0.22) * 0.88;
      slashArcMesh.rotation.z = (1 - slashTimer / 0.22) * 1.2;
    } else {
      slashArcMesh.visible = false;
    }

    portalOuter.rotation.z = elapsed * 2.5;
    nexusCrystal.rotation.y = elapsed * 1.8;
    nexusShieldRing.rotation.z = -elapsed * 1.5;

    // Wave Defense Spawner
    if (combatState.mode === 'defense' && defenseState.active) {
      if (defenseState.spawnedCount < defenseState.totalToSpawn) {
        defenseState.spawnTimer -= dt;
        if (defenseState.spawnTimer <= 0) {
          defenseState.spawnTimer = rand(0.95, 1.55);
          defenseState.spawnedCount++;
          const w = defenseState.wave;
          const hpScale = Math.pow(1.24, w - 1);
          const atkScale = Math.pow(1.16, w - 1);
          const isLast = defenseState.spawnedCount === defenseState.totalToSpawn;
          if (isLast && w % 5 === 0 && !defenseState.bossSpawned) {
            defenseState.bossSpawned = true;
            const bossKey = w >= 15 ? 'boss15' : (w >= 10 ? 'boss10' : 'boss5');
            spawnEnemy(bossKey, 1.62, hpScale * 1.35, atkScale * 1.2, true);
            if (fxApi) fxApi.floatText(`⚠️ BOSS 출현!`, '#ef4444', 1.92, 0.17, 2.2);
          } else {
            const pool = w >= 4 ? ['slime', 'imp', 'drone'] : ['slime', 'imp'];
            spawnEnemy(pool[Math.floor(Math.random() * pool.length)], 1.62, hpScale, atkScale, false);
          }
        }
      }
    }

    // Update Projectiles
    for (let i = activeProjectiles.length - 1; i >= 0; i--) {
      const pr = activeProjectiles[i];
      pr.life += dt;
      if (!pr.target || pr.target.hp <= 0 || pr.life > 2.2) {
        projectilesGroup.remove(pr.mesh);
        activeProjectiles.splice(i, 1);
        continue;
      }
      const tx = pr.target.mesh.position.x, ty = pr.target.mesh.position.y + 0.22, tz = pr.target.mesh.position.z;
      const dx = tx - pr.mesh.position.x, dy = ty - pr.mesh.position.y, dz = tz - pr.mesh.position.z;
      const dist = Math.hypot(dx, dy, dz) || 0.001;
      if (dist <= 0.14) {
        if (pr.effectType === 'frost') pr.target.slowTimer = 2.8;
        damageEnemy(pr.target, pr.damage, Math.random() < 0.2, pr.effectType);
        projectilesGroup.remove(pr.mesh);
        activeProjectiles.splice(i, 1);
      } else {
        const step = Math.min(dist, pr.speed * dt);
        pr.mesh.position.x += (dx / dist) * step;
        pr.mesh.position.y += (dy / dist) * step;
        pr.mesh.position.z += (dz / dist) * step;
      }
    }

    // Update Enemies & Combat AI
    const stats = calcHeroStats();
    const stopX = combatState.mode === 'defense' ? -0.45 : 0.36;
    let frontEnemy = null;
    let minEnemyX = 999;

    for (let i = activeEnemies.length - 1; i >= 0; i--) {
      const e = activeEnemies[i];
      if (e.flashTimer > 0) {
        e.flashTimer -= dt;
        if (e.flashTimer <= 0 && e.mesh.userData.bodyMat) {
          e.mesh.userData.bodyMat.emissiveIntensity = 0;
        }
      }
      if (e.slowTimer > 0) e.slowTimer -= dt;
      if (e.stunTimer > 0) e.stunTimer -= dt;

      // Knockback decay
      if (Math.abs(e.vx) > 0.01) {
        e.mesh.position.x += e.vx * dt;
        e.vx *= Math.exp(-9 * dt);
      }

      if (e.stunTimer <= 0) {
        const spdMult = e.slowTimer > 0 ? 0.52 : 1.0;
        if (e.mesh.position.x > stopX) {
          e.mesh.position.x -= e.speed * spdMult * dt;
          const hop = Math.abs(Math.sin(elapsed * 8 + e.phase));
          e.mesh.position.y = 0.01 + (e.archetype === 'drone' ? 0.15 + hop * 0.06 : hop * 0.05);
        } else {
          // Enemy attacks Hero / Core
          e.atkTimer -= dt;
          if (e.atkTimer <= 0) {
            e.atkTimer = 1.25;
            const barReduction = Math.min(0.45, (rpgState.turrets.barricade || 0) * 0.08);
            const taken = Math.max(1, Math.round(e.atk * (1 - barReduction)));
            if (combatState.mode === 'defense') {
              combatState.coreHP = Math.max(0, combatState.coreHP - taken);
              combatState.heroHP = Math.max(0, combatState.heroHP - Math.round(taken * 0.5));
              if (combatState.heroHP < combatState.heroMaxHP * 0.55) {
                tryConsumeBattleBento('low_hp');
              }
            } else {
              combatState.heroHP = Math.max(10, combatState.heroHP - taken);
            }
          }
        }
      }

      if (e.mesh.position.x < minEnemyX) {
        minEnemyX = e.mesh.position.x;
        frontEnemy = e;
      }
    }

    // Hero Attack & Auto-Turret Attacks
    if (frontEnemy) {
      stageGroup.rotation.y = lerp(stageGroup.rotation.y, 0.55, 1 - Math.exp(-10 * dt));
      combatState.attackCooldown -= dt;
      if (combatState.attackCooldown <= 0) {
        combatState.attackCooldown = 1.0 / Math.max(0.5, stats.aps);
        combatState.comboStep = (combatState.comboStep + 1) % 3;
        const isCrit = Math.random() < (0.22 + rpgState.weaponTier * 0.05);
        const mult = combatState.comboStep === 2 ? 1.35 : 1.0;

        if (frontEnemy.mesh.position.x <= 0.85) {
          // Melee Slash
          slashTimer = 0.22;
          slashArcMesh.position.set(frontEnemy.mesh.position.x * 0.65, 0.55, 0.32);
          const rig = getRigBones();
          if (rig && rig.rightArm) addBoneEulerOffset(rig.rightArm, -0.6, -0.8, 1.4);
          damageEnemy(frontEnemy, stats.atk * mult * (isCrit ? 1.75 : 1.0), isCrit, 'hero');
        } else {
          // Ranged Horn Magic Bolt
          const rig = getRigBones();
          if (rig && rig.horn) {
            rig.horn.getWorldPosition(tmpHorn);
          } else {
            tmpHorn.set(0, 1.35, 0.2);
          }
          spawnProjectile(tmpHorn, frontEnemy, 0xfacc15, stats.atk * (isCrit ? 1.6 : 1.0), 'hero');
        }
      }

      // Defense Mode Auto-Turrets
      if (combatState.mode === 'defense') {
        const tLv = rpgState.turrets;
        if (tLv.ballista > 0) {
          combatState.turretCooldowns.ballista -= dt;
          if (combatState.turretCooldowns.ballista <= 0) {
            combatState.turretCooldowns.ballista = Math.max(0.35, 1.1 - tLv.ballista * 0.12);
            spawnProjectile(new THREE.Vector3(-1.15, 0.28, -0.05), frontEnemy, 0x22c55e, 14 + tLv.ballista * 9, 'ballista');
          }
        }
        if (tLv.frost > 0) {
          combatState.turretCooldowns.frost -= dt;
          if (combatState.turretCooldowns.frost <= 0) {
            combatState.turretCooldowns.frost = 1.6;
            spawnProjectile(new THREE.Vector3(-1.28, 0.35, 0.35), frontEnemy, 0x38bdf8, 10 + tLv.frost * 8, 'frost');
          }
        }
        if (tLv.arc > 0) {
          combatState.turretCooldowns.arc -= dt;
          if (combatState.turretCooldowns.arc <= 0) {
            combatState.turretCooldowns.arc = 1.85;
            // Chain lightning hits up to 3 enemies!
            activeEnemies.slice(0, 3).forEach((target) => {
              damageEnemy(target, 18 + tLv.arc * 14, true, 'arc');
            });
            if (fxApi) fxApi.ring(frontEnemy.mesh.position.x, 0.25, 0.2, 0xfacc15, { size: 1.1, max: 0.35 });
          }
        }
      }
    }

    // Check Skirmish Victory
    if (combatState.mode === 'skirmish' && activeEnemies.length === 0) {
      stopCombatAndDefense();
      playAnimation && playAnimation('HappySpin', { durationMs: 2400, emotion: 'proud' });
      if (fxApi) {
        fxApi.pillar();
        fxApi.floatText('🛡️ 바탕화면 수호 완료! (+침입자 코어)', '#a3e635', 1.82, 0.15, 2.2);
      }
      if (typeof window.emitPpongSync === 'function') {
        window.emitPpongSync({ type: 'skirmish_victory' });
      }
      return;
    }

    // Check Wave Defense Victory or Defeat
    if (combatState.mode === 'defense' && defenseState.active) {
      nexusHpFill.scale.x = Math.max(0.001, combatState.coreHP / Math.max(1, combatState.coreMaxHP));
      updateMiniHudBadge(
        `🏰 [WAVE ${defenseState.wave}] Core HP: ${combatState.coreHP}/${combatState.coreMaxHP} | 적 잔여: ${activeEnemies.length + (defenseState.totalToSpawn - defenseState.spawnedCount)}`,
        true
      );

      if (combatState.coreHP <= 0) {
        const failedWave = defenseState.wave;
        stopCombatAndDefense();
        playAnimation && playAnimation('Sad', { durationMs: 3000, emotion: 'sad' });
        if (fxApi) {
          fxApi.floatText(`💥 WAVE ${failedWave} 방어 실패! (채굴 강화 & 요리 도시락 필요!)`, '#ef4444', 1.82, 0.14, 2.8);
        }
        if (typeof window.emitPpongSync === 'function') {
          window.emitPpongSync({
            type: 'wave_defense_result',
            victory: false,
            wave: failedWave
          });
        }
        return;
      }

      if (defenseState.spawnedCount >= defenseState.totalToSpawn && activeEnemies.length === 0 && !defenseState.waveClearPending) {
        defenseState.waveClearPending = true;
        const clearedWave = defenseState.wave;
        rpgState.highestWave = Math.max(rpgState.highestWave || 0, clearedWave);
        if (fxApi) {
          fxApi.pillar();
          fxApi.floatText(`🏆 WAVE ${clearedWave} 완벽 클리어!!`, '#facc15', 1.92, 0.17, 2.5);
        }
        playAnimation && playAnimation('HappySpin', { durationMs: 2800, emotion: 'proud' });
        const gReward = 80 + clearedWave * 35;
        const xReward = 45 + clearedWave * 15;
        const cReward = clearedWave % 5 === 0 ? 3 : 1;
        if (typeof window.emitPpongSync === 'function') {
          window.emitPpongSync({
            type: 'wave_defense_result',
            victory: true,
            wave: clearedWave,
            goldReward: gReward,
            xpReward: xReward,
            coreReward: cReward,
            rewardGold: gReward,
            rewardXp: xReward,
            rewardCore: cReward
          });
        }
        setTimeout(() => {
          if (combatState.mode === 'defense') {
            stopCombatAndDefense();
          }
        }, 2600);
      }
    }
  }

  function syncRPGStateFromPython(newState) {
    if (!newState || typeof newState !== 'object') return;
    Object.assign(rpgState, newState);
    if (newState.worldview && WORLDVIEW_THEMES[newState.worldview]) {
      applyWorldviewTheme(newState.worldview);
    } else {
      rebuildHeroWeapon();
    }
  }

  return {
    updateWorldRPGDefense,
    startSkirmish,
    startWaveDefense,
    stopCombatAndDefense,
    triggerCursorSmite,
    applyWorldviewTheme,
    syncRPGStateFromPython,
    getRPGState: () => ({ ...rpgState }),
    isCombatActive: () => combatState.mode !== 'none',
    getCombatMode: () => combatState.mode
  };
}
