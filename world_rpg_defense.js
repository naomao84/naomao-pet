/**
 * world_rpg_defense.js — v8.0 (Professional CC0 .glb 3D Character Assets, Skeletal Animation FSM, TTK Balance & Tactical Defense)
 * =================================================================================================================================
 * Implements:
 * 1. Authentic 3D Character & Weapon .glb Asset Pipeline (`EnemyGlbAssetRegistry`, `GLTFLoader`, `SkeletonUtils.clone()`):
 *    - 23 Rigged Bracket/Role 3D Enemy Models (KayKit CC0 + Quaternius CC0) across Beasts, Mecha Golems, Undead Knights & Apex Overlords.
 *    - Auto-normalization to target scale & ground plane (`y = 0`), embedded light stripping, SSS + Fresnel Rim shader upgrade.
 *    - Real 3D .glb weapons & shields (`Sword_Golden`, `Shield_Heater`, `Shield_Celtic_Golden`, `Spear`, `Hammer_Double`, `Bow_Evil`, `Scythe`)
 *      bound to discovered skeleton hand sockets via world-matrix bone tracking.
 * 2. Skeletal Animation FSM (`THREE.AnimationMixer` + `crossFadeTo` + Post-Mixer Additive Bone Layering):
 *    - 6 canonical states (`IDLE`, `WALK`, `RUN`, `ATTACK`, `HIT`, `DEATH`), velocity-locked `timeScale`, Hit-Frame attack impact sync,
 *      rest-pose-relative missing clip synthesis, Look-At tracking, Hit Recoil, Stun Wobble & Boss Phase 2 Enrage / Cast layers.
 * 3. TTK-Balanced Combat Math, 4 Tactical Roles, Every-5-Wave Bosses, 3D Turrets, Chronicles & Tactical HUD (`[Q/W/E/1~4]`).
 */

export function createWorldRPGDefenseSubsystem(ctx) {
  const {
    THREE,
    GLTFLoader,
    DRACOLoader,
    SkeletonUtils,
    createSoftVinylMaterial,
    scene,
    camera,
    characterPivot,
    stageGroup,
    hemiLight,
    keyLight,
    fillLight = null,
    backRimLight,
    getRigBones,
    setStageYawOverride,
    setHeroAnimTimeScale,
    addBoneEulerOffset,
    playAnimation,
    triggerEmotionEmote,
    primaryCharId = 'ppong',
    partnerCharId = 'tree',
    partnerStageGroup = null,
    partnerPivot = null,
    getPartnerRigBones = null,
    ensurePartnerRigReady = null,
    playPartnerAnimation = null,
    isPartnerReady = null,
  } = ctx;

  const PARTNER_LABEL = partnerCharId === 'tree' ? 'TREE' : 'PPONG';
  const PARTNER_NAME_KR = partnerCharId === 'tree' ? '트리' : '퐁퐁이';

  // ===========================================================================
  // 1. Persistent RPG State, TTK Weapon Specs, Tactical Roles & Chronicles
  // ===========================================================================
  const rpgState = {
    worldview: 'fantasy',
    gold: 250,
    etherCores: 3,
    highestWave: 1,
    equippedWeapon: 'fist',
    unlockedWeapons: ['fist'],
    weaponEnhance: 0,
    weaponTier: 1,
    petLevel: 1,
    turrets: {
      barricade: 1,
      ballista: 1,
      cannon: 0,
      frost: 0,
      arc: 0,
      sniper: 0,
    },
    towerPads: {
      pad_0: { type: 'ballista', level: 1 },
      pad_1: { type: null, level: 0 },
      pad_2: { type: null, level: 0 },
      pad_3: { type: null, level: 0 },
      pad_4: { type: null, level: 0 },
    },
    typingStats: {
      level: 1,
      totalKeystrokes: 0,
      curLevelProgress: 0,
      curLevelReq: 10000,
      liveCpm: 0,
      atkMult: 1.0,
      towerDmgMult: 1.0,
      towerSpdMult: 1.0,
      upgradeDiscount: 0.0,
      skillCdMult: 1.0,
      armorPenBonus: 0.0,
    },
    dualHeroEnabled: true,
    farm: {
      planted: true,
      cropType: '튼튼 감자',
      growth: 0.45,
    },
    bentos: {
      potato_fish: 1,
      trout_steak: 0,
      carp_stew: 0,
      star_emperor: 0,
    },
    consumables: {
      hp_potion: 2,
      haste_elixir: 1,
      rage_elixir: 1,
      meteor_scroll: 1,
      shield_scroll: 1,
      luck_potion: 1,
    },
    excavation: {
      active: false,
      progress: 0.0,
    },
    basecampVisible: true,
    workSafeMode: false,
  };

  // Camera Distance Constants: wide panoramic Z (39.5) keeps Ppong-ppong-i, enemies & tower at compact minimum size across desktop
  const NORMAL_CAMERA_POS = { x: 0, y: 1.15, z: 6.65, lookY: 1.05 };
  const DEFENSE_CAMERA_POS = { x: 0, y: 1.02, z: 39.5, lookY: 1.02 };

  // Deliberate, Weighty Weapon Specs (slower readable attack rhythm + higher per-hit impact)
  const WEAPON_SPECS = {
    fist: {
      key: 'fist',
      name: '👊 맨손 무투 (격투)',
      engageRange: 1.35,
      apsMult: 0.96,
      atkMult: 1.28,
      armorPen: 0.00,
      knockback: 0.55,
      animDur: 0.72,
      hitRatio: 0.40,
      isRanged: false,
    },
    sword: {
      key: 'sword',
      name: '🗡️ 기사단 룬 명검 (칼)',
      engageRange: 1.78,
      apsMult: 0.86,
      atkMult: 1.52,
      armorPen: 0.15,
      knockback: 0.78,
      animDur: 0.86,
      hitRatio: 0.42,
      isRanged: false,
    },
    bow: {
      key: 'bow',
      name: '🏹 엘프의 바람 장궁 (활)',
      engageRange: 7.40,
      apsMult: 0.84,
      atkMult: 1.44,
      armorPen: 0.20,
      knockback: 0.45,
      animDur: 0.88,
      hitRatio: 0.48,
      isRanged: true,
    },
    gun: {
      key: 'gun',
      name: '🔫 네온 플라즈마 블래스터',
      engageRange: 9.20,
      apsMult: 0.92,
      atkMult: 1.48,
      armorPen: 0.35,
      knockback: 0.62,
      animDur: 0.80,
      hitRatio: 0.34,
      isRanged: true,
    },
  };

  // Stage-Bracket Soft-Vinyl Monster Species (Balanced TTK HP & Armor)
  const STAGE_BRACKET_SPECS = [
    {
      bracket: 0,
      stageRange: '1~10단계',
      speciesKey: 'mochi_fox',
      speciesTitle: '모찌 여우 도적단',
      bodyHex: 0xff9ebb,
      bellyHex: 0xfff1f5,
      sssHex: 0xff5e94,
      rimHex: 0xfde047,
      eyeHex: 0x1e1024,
      baseHp: 115,
      baseArmor: 2,
      baseAtk: 9,
      baseSpeed: 1.38,
      loot: { name: '모찌 여우의 별빛 털뭉치', icon: '🧶', tier: 'Common' },
    },
    {
      bracket: 1,
      stageRange: '11~20단계',
      speciesKey: 'clockwork_bot',
      speciesTitle: '태엽 기갑 골렘단',
      bodyHex: 0x7dd3fc,
      bellyHex: 0xf0f9ff,
      sssHex: 0x38bdf8,
      rimHex: 0xa5f3fc,
      eyeHex: 0x22d3ee,
      baseHp: 460,
      baseArmor: 7,
      baseAtk: 18,
      baseSpeed: 1.46,
      loot: { name: '고대 태엽 에테르 기어', icon: '⚙️', tier: 'Rare' },
    },
    {
      bracket: 2,
      stageRange: '21~30단계',
      speciesKey: 'plush_knight',
      speciesTitle: '황혼 다크나이트단',
      bodyHex: 0xc084fc,
      bellyHex: 0xf5f3ff,
      sssHex: 0xa855f7,
      rimHex: 0xf472b6,
      eyeHex: 0xfacc15,
      baseHp: 1850,
      baseArmor: 14,
      baseAtk: 30,
      baseSpeed: 1.54,
      loot: { name: '친위대 룬 마력 훈장', icon: '🛡️', tier: 'Epic' },
    },
    {
      bracket: 3,
      stageRange: '31단계+',
      speciesKey: 'star_overlord',
      speciesTitle: '심연 드래곤 마왕군',
      bodyHex: 0xfb7185,
      bellyHex: 0xfff1f2,
      sssHex: 0xf43f5e,
      rimHex: 0xfacc15,
      eyeHex: 0xfde047,
      baseHp: 7400,
      baseArmor: 24,
      baseAtk: 46,
      baseSpeed: 1.62,
      loot: { name: '초월자의 황금 코어 왕관', icon: '👑', tier: 'Legendary' },
    },
  ];

  // Tactical Combat Roles + Dedicated Boss Archetype (Kingdom Rush / Arknights Inspired)
  const TACTICAL_ROLE_SPECS = {
    vanguard: {
      key: 'vanguard',
      title: '돌격병',
      roleBadge: '⚔️ 돌격병',
      icon: '⚔️',
      hpMult: 1.00,
      shieldMult: 0.00,
      armorBonus: 0,
      spdMult: 1.12,
      atkMult: 1.00,
      attackRange: 0.95,
      scaleMult: 1.12,
      hpBarColor: 0x22c55e,
    },
    shield_tank: {
      key: 'shield_tank',
      title: '방패병',
      roleBadge: '🛡️ 중갑 방패병',
      icon: '🛡️',
      hpMult: 1.55,
      shieldMult: 0.90,
      armorBonus: 6,
      spdMult: 0.82,
      atkMult: 1.20,
      attackRange: 1.05,
      scaleMult: 1.26,
      hpBarColor: 0x38bdf8,
    },
    arcane_ranger: {
      key: 'arcane_ranger',
      title: '마도사',
      roleBadge: '🔮 원거리 포격병',
      icon: '🔮',
      hpMult: 0.85,
      shieldMult: 0.00,
      armorBonus: 0,
      spdMult: 0.96,
      atkMult: 1.15,
      attackRange: 4.60,
      scaleMult: 1.14,
      hpBarColor: 0xc084fc,
    },
    support_shaman: {
      key: 'support_shaman',
      title: '주술사',
      roleBadge: '🚩 치유 샤먼',
      icon: '🚩',
      hpMult: 1.15,
      shieldMult: 0.30,
      armorBonus: 2,
      spdMult: 0.86,
      atkMult: 0.85,
      attackRange: 3.60,
      healInterval: 3.5,
      scaleMult: 1.18,
      hpBarColor: 0x4ade80,
    },
    boss: {
      key: 'boss',
      title: '군단장',
      roleBadge: '👑 군단장 보스',
      icon: '👑',
      hpMult: 6.50,
      shieldMult: 1.65,
      armorBonus: 10,
      spdMult: 0.78,
      atkMult: 1.85,
      attackRange: 1.38,
      scaleMult: 1.00,
      hpBarColor: 0xf43f5e,
    },
  };

  // Wave Story Chronicles across 4 Worldviews
  const WAVE_STORY_CHRONICLES = {
    fantasy: {
      worldTitle: '🏰 판타지 왕국: 별빛 성소 수호기',
      intro: {
        badge: 'CHAPTER I · 성소 방어전',
        speaker: '🧙‍♂️ 대현자 루멘',
        title: '균열에서 쏟아져 나온 침략 군단!',
        line: '“뽕뽕이여! 왼쪽 아래 별빛 성소를 사수하라! 사방에서 몰려오는 적들을 막아내야 한다!”',
        accent: '#38bdf8',
      },
      waveMilestones: {
        1: { title: 'Stage 1 · 여우 정찰대 습격', line: '모찌 여우 돌격병과 방패병이 성소를 향해 돌진합니다!' },
        2: { title: 'Stage 2 · 강철 방패 전열', line: '⚠️ 전면 방패를 든 [중갑 방패병]을 집중 공격해 방패를 부수세요!' },
        3: { title: 'Stage 3 · 원거리 비전 포격', line: '⚠️ 후방에서 보라색 마법탄을 쏘는 [마도사]를 먼저 끊어내세요!' },
        4: { title: 'Stage 4 · 치유 주술사 합류', line: '⚠️ 주변 적을 치유하는 [주술사]가 나타났습니다! [E] 오버드라이브로 돌파하세요!' },
        5: { title: 'Stage 5 · 군단장 보스 강림!', line: '🔥 붉은 경고 장판(Red AoE)은 회피하거나 마우스 클릭으로 차단하세요!' },
      },
      bosses: [
        {
          bracket: 0,
          name: '구미호 대군주 폭시온',
          title: '🦊 별빛 숲의 폭군',
          introLine: '“폭신폭신한 성소 코어군! 내 아홉 꼬리의 간식으로 삼아주마!”',
          phase2Line: '“크아악! 감히 내 털을 그을려?! 붉은 여우불 유성 장판을 받아라!!”',
        },
        {
          bracket: 1,
          name: '태엽 거신 크로노스-IX',
          title: '⚙️ 고대 유적 파수꾼',
          introLine: '“삐빅— 성소 마력원 탐지 완료. 전면 장갑 전개 및 소각 프로토콜 가동!”',
          phase2Line: '“경고: 동력 50% 이하! 과부하 충격파 장판 강제 개방!!”',
        },
        {
          bracket: 2,
          name: '황혼 흑기사 아스모델',
          title: '🛡️ 몰락한 친위대장',
          introLine: '“내 룬 방패를 뚫을 수 있을 것 같으냐? 전군, 성소를 짓밟아라!”',
          phase2Line: '“방패가 금이 가다니…! 황혼의 심판 장판으로 끝내주마!”',
        },
        {
          bracket: 3,
          name: '심연 마왕 아스트라',
          title: '👑 차원 균열의 지배자',
          introLine: '“데스크톱의 수호자여, 영원한 밤의 장막 앞에 무릎 꿇어라!”',
          phase2Line: '“감히 마왕의 피를 보게 하다니! 차원 붕괴 메테오를 견뎌보아라!”',
        },
      ],
      victory: {
        speaker: '🦄 수호기사 뽕뽕이',
        title: '✨ 성소 방어 대승리!',
        line: '“별빛 성소를 지켜냈어! 전리품 코어와 골드로 무기와 포탑을 강화하자!”',
      },
    },
    cyberpunk: {
      worldTitle: '🌃 네온 시티: 메인프레임 방화벽 수호',
      intro: {
        badge: 'NET-DEFENSE · 방화벽 가동',
        speaker: '🕶️ 오퍼레이터 제로',
        title: '블랙 아이스 해커 군단 침투!',
        line: '“뽕뽕이! 좌하단 양자 서버 코어가 뚫리기 전에 방패 기갑병과 해커 마도사를 부숴!”',
        accent: '#f43f5e',
      },
      waveMilestones: {
        1: { title: 'Stage 1 · 크롬 스카우트 패킷 침투', line: '고속 돌파형 돌격 드론과 방화벽 방패병이 접근합니다!' },
        2: { title: 'Stage 2 · 방패 방화벽 장갑대', line: '⚠️ 전면 실드 탱커의 에너지 방패를 집중 사격으로 붕괴시키세요!' },
        3: { title: 'Stage 3 · 바이러스 스나이퍼 전개', line: '⚠️ 후열 원거리 해커 마도사의 보라색 패킷탄을 먼저 끊으세요!' },
        4: { title: 'Stage 4 · 나노 복구 봇 합류', line: '⚠️ 아군 적을 수리하는 주술사 유닛을 [Q] 유성우로 제압하세요!' },
        5: { title: 'Stage 5 · 오버로드 백신 파괴 보스!', line: '🔥 붉은 EMP 예고 장판은 커서 클릭(강타) 2타로 차단할 수 있습니다!' },
      },
      bosses: [
        {
          bracket: 0,
          name: '네온 팬텀 K-9',
          title: '🦊 크롬 폭스 넷러너',
          introLine: '“방화벽이 꽤 귀여운데? 3분 안에 루트 권한을 탈취해주지!”',
          phase2Line: '“오버클럭 200%!! EMP 플라즈마 장판을 피할 수 있을까?!”',
        },
        {
          bracket: 1,
          name: '메카 타이탄 MK-II',
          title: '⚙️ 사이버 팩토리 수호기갑',
          introLine: '“시스템 장악 개시. 모든 방어 터렛 무력화 프로토콜 실행.”',
          phase2Line: '“코어 온도 임계점 돌파!! 전 구역 고압 스파크 방출!”',
        },
        {
          bracket: 2,
          name: '사이퍼 리퍼 V',
          title: '🛡️ 블랙 아이스 집행관',
          introLine: '“내 양자 룬 방패를 뚫고 서버를 지킬 수 있을 것 같으냐?”',
          phase2Line: '“암호 해독 완료! 데이터 소멸 장판을 전개한다!!”',
        },
        {
          bracket: 3,
          name: '제네시스 코어 오메가',
          title: '👑 네오 도쿄 최후의 AI',
          introLine: '“디지털 세계의 주인은 나다! 인간과 수호 펫을 소거한다!”',
          phase2Line: '“최종 셧다운 시퀀스 개시! 차원 바이러스 폭풍을 견뎌봐라!”',
        },
      ],
      victory: {
        speaker: '🦄 넷러너 뽕뽕이',
        title: '⚡ 해킹 웨이브 완벽 차단!',
        line: '“악성 군단 클리어! 확보한 크레딧으로 플라즈마 무장을 업그레이드하자!”',
      },
    },
    scifi: {
      worldTitle: '🚀 오비탈 스테이션: 다크매터 코어 방어',
      intro: {
        badge: 'ORBITAL ALERT · 궤도 방어',
        speaker: '🛰️ 함교 AI 아테나',
        title: '외계 보이드 함대 강습 부대 워프!',
        line: '“주 동력로를 사수하십시오! 발리스타와 아크 캐논, 전술 스킬을 총동원하세요!”',
        accent: '#60a5fa',
      },
      waveMilestones: {
        1: { title: 'Stage 1 · 궤도 정찰 포드 착륙', line: '외계 선봉대와 궤도 장갑병이 도킹 베이를 향해 돌격합니다!' },
        2: { title: 'Stage 2 · 플라즈마 실드 대열', line: '⚠️ 전면 궤도 방패를 집중 타격해 가드 브레이크를 유도하세요!' },
        3: { title: 'Stage 3 · 다크매터 저격수 출현', line: '⚠️ 원거리 에너지 볼트를 발사하는 마도사 유닛을 우선 제거하세요!' },
        4: { title: 'Stage 4 · 생체 재생 드론 배치', line: '⚠️ 주변 침략군을 회복시키는 주술사 개체를 먼저 격추하세요!' },
        5: { title: 'Stage 5 · 기함 사령관 강하!', line: '🔥 보스의 궤도 폭격 예고 원(Red AoE)은 커서 클릭으로 저지하세요!' },
      },
      bosses: [
        {
          bracket: 0,
          name: '보이드 제독 볼텍스',
          title: '🛸 성간 침략군 선봉장',
          introLine: '“이 정거장의 다크매터 코어는 우리 제국이 접수한다!”',
          phase2Line: '“주포 궤도 폭격 좌표 입력 완료! 붉은 타겟 구역을 소멸시켜라!”',
        },
        {
          bracket: 1,
          name: '오비탈 골렘 X-7',
          title: '⚙️ 심우주 중장갑 거신',
          introLine: '“선체 외부 장갑 전개. 방어선 돌파까지 12초.”',
          phase2Line: '“리액터 폭주! 중력자 충격파를 방사한다!!”',
        },
        {
          bracket: 2,
          name: '네뷸라 팔라딘 자르',
          title: '🛡️ 성운 기사단 단장',
          introLine: '“별빛 아래 내 포톤 방패를 깰 자는 존재하지 않는다!”',
          phase2Line: '“성운 심판 가동! 정거장을 산산조각 내주마!!”',
        },
        {
          bracket: 3,
          name: '코스모스 파괴신 보이드',
          title: '👑 은하계 정복 군주',
          introLine: '“작은 유니콘 수호자여, 은하 함대의 위압감 앞에 무릎 꿇어라!”',
          phase2Line: '“슈퍼노바 붕괴 프로토콜! 전 함대 일제 포격 개시!!”',
        },
      ],
      victory: {
        speaker: '🦄 우주 사령관 뽕뽕이',
        title: '🌟 궤도 스테이션 방어 완료!',
        line: '“침략군 격퇴! 획득한 코어로 오리할콘 아크포를 증축하자!”',
      },
    },
    cozy: {
      worldTitle: '🌼 코지 힐링 아일랜드: 낮잠 쿠션 성소',
      intro: {
        badge: 'COZY GUARD · 평화 수호',
        speaker: '🌼 정원사 요정',
        title: '장난꾸러기 솜사탕 친구들의 소동!',
        line: '“뽕뽕아~ 장난꾸러기들이 별사탕 쿠션을 탐내며 몰려와! 비눗방울과 포옹으로 진정시켜주자!”',
        accent: '#fde047',
      },
      waveMilestones: {
        1: { title: 'Stage 1 · 말랑 여우 소동 시작!', line: '장난꾸러기 젤리 여우들이 별사탕 성소를 향해 달려옵니다!' },
        2: { title: 'Stage 2 · 폭신 방석 방패대', line: '⚠️ 푹신한 방석을 앞세운 방패병을 톡톡 두드려 깨워주세요!' },
        3: { title: 'Stage 3 · 별사탕 마법사 등장', line: '⚠️ 멀리서 보라색 꿀방울을 던지는 장난꾸러기 마도사를 먼저 진정시키세요!' },
        4: { title: 'Stage 4 · 간식 나누미 주술사', line: '⚠️ 친구들에게 체력을 나눠주는 주술사를 [Q] 별똥별로 놀라게 해주세요!' },
        5: { title: 'Stage 5 · 낮잠 대장 보스 행차!', line: '🔥 붉은 딸기 시럽 예고 장판이 뜨면 톡톡 클릭해서 취소시키세요!' },
      },
      bosses: [
        {
          bracket: 0,
          name: '대왕 모찌 폭신왕',
          title: '👑 낮잠 방해꾼 대장',
          introLine: '“헤헤! 별빛 도시락이랑 쿠션은 전부 내 차지다~!”',
          phase2Line: '“간지럼 태우지 마~! 왕큰 딸기 시럽 방울을 던질 거야!!”',
        },
        {
          bracket: 1,
          name: '오르골 거인 팅클',
          title: '⚙️ 태엽 장난감 대장',
          introLine: '“딸랑딸랑~ 태엽 소리 들으면서 전부 낮잠 시간이다!”',
          phase2Line: '“태엽이 너무 빨리 감겼어!! 왕큰 멜로디 충격파 나간다~!”',
        },
        {
          bracket: 2,
          name: '베개 기사 펌킨',
          title: '🛡️ 푹신 요새 수호병',
          introLine: '“내 황금 구름 베개 방패는 뚫을 수 없을걸~!”',
          phase2Line: '“베개 깃털 대폭발! 폭신폭신 구름 소나기 받아라~!”',
        },
        {
          bracket: 3,
          name: '별사탕 드래곤 슈가',
          title: '👑 달콤한 섬의 장난왕',
          introLine: '“세상에서 제일 달콤한 도시락 파티를 차지하러 왔다!”',
          phase2Line: '“초대형 카라멜 유성우 소환! 모두 달콤함에 빠져봐라~!”',
        },
      ],
      victory: {
        speaker: '🦄 힐링 뽕뽕이',
        title: '🌈 평화로운 티타임 수호!',
        line: '“모두 사이좋게 돌아갔어! 수확한 작물과 물고기로 맛있는 도시락을 만들자!”',
      },
    },
  };

  const WORLDVIEW_THEMES = {
    fantasy: {
      key: 'fantasy',
      name: '🏰 판타지 왕국',
      hemiSky: 0xfff8fc,
      hemiGround: 0xdbeafe,
      keyColor: 0xfff5ea,
      fillColor: 0xffe8dc,
      rimColor: 0x93c5fd,
      portalColor: 0x38bdf8,
      weaponColor: [0x93c5fd, 0x38bdf8, 0xa855f7, 0xfacc15],
    },
    cyberpunk: {
      key: 'cyberpunk',
      name: '🌃 사이버펑크 네온 시티',
      hemiSky: 0xf5d0fe,
      hemiGround: 0x0f172a,
      keyColor: 0xe0f2fe,
      fillColor: 0x38bdf8,
      rimColor: 0xf43f5e,
      portalColor: 0xf43f5e,
      weaponColor: [0x22d3ee, 0xf43f5e, 0xd946ef, 0xfacc15],
    },
    scifi: {
      key: 'scifi',
      name: '🚀 SF 오비탈 스테이션',
      hemiSky: 0xe0f2fe,
      hemiGround: 0x1e293b,
      keyColor: 0xf8fafc,
      fillColor: 0x93c5fd,
      rimColor: 0x38bdf8,
      portalColor: 0x60a5fa,
      weaponColor: [0x60a5fa, 0x34d399, 0x818cf8, 0xfbbf24],
    },
    cozy: {
      key: 'cozy',
      name: '🌼 코지 힐링 아일랜드',
      hemiSky: 0xfef9c3,
      hemiGround: 0xd9f99d,
      keyColor: 0xffedd5,
      fillColor: 0xfef08a,
      rimColor: 0xfde047,
      portalColor: 0x38bdf8,
      weaponColor: [0xf9a8d4, 0x6ee7b7, 0xfde047, 0xc4b5fd],
    },
  };

  function makePlumpStarGeo(outerR = 0.22, innerR = 0.11, points = 5, depth = 0.06) {
    const s = new THREE.Shape();
    for (let i = 0; i < points * 2; i++) {
      const a = (i * Math.PI) / points - Math.PI * 0.5;
      const r = i % 2 === 0 ? outerR : innerR;
      const x = Math.cos(a) * r;
      const y = Math.sin(a) * r;
      if (i === 0) s.moveTo(x, y);
      else s.lineTo(x, y);
    }
    s.closePath();
    const g = new THREE.ExtrudeGeometry(s, {
      depth,
      bevelEnabled: true,
      bevelThickness: depth * 0.48,
      bevelSize: depth * 0.38,
      bevelSegments: 2,
    });
    g.center();
    return g;
  }

  const SHARED_GEO = {
    unitPlane: new THREE.PlaneGeometry(1, 1),
    ringBase: new THREE.RingGeometry(0.18, 0.30, 28),
    shadowDisc: new THREE.PlaneGeometry(1.18, 1.18),
    slashRibbon: new THREE.RingGeometry(0.32, 0.90, 28, 1, -Math.PI * 0.48, Math.PI * 0.96),
    whirlwindRibbon: new THREE.RingGeometry(0.38, 1.18, 36),
    particleSphere: new THREE.SphereGeometry(0.064, 8, 8),
    particleStar: makePlumpStarGeo(0.085, 0.038, 4, 0.025),
    meteorRock: new THREE.DodecahedronGeometry(0.36, 1),
    meteorCore: new THREE.SphereGeometry(0.24, 12, 12),
    meteorHalo: new THREE.SphereGeometry(0.50, 14, 12),
    arrowShaft: new THREE.CylinderGeometry(0.018, 0.014, 0.68, 8),
    arrowHead: new THREE.OctahedronGeometry(0.056, 0),
    arrowFeather: new THREE.BoxGeometry(0.08, 0.13, 0.01),
    bulletTracer: new THREE.CapsuleGeometry(0.036, 0.30, 6, 8),
    cannonShell: new THREE.SphereGeometry(0.13, 14, 12),
    cannonHalo: new THREE.SphereGeometry(0.22, 12, 10),
    plasmaOrb: new THREE.SphereGeometry(0.095, 12, 12),
    enemyBolt: new THREE.OctahedronGeometry(0.105, 1),
    frostOrb: new THREE.OctahedronGeometry(0.14, 0),
    starOrb: makePlumpStarGeo(0.22, 0.115, 5, 0.07),
    starComet: makePlumpStarGeo(0.16, 0.082, 5, 0.045),
    telegraphQuad: new THREE.PlaneGeometry(3.8, 3.8),
    shockwaveQuad: new THREE.PlaneGeometry(2.0, 2.0),
    ribbonQuad: new THREE.PlaneGeometry(1.0, 1.0),
    orb: new THREE.SphereGeometry(0.16, 12, 12),
    orbRing: new THREE.TorusGeometry(0.38, 0.034, 10, 28),
  };
  SHARED_GEO.arrowShaft.rotateX(Math.PI / 2);
  SHARED_GEO.arrowHead.rotateX(Math.PI / 2);
  SHARED_GEO.arrowHead.translate(0, 0, 0.34);
  SHARED_GEO.arrowFeather.translate(0, 0, -0.28);
  SHARED_GEO.bulletTracer.rotateX(Math.PI / 2);

  const SHARED_MAT = {
    softContactShadow: new THREE.ShaderMaterial({
      uniforms: {},
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        varying vec2 vUv;
        void main() {
          vec2 p = vUv * 2.0 - 1.0;
          float r2 = dot(p, p);
          if (r2 > 1.0) discard;
          float g = exp(-r2 * 3.1) * (1.0 - smoothstep(0.58, 1.0, sqrt(r2)));
          gl_FragColor = vec4(0.06, 0.09, 0.16, g * 0.36);
        }
      `,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    }),
    bossAuraRing: new THREE.MeshBasicMaterial({
      color: 0xf43f5e,
      side: THREE.DoubleSide,
      transparent: true,
      opacity: 0.65,
      depthWrite: false,
      toneMapped: false,
    }),
  };

  // ===========================================================================
  // 2. Scene Hierarchy, Story Chronicle Banner & Tactical Skill HUD (DOM)
  // ===========================================================================
  const worldRoot = new THREE.Group();
  worldRoot.name = 'WorldRPGDefenseRoot';
  scene.add(worldRoot);

  const enemiesGroup = new THREE.Group();
  enemiesGroup.name = 'DesktopIndependentEnemies';
  worldRoot.add(enemiesGroup);

  const projectilesGroup = new THREE.Group();
  projectilesGroup.name = 'ProjectilesAndVFX';
  worldRoot.add(projectilesGroup);

  const excavationGroup = new THREE.Group();
  excavationGroup.visible = false;
  worldRoot.add(excavationGroup);

  const heroCombatShadow = new THREE.Mesh(SHARED_GEO.shadowDisc, SHARED_MAT.softContactShadow);
  heroCombatShadow.rotation.x = -Math.PI * 0.34;
  heroCombatShadow.scale.setScalar(1.20);
  heroCombatShadow.renderOrder = 3;
  heroCombatShadow.visible = false;
  worldRoot.add(heroCombatShadow);

  const partnerCombatShadow = new THREE.Mesh(SHARED_GEO.shadowDisc, SHARED_MAT.softContactShadow);
  partnerCombatShadow.rotation.x = -Math.PI * 0.34;
  partnerCombatShadow.scale.setScalar(1.16);
  partnerCombatShadow.renderOrder = 3;
  partnerCombatShadow.visible = false;
  worldRoot.add(partnerCombatShadow);

  const padTowersGroup = new THREE.Group();
  padTowersGroup.name = 'DesktopBuildPadTowers';
  padTowersGroup.visible = false;
  worldRoot.add(padTowersGroup);

  const TOWER_DEFS = {
    ballista: {
      key: 'ballista',
      name: '발리스타',
      icon: '🏹',
      role: '단일·속사',
      colorHex: 0xb45309,
      accentHex: 0xfbbf24,
      accentCss: '#fbbf24',
      costs: [90, 140, 220, 320, 450],
      dmgMult: [1.0, 1.35, 1.75, 2.25, 2.90],
      rate: [1.15, 1.28, 1.42, 1.58, 1.75],
      range: 7.8,
      armorPen: 0.18,
    },
    cannon: {
      key: 'cannon',
      name: '봄버드 대포',
      icon: '💣',
      role: '광역 스플래시',
      colorHex: 0xc2410c,
      accentHex: 0xf97316,
      accentCss: '#fb923c',
      costs: [130, 190, 280, 400, 560],
      dmgMult: [1.6, 2.15, 2.80, 3.60, 4.60],
      rate: [0.48, 0.52, 0.56, 0.62, 0.68],
      range: 6.5,
      splashRadius: 2.2,
      armorPen: 0.35,
    },
    frost: {
      key: 'frost',
      name: '서리 프리즘',
      icon: '❄️',
      role: '감속·치유반감',
      colorHex: 0x0284c7,
      accentHex: 0x7dd3fc,
      accentCss: '#38bdf8',
      costs: [110, 170, 250, 360, 500],
      dmgMult: [0.45, 0.60, 0.80, 1.05, 1.35],
      rate: [0.85, 0.92, 1.00, 1.08, 1.18],
      range: 5.8,
      slowSec: 3.0,
      armorPen: 0.25,
    },
    arc: {
      key: 'arc',
      name: '번개 파일런',
      icon: '⚡',
      role: '연쇄 감전',
      colorHex: 0x4338ca,
      accentHex: 0x38bdf8,
      accentCss: '#818cf8',
      costs: [150, 220, 320, 450, 620],
      dmgMult: [0.95, 1.30, 1.70, 2.20, 2.85],
      rate: [0.78, 0.85, 0.92, 1.00, 1.10],
      range: 6.8,
      chains: [3, 4, 4, 5, 6],
      armorPen: 0.52,
    },
    sniper: {
      key: 'sniper',
      name: '별빛 스나이퍼',
      icon: '🎯',
      role: '초장거리 관통',
      colorHex: 0x6d28d9,
      accentHex: 0xfde047,
      accentCss: '#c084fc',
      costs: [170, 250, 360, 510, 700],
      dmgMult: [2.8, 3.8, 5.0, 6.5, 8.4],
      rate: [0.32, 0.36, 0.40, 0.44, 0.48],
      range: 13.5,
      armorPen: 0.65,
    },
  };

  const PAD_SLOT_SPECS = [
    { id: 'pad_0', nx: 0.165, ny: 0.28, label: '서쪽 요충지' },
    { id: 'pad_1', nx: 0.255, ny: 0.42, label: '북서 성벽' },
    { id: 'pad_2', nx: 0.425, ny: 0.32, label: '중앙 교차로' },
    { id: 'pad_3', nx: 0.595, ny: 0.36, label: '동쪽 초소' },
    { id: 'pad_4', nx: 0.355, ny: 0.56, label: '고지대 전망' },
  ];

  // Tactical Chokepoint Lane Waypoint Chains (normalized desktop world coords routing spawns past build pads!)
  const LANE_WAYPOINTS = [
    [ { nx: 0.38, ny: 0.60 }, { nx: 0.25, ny: 0.40 }, { nx: 0.14, ny: 0.20 } ], // Zone 0: North -> pad_4 -> pad_1 -> pad_0 -> Base
    [ { nx: 0.62, ny: 0.46 }, { nx: 0.42, ny: 0.34 }, { nx: 0.17, ny: 0.22 } ], // Zone 1: North-East -> pad_3 -> pad_2 -> pad_0 -> Base
    [ { nx: 0.62, ny: 0.34 }, { nx: 0.40, ny: 0.28 }, { nx: 0.16, ny: 0.19 } ], // Zone 2: East -> pad_3 -> pad_2 -> pad_0 -> Base
    [ { nx: 0.52, ny: 0.24 }, { nx: 0.32, ny: 0.22 }, { nx: 0.15, ny: 0.16 } ], // Zone 3: South-East -> pad_2/0 -> Base
  ];

  // Story Banner & AAA 3D Defense Tactical Command Dock (DOM)
  let storyBannerTimer = null;
  let lastHudSyncAt = 0;
  let prevHudSnap = null;
  let lastPopoverGold = -1;
  let coachToastTimer = null;
  function ensureDefenseDomOverlays() {
    if (typeof document === 'undefined') return;
    if (!document.getElementById('defense-hud-styles')) {
      const styleEl = document.createElement('style');
      styleEl.id = 'defense-hud-styles';
      styleEl.textContent = `
        #defense-story-banner {
          position: fixed;
          top: 16px;
          left: 50%;
          transform: translateX(-50%) translateZ(0);
          width: max-content;
          min-width: min(300px, calc(100vw - 24px));
          max-width: min(580px, calc(100vw - 24px));
          padding: 12px 24px 13px;
          background: linear-gradient(165deg, rgba(20, 29, 48, 0.84) 0%, rgba(11, 16, 30, 0.90) 100%);
          border: 1px solid rgba(255, 255, 255, 0.16);
          border-radius: 18px;
          color: #f8fafc;
          font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Malgun Gothic", sans-serif;
          text-align: center;
          z-index: 9998;
          pointer-events: none;
          box-shadow:
            0 8px 24px rgba(2, 6, 23, 0.36),
            inset 0 1px 0 rgba(255, 255, 255, 0.20),
            inset 0 0 18px rgba(255, 255, 255, 0.04),
            inset 0 -1px 2px rgba(2, 6, 23, 0.55);
          opacity: 0;
          transition: opacity 0.24s cubic-bezier(0.22, 1, 0.36, 1);
        }
        #defense-tactical-hud {
          position: fixed;
          bottom: 18px;
          left: 50%;
          transform: translateX(-50%) translateZ(0);
          display: none;
          align-items: stretch;
          gap: 12px;
          padding: 10px 16px;
          background: linear-gradient(165deg, rgba(20, 29, 48, 0.84) 0%, rgba(11, 16, 30, 0.90) 100%);
          border: 1px solid rgba(255, 255, 255, 0.16);
          border-radius: 20px;
          z-index: 9999;
          pointer-events: auto;
          user-select: none;
          font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Malgun Gothic", sans-serif;
          box-shadow:
            0 10px 28px rgba(2, 6, 23, 0.40),
            inset 0 1px 0 rgba(255, 255, 255, 0.20),
            inset 0 0 20px rgba(255, 255, 255, 0.04),
            inset 0 -1px 2px rgba(2, 6, 23, 0.58);
        }
        #defense-tactical-hud::before {
          content: '';
          position: absolute;
          inset: 1px;
          border-radius: 19px;
          border: 1px solid rgba(255, 255, 255, 0.04);
          pointer-events: none;
        }
        .def-hud-section {
          display: flex;
          align-items: center;
          gap: 8px;
          position: relative;
        }
        .def-hud-divider {
          width: 1px;
          align-self: stretch;
          margin: 6px 2px;
          background: linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.16), rgba(255,255,255,0.02));
        }
        .def-telemetry-col {
          display: flex;
          flex-direction: column;
          justify-content: center;
          gap: 5px;
          min-width: 174px;
          padding: 7px 12px;
          background: rgba(9, 13, 24, 0.56);
          border: 1px solid rgba(255, 255, 255, 0.07);
          border-radius: 14px;
          box-shadow:
            inset 2px 2px 5px rgba(2, 6, 23, 0.68),
            inset -1px -1px 1px rgba(255, 255, 255, 0.06);
        }
        .def-bar-row {
          display: flex;
          flex-direction: column;
          gap: 2px;
        }
        .def-bar-meta {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 10px;
          font-weight: 700;
          letter-spacing: 0.2px;
          color: #cbd5e1;
          white-space: nowrap;
        }
        .def-bar-track {
          position: relative;
          height: 6px;
          width: 100%;
          border-radius: 99px;
          background: rgba(6, 10, 20, 0.88);
          box-shadow: inset 1px 1px 3px rgba(0, 0, 0, 0.72), inset 0 -1px 0 rgba(255, 255, 255, 0.06);
          overflow: hidden;
        }
        .def-bar-fill {
          height: 100%;
          width: 100%;
          border-radius: 99px;
          transition: width 0.16s ease-out;
        }
        .def-skill-card {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 68px;
          height: 64px;
          padding: 5px 4px 4px;
          border-radius: 14px;
          border: 1px solid rgba(255, 255, 255, 0.13);
          background: linear-gradient(165deg, rgba(24, 34, 54, 0.78), rgba(13, 19, 33, 0.88));
          color: #f8fafc;
          cursor: pointer;
          overflow: hidden;
          transition: transform 0.14s cubic-bezier(0.22,1,0.36,1), filter 0.14s ease, border-color 0.16s ease;
          box-shadow:
            0 4px 10px rgba(2, 6, 23, 0.34),
            inset 1px 1px 0 rgba(255, 255, 255, 0.14),
            inset -1px -1px 2px rgba(2, 6, 23, 0.52);
        }
        .def-skill-card:hover:not(.is-cooling) {
          transform: translateY(-2px);
          filter: brightness(1.10);
          border-color: rgba(255, 255, 255, 0.28);
        }
        .def-skill-card:active {
          transform: translateY(1px) scale(0.98);
          box-shadow: inset 2px 2px 5px rgba(2, 6, 23, 0.65);
        }
        .def-skill-card[data-accent="fire"] {
          background: linear-gradient(165deg, rgba(58, 28, 24, 0.78), rgba(26, 14, 16, 0.88));
          border-color: rgba(251, 146, 60, 0.38);
        }
        .def-skill-card[data-accent="aegis"] {
          background: linear-gradient(165deg, rgba(18, 44, 66, 0.78), rgba(11, 24, 42, 0.88));
          border-color: rgba(56, 189, 248, 0.38);
        }
        .def-skill-card[data-accent="titan"] {
          background: linear-gradient(165deg, rgba(64, 22, 34, 0.78), rgba(28, 12, 22, 0.88));
          border-color: rgba(251, 113, 133, 0.42);
        }
        .def-skill-card.is-ready {
          box-shadow:
            0 4px 12px rgba(2, 6, 23, 0.36),
            inset 1px 1px 0 rgba(255, 255, 255, 0.16),
            inset -1px -1px 2px rgba(2, 6, 23, 0.50);
        }
        .def-skill-card.is-cooling {
          border-color: rgba(148, 163, 184, 0.16);
          filter: saturate(0.45) brightness(0.78);
        }
        .def-cd-wipe {
          z-index: 2;
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: var(--cd-pct, 0%);
          background: rgba(6, 10, 22, 0.82);
          border-top: 1px solid rgba(255, 255, 255, 0.24);
          pointer-events: none;
          transition: height 0.12s linear;
        }
        .def-cd-text {
          position: absolute;
          inset: 0;
          display: none;
          align-items: center;
          justify-content: center;
          font-size: 14.5px;
          font-weight: 800;
          color: #f8fafc;
          text-shadow: 0 1px 4px rgba(2, 6, 23, 0.85);
          z-index: 3;
          pointer-events: none;
        }
        .def-skill-card.is-cooling .def-cd-text {
          display: flex;
        }
        .def-keycap {
          position: absolute;
          top: 4px;
          left: 5px;
          min-width: 16px;
          height: 15px;
          padding: 0 4px;
          border-radius: 5px;
          background: rgba(15, 23, 42, 0.72);
          border: 1px solid rgba(255, 255, 255, 0.16);
          font-size: 9px;
          font-weight: 800;
          line-height: 13px;
          color: #e2e8f0;
          text-align: center;
          z-index: 4;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.10);
        }
        .def-slot-icon {
          width: 24px;
          height: 24px;
          margin-top: 5px;
          margin-bottom: 2px;
          filter: drop-shadow(0 1px 2px rgba(2, 6, 23, 0.45));
          z-index: 1;
        }
        .def-slot-label {
          font-size: 10.5px;
          font-weight: 700;
          letter-spacing: -0.2px;
          color: #f1f5f9;
          z-index: 1;
        }
        .def-wep-card {
          position: relative;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          width: 58px;
          height: 64px;
          padding: 5px 4px 4px;
          border-radius: 13px;
          border: 1px solid rgba(255, 255, 255, 0.10);
          background: linear-gradient(165deg, rgba(22, 30, 48, 0.72), rgba(12, 17, 30, 0.84));
          color: #94a3b8;
          cursor: pointer;
          transition: transform 0.12s ease, border-color 0.14s ease, box-shadow 0.14s ease;
          box-shadow:
            0 3px 8px rgba(2, 6, 23, 0.28),
            inset 1px 1px 0 rgba(255, 255, 255, 0.10),
            inset -1px -1px 2px rgba(2, 6, 23, 0.48);
        }
        .def-wep-card:hover {
          transform: translateY(-2px);
          border-color: rgba(255, 255, 255, 0.24);
          color: #f8fafc;
        }
        .def-wep-card.is-equipped {
          border-color: rgba(56, 189, 248, 0.65);
          background: linear-gradient(165deg, rgba(24, 52, 82, 0.84), rgba(14, 30, 52, 0.92));
          color: #f8fafc;
          box-shadow:
            0 4px 12px rgba(14, 165, 233, 0.22),
            inset 1px 1px 0 rgba(255, 255, 255, 0.22),
            inset -1px -1px 2px rgba(2, 6, 23, 0.52);
          transform: translateY(-1px);
        }
        .def-wep-card .def-keycap {
          border-color: rgba(255, 255, 255, 0.12);
          color: #94a3b8;
        }
        .def-wep-card.is-equipped .def-keycap {
          border-color: rgba(56, 189, 248, 0.55);
          color: #7dd3fc;
          background: rgba(12, 74, 110, 0.72);
        }
        #def-live-coach-toast {
          position: fixed;
          bottom: 112px;
          left: 50%;
          transform: translateX(-50%) translateY(6px);
          padding: 8px 18px;
          border-radius: 999px;
          background: linear-gradient(165deg, rgba(20, 29, 48, 0.86), rgba(10, 15, 28, 0.92));
          border: 1px solid rgba(255, 255, 255, 0.17);
          color: #f8fafc;
          font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Malgun Gothic", sans-serif;
          font-size: 12px;
          font-weight: 700;
          letter-spacing: -0.2px;
          z-index: 10000;
          pointer-events: none;
          opacity: 0;
          transition: opacity 0.22s ease, transform 0.22s ease;
          box-shadow:
            0 6px 18px rgba(2, 6, 23, 0.36),
            inset 0 1px 0 rgba(255, 255, 255, 0.18),
            inset 0 0 14px rgba(255, 255, 255, 0.04);
          white-space: nowrap;
        }
        #def-live-coach-toast.visible {
          opacity: 1;
          transform: translateX(-50%) translateY(0);
        }
        #defense-pad-popover {
          position: fixed;
          display: none;
          min-width: 252px;
          max-width: 300px;
          padding: 13px 14px;
          border-radius: 18px;
          background: linear-gradient(165deg, rgba(20, 29, 48, 0.86), rgba(10, 15, 28, 0.92));
          border: 1px solid rgba(255, 255, 255, 0.17);
          color: #f8fafc;
          z-index: 10010;
          pointer-events: auto;
          font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Malgun Gothic", sans-serif;
          box-shadow:
            0 12px 28px rgba(2, 6, 23, 0.44),
            inset 0 1px 0 rgba(255, 255, 255, 0.20),
            inset 0 0 16px rgba(255, 255, 255, 0.04),
            inset 0 -1px 2px rgba(2, 6, 23, 0.55);
        }
        .def-pad-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 7px;
          margin-top: 9px;
        }
        .def-pad-btn {
          display: flex;
          flex-direction: column;
          align-items: flex-start;
          gap: 2px;
          padding: 7px 9px;
          border-radius: 11px;
          border: 1px solid rgba(255, 255, 255, 0.10);
          background: rgba(24, 34, 54, 0.68);
          color: #e2e8f0;
          cursor: pointer;
          font-size: 11px;
          font-weight: 700;
          text-align: left;
          box-shadow: inset 1px 1px 0 rgba(255, 255, 255, 0.08), inset -1px -1px 2px rgba(2, 6, 23, 0.45);
          transition: transform 0.1s ease, border-color 0.12s ease, background 0.12s ease;
        }
        .def-pad-btn:hover:not(:disabled) {
          transform: translateY(-1px);
          border-color: rgba(56, 189, 248, 0.55);
          background: rgba(36, 50, 76, 0.84);
        }
        .def-pad-btn:disabled {
          opacity: 0.42;
          cursor: not-allowed;
        }
        #defense-defeat-report {
          position: fixed;
          top: 50%;
          left: 50%;
          transform: translate(-50%, -50%);
          display: none;
          width: min(560px, 92vw);
          max-height: 86vh;
          overflow-y: auto;
          padding: 20px 22px;
          border-radius: 22px;
          background: linear-gradient(165deg, rgba(20, 29, 48, 0.88), rgba(10, 15, 28, 0.94));
          border: 1px solid rgba(255, 255, 255, 0.17);
          color: #f8fafc;
          z-index: 10020;
          pointer-events: auto;
          font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Malgun Gothic", sans-serif;
          box-shadow:
            0 18px 42px rgba(2, 6, 23, 0.52),
            inset 0 1px 0 rgba(255, 255, 255, 0.16),
            inset 0 -1px 2px rgba(2, 6, 23, 0.58);
        }
        .def-diag-card {
          margin-top: 8px;
          padding: 10px 12px;
          border-radius: 13px;
          background: rgba(15, 23, 42, 0.62);
          border: 1px solid rgba(255, 255, 255, 0.09);
          box-shadow: inset 1px 1px 2px rgba(2, 6, 23, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.06);
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 10px;
        }
        .def-diag-cta {
          padding: 6px 12px;
          border-radius: 9px;
          border: 1px solid rgba(56, 189, 248, 0.45);
          background: linear-gradient(180deg, rgba(14, 116, 144, 0.78), rgba(12, 74, 110, 0.88));
          color: #e0f2fe;
          font-size: 11px;
          font-weight: 700;
          cursor: pointer;
          white-space: nowrap;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.18);
        }
      `;
      document.head.appendChild(styleEl);
    }

    if (!document.getElementById('defense-story-banner')) {
      const banner = document.createElement('div');
      banner.id = 'defense-story-banner';
      banner.innerHTML = '<div id="dsb-badge" style="display:inline-block;padding:2px 10px;border-radius:999px;background:rgba(15,23,42,0.58);border:1px solid rgba(255,255,255,0.12);font-size:10.5px;font-weight:700;color:#38bdf8;letter-spacing:0.6px;text-transform:uppercase;"></div>'
        + '<div id="dsb-title" style="font-size:15px;font-weight:700;color:#f8fafc;margin:6px 0 3px;letter-spacing:-0.3px;"></div>'
        + '<div id="dsb-line" style="font-size:12px;color:#cbd5e1;line-height:1.45;font-weight:500;letter-spacing:-0.15px;"></div>';
      document.body.appendChild(banner);
    }

    if (!document.getElementById('def-live-coach-toast')) {
      const toast = document.createElement('div');
      toast.id = 'def-live-coach-toast';
      document.body.appendChild(toast);
    }

    if (!document.getElementById('defense-pad-popover')) {
      const pop = document.createElement('div');
      pop.id = 'defense-pad-popover';
      pop.addEventListener('pointerdown', (e) => { e.stopPropagation(); });
      document.body.appendChild(pop);
    }

    if (!document.getElementById('defense-defeat-report')) {
      const rep = document.createElement('div');
      rep.id = 'defense-defeat-report';
      rep.addEventListener('pointerdown', (e) => { e.stopPropagation(); });
      document.body.appendChild(rep);
    }

    if (!document.getElementById('defense-tactical-hud')) {
      const hud = document.createElement('div');
      hud.id = 'defense-tactical-hud';
      hud.innerHTML = `
        <div class="def-telemetry-col">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;white-space:nowrap;">
            <span id="def-hud-wave" style="font-size:11px;font-weight:800;color:#f8fafc;letter-spacing:-0.1px;white-space:nowrap;">STAGE 1</span>
            <span id="def-readiness-pill" style="font-size:10px;font-weight:700;padding:1px 7px;border-radius:99px;background:rgba(34,197,94,0.18);border:1px solid rgba(74,222,128,0.28);color:#86efac;white-space:nowrap;">🟢 우세</span>
          </div>
          <div style="display:flex;justify-content:space-between;align-items:center;gap:8px;white-space:nowrap;">
            <span id="def-typing-pill" style="font-size:10px;font-weight:700;color:#93c5fd;white-space:nowrap;">⌨️ Lv.1</span>
            <span id="def-hud-gold" style="font-size:10.5px;font-weight:800;color:#fbbf24;white-space:nowrap;">0 G</span>
          </div>
          <div class="def-bar-row">
            <div class="def-bar-meta"><span>HERO</span><span id="def-hero-hp-txt">100%</span></div>
            <div class="def-bar-track"><div id="def-hero-hp-bar" class="def-bar-fill" style="background:linear-gradient(90deg,#16a34a,#4ade80);"></div></div>
          </div>
          <div class="def-bar-row">
            <div class="def-bar-meta"><span>${PARTNER_LABEL}</span><span id="def-partner-hp-txt">100%</span></div>
            <div class="def-bar-track"><div id="def-partner-hp-bar" class="def-bar-fill" style="background:linear-gradient(90deg,#059669,#fde047);"></div></div>
          </div>
          <div class="def-bar-row">
            <div class="def-bar-meta"><span>NEXUS</span><span id="def-base-hp-txt">100%</span></div>
            <div class="def-bar-track"><div id="def-base-hp-bar" class="def-bar-fill" style="background:linear-gradient(90deg,#0284c7,#38bdf8);"></div></div>
          </div>
        </div>
        <div class="def-hud-divider"></div>
        <div class="def-hud-section">
          <button id="tac-btn-q" class="def-skill-card is-ready" data-accent="fire" title="전술 유성우 폭격 [Q]">
            <span class="def-keycap">Q</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <path d="M25 5L14 16" stroke="#fde047" stroke-width="2.4" stroke-linecap="round"/>
              <path d="M27 11L19 19" stroke="#fb923c" stroke-width="2" stroke-linecap="round"/>
              <circle cx="12" cy="20" r="6.5" fill="url(#mGrad)" stroke="#fef08a" stroke-width="1.5"/>
              <defs><radialGradient id="mGrad" cx="35%" cy="35%"><stop offset="0%" stop-color="#fef08a"/><stop offset="55%" stop-color="#f97316"/><stop offset="100%" stop-color="#9a3412"/></radialGradient></defs>
            </svg>
            <span class="def-slot-label">유성우</span>
            <div class="def-cd-wipe"></div>
            <div class="def-cd-text"></div>
          </button>
          <button id="tac-btn-w" class="def-skill-card is-ready" data-accent="aegis" title="성소 절대방어막 + 수리 [W]">
            <span class="def-keycap">W</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <path d="M16 4L26 8.2V15.6C26 21.8 21.7 26.8 16 28.5C10.3 26.8 6 21.8 6 15.6V8.2L16 4Z" fill="#0ea5e9" fill-opacity="0.35" stroke="#7dd3fc" stroke-width="2"/>
              <path d="M16 9V23M11 16H21" stroke="#e0f2fe" stroke-width="2.4" stroke-linecap="round"/>
            </svg>
            <span class="def-slot-label">보호막</span>
            <div class="def-cd-wipe"></div>
            <div class="def-cd-text"></div>
          </button>
          <button id="tac-btn-e" class="def-skill-card is-ready" data-accent="titan" title="거대화 오버드라이브 [E]">
            <span class="def-keycap">E</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <path d="M16 4C19.5 9.2 24 12.2 24 18.2C24 23.2 20.4 27 16 27C11.6 27 8 23.2 8 18.2C8 14.3 10.6 11.4 12.6 9.2C13 11.8 14.4 12.8 15.6 11.4C16.2 9.4 15.8 6.4 16 4Z" fill="#ef4444" stroke="#fde047" stroke-width="1.6"/>
              <path d="M16 14.5C17.8 16.5 19.2 18.2 19.2 20.5C19.2 22.4 17.8 24 16 24C14.2 24 12.8 22.4 12.8 20.5C12.8 18.2 14.2 16.5 16 14.5Z" fill="#fef08a"/>
            </svg>
            <span class="def-slot-label">거대화</span>
            <div class="def-cd-wipe"></div>
            <div class="def-cd-text"></div>
          </button>
        </div>
        <div class="def-hud-divider"></div>
        <div class="def-hud-section">
          <button id="tac-wep-fist" class="def-wep-card" title="맨손 격투 [1]">
            <span class="def-keycap">1</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <rect x="7" y="11" width="18" height="13" rx="5" fill="#fbbf24" fill-opacity="0.24" stroke="#fde047" stroke-width="1.8"/>
              <path d="M11 11V8M16 11V7.5M21 11V8.5" stroke="#fef08a" stroke-width="2" stroke-linecap="round"/>
            </svg>
            <span class="def-slot-label">맨손</span>
          </button>
          <button id="tac-wep-sword" class="def-wep-card" title="성검 참격 [2]">
            <span class="def-keycap">2</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <path d="M24.5 5.5L26 11L13.5 23.5L8.5 18.5L21 6L24.5 5.5Z" fill="#38bdf8" fill-opacity="0.32" stroke="#bae6fd" stroke-width="1.8"/>
              <path d="M7 20L12 25M6.5 25.5L9.5 22.5" stroke="#fde047" stroke-width="2.2" stroke-linecap="round"/>
            </svg>
            <span class="def-slot-label">성검</span>
          </button>
          <button id="tac-wep-bow" class="def-wep-card" title="별빛 활 [3]">
            <span class="def-keycap">3</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <path d="M10 6C20 8.5 20 23.5 10 26" stroke="#c084fc" stroke-width="2.4" stroke-linecap="round"/>
              <path d="M10 6V26" stroke="#e2e8f0" stroke-width="1.2"/>
              <path d="M7 16H25M22 13L25.5 16L22 19" stroke="#fde047" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <span class="def-slot-label">장궁</span>
          </button>
          <button id="tac-wep-gun" class="def-wep-card" title="마도 캐논건 [4]">
            <span class="def-keycap">4</span>
            <svg class="def-slot-icon" viewBox="0 0 32 32" fill="none">
              <rect x="6" y="11" width="18" height="7" rx="2" fill="#f43f5e" fill-opacity="0.3" stroke="#fda4af" stroke-width="1.8"/>
              <path d="M10 18L8 25H13L15 18" fill="#475569" stroke="#cbd5e1" stroke-width="1.5"/>
              <circle cx="26.5" cy="14.5" r="2.2" fill="#fde047"/>
            </svg>
            <span class="def-slot-label">총포</span>
          </button>
        </div>
        <div class="def-hud-divider"></div>
        <div class="def-hud-section">
          <button id="tac-item-hp" class="def-wep-card" title="생명 회복 물약 사용 [5]">
            <span class="def-keycap">5</span>
            <span style="font-size:15px;line-height:1;">🧪</span>
            <span id="tac-item-hp-cnt" class="def-slot-label">포션 0</span>
          </button>
          <button id="tac-item-haste" class="def-wep-card" title="질풍 가속 비약 사용 [6]">
            <span class="def-keycap">6</span>
            <span style="font-size:15px;line-height:1;">⚡</span>
            <span id="tac-item-haste-cnt" class="def-slot-label">가속 0</span>
          </button>
          <button id="tac-btn-retreat" class="def-wep-card" style="border-color:rgba(248,113,113,0.32);" title="디펜스 후퇴 및 종료 [ESC]">
            <span class="def-keycap">ESC</span>
            <span style="font-size:14px;line-height:1;">🏳️</span>
            <span class="def-slot-label" style="color:#fca5a5;">후퇴</span>
          </button>
        </div>
      `;
      document.body.appendChild(hud);

      document.getElementById('tac-btn-q').onclick = () => triggerTacticalSkill('Q');
      document.getElementById('tac-btn-w').onclick = () => triggerTacticalSkill('W');
      document.getElementById('tac-btn-e').onclick = () => triggerTacticalSkill('E');
      document.getElementById('tac-wep-fist').onclick = () => setWeaponType('fist');
      document.getElementById('tac-wep-sword').onclick = () => setWeaponType('sword');
      document.getElementById('tac-wep-bow').onclick = () => setWeaponType('bow');
      document.getElementById('tac-wep-gun').onclick = () => setWeaponType('gun');
      document.getElementById('tac-item-hp').onclick = () => tryUseBattleQuickItem('hp_potion');
      document.getElementById('tac-item-haste').onclick = () => tryUseBattleQuickItem('haste_elixir');
      document.getElementById('tac-btn-retreat').onclick = () => retreatFromDefense();
      hud.addEventListener('pointerdown', (e) => { e.stopPropagation(); });
    }
  }

  function showDefenseStoryBanner(badge, title, line, accent = '#38bdf8', durationMs = 4200) {
    ensureDefenseDomOverlays();
    const banner = document.getElementById('defense-story-banner');
    if (!banner) return;
    const elBadge = document.getElementById('dsb-badge');
    const elTitle = document.getElementById('dsb-title');
    const elLine = document.getElementById('dsb-line');
    if (elBadge) {
      elBadge.textContent = badge || '';
      elBadge.style.color = accent;
      elBadge.style.borderColor = 'rgba(255, 255, 255, 0.14)';
    }
    if (elTitle) elTitle.textContent = title || '';
    if (elLine) elLine.textContent = line || '';
    banner.style.borderColor = 'rgba(255, 255, 255, 0.16)';
    banner.style.opacity = '1';
    if (storyBannerTimer) clearTimeout(storyBannerTimer);
    storyBannerTimer = setTimeout(() => {
      if (banner) banner.style.opacity = '0';
    }, durationMs);
  }

  function triggerChronicleStoryBanner(eventKind, waveNum = 1, bossObj = null) {
    const ch = WAVE_STORY_CHRONICLES[rpgState.worldview] || WAVE_STORY_CHRONICLES.fantasy;
    const { spec } = getStageBracketInfo(waveNum);
    if (eventKind === 'intro') {
      const m = (ch.waveMilestones && ch.waveMilestones[waveNum]) || null;
      const title = m ? m.title : ch.intro.title;
      const line = m ? m.line : ch.intro.line;
      showDefenseStoryBanner(`${ch.worldTitle} | ${ch.intro.badge}`, title, line, ch.intro.accent, 4500);
    } else if (eventKind === 'boss_intro') {
      const bStory = (ch.bosses || []).find((b) => b.bracket === spec.bracket) || (ch.bosses && ch.bosses[0]);
      if (bStory) {
        showDefenseStoryBanner(`👑 BOSS · ${bStory.title}`, `${bStory.name} 출현!`, bStory.introLine, '#f43f5e', 4800);
      }
    } else if (eventKind === 'boss_phase2') {
      const bStory = (ch.bosses || []).find((b) => b.bracket === spec.bracket) || (ch.bosses && ch.bosses[0]);
      const p2 = bStory ? bStory.phase2Line : '“전력 개방! 붉은 경고 장판을 피하라!!”';
      showDefenseStoryBanner('🔥 BOSS PHASE 2 광폭화!', bossObj ? bossObj.name : '군단장 각성', p2, '#ef4444', 4400);
    } else if (eventKind === 'victory') {
      showDefenseStoryBanner(`✨ ${ch.victory.speaker}`, ch.victory.title, ch.victory.line, '#4ade80', 4200);
    }
  }

  function showDefenseNotice(text, accent = '#38bdf8') {
    const clean = String(text || '').trim();
    if (!clean) return false;
    const lines = clean.split('\n');
    const title = lines[0] || '';
    const detail = lines.slice(1).join(' · ') || '';
    showDefenseStoryBanner('⚔️ 전술 알림', title, detail, accent, 3200);
    return true;
  }

  function updateTacticalHudVisibility(visible) {
    const hud = typeof document !== 'undefined' ? document.getElementById('defense-tactical-hud') : null;
    if (!hud) return;
    if (!visible) {
      if (hud.style.display !== 'none') hud.style.display = 'none';
      prevHudSnap = null;
      return;
    }
    if (hud.style.display !== 'flex') hud.style.display = 'flex';

    const nowMs = (typeof performance !== 'undefined') ? performance.now() : Date.now();
    lastHudSyncAt = nowMs;

    let aliveEnemiesCount = 0;
    for (let i = 0; i < activeEnemies.length; i++) {
      if (activeEnemies[i].dyingTimer < 0) aliveEnemiesCount++;
    }
    const aliveCount = aliveEnemiesCount + (combatState.enemiesToSpawn || 0);
    const waveStr = combatState.mode === 'WAVE_DEFENSE' ? `STAGE ${combatState.wave} · 적 ${aliveCount}` : `SKIRMISH · 적 ${aliveCount}`;
    const goldVal = Math.floor(rpgState.gold || 0);
    if (combatState.selectedPadId && goldVal !== lastPopoverGold) {
      lastPopoverGold = goldVal;
      openBuildPadPopover(combatState.selectedPadId);
    }
    const hMax = Math.max(1, combatState.heroMaxHp || 1);
    const hCur = Math.max(0, Math.round(combatState.heroHp));
    const hPct = Math.max(0, Math.min(100, Math.round((combatState.heroHp / hMax) * 100)));
    const pMax = Math.max(1, combatState.partnerMaxHp || 1);
    const pCur = Math.max(0, Math.round(combatState.partnerHp));
    const pPct = Math.max(0, Math.min(100, Math.round((combatState.partnerHp / pMax) * 100)));
    const bMax = Math.max(1, combatState.baseMaxHp || 1);
    const bCur = Math.max(0, Math.round(combatState.baseHp));
    const bPct = Math.max(0, Math.min(100, Math.round((combatState.baseHp / bMax) * 100)));
    const cdQ = combatState.skillCdQ > 0 ? Math.ceil(combatState.skillCdQ * 10) : 0;
    const cdW = combatState.skillCdW > 0 ? Math.ceil(combatState.skillCdW * 10) : 0;
    const cdE = combatState.skillCdE > 0 ? Math.ceil(combatState.skillCdE * 10) : 0;
    const rdy = computeDefenseReadiness();
    const tInfo = getTypingLevelInfo();
    const tLv = tInfo.level;
    const hpPotCnt = Math.max(0, parseInt((rpgState.consumables && rpgState.consumables.hp_potion) || 0, 10));
    const hsPotCnt = Math.max(0, parseInt((rpgState.consumables && rpgState.consumables.haste_elixir) || 0, 10));
    const snap = `${waveStr}|${goldVal}|${hCur}/${hMax}|${pCur}/${pMax}|${bCur}/${bMax}|${cdQ}|${cdW}|${cdE}|${rpgState.equippedWeapon}|${(rpgState.unlockedWeapons || []).join(',')}|${hpPotCnt}|${hsPotCnt}|${rdy.label}|${tLv}|${tInfo.curLevelProgress}|${tInfo.liveCpm}`;
    if (snap === prevHudSnap) return;
    prevHudSnap = snap;

    const elWave = document.getElementById('def-hud-wave');
    const elGold = document.getElementById('def-hud-gold');
    if (elWave && elWave.textContent !== waveStr) elWave.textContent = waveStr;
    const goldTxt = `${goldVal.toLocaleString()} G`;
    if (elGold && elGold.textContent !== goldTxt) elGold.textContent = goldTxt;

    const elRdy = document.getElementById('def-readiness-pill');
    if (elRdy) {
      elRdy.textContent = rdy.label;
      elRdy.style.background = rdy.bg;
      elRdy.style.color = rdy.fg;
    }
    const elTyp = document.getElementById('def-typing-pill');
    if (elTyp) {
      const pctTyp = Math.min(99, Math.floor((tInfo.curLevelProgress / Math.max(1, tInfo.curLevelReq)) * 100));
      const cpmSuffix = tInfo.liveCpm >= 60 ? ` · ⚡${Math.round(tInfo.liveCpm)}타` : '';
      elTyp.textContent = `⌨️ Lv.${tLv} (${pctTyp}%)${cpmSuffix}`;
    }

    const hBar = document.getElementById('def-hero-hp-bar');
    const hTxt = document.getElementById('def-hero-hp-txt');
    if (hBar) hBar.style.width = `${hPct}%`;
    if (hTxt) hTxt.textContent = combatState.heroReviveTimer > 0 ? `부활 ${Math.ceil(combatState.heroReviveTimer)}s` : `${hCur}/${hMax}`;

    const pBar = document.getElementById('def-partner-hp-bar');
    const pTxt = document.getElementById('def-partner-hp-txt');
    if (pBar) pBar.style.width = `${pPct}%`;
    if (pTxt) pTxt.textContent = combatState.partnerReviveTimer > 0 ? `부활 ${Math.ceil(combatState.partnerReviveTimer)}s` : `${pCur}/${pMax}`;

    const bBar = document.getElementById('def-base-hp-bar');
    const bTxt = document.getElementById('def-base-hp-txt');
    if (bBar) bBar.style.width = `${bPct}%`;
    if (bTxt) bTxt.textContent = `${bCur}/${bMax}`;

    const syncSkill = (id, cd, maxCd) => {
      const el = document.getElementById(id);
      if (!el) return;
      const pct = cd > 0 ? Math.min(100, Math.max(0, (cd / maxCd) * 100)) : 0;
      el.style.setProperty('--cd-pct', `${pct.toFixed(1)}%`);
      const cdTxt = el.querySelector('.def-cd-text');
      const nextStr = cd > 0 ? `${Math.ceil(cd)}s` : '';
      if (cdTxt && cdTxt.textContent !== nextStr) cdTxt.textContent = nextStr;
      if (cd > 0) {
        el.classList.add('is-cooling');
        el.classList.remove('is-ready');
      } else {
        el.classList.remove('is-cooling');
        el.classList.add('is-ready');
      }
    };
    syncSkill('tac-btn-q', combatState.skillCdQ, 18.0);
    syncSkill('tac-btn-w', combatState.skillCdW, 15.0);
    syncSkill('tac-btn-e', combatState.skillCdE, 22.0);

    const unlockedList = Array.isArray(rpgState.unlockedWeapons) && rpgState.unlockedWeapons.length > 0
      ? rpgState.unlockedWeapons
      : ['fist'];
    const wepMap = { fist: 'tac-wep-fist', sword: 'tac-wep-sword', bow: 'tac-wep-bow', gun: 'tac-wep-gun' };
    Object.entries(wepMap).forEach(([k, id]) => {
      const el = document.getElementById(id);
      if (!el) return;
      const unlocked = unlockedList.includes(k);
      el.classList.toggle('is-equipped', rpgState.equippedWeapon === k);
      el.style.opacity = unlocked ? '1' : '0.42';
    });
    const elHpCnt = document.getElementById('tac-item-hp-cnt');
    if (elHpCnt) elHpCnt.textContent = `포션 ${hpPotCnt}`;
    const elHsCnt = document.getElementById('tac-item-haste-cnt');
    if (elHsCnt) elHsCnt.textContent = `가속 ${hsPotCnt}`;
    const btnHp = document.getElementById('tac-item-hp');
    if (btnHp) btnHp.style.opacity = hpPotCnt > 0 ? '1' : '0.45';
    const btnHs = document.getElementById('tac-item-haste');
    if (btnHs) btnHs.style.opacity = hsPotCnt > 0 ? '1' : '0.45';
  }

  function bakeVerticalAndCreviceAO(geo, bottomHex, topHex, midHex = null) {
    if (!geo || !geo.attributes || !geo.attributes.position) return geo;
    geo.computeBoundingBox();
    const bb = geo.boundingBox;
    const minY = bb ? bb.min.y : 0;
    const spanY = Math.max(0.001, (bb ? bb.max.y : 1) - minY);
    const pos = geo.attributes.position;
    const colArr = new Float32Array(pos.count * 3);
    const cBot = new THREE.Color(bottomHex);
    const cTop = new THREE.Color(topHex);
    const cMid = midHex !== null ? new THREE.Color(midHex) : null;
    const tmpC = new THREE.Color();
    for (let i = 0; i < pos.count; i++) {
      const t = Math.max(0, Math.min(1, (pos.getY(i) - minY) / spanY));
      if (cMid) {
        if (t < 0.5) tmpC.copy(cBot).lerp(cMid, t * 2.0);
        else tmpC.copy(cMid).lerp(cTop, (t - 0.5) * 2.0);
      } else {
        tmpC.copy(cBot).lerp(cTop, t);
      }
      // Subtle seam crevice darkening near bottom base contact
      const ao = 0.86 + 0.14 * Math.min(1.0, t * 2.4);
      colArr[i * 3] = tmpC.r * ao;
      colArr[i * 3 + 1] = tmpC.g * ao;
      colArr[i * 3 + 2] = tmpC.b * ao;
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colArr, 3));
    return geo;
  }

  function makeDefenseSoftVinylMat(opts = {}) {
    const sssCol = new THREE.Color(opts.sssColor ?? opts.color ?? 0xffffff);
    const rimCol = new THREE.Color(opts.rimColor ?? 0xffffff);
    const sssStr = opts.sssStrength ?? 0.20;
    const rimStr = opts.rimStrength ?? 0.18;
    const mat = new THREE.MeshStandardMaterial({
      color: opts.vertexColors ? 0xffffff : (opts.color ?? 0xf8fafc),
      roughness: opts.roughness ?? 0.62,
      metalness: opts.metalness ?? 0.0,
      envMapIntensity: opts.envMapIntensity ?? 0.25,
      vertexColors: Boolean(opts.vertexColors),
    });
    mat.customProgramCacheKey = () => 'def_softvinyl_v2';
    mat.onBeforeCompile = (shader) => {
      shader.uniforms.uDefSssColor = { value: sssCol };
      shader.uniforms.uDefSssStrength = { value: sssStr };
      shader.uniforms.uDefRimColor = { value: rimCol };
      shader.uniforms.uDefRimStrength = { value: rimStr };
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        `#include <common>
         uniform vec3 uDefSssColor;
         uniform float uDefSssStrength;
         uniform vec3 uDefRimColor;
         uniform float uDefRimStrength;`
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <tonemapping_fragment>',
        `vec3 defViewDir = normalize(vViewPosition);
         vec3 defKeyDir = normalize(vec3(0.42, 0.68, 0.60));
         float defNdl = dot(normal, defKeyDir);
         float defSss = smoothstep(-0.65, 0.35, defNdl) * (1.0 - smoothstep(0.05, 0.75, defNdl));
         gl_FragColor.rgb += uDefSssColor * (defSss * uDefSssStrength + 0.025 * uDefSssStrength);
         float defFres = pow(1.0 - clamp(dot(normal, defViewDir), 0.0, 1.0), 3.0);
         gl_FragColor.rgb += uDefRimColor * (defFres * uDefRimStrength);
         #include <tonemapping_fragment>`
      );
    };
    return mat;
  }

  function makeDefenseSatinMetalMat(opts = {}) {
    return new THREE.MeshPhysicalMaterial({
      color: opts.color ?? 0xf4c430,
      roughness: opts.roughness ?? 0.28,
      metalness: opts.metalness ?? 0.74,
      clearcoat: opts.clearcoat ?? 0.45,
      clearcoatRoughness: opts.clearcoatRoughness ?? 0.22,
      envMapIntensity: opts.envMapIntensity ?? 0.78,
      vertexColors: Boolean(opts.vertexColors),
    });
  }

  function makeDefenseCrystalMat(opts = {}) {
    return new THREE.MeshPhysicalMaterial({
      color: opts.color ?? 0x7dd3fc,
      emissive: opts.emissive ?? 0x0ea5e9,
      emissiveIntensity: opts.emissiveIntensity ?? 0.55,
      roughness: 0.12,
      metalness: 0.08,
      clearcoat: 1.0,
      clearcoatRoughness: 0.08,
      envMapIntensity: 0.95,
      transparent: true,
      opacity: opts.opacity ?? 0.88,
    });
  }

  function makeAdditiveHaloMat(colorHex, opacity = 0.55, power = 2.2) {
    return new THREE.ShaderMaterial({
      uniforms: {
        uColor: { value: new THREE.Color(colorHex) },
        uOpacity: { value: opacity },
        uPower: { value: power },
      },
      vertexShader: `
        varying vec3 vNorm;
        varying vec3 vViewPos;
        void main() {
          vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
          vNorm = normalize(normalMatrix * normal);
          vViewPos = -mvPos.xyz;
          gl_Position = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        uniform vec3 uColor;
        uniform float uOpacity;
        uniform float uPower;
        varying vec3 vNorm;
        varying vec3 vViewPos;
        void main() {
          float ndv = clamp(abs(dot(normalize(vNorm), normalize(vViewPos))), 0.0, 1.0);
          float rim = pow(ndv, uPower);
          gl_FragColor = vec4(uColor, rim * uOpacity);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      toneMapped: false,
      side: THREE.FrontSide,
    });
  }

  function harmonizePropGlbMaterials(root, style = 'citadel_gold') {
    if (!root) return;
    const isCitadel = style === 'citadel_gold';
    const tmpHsl = { h: 0, s: 0, l: 0 };
    root.traverse((node) => {
      if (!node.isMesh && !node.isSkinnedMesh) return;
      const list = Array.isArray(node.material) ? node.material : [node.material];
      const mapped = list.map((orig) => {
        if (!orig) return orig;
        const m = orig.clone();
        if (m.color) {
          m.color.getHSL(tmpHsl);
          m.color.setHSL(tmpHsl.h, Math.min(1.0, tmpHsl.s * 1.15 + 0.04), Math.max(isCitadel ? 0.28 : 0.20, Math.min(0.86, tmpHsl.l * 1.08 + (isCitadel ? 0.08 : 0.03))));
        }
        if (typeof m.envMapIntensity === 'number') m.envMapIntensity = 0.52;
        if (typeof m.roughness === 'number') m.roughness = Math.max(0.32, Math.min(0.60, m.roughness));
        if (typeof m.metalness === 'number') m.metalness = Math.min(0.68, Math.max(0.08, m.metalness));
        m.needsUpdate = true;
        return m;
      });
      node.material = Array.isArray(node.material) ? mapped : mapped[0];
    });
  }

  function createRoundedPillBarMesh(width, height, fillHex, hasShield = false) {
    const aspect = width / Math.max(0.01, height);
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        uHpRatio: { value: 1.0 },
        uShieldRatio: { value: hasShield ? 1.0 : 0.0 },
        uHasShield: { value: hasShield ? 1.0 : 0.0 },
        uFillColor: { value: new THREE.Color(fillHex) },
        uAspect: { value: aspect },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uHpRatio;
        uniform float uShieldRatio;
        uniform float uHasShield;
        uniform vec3 uFillColor;
        uniform float uAspect;
        varying vec2 vUv;
        float sdPill(vec2 p, vec2 b, float r) {
          vec2 q = abs(p) - b + vec2(r);
          return min(max(q.x, q.y), 0.0) + length(max(q, 0.0)) - r;
        }
        void main() {
          vec2 p = vec2((vUv.x - 0.5) * uAspect, vUv.y - 0.5);
          vec2 halfBox = vec2(uAspect * 0.5 - 0.02, 0.44);
          float r = 0.38;
          float d = sdPill(p, halfBox, r);
          if (d > 0.05) discard;
          float aa = 0.045;
          float bodyMask = 1.0 - smoothstep(-aa, aa, d);
          float innerD = sdPill(p, halfBox - vec2(0.08, 0.09), max(0.08, r - 0.08));
          float innerMask = 1.0 - smoothstep(-aa, aa, innerD);
          vec3 trackCol = vec3(0.04, 0.07, 0.14);
          vec3 borderCol = vec3(0.28, 0.36, 0.52);
          float u = clamp((vUv.x - 0.04) / 0.92, 0.0, 1.0);
          float hpOn = step(u, clamp(uHpRatio, 0.0, 1.0));
          float splitY = uHasShield > 0.5 ? 0.58 : 0.0;
          vec3 col = trackCol;
          if (vUv.y >= splitY) {
            float gBoost = 0.85 + 0.25 * smoothstep(0.5, 0.92, vUv.y);
            col = mix(trackCol, uFillColor * gBoost, hpOn);
          } else if (uHasShield > 0.5) {
            float shOn = step(u, clamp(uShieldRatio, 0.0, 1.0));
            col = mix(trackCol, vec3(0.22, 0.74, 0.98) * 1.15, shOn);
          }
          // Subtle top glossy gleam inside pill
          col += vec3(0.18) * smoothstep(0.68, 0.88, vUv.y) * innerMask;
          vec3 finalRgb = mix(borderCol, col, innerMask);
          gl_FragColor = vec4(finalRgb, bodyMask * 0.96);
        }
      `,
      transparent: true,
      depthTest: false,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    mat.customProgramCacheKey = () => 'def_hp_pill_v1';
    const mesh = new THREE.Mesh(SHARED_GEO.unitPlane, mat);
    mesh.scale.set(width, height, 1);
    mesh.renderOrder = 20;
    mesh.userData.sharedGeo = true;
    return mesh;
  }

  function setPillBarValues(mesh, hpRatio, shieldRatio = 0, hasShield = null) {
    if (!mesh || !mesh.material || !mesh.material.uniforms) return;
    mesh.material.uniforms.uHpRatio.value = Math.max(0.0, Math.min(1.0, hpRatio));
    if (mesh.material.uniforms.uShieldRatio) {
      mesh.material.uniforms.uShieldRatio.value = Math.max(0.0, Math.min(1.0, shieldRatio));
    }
    if (hasShield !== null && mesh.material.uniforms.uHasShield) {
      mesh.material.uniforms.uHasShield.value = hasShield ? 1.0 : 0.0;
    }
  }

  function makeSoftVinylMat(opts) {
    return makeDefenseSoftVinylMat({
      color: opts.color,
      roughness: opts.roughness ?? 0.58,
      sssColor: opts.sssColor ?? opts.color,
      sssStrength: opts.sssStrength ?? 0.20,
      rimColor: opts.rimColor ?? 0xffffff,
      rimStrength: opts.rimStrength ?? 0.18,
      envMapIntensity: opts.envMapIntensity ?? 0.25,
      vertexColors: Boolean(opts.vertexColors),
    });
  }

  // ===========================================================================
  // 3. Soft-Vinyl Sanctuary Defense Tower + 3D Turrets (barricade, ballista, frost, arc)
  // ===========================================================================
  const defenseTowerGroup = new THREE.Group();
  defenseTowerGroup.name = 'BottomLeftDefenseBaseTower';
  defenseTowerGroup.visible = false;
  worldRoot.add(defenseTowerGroup);

  const towerVisualWrap = new THREE.Group();
  defenseTowerGroup.add(towerVisualWrap);

  let towerCrystalMesh = null;
  let towerHaloRing = null;
  let towerOuterRing = null;
  let towerRangeRingMesh = null;
  let towerShieldDomeMesh = null;
  let towerHpBar = null;
  let towerLanternHalo = null;
  let towerSquash = 0;

  let turretBarricadeGroup = null;
  let turretBallistaGroup = null;
  let turretFrostGroup = null;
  let turretArcGroup = null;
  let turretFrostCrystal = null;

  function attachGlbPropToNode(parentNode, url, targetSize = 0.65, pos = [0, 0, 0], rot = [0, 0, 0], harmonizeStyle = 'citadel_gold') {
    if (!parentNode) return;
    loadGlbTemplateCached(url).then((tpl) => {
      if (!tpl || !tpl.scene) return;
      const cloned = tpl.scene.clone(true);
      const { normWrap } = normalizeClonedGlbScene(cloned, targetSize, 0);
      if (harmonizeStyle) harmonizePropGlbMaterials(normWrap, harmonizeStyle);
      normWrap.position.set(pos[0], pos[1], pos[2]);
      normWrap.rotation.set(rot[0], rot[1], rot[2]);
      parentNode.add(normWrap);
    }).catch(() => {});
  }

  function buildBottomLeftDefenseBaseTower() {
    disposeObjectTreeChildren(towerVisualWrap);
    if (towerHpBar) {
      defenseTowerGroup.remove(towerHpBar);
      towerHpBar.material?.dispose?.();
      towerHpBar = null;
    }

    const towerShadow = new THREE.Mesh(SHARED_GEO.shadowDisc, SHARED_MAT.softContactShadow);
    towerShadow.rotation.x = -Math.PI * 0.35;
    towerShadow.position.y = 0.002;
    towerShadow.scale.setScalar(2.85);
    towerShadow.renderOrder = 1;
    towerShadow.userData.sharedGeo = true;
    towerShadow.userData.sharedMat = true;
    towerVisualWrap.add(towerShadow);

    // 0. Tilted Sanctuary Runic Floor Perimeter Shader (replaces vertical hula-hoop)
    const sanctFloorMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color(0x38bdf8) },
        uGold: { value: new THREE.Color(0xfde047) },
        uOpacity: { value: 0.30 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        uniform vec3 uGold;
        uniform float uOpacity;
        varying vec2 vUv;
        void main() {
          vec2 p = vUv * 2.0 - 1.0;
          float r = length(p);
          if (r > 1.0) discard;
          float ang = atan(p.y, p.x);
          float outer = smoothstep(0.032, 0.0, abs(r - 0.88));
          float inner = smoothstep(0.022, 0.0, abs(r - 0.72));
          float ticks = pow(max(0.0, cos((ang + uTime * 0.25) * 12.0)), 6.0) * smoothstep(0.06, 0.0, abs(r - 0.80));
          float aura = exp(-abs(r - 0.80) * 8.0) * 0.25;
          vec3 col = mix(uColor, uGold, ticks * 0.85);
          float a = clamp(outer * 0.65 + inner * 0.38 + ticks * 0.75 + aura, 0.0, 1.0);
          gl_FragColor = vec4(col, a * uOpacity);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
      toneMapped: false,
    });
    towerRangeRingMesh = new THREE.Mesh(new THREE.PlaneGeometry(3.8, 3.8), sanctFloorMat);
    towerRangeRingMesh.rotation.x = -Math.PI * 0.35;
    towerRangeRingMesh.position.set(0, 0.02, 0.0);
    towerRangeRingMesh.renderOrder = 2;
    towerVisualWrap.add(towerRangeRingMesh);

    // 1. Warm Amiibo Fairytale Materials with Vertex Crevice AO
    const slateMat = makeDefenseSoftVinylMat({ vertexColors: true, roughness: 0.60, sssColor: 0x94a3b8, rimColor: 0xdbeafe, rimStrength: 0.16 });
    const stoneMat = makeDefenseSoftVinylMat({ vertexColors: true, roughness: 0.64, sssColor: 0xffe4c4, rimColor: 0xffffff, rimStrength: 0.16 });
    const roofMat = makeDefenseSoftVinylMat({ vertexColors: true, roughness: 0.50, sssColor: 0xa5b4fc, rimColor: 0xe0f2fe, rimStrength: 0.22 });
    const goldMat = makeDefenseSatinMetalMat({ color: 0xf4c430, roughness: 0.26, metalness: 0.76, clearcoat: 0.48 });
    const woodMat = makeDefenseSoftVinylMat({ color: 0x6d4534, roughness: 0.58, sssColor: 0xb47855, rimColor: 0xfef3c7, rimStrength: 0.14 });

    // Sculpted Stepped Beveled Diorama Plinth (28-seg smooth lathe)
    const plinthPts = [
      new THREE.Vector2(0.0, 0.0),
      new THREE.Vector2(1.20, 0.0),
      new THREE.Vector2(1.22, 0.06),
      new THREE.Vector2(1.16, 0.15),
      new THREE.Vector2(1.06, 0.18),
      new THREE.Vector2(1.06, 0.24),
      new THREE.Vector2(0.95, 0.32),
      new THREE.Vector2(0.92, 0.42),
      new THREE.Vector2(0.0, 0.42),
    ];
    const plinthGeo = bakeVerticalAndCreviceAO(new THREE.LatheGeometry(plinthPts, 28), 0x5c6682, 0x8e99b8, 0x7681a0);
    towerVisualWrap.add(new THREE.Mesh(plinthGeo, slateMat));

    const waistCollar = new THREE.Mesh(new THREE.TorusGeometry(0.93, 0.048, 12, 32), goldMat);
    waistCollar.rotation.x = Math.PI / 2;
    waistCollar.position.y = 0.42;
    towerVisualWrap.add(waistCollar);

    // 2. Sculpted Convex Keep Drum + Rounded Parapet Overhang
    const keepPts = [
      new THREE.Vector2(0.0, 0.42),
      new THREE.Vector2(0.75, 0.42),
      new THREE.Vector2(0.77, 0.56),
      new THREE.Vector2(0.73, 0.96),
      new THREE.Vector2(0.67, 1.32),
      new THREE.Vector2(0.74, 1.40),
      new THREE.Vector2(0.76, 1.48),
      new THREE.Vector2(0.0, 1.48),
    ];
    const keepGeo = bakeVerticalAndCreviceAO(new THREE.LatheGeometry(keepPts, 24), 0xd4c7b4, 0xf5ede2, 0xe8dfd2);
    towerVisualWrap.add(new THREE.Mesh(keepGeo, stoneMat));

    const topCollar = new THREE.Mesh(new THREE.TorusGeometry(0.74, 0.036, 10, 28), goldMat);
    topCollar.rotation.x = Math.PI / 2;
    topCollar.position.y = 1.44;
    towerVisualWrap.add(topCollar);

    // 4 Corner Fairytale Watchtowers with Ogive Bell Roofs + Satin-Gold Finials
    const pillarGeo = bakeVerticalAndCreviceAO(new THREE.CylinderGeometry(0.21, 0.25, 1.12, 18), 0xd2c4b0, 0xf2eadf);
    const corbelGeo = bakeVerticalAndCreviceAO(new THREE.CylinderGeometry(0.28, 0.22, 0.14, 18), 0x626c88, 0x8a95b3);
    const bellPts = [
      new THREE.Vector2(0.0, 0.0),
      new THREE.Vector2(0.31, 0.0),
      new THREE.Vector2(0.27, 0.14),
      new THREE.Vector2(0.16, 0.34),
      new THREE.Vector2(0.06, 0.48),
      new THREE.Vector2(0.0, 0.56),
    ];
    const bellGeo = bakeVerticalAndCreviceAO(new THREE.LatheGeometry(bellPts, 18), 0x3b40ad, 0x7477f7, 0x5257da);
    const finialGeo = new THREE.SphereGeometry(0.055, 12, 10);

    for (let i = 0; i < 4; i++) {
      const ang = (i * Math.PI) / 2 + Math.PI / 4;
      const px = Math.cos(ang) * 0.64;
      const pz = Math.sin(ang) * 0.64;
      const p = new THREE.Mesh(pillarGeo, stoneMat);
      p.position.set(px, 0.96, pz);
      const cap = new THREE.Mesh(corbelGeo, slateMat);
      cap.position.set(px, 1.56, pz);
      const roof = new THREE.Mesh(bellGeo, roofMat);
      roof.position.set(px, 1.62, pz);
      const fin = new THREE.Mesh(finialGeo, goldMat);
      fin.position.set(px, 2.20, pz);
      towerVisualWrap.add(p, cap, roof, fin);
    }

    // 8 Beveled Arch-Topped Merlons around Parapet (Zero sharp boxes)
    const merlonShape = new THREE.Shape();
    merlonShape.moveTo(-0.085, 0);
    merlonShape.lineTo(-0.085, 0.13);
    merlonShape.absarc(0, 0.13, 0.085, Math.PI, 0, true);
    merlonShape.lineTo(0.085, 0);
    merlonShape.closePath();
    const merlonGeo = bakeVerticalAndCreviceAO(
      new THREE.ExtrudeGeometry(merlonShape, { depth: 0.10, bevelEnabled: true, bevelThickness: 0.022, bevelSize: 0.018, bevelSegments: 2 }),
      0x68728e, 0x919cb9
    );
    merlonGeo.center();
    for (let i = 0; i < 8; i++) {
      const ang = (i * Math.PI) / 4;
      const merlon = new THREE.Mesh(merlonGeo, slateMat);
      merlon.position.set(Math.cos(ang) * 0.68, 1.56, Math.sin(ang) * 0.68);
      merlon.rotation.y = -ang + Math.PI / 2;
      towerVisualWrap.add(merlon);
    }

    // 3. Recessed Espresso Archway Double Door + Brushed-Gold Archivolt + Lantern Glow
    const doorShape = new THREE.Shape();
    doorShape.moveTo(-0.20, 0);
    doorShape.lineTo(-0.20, 0.30);
    doorShape.absarc(0, 0.30, 0.20, Math.PI, 0, true);
    doorShape.lineTo(0.20, 0);
    doorShape.closePath();
    const doorGeo = new THREE.ExtrudeGeometry(doorShape, { depth: 0.10, bevelEnabled: true, bevelThickness: 0.03, bevelSize: 0.025, bevelSegments: 3 });
    const doorMesh = new THREE.Mesh(doorGeo, woodMat);
    doorMesh.position.set(0, 0.42, 0.66);
    const doorFrame = new THREE.Mesh(new THREE.TorusGeometry(0.22, 0.034, 10, 22, Math.PI), goldMat);
    doorFrame.position.set(0, 0.72, 0.73);
    towerVisualWrap.add(doorMesh, doorFrame);

    const lantern = new THREE.Mesh(new THREE.SphereGeometry(0.085, 14, 12), new THREE.MeshBasicMaterial({ color: 0xfef08a, toneMapped: false }));
    lantern.position.set(0, 0.99, 0.75);
    towerLanternHalo = new THREE.Mesh(new THREE.SphereGeometry(0.18, 12, 10), makeAdditiveHaloMat(0xf59e0b, 0.58, 2.2));
    towerLanternHalo.position.copy(lantern.position);
    towerVisualWrap.add(lantern, towerLanternHalo);

    // Centered Harmonized Royal Emblem Crest on Facade (uncluttered!)
    attachGlbPropToNode(towerVisualWrap, ENEMY_GEAR_PROP_URLS.shield_heater, 0.48, [0, 1.24, 0.74], [0, 0, 0], 'citadel_gold');
    attachGlbPropToNode(towerVisualWrap, ENEMY_GEAR_PROP_URLS.sword, 0.62, [-0.20, 1.26, 0.70], [0, 0, -0.62], 'citadel_gold');
    attachGlbPropToNode(towerVisualWrap, ENEMY_GEAR_PROP_URLS.sword, 0.62, [0.20, 1.26, 0.70], [0, 0, 0.62], 'citadel_gold');

    // 4. Grand Fairytale Ogive Spire Roof + 3-Layer Volumetric Crystal Core & Dual Astrolabe Rings
    const roofPoints = [
      new THREE.Vector2(0.0, 1.46),
      new THREE.Vector2(0.80, 1.46),
      new THREE.Vector2(0.82, 1.54),
      new THREE.Vector2(0.62, 1.80),
      new THREE.Vector2(0.32, 2.04),
      new THREE.Vector2(0.12, 2.22),
      new THREE.Vector2(0.0, 2.30),
    ];
    const mainRoofGeo = bakeVerticalAndCreviceAO(new THREE.LatheGeometry(roofPoints, 28), 0x3b40ad, 0x7477f7, 0x5257da);
    towerVisualWrap.add(new THREE.Mesh(mainRoofGeo, roofMat));

    const crownSeat = new THREE.Mesh(new THREE.TorusGeometry(0.18, 0.032, 10, 24), goldMat);
    crownSeat.rotation.x = Math.PI / 2;
    crownSeat.position.y = 2.24;
    towerVisualWrap.add(crownSeat);

    const crystalMat = makeDefenseCrystalMat({ color: 0x7dd3fc, emissive: 0x0ea5e9, emissiveIntensity: 0.60, opacity: 0.88 });
    towerCrystalMesh = new THREE.Group();
    towerCrystalMesh.position.y = 2.66;
    const outerCry = new THREE.Mesh(new THREE.OctahedronGeometry(0.28, 0), crystalMat);
    outerCry.scale.set(0.76, 1.42, 0.76);
    const innerCry = new THREE.Mesh(new THREE.OctahedronGeometry(0.12, 0), new THREE.MeshBasicMaterial({ color: 0xf8fafc, toneMapped: false }));
    innerCry.scale.set(0.76, 1.42, 0.76);
    const cryGlow = new THREE.Mesh(new THREE.SphereGeometry(0.46, 16, 14), makeAdditiveHaloMat(0x38bdf8, 0.56, 2.3));
    towerCrystalMesh.add(outerCry, innerCry, cryGlow);
    towerVisualWrap.add(towerCrystalMesh);

    towerHaloRing = new THREE.Mesh(new THREE.TorusGeometry(0.46, 0.026, 10, 32), goldMat);
    towerHaloRing.position.y = 2.66;
    towerOuterRing = new THREE.Mesh(new THREE.TorusGeometry(0.57, 0.018, 8, 32), goldMat);
    towerOuterRing.position.y = 2.66;
    towerVisualWrap.add(towerHaloRing, towerOuterRing);

    // Upgraded [W] Fresnel Hex-Ripple Energy Barrier Dome
    const domeMat = new THREE.ShaderMaterial({
      uniforms: {
        uTime: { value: 0 },
        uColor: { value: new THREE.Color(0x38bdf8) },
      },
      vertexShader: `
        varying vec3 vNormal;
        varying vec3 vViewPos;
        varying vec3 vLocalPos;
        void main() {
          vLocalPos = position;
          vec4 mvPos = modelViewMatrix * vec4(position, 1.0);
          vNormal = normalize(normalMatrix * normal);
          vViewPos = -mvPos.xyz;
          gl_Position = projectionMatrix * mvPos;
        }
      `,
      fragmentShader: `
        uniform float uTime;
        uniform vec3 uColor;
        varying vec3 vNormal;
        varying vec3 vViewPos;
        varying vec3 vLocalPos;
        void main() {
          float fres = pow(1.0 - clamp(abs(dot(normalize(vNormal), normalize(vViewPos))), 0.0, 1.0), 2.2);
          float ripple = 0.5 + 0.5 * sin(vLocalPos.y * 10.0 - uTime * 4.5 + vLocalPos.x * 6.0);
          float a = clamp(fres * 0.75 + ripple * fres * 0.35 + 0.06, 0.0, 0.85);
          gl_FragColor = vec4(mix(uColor, vec3(1.0), fres * 0.45), a);
        }
      `,
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
      side: THREE.DoubleSide,
      toneMapped: false,
    });
    towerShieldDomeMesh = new THREE.Mesh(new THREE.SphereGeometry(1.74, 24, 18), domeMat);
    towerShieldDomeMesh.position.y = 1.15;
    towerShieldDomeMesh.visible = false;
    towerVisualWrap.add(towerShieldDomeMesh);

    // 5. Curved Diorama Oak-and-Stone Barricade Rampart (+1.22, 0, +0.20)
    turretBarricadeGroup = new THREE.Group();
    turretBarricadeGroup.position.set(1.22, 0.0, 0.20);
    const postGeo = bakeVerticalAndCreviceAO(new THREE.CapsuleGeometry(0.085, 0.46, 6, 12), 0x5c3c2d, 0x8a5b44);
    for (let pi = -1; pi <= 1; pi++) {
      const ang = pi * 0.42;
      const post = new THREE.Mesh(postGeo, makeDefenseSoftVinylMat({ vertexColors: true, roughness: 0.58, sssColor: 0xc27038 }));
      post.position.set(Math.cos(ang) * 0.14 - 0.12, 0.31, Math.sin(ang) * 0.72);
      turretBarricadeGroup.add(post);
    }
    const arcRail = new THREE.Mesh(new THREE.TorusGeometry(0.45, 0.065, 10, 20, Math.PI * 0.68), goldMat);
    arcRail.rotation.x = Math.PI / 2;
    arcRail.rotation.z = -Math.PI * 0.34;
    arcRail.position.set(-0.22, 0.36, 0);
    turretBarricadeGroup.add(arcRail);
    attachGlbPropToNode(turretBarricadeGroup, ENEMY_GEAR_PROP_URLS.shield_heater, 0.46, [0.14, 0.34, -0.22], [0, Math.PI / 2, 0], 'citadel_gold');
    attachGlbPropToNode(turretBarricadeGroup, ENEMY_GEAR_PROP_URLS.shield_heater, 0.46, [0.14, 0.34, 0.22], [0, Math.PI / 2, 0], 'citadel_gold');
    towerVisualWrap.add(turretBarricadeGroup);

    // Legacy auxiliary placeholders (kept hidden in favor of 5 sculpted desktop pad towers)
    turretBallistaGroup = new THREE.Group();
    turretBallistaGroup.visible = false;
    turretFrostGroup = new THREE.Group();
    turretFrostGroup.visible = false;
    turretArcGroup = new THREE.Group();
    turretArcGroup.visible = false;

    // 1-Draw-Call Rounded-Pill Citadel HP Bar
    towerHpBar = createRoundedPillBarMesh(1.64, 0.21, 0x38bdf8, false);
    towerHpBar.position.set(0, 3.22, 0.06);
    defenseTowerGroup.add(towerHpBar);
  }
  let defenseTowerBuilt = false;
  function ensureDefenseTowerBuilt() {
    if (!defenseTowerBuilt) {
      buildBottomLeftDefenseBaseTower();
      defenseTowerBuilt = true;
    }
  }

  function refreshTurretMeshesVisibility() {
    if (defenseTowerBuilt) {
      const t = rpgState.turrets || {};
      if (turretBarricadeGroup) turretBarricadeGroup.visible = (t.barricade || 0) > 0;
      if (turretBallistaGroup) turretBallistaGroup.visible = false;
      if (turretFrostGroup) turretFrostGroup.visible = false;
      if (turretArcGroup) turretArcGroup.visible = false;
      if (towerRangeRingMesh) towerRangeRingMesh.visible = true;
    }
    syncBuildPadsToRpgState();
  }

  // ===========================================================================
  // 3B. Desktop 5-Pad Build Grid, 5 Tower Archetypes (Lv.1~5), Popover & Coaching
  // ===========================================================================
  const buildPads = [];
  let buildPadsInitialized = false;
  let partnerStaffOrb = null;
  let partnerAuraRing = null;
  let synchroBeamMesh = null;

  function disposeObjectTreeChildren(group) {
    if (!group) return;
    while (group.children.length > 0) {
      const ch = group.children[0];
      group.remove(ch);
      ch.traverse((node) => {
        if (node.geometry && !node.userData?.sharedGeo && typeof node.geometry.dispose === 'function') {
          node.geometry.dispose();
        }
        if (node.material && !node.userData?.sharedMat) {
          if (Array.isArray(node.material)) node.material.forEach((m) => m?.dispose?.());
          else node.material.dispose?.();
        }
      });
    }
  }

  function getTypingLevelInfo() {
    const ts = rpgState.typingStats || {};
    const level = Math.max(1, Number(ts.level ?? ts.typingLevel ?? rpgState.petLevel ?? 1) || 1);
    const curLevelProgress = Math.max(0, Number(ts.curLevelProgress ?? ts.progressInLevel ?? 0) || 0);
    const curLevelReq = Math.max(1, Number(ts.curLevelReq ?? ts.nextLevelReq ?? 10000) || 10000);
    const liveCpm = Number(ts.liveCpm ?? ts.currentCpm ?? 0) || 0;
    const cpmHasteMult = liveCpm >= 60 ? (1.0 + Math.min(0.18, (liveCpm - 60) * 0.0012)) : 1.0;
    return {
      level,
      curLevelProgress,
      curLevelReq,
      liveCpm,
      cpmHasteMult,
      feverActive: Boolean(ts.feverActive),
      critChance: Number(ts.critChance ?? Math.min(0.55, 0.14 + 0.025 * (level - 1))) || 0.16,
      critMult: Number(ts.critMult ?? (level >= 6 ? 1.65 : 1.35)) || 1.35,
      waveStartGoldBonus: Number(ts.waveStartGoldBonus ?? (level >= 2 ? 60 : 0)) || 0,
      atkMult: Number(ts.atkMult ?? (1.0 + 0.08 * (level - 1))) || 1.0,
      towerDmgMult: Number(ts.towerDmgMult ?? (1.0 + 0.05 * (level - 1))) || 1.0,
      towerSpdMult: (Number(ts.towerSpdMult ?? (1.0 + 0.02 * Math.min(15, level - 1))) || 1.0) * cpmHasteMult,
      upgradeDiscount: Number(ts.upgradeDiscount ?? (level >= 4 ? 0.08 : 0.0)) || 0.0,
      skillCdMult: Number(ts.skillCdMult ?? (level >= 2 ? 0.94 : 1.0)) || 1.0,
      armorPenBonus: Number(ts.armorPenBonus ?? (level >= 7 ? 0.10 : 0.0)) || 0.0,
    };
  }

  function getEffectiveTowerRange(typeKey, level = 1) {
    const spec = TOWER_DEFS[typeKey];
    if (!spec) return 6.5;
    if (typeKey === 'sniper') {
      return 11.5 + Math.max(0, Math.min(4, (level || 1) - 1)) * 1.35;
    }
    return spec.range;
  }

  function getTowerBuildDiscountedCost(baseGoldCost) {
    const disc = getTypingLevelInfo().upgradeDiscount;
    return disc > 0 ? Math.max(10, Math.round(baseGoldCost * (1.0 - disc))) : baseGoldCost;
  }

  let hoveredPadId = null;
  let towerPool = null;

  function getTowerAssetPool() {
    if (towerPool) return towerPool;

    const makeLimbGeo = (sign) => {
      const curve = new THREE.CatmullRomCurve3([
        new THREE.Vector3(0.06, 0.0, sign * 0.04),
        new THREE.Vector3(0.14, 0.02, sign * 0.24),
        new THREE.Vector3(-0.04, 0.03, sign * 0.42),
        new THREE.Vector3(-0.18, 0.02, sign * 0.48),
      ]);
      return new THREE.TubeGeometry(curve, 16, 0.034, 8, false);
    };

    const pedPts = [
      new THREE.Vector2(0.0, 0.0),
      new THREE.Vector2(0.41, 0.0),
      new THREE.Vector2(0.42, 0.06),
      new THREE.Vector2(0.36, 0.16),
      new THREE.Vector2(0.32, 0.24),
      new THREE.Vector2(0.35, 0.28),
      new THREE.Vector2(0.0, 0.28),
    ];
    const cannonPts = [
      new THREE.Vector2(0.0, -0.22),
      new THREE.Vector2(0.15, -0.20),
      new THREE.Vector2(0.17, -0.05),
      new THREE.Vector2(0.12, 0.24),
      new THREE.Vector2(0.165, 0.34),
      new THREE.Vector2(0.135, 0.36),
      new THREE.Vector2(0.08, 0.30),
      new THREE.Vector2(0.0, 0.20),
    ];
    const cannonBarrelGeo = bakeVerticalAndCreviceAO(new THREE.LatheGeometry(cannonPts, 20), 0x3b4460, 0x5d698f);
    cannonBarrelGeo.rotateZ(-Math.PI / 2);

    const arcPts = [
      new THREE.Vector2(0.0, 0.24),
      new THREE.Vector2(0.24, 0.24),
      new THREE.Vector2(0.18, 0.38),
      new THREE.Vector2(0.22, 0.44),
      new THREE.Vector2(0.15, 0.56),
      new THREE.Vector2(0.19, 0.62),
      new THREE.Vector2(0.12, 0.74),
      new THREE.Vector2(0.0, 0.74),
    ];
    const sniperPts = [
      new THREE.Vector2(0.0, 0.24),
      new THREE.Vector2(0.22, 0.24),
      new THREE.Vector2(0.14, 0.58),
      new THREE.Vector2(0.18, 0.74),
      new THREE.Vector2(0.0, 0.74),
    ];
    const sniperRailGeo = new THREE.CapsuleGeometry(0.036, 0.66, 6, 12);
    sniperRailGeo.rotateZ(Math.PI / 2);

    const balStockGeo = new THREE.CapsuleGeometry(0.055, 0.44, 6, 12);
    balStockGeo.rotateZ(Math.PI / 2);

    const padPlinthPts = [
      new THREE.Vector2(0.0, 0.0),
      new THREE.Vector2(0.45, 0.0),
      new THREE.Vector2(0.46, 0.045),
      new THREE.Vector2(0.40, 0.09),
      new THREE.Vector2(0.32, 0.07),
      new THREE.Vector2(0.0, 0.07),
    ];
    const frostPetalGeo = new THREE.CapsuleGeometry(0.065, 0.26, 6, 10);

    towerPool = {
      geo: {
        padPlinth: bakeVerticalAndCreviceAO(new THREE.LatheGeometry(padPlinthPts, 24), 0xcbc0ae, 0xf2eae0),
        pedestal: bakeVerticalAndCreviceAO(new THREE.LatheGeometry(pedPts, 20), 0xc8bba8, 0xf2eae0),
        collar: new THREE.TorusGeometry(0.33, 0.036, 10, 24),
        waistRing: new THREE.TorusGeometry(0.38, 0.028, 10, 24),
        beaconCry: new THREE.OctahedronGeometry(0.095, 0),
        beaconHalo: new THREE.SphereGeometry(0.19, 12, 10),
        pipGem: new THREE.OctahedronGeometry(0.042, 0),
        crownHalo: new THREE.TorusGeometry(0.36, 0.024, 8, 28),
        auraDisc: new THREE.PlaneGeometry(1.18, 1.18),
        rangeDisc: new THREE.PlaneGeometry(2.0, 2.0),
        padRuneQuad: new THREE.PlaneGeometry(1.08, 1.08),
        balTurntable: bakeVerticalAndCreviceAO(new THREE.CylinderGeometry(0.20, 0.24, 0.14, 18), 0x8f5025, 0xd4854a),
        balStock: balStockGeo,
        balLimbL: makeLimbGeo(1),
        balLimbR: makeLimbGeo(-1),
        balLimbCap: new THREE.SphereGeometry(0.045, 10, 8),
        balString: new THREE.CylinderGeometry(0.010, 0.010, 0.92, 6),
        balBolt: new THREE.ConeGeometry(0.048, 0.42, 8),
        cannonDrum: bakeVerticalAndCreviceAO(new THREE.CylinderGeometry(0.28, 0.32, 0.22, 18), 0x8c4e24, 0xc27038),
        cannonBarrel: cannonBarrelGeo,
        cannonRing: new THREE.TorusGeometry(0.14, 0.026, 8, 20),
        cannonCore: new THREE.SphereGeometry(0.11, 10, 10),
        cannonCheek: new THREE.CapsuleGeometry(0.07, 0.16, 6, 10),
        frostPetal: frostPetalGeo,
        frostCrystal: new THREE.OctahedronGeometry(0.24, 0),
        frostCore: new THREE.OctahedronGeometry(0.11, 0),
        frostShard: new THREE.OctahedronGeometry(0.075, 0),
        frostHalo: new THREE.SphereGeometry(0.40, 14, 12),
        arcSpire: bakeVerticalAndCreviceAO(new THREE.LatheGeometry(arcPts, 20), 0xd4cbbe, 0xf6f1e8),
        arcCoil: new THREE.TorusGeometry(0.24, 0.030, 8, 24),
        arcProng: new THREE.CapsuleGeometry(0.026, 0.22, 5, 8),
        arcOrb: new THREE.SphereGeometry(0.12, 14, 12),
        arcOrbHalo: new THREE.SphereGeometry(0.26, 14, 12),
        sniperMast: bakeVerticalAndCreviceAO(new THREE.LatheGeometry(sniperPts, 20), 0xd6cab9, 0xf5efe6),
        sniperGimbal: new THREE.TorusGeometry(0.19, 0.026, 8, 24),
        sniperRail: sniperRailGeo,
        sniperScope: new THREE.CylinderGeometry(0.065, 0.055, 0.28, 14),
        sniperLens: new THREE.SphereGeometry(0.072, 12, 10),
        sniperLensHalo: new THREE.SphereGeometry(0.16, 12, 10),
        sniperWing: new THREE.CapsuleGeometry(0.026, 0.22, 5, 8),
      },
      mat: {
        stone: makeDefenseSoftVinylMat({ vertexColors: true, roughness: 0.62, sssColor: 0xffe4c4, rimColor: 0xffffff, rimStrength: 0.16 }),
        wood: makeDefenseSoftVinylMat({ vertexColors: true, roughness: 0.56, sssColor: 0xe69f66, rimColor: 0xfef3c7, rimStrength: 0.16 }),
        gold: makeDefenseSatinMetalMat({ color: 0xf4c430, roughness: 0.26, metalness: 0.78, clearcoat: 0.45 }),
        copper: makeDefenseSatinMetalMat({ color: 0xf59e0b, roughness: 0.28, metalness: 0.74, clearcoat: 0.42 }),
        gunmetal: makeDefenseSatinMetalMat({ color: 0x3b4460, roughness: 0.34, metalness: 0.58, clearcoat: 0.35 }),
        frostBody: makeDefenseSoftVinylMat({ color: 0xe6f2f9, roughness: 0.46, sssColor: 0xbae6fd, rimColor: 0xffffff, rimStrength: 0.22 }),
        frostCry: makeDefenseCrystalMat({ color: 0x7dd3fc, emissive: 0x0ea5e9, emissiveIntensity: 0.60, opacity: 0.90 }),
        arcIndigo: makeDefenseSoftVinylMat({ color: 0x4338ca, roughness: 0.48, sssColor: 0x818cf8, rimColor: 0x38bdf8, rimStrength: 0.24 }),
        sniperPlum: makeDefenseSoftVinylMat({ color: 0x6d28d9, roughness: 0.46, sssColor: 0xc084fc, rimColor: 0xfde047, rimStrength: 0.24 }),
        whiteHot: new THREE.MeshBasicMaterial({ color: 0xf8fafc, toneMapped: false }),
        pipGold: new THREE.MeshBasicMaterial({ color: 0xfde047, toneMapped: false }),
        emberHalo: makeAdditiveHaloMat(0xf97316, 0.62, 2.2),
        frostHalo: makeAdditiveHaloMat(0x38bdf8, 0.52, 2.3),
        arcHalo: makeAdditiveHaloMat(0x38bdf8, 0.58, 2.1),
        sniperHalo: makeAdditiveHaloMat(0xe879f9, 0.62, 2.1),
        goldHalo: makeAdditiveHaloMat(0xfde047, 0.54, 2.3),
      },
    };
    towerPool.geo.balBolt.rotateZ(-Math.PI / 2);
    towerPool.geo.sniperScope.rotateZ(Math.PI / 2);
    towerPool.geo.collar.rotateX(Math.PI / 2);
    towerPool.geo.waistRing.rotateX(Math.PI / 2);
    towerPool.geo.arcCoil.rotateX(Math.PI / 2);
    towerPool.geo.crownHalo.rotateX(Math.PI / 2);
    return towerPool;
  }

  function makeSharedMesh(geo, mat) {
    const m = new THREE.Mesh(geo, mat);
    m.userData.sharedGeo = true;
    m.userData.sharedMat = true;
    return m;
  }

  function buildTowerMeshForPad(padObj, typeKey, level) {
    disposeObjectTreeChildren(padObj.turretRoot);
    padObj.turretHead = null;
    padObj.barrelMesh = null;
    padObj.orbMesh = null;
    padObj.orbitGroup = null;
    padObj.crownGroup = null;
    padObj.recoil = 0;
    padObj.type = typeKey || null;
    padObj.level = level || 0;

    const pool = getTowerAssetPool();

    if (!typeKey || level <= 0 || !TOWER_DEFS[typeKey]) {
      padObj.runeMat.uniforms.uColor.value.setHex(0xfde047);
      padObj.runeMat.uniforms.uOccupied.value = 0.0;
      padObj.beaconGroup.visible = true;
      padObj.rangeField.visible = false;
      return;
    }

    const spec = TOWER_DEFS[typeKey];
    padObj.beaconGroup.visible = false;
    padObj.runeMat.uniforms.uColor.value.setHex(spec.accentHex);
    padObj.runeMat.uniforms.uOccupied.value = 1.0;
    padObj.rangeField.scale.setScalar(spec.range);
    padObj.rangeFieldMat.uniforms.uColor.value.setHex(spec.accentHex);

    const lv = Math.max(1, Math.min(5, level));
    const G = pool.geo;
    const M = pool.mat;

    // 1. Sculpted Stone Pedestal + Brushed Gold Collar
    padObj.turretRoot.add(makeSharedMesh(G.pedestal, M.stone));
    const col = makeSharedMesh(G.collar, M.gold);
    col.position.y = 0.27;
    padObj.turretRoot.add(col);

    // 2. Unified Rotating Head Sub-Group (all aiming pieces move cleanly together!)
    const yawWrap = new THREE.Group();
    yawWrap.position.y = typeKey === 'sniper' ? 0.76 : (typeKey === 'cannon' ? 0.44 : 0.36);
    yawWrap.rotation.y = 0.32;
    const pitchWrap = new THREE.Group();
    yawWrap.add(pitchWrap);
    padObj.turretHead = yawWrap;
    padObj.pitchGroup = pitchWrap;

    if (typeKey === 'ballista') {
      const turn = makeSharedMesh(G.balTurntable, M.wood);
      turn.position.y = 0.30;
      padObj.turretRoot.add(turn);

      const stock = makeSharedMesh(G.balStock, M.wood);
      const limbL = makeSharedMesh(G.balLimbL, M.wood);
      const limbR = makeSharedMesh(G.balLimbR, M.wood);
      const capL = makeSharedMesh(G.balLimbCap, M.gold);
      capL.position.set(-0.18, 0.02, 0.48);
      const capR = makeSharedMesh(G.balLimbCap, M.gold);
      capR.position.set(-0.18, 0.02, -0.48);
      const str = makeSharedMesh(G.balString, M.whiteHot);
      str.rotation.x = Math.PI / 2;
      str.position.set(-0.16, 0.02, 0);
      const bolt = makeSharedMesh(G.balBolt, M.pipGold);
      bolt.position.set(0.18, 0.05, 0);
      pitchWrap.add(stock, limbL, limbR, capL, capR, str, bolt);
      if (lv >= 3) {
        const l2 = makeSharedMesh(G.balLimbL, M.gold);
        l2.position.y = 0.09;
        l2.scale.setScalar(0.84);
        const r2 = makeSharedMesh(G.balLimbR, M.gold);
        r2.position.y = 0.09;
        r2.scale.setScalar(0.84);
        pitchWrap.add(l2, r2);
      }
      padObj.turretRoot.add(yawWrap);
    } else if (typeKey === 'cannon') {
      const drum = makeSharedMesh(G.cannonDrum, M.wood);
      drum.position.y = 0.32;
      padObj.turretRoot.add(drum);

      const barrel = makeSharedMesh(G.cannonBarrel, M.gunmetal);
      const band1 = makeSharedMesh(G.cannonRing, M.gold);
      band1.rotation.y = Math.PI / 2;
      band1.position.set(-0.02, 0, 0);
      const band2 = makeSharedMesh(G.cannonRing, M.gold);
      band2.rotation.y = Math.PI / 2;
      band2.position.set(0.32, 0, 0);
      band2.scale.setScalar(1.12);
      const boreGlow = makeSharedMesh(G.cannonCore, M.emberHalo);
      boreGlow.position.set(0.36, 0, 0);
      pitchWrap.add(barrel, band1, band2, boreGlow);
      if (lv >= 3) {
        const chL = makeSharedMesh(G.cannonCheek, M.gold);
        chL.rotation.z = Math.PI / 2;
        chL.position.set(0.02, -0.04, 0.21);
        const chR = makeSharedMesh(G.cannonCheek, M.gold);
        chR.rotation.z = Math.PI / 2;
        chR.position.set(0.02, -0.04, -0.21);
        pitchWrap.add(chL, chR);
      }
      padObj.turretRoot.add(yawWrap);
    } else if (typeKey === 'frost') {
      // 4-petal sculpted alabaster lotus cradle hugging glacial crystal
      for (let pi = 0; pi < 4; pi++) {
        const ang = (pi * Math.PI) / 2 + Math.PI * 0.25;
        const pet = makeSharedMesh(G.frostPetal, M.frostBody);
        pet.position.set(Math.cos(ang) * 0.17, 0.39, Math.sin(ang) * 0.17);
        pet.rotation.set(Math.sin(ang) * 0.38, 0, -Math.cos(ang) * 0.38);
        padObj.turretRoot.add(pet);
      }
      const cryGroup = new THREE.Group();
      cryGroup.position.y = 0.74;
      const outerC = makeSharedMesh(G.frostCrystal, M.frostCry);
      outerC.scale.set(0.74, 1.52, 0.74);
      const coreC = makeSharedMesh(G.frostCore, M.whiteHot);
      coreC.scale.set(0.74, 1.52, 0.74);
      const haloC = makeSharedMesh(G.frostHalo, M.frostHalo);
      cryGroup.add(outerC, coreC, haloC);
      padObj.orbMesh = cryGroup;
      padObj.turretRoot.add(cryGroup);

      if (lv >= 3) {
        const orbGrp = new THREE.Group();
        orbGrp.position.y = 0.74;
        for (let si = 0; si < 2; si++) {
          const sh = makeSharedMesh(G.frostShard, M.frostCry);
          sh.scale.set(0.7, 1.4, 0.7);
          sh.position.set(si === 0 ? 0.34 : -0.34, 0, 0);
          orbGrp.add(sh);
        }
        padObj.orbitGroup = orbGrp;
        padObj.turretRoot.add(orbGrp);
      }
    } else if (typeKey === 'arc') {
      const spire = makeSharedMesh(G.arcSpire, M.arcIndigo);
      const coil1 = makeSharedMesh(G.arcCoil, M.copper);
      coil1.position.y = 0.44;
      padObj.turretRoot.add(spire, coil1);
      if (lv >= 3) {
        const coil2 = makeSharedMesh(G.arcCoil, M.gold);
        coil2.scale.setScalar(0.82);
        coil2.position.y = 0.62;
        padObj.orbitGroup = coil2;
        padObj.turretRoot.add(coil2);
      }
      for (let pi = 0; pi < 3; pi++) {
        const ang = (pi * Math.PI * 2) / 3;
        const pr = makeSharedMesh(G.arcProng, M.copper);
        pr.position.set(Math.cos(ang) * 0.14, 0.80, Math.sin(ang) * 0.14);
        pr.rotation.set(Math.sin(ang) * 0.25, 0, -Math.cos(ang) * 0.25);
        padObj.turretRoot.add(pr);
      }
      const orbGrp = new THREE.Group();
      orbGrp.position.y = 0.92;
      orbGrp.add(makeSharedMesh(G.arcOrb, M.whiteHot), makeSharedMesh(G.arcOrbHalo, M.arcHalo));
      padObj.orbMesh = orbGrp;
      padObj.turretRoot.add(orbGrp);
    } else if (typeKey === 'sniper') {
      const mast = makeSharedMesh(G.sniperMast, M.sniperPlum);
      const gimbal = makeSharedMesh(G.sniperGimbal, M.gold);
      gimbal.position.y = 0.74;
      gimbal.rotation.x = Math.PI / 2;
      padObj.turretRoot.add(mast, gimbal);

      const railTop = makeSharedMesh(G.sniperRail, M.gunmetal);
      railTop.position.set(0.18, 0.055, 0);
      const railBot = makeSharedMesh(G.sniperRail, M.sniperPlum);
      railBot.position.set(0.18, -0.055, 0);
      const scope = makeSharedMesh(G.sniperScope, M.gold);
      scope.position.set(0.05, 0.12, 0);
      const lens = makeSharedMesh(G.sniperLens, M.whiteHot);
      lens.position.set(0.54, 0, 0);
      const lensHalo = makeSharedMesh(G.sniperLensHalo, M.sniperHalo);
      lensHalo.position.set(0.54, 0, 0);
      pitchWrap.add(railTop, railBot, scope, lens, lensHalo);
      if (lv >= 3) {
        const w1 = makeSharedMesh(G.sniperWing, M.gold);
        w1.position.set(-0.08, 0.12, 0.12);
        w1.rotation.x = 0.65;
        const w2 = makeSharedMesh(G.sniperWing, M.gold);
        w2.position.set(-0.08, 0.12, -0.12);
        w2.rotation.x = -0.65;
        pitchWrap.add(w1, w2);
      }
      padObj.turretRoot.add(yawWrap);
    }

    // 3. Lv.1~5 Legible Architectural Evolution + Front Framed Pip Gems
    if (lv >= 2) {
      const wr = makeSharedMesh(G.waistRing, M.gold);
      wr.position.y = 0.16;
      padObj.turretRoot.add(wr);
    }
    if (lv >= 4) {
      const auraDisc = makeSharedMesh(G.auraDisc, M.goldHalo);
      auraDisc.rotation.x = -Math.PI * 0.36;
      auraDisc.position.y = 0.03;
      padObj.turretRoot.add(auraDisc);
    }
    if (lv >= 5) {
      const crownGrp = new THREE.Group();
      crownGrp.position.y = typeKey === 'sniper' || typeKey === 'arc' ? 1.18 : 1.02;
      const halo = makeSharedMesh(G.crownHalo, M.gold);
      crownGrp.add(halo);
      for (let si = 0; si < 4; si++) {
        const ang = (si * Math.PI) / 2;
        const gem = makeSharedMesh(G.pipGem, M.pipGold);
        gem.position.set(Math.cos(ang) * 0.36, 0.05, Math.sin(ang) * 0.36);
        crownGrp.add(gem);
      }
      padObj.crownGroup = crownGrp;
      padObj.turretRoot.add(crownGrp);
    }

    // Front bevel level pip gems (1..5 clearly readable)
    const span = Math.min(5, lv);
    for (let i = 0; i < span; i++) {
      const ang = (i - (span - 1) * 0.5) * 0.32;
      const pip = makeSharedMesh(G.pipGem, M.pipGold);
      pip.position.set(Math.sin(ang) * 0.36, 0.12, Math.cos(ang) * 0.36);
      padObj.turretRoot.add(pip);
    }

    const lvScale = 0.74 + lv * 0.045 + (lv >= 4 ? 0.03 : 0);
    padObj.baseScale = lvScale;
    padObj.turretRoot.scale.setScalar(lvScale);
  }

  function ensureBuildPadsInitialized() {
    if (buildPadsInitialized) return;
    buildPadsInitialized = true;
    const pool = getTowerAssetPool();

    PAD_SLOT_SPECS.forEach((slot) => {
      const group = new THREE.Group();
      group.name = `BuildPad_${slot.id}`;

      const padShadow = makeSharedMesh(SHARED_GEO.shadowDisc, SHARED_MAT.softContactShadow);
      padShadow.rotation.x = -Math.PI * 0.36;
      padShadow.scale.setScalar(1.22);
      padShadow.position.y = -0.02;
      padShadow.renderOrder = 2;

      const plinthMesh = makeSharedMesh(pool.geo.padPlinth, pool.mat.stone);
      plinthMesh.rotation.x = 0.24;

      const runeMat = new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uColor: { value: new THREE.Color(0xfde047) },
          uOccupied: { value: 0.0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform float uTime;
          uniform vec3 uColor;
          uniform float uOccupied;
          varying vec2 vUv;
          void main() {
            vec2 p = vUv * 2.0 - 1.0;
            float r = length(p);
            if (r > 1.0) discard;
            float ang = atan(p.y, p.x);
            float outer = smoothstep(0.055, 0.0, abs(r - 0.86));
            float inner = smoothstep(0.04, 0.0, abs(r - 0.62));
            float ticks = pow(max(0.0, cos((ang + uTime * 0.7) * 8.0)), 4.0) * smoothstep(0.08, 0.0, abs(r - 0.74));
            float a = clamp(outer * 0.80 + inner * (uOccupied > 0.5 ? 0.25 : 0.55) + ticks * 0.65, 0.0, 1.0);
            gl_FragColor = vec4(uColor, a * (uOccupied > 0.5 ? 0.58 : 0.82));
          }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
        toneMapped: false,
      });
      const runeMesh = new THREE.Mesh(pool.geo.padRuneQuad, runeMat);
      runeMesh.rotation.x = -Math.PI * 0.36;
      runeMesh.position.y = 0.03;
      runeMesh.renderOrder = 3;

      const beaconGroup = new THREE.Group();
      beaconGroup.position.y = 0.22;
      beaconGroup.add(
        makeSharedMesh(pool.geo.beaconCry, pool.mat.pipGold),
        makeSharedMesh(pool.geo.beaconHalo, pool.mat.goldHalo)
      );

      const rangeFieldMat = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: new THREE.Color(0x38bdf8) },
          uAlpha: { value: 0.0 },
          uTime: { value: 0.0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uAlpha;
          uniform float uTime;
          varying vec2 vUv;
          void main() {
            if (uAlpha <= 0.01) discard;
            vec2 p = vUv * 2.0 - 1.0;
            float r = length(p);
            if (r > 1.0) discard;
            float ang = atan(p.y, p.x);
            float dash = step(-0.2, sin((ang + uTime * 0.25) * 18.0));
            float rim = smoothstep(0.028, 0.0, abs(r - 0.97)) * (0.45 + 0.55 * dash);
            float fill = (1.0 - smoothstep(0.88, 1.0, r)) * 0.09;
            gl_FragColor = vec4(uColor, (rim * 0.62 + fill) * uAlpha);
          }
        `,
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide,
        toneMapped: false,
      });
      const rangeField = new THREE.Mesh(pool.geo.rangeDisc, rangeFieldMat);
      rangeField.rotation.x = 0.0;
      rangeField.position.y = 0.01;
      rangeField.visible = false;
      rangeField.renderOrder = 2;

      const turretRoot = new THREE.Group();
      group.add(padShadow, plinthMesh, runeMesh, beaconGroup, rangeField, turretRoot);
      padTowersGroup.add(group);

      buildPads.push({
        id: slot.id,
        nx: slot.nx,
        ny: slot.ny,
        label: slot.label,
        group,
        ringMesh: runeMesh,
        runeMat,
        beaconGroup,
        rangeField,
        rangeFieldMat,
        turretRoot,
        turretHead: null,
        pitchGroup: null,
        orbMesh: null,
        orbitGroup: null,
        crownGroup: null,
        baseScale: 0.80,
        recoil: 0,
        rangeAlpha: 0,
        previewRange: 0,
        targetMode: 'first',
        type: null,
        level: 0,
        cooldown: 0,
      });
    });

    // Ensure Partner Plump 5-Point Beveled Golden Star-Orb + Starlight Ring + Gaussian Synchro Tether
    if (partnerStageGroup && !partnerStaffOrb) {
      partnerStaffOrb = new THREE.Group();
      const orbCore = makeSharedMesh(SHARED_GEO.starOrb, pool.mat.pipGold);
      const orbHalo = makeSharedMesh(pool.geo.frostHalo, pool.mat.goldHalo);
      orbHalo.scale.setScalar(0.85);
      const orbRing = makeSharedMesh(new THREE.TorusGeometry(0.32, 0.028, 10, 26), pool.mat.gold);
      partnerStaffOrb.add(orbCore, orbHalo, orbRing);
      partnerStaffOrb.position.set(0.68, 1.48, 0.25);
      partnerStaffOrb.visible = false;
      partnerStageGroup.add(partnerStaffOrb);

      const auraMat = new THREE.ShaderMaterial({
        uniforms: {
          uTime: { value: 0 },
          uColor: { value: new THREE.Color(0x4ade80) },
          uGold: { value: new THREE.Color(0xfde047) },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
        `,
        fragmentShader: `
          uniform float uTime;
          uniform vec3 uColor;
          uniform vec3 uGold;
          varying vec2 vUv;
          void main() {
            vec2 p = vUv * 2.0 - 1.0;
            float r = length(p);
            if (r > 1.0) discard;
            float ang = atan(p.y, p.x);
            float ring = smoothstep(0.06, 0.0, abs(r - 0.84));
            float petals = pow(max(0.0, cos((ang - uTime * 0.8) * 6.0)), 4.0) * smoothstep(0.09, 0.0, abs(r - 0.78));
            vec3 col = mix(uColor, uGold, petals * 0.75);
            gl_FragColor = vec4(col, clamp(ring * 0.48 + petals * 0.42, 0.0, 0.75));
          }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
        toneMapped: false,
      });
      partnerAuraRing = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 2.2), auraMat);
      partnerAuraRing.rotation.x = -Math.PI * 0.36;
      partnerAuraRing.position.y = 0.02;
      partnerAuraRing.visible = false;
      partnerStageGroup.add(partnerAuraRing);
    }

    if (!synchroBeamMesh) {
      const syncMat = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: new THREE.Color(0xfde047) },
          uOpacity: { value: 0.90 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() { vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0); }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uOpacity;
          varying vec2 vUv;
          void main() {
            float y = abs(vUv.x - 0.5) * 2.0;
            float core = exp(-y * y * 14.0);
            float halo = exp(-y * y * 3.2);
            vec3 col = mix(uColor, vec3(1.0), core * 0.85);
            gl_FragColor = vec4(col, clamp(halo * 0.78 + core, 0.0, 1.0) * uOpacity);
          }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        side: THREE.DoubleSide,
        toneMapped: false,
      });
      synchroBeamMesh = new THREE.Mesh(SHARED_GEO.ribbonQuad, syncMat);
      synchroBeamMesh.visible = false;
      synchroBeamMesh.renderOrder = 16;
      worldRoot.add(synchroBeamMesh);
    }
  }

  function syncBuildPadsToRpgState() {
    ensureBuildPadsInitialized();
    const { xMin, yMin, width, height } = getDesktopWorldBounds();
    const statePads = rpgState.towerPads || {};
    buildPads.forEach((pad) => {
      pad.group.position.set(xMin + width * pad.nx, yMin + height * pad.ny, -0.05);
      const info = statePads[pad.id] || { type: null, level: 0 };
      const wantType = info.type || null;
      const wantLv = Math.max(0, Math.min(5, parseInt(info.level || 0, 10) || 0));
      if (pad.type !== wantType || pad.level !== wantLv) {
        buildTowerMeshForPad(pad, wantType, wantLv);
      }
    });
  }

  function getDesktopBuildPads() {
    syncBuildPadsToRpgState();
    return buildPads.map((p) => ({
      id: p.id,
      label: p.label,
      type: p.type,
      level: p.level,
      x: p.group.position.x,
      y: p.group.position.y,
    }));
  }

  function hideBuildPadPopover() {
    if (combatState.selectedPadId) {
      const p = buildPads.find((x) => x.id === combatState.selectedPadId);
      if (p) p.previewRange = 0;
    }
    combatState.selectedPadId = null;
    if (typeof document !== 'undefined') {
      const pop = document.getElementById('defense-pad-popover');
      if (pop) pop.style.display = 'none';
    }
  }

  function updateBuildPadHover(nx, ny) {
    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') {
      hoveredPadId = null;
      return null;
    }
    ndcVec.set(nx, ny);
    raycaster.setFromCamera(ndcVec, camera);
    const hasHit = raycaster.ray.intersectPlane(screenPlaneMath, rayHitPoint);
    if (!hasHit) {
      hoveredPadId = null;
      return null;
    }
    let best = null;
    let bestD = 1.28;
    for (let i = 0; i < buildPads.length; i++) {
      const p = buildPads[i];
      const d = Math.hypot(p.group.position.x - rayHitPoint.x, p.group.position.y - rayHitPoint.y);
      if (d <= bestD) {
        bestD = d;
        best = p;
      }
    }
    hoveredPadId = best ? best.id : null;
    return hoveredPadId;
  }

  function applyPadTowerAction(action, padId, towerType = null) {
    const pad = buildPads.find((p) => p.id === padId);
    if (!pad) return false;
    if (!rpgState.towerPads) rpgState.towerPads = {};
    const cur = rpgState.towerPads[padId] || { type: null, level: 0 };

    if (action === 'build') {
      const spec = TOWER_DEFS[towerType];
      if (!spec || cur.type) return false;
      const cost = getTowerBuildDiscountedCost(spec.costs[0]);
      if ((rpgState.gold || 0) < cost) {
        showLiveCoachingToast(`⚠️ 골드 부족! ${spec.name} 건설에 ${cost}G 필요`);
        return false;
      }
      rpgState.gold -= cost;
      rpgState.towerPads[padId] = { type: towerType, level: 1 };
      buildTowerMeshForPad(pad, towerType, 1);
      spawnShockwaveRing(pad.group.position, spec.accentHex, 1.35);
      spawnFloatText(`${spec.icon} ${spec.name} Lv.1 건설!`, pad.group.position, spec.accentCss, 1.05);
      if (typeof window.emitPpongSync === 'function') {
        window.emitPpongSync({ type: 'tower_pad_action', action: 'build', padId, towerType, level: 1, cost, goldDelta: -cost });
      }
      hideBuildPadPopover();
      updateTacticalHudVisibility(true);
      return true;
    }

    if (action === 'upgrade') {
      const spec = TOWER_DEFS[cur.type];
      if (!spec || (cur.level || 0) >= 5) return false;
      const nextLv = (cur.level || 1) + 1;
      const cost = getTowerBuildDiscountedCost(spec.costs[nextLv - 1]);
      if ((rpgState.gold || 0) < cost) {
        showLiveCoachingToast(`⚠️ 골드 부족! Lv.${nextLv} 업그레이드에 ${cost}G 필요`);
        return false;
      }
      rpgState.gold -= cost;
      rpgState.towerPads[padId] = { type: cur.type, level: nextLv };
      buildTowerMeshForPad(pad, cur.type, nextLv);
      spawnShockwaveRing(pad.group.position, 0xfde047, 1.5);
      spawnFloatText(`⬆️ ${spec.name} Lv.${nextLv}!`, pad.group.position, '#fde047', 1.1);
      if (typeof window.emitPpongSync === 'function') {
        window.emitPpongSync({ type: 'tower_pad_action', action: 'upgrade', padId, towerType: cur.type, level: nextLv, cost, goldDelta: -cost });
      }
      hideBuildPadPopover();
      updateTacticalHudVisibility(true);
      return true;
    }

    if (action === 'sell') {
      const spec = TOWER_DEFS[cur.type];
      if (!spec) return false;
      let totalSpent = 0;
      for (let i = 0; i < (cur.level || 1); i++) totalSpent += spec.costs[i] || 100;
      const refund = Math.round(totalSpent * 0.70);
      rpgState.gold += refund;
      rpgState.towerPads[padId] = { type: null, level: 0 };
      buildTowerMeshForPad(pad, null, 0);
      spawnFloatText(`💰 +${refund}G 회수`, pad.group.position, '#fbbf24', 1.0);
      if (typeof window.emitPpongSync === 'function') {
        window.emitPpongSync({ type: 'tower_pad_action', action: 'sell', padId, towerType: null, level: 0, refund, goldDelta: refund });
      }
      hideBuildPadPopover();
      updateTacticalHudVisibility(true);
      return true;
    }
    return false;
  }

  function openBuildPadPopover(padId) {
    if (typeof document === 'undefined') return false;
    const pad = buildPads.find((p) => p.id === padId);
    const pop = document.getElementById('defense-pad-popover');
    if (!pad || !pop) return false;
    combatState.selectedPadId = padId;

    const proj = pad.group.position.clone().project(camera);
    const sx = (proj.x * 0.5 + 0.5) * (window.innerWidth || 1920);
    const sy = (-proj.y * 0.5 + 0.5) * (window.innerHeight || 1080);
    const left = Math.max(16, Math.min((window.innerWidth || 1920) - 316, sx + 18));
    const top = Math.max(16, Math.min((window.innerHeight || 1080) - 380, sy - 125));

    const gold = Math.floor(rpgState.gold || 0);
    lastPopoverGold = gold;
    const tInfo = getTypingLevelInfo();
    const tDiscountBadge = tInfo.upgradeDiscount > 0 ? ' <span style="color:#4ade80;font-size:10px;">(-8% 할인)</span>' : '';
    const TARGET_LABELS = { first: '🎯 선두 우선', strong: '💪 고체력 우선', support: '🚩 주술·원거리', shield: '🛡️ 방패병 우선' };

    if (!pad.type) {
      pad.previewRange = TOWER_DEFS.ballista.range;
      if (pad.rangeField) pad.rangeField.scale.setScalar(pad.previewRange);
      if (pad.rangeFieldMat?.uniforms?.uColor) pad.rangeFieldMat.uniforms.uColor.value.setHex(TOWER_DEFS.ballista.accentHex);

      let btnsHtml = '';
      Object.values(TOWER_DEFS).forEach((spec) => {
        const wsFloorLv = Math.max(1, Math.min(5, parseInt((rpgState.turrets && rpgState.turrets[spec.key]) || 0, 10) > 1 ? 2 : 1));
        const cost = getTowerBuildDiscountedCost(spec.costs[0]);
        const disabled = gold < cost ? 'disabled' : '';
        const lvTag = wsFloorLv > 1 ? ` · Lv.${wsFloorLv} 연구` : '';
        btnsHtml += `<button class="def-pad-btn" data-act="build" data-type="${spec.key}" ${disabled}>`
          + `<span>${spec.icon} ${spec.name}${lvTag}</span>`
          + `<span style="color:${gold >= cost ? '#fbbf24' : '#f87171'};font-size:10px;">${cost}G · ${spec.role}</span>`
          + `</button>`;
      });
      pop.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;">`
        + `<span style="font-size:12.5px;font-weight:900;color:#fde047;">🏗️ ${pad.label}${tDiscountBadge}</span>`
        + `<button id="pad-pop-close" style="background:none;border:none;color:#94a3b8;font-size:14px;cursor:pointer;">✕</button></div>`
        + `<div style="font-size:10.5px;color:#cbd5e1;margin-top:2px;">건설할 포탑 선택 · 마우스 오버 시 사거리 표시 (보유 ${gold}G)</div>`
        + `<div class="def-pad-grid">${btnsHtml}</div>`;
    } else {
      pad.previewRange = 0;
      const spec = TOWER_DEFS[pad.type];
      const lv = pad.level || 1;
      const effRange = getEffectiveTowerRange(pad.type, lv);
      if (pad.rangeField) pad.rangeField.scale.setScalar(effRange);
      const dmg = Math.round(combatState.heroAtk * spec.dmgMult[lv - 1] * (tInfo.towerDmgMult || 1.0));
      const upCost = lv < 5 ? getTowerBuildDiscountedCost(spec.costs[lv]) : 0;
      let totalSpent = 0;
      for (let i = 0; i < lv; i++) totalSpent += spec.costs[i] || 100;
      const refund = Math.round(totalSpent * 0.70);
      const curMode = pad.targetMode || 'first';
      pop.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;">`
        + `<span style="font-size:12.5px;font-weight:900;color:${spec.accentCss};">${spec.icon} ${spec.name} Lv.${lv}${tDiscountBadge}</span>`
        + `<button id="pad-pop-close" style="background:none;border:none;color:#94a3b8;font-size:14px;cursor:pointer;">✕</button></div>`
        + `<div style="font-size:10.5px;color:#cbd5e1;margin:4px 0;">공격 ${dmg} · 공속 ${spec.rate[lv - 1].toFixed(2)}/s · 사거리 ${effRange.toFixed(1)}</div>`
        + `<button id="pad-target-cycle" class="def-pad-btn" style="width:100%;margin-bottom:6px;flex-direction:row;justify-content:space-between;align-items:center;">`
        + `<span style="font-size:10.5px;color:#93c5fd;">조준 우선순위</span><span style="font-size:10.5px;font-weight:800;color:#f8fafc;">${TARGET_LABELS[curMode] || TARGET_LABELS.first} ↻</span></button>`
        + `<div class="def-pad-grid">`
        + (lv < 5
          ? `<button class="def-pad-btn" data-act="upgrade" ${gold < upCost ? 'disabled' : ''}><span>⬆️ Lv.${lv + 1} 강화</span><span style="color:${gold >= upCost ? '#fbbf24' : '#f87171'};font-size:10px;">${upCost}G</span></button>`
          : `<button class="def-pad-btn" disabled><span>👑 MAX</span><span style="color:#fde047;font-size:10px;">최고 단계</span></button>`)
        + `<button class="def-pad-btn" data-act="sell"><span>💥 철거 판매</span><span style="color:#4ade80;font-size:10px;">+${refund}G</span></button>`
        + `</div>`;
    }

    pop.style.left = `${Math.round(left)}px`;
    pop.style.top = `${Math.round(top)}px`;
    pop.style.display = 'block';

    const btnClose = pop.querySelector('#pad-pop-close');
    if (btnClose) btnClose.onclick = () => hideBuildPadPopover();
    const btnCycle = pop.querySelector('#pad-target-cycle');
    if (btnCycle) {
      btnCycle.onclick = () => {
        const order = ['first', 'strong', 'support', 'shield'];
        pad.targetMode = order[(order.indexOf(pad.targetMode || 'first') + 1) % order.length];
        openBuildPadPopover(padId);
      };
    }
    pop.querySelectorAll('.def-pad-btn[data-act]').forEach((btn) => {
      const act = btn.getAttribute('data-act');
      const tp = btn.getAttribute('data-type');
      if (act === 'build' && tp && TOWER_DEFS[tp]) {
        btn.onpointerenter = () => {
          const r = getEffectiveTowerRange(tp, 1);
          pad.previewRange = r;
          if (pad.rangeField) pad.rangeField.scale.setScalar(r);
          if (pad.rangeFieldMat?.uniforms?.uColor) pad.rangeFieldMat.uniforms.uColor.value.setHex(TOWER_DEFS[tp].accentHex);
        };
      }
      btn.onclick = () => {
        applyPadTowerAction(act, padId, tp);
      };
    });
    return true;
  }

  function showLiveCoachingToast(text) {
    if (typeof document === 'undefined') return;
    const toast = document.getElementById('def-live-coach-toast');
    if (!toast) return;
    toast.textContent = text;
    toast.classList.add('visible');
    if (coachToastTimer) clearTimeout(coachToastTimer);
    coachToastTimer = setTimeout(() => {
      if (toast) toast.classList.remove('visible');
    }, 4500);
  }

  function computeDefenseReadiness() {
    const w = Math.max(1, combatState.wave || rpgState.highestWave || 1);
    const tInfo = getTypingLevelInfo();
    const pads = Object.values(rpgState.towerPads || {});
    let towerPower = 0;
    pads.forEach((p) => {
      if (p && p.type && TOWER_DEFS[p.type]) {
        const lv = Math.max(1, Math.min(5, p.level || 1));
        towerPower += combatState.heroAtk * (tInfo.towerDmgMult || 1.0) * TOWER_DEFS[p.type].dmgMult[lv - 1] * TOWER_DEFS[p.type].rate[lv - 1] * 0.85;
      }
    });
    const barBonus = (rpgState.turrets?.barricade || 0) * 18;
    const playerPower = Math.round((combatState.heroAtk * combatState.heroAps * 1.45) + ((combatState.partnerAtk || 18) * 1.25) + towerPower + barBonus);
    const waveNeed = Math.round(90 + 42 * w + 10 * Math.pow(w, 1.48));
    const ratio = playerPower / Math.max(1, waveNeed);
    if (ratio >= 1.12) return { label: '🟢 우세', ratio, playerPower, waveNeed, bg: 'rgba(22,163,74,0.28)', fg: '#86efac' };
    if (ratio >= 0.80) return { label: '🟡 박빙', ratio, playerPower, waveNeed, bg: 'rgba(217,119,6,0.28)', fg: '#fde047' };
    return { label: '🔴 열세', ratio, playerPower, waveNeed, bg: 'rgba(225,29,72,0.32)', fg: '#fda4af' };
  }

  function buildDefeatDiagnosis() {
    const tel = combatState.telemetry || {};
    const dmgSrc = tel.dmgBySource || {};
    const takenSrc = tel.damageTakenBySource || {};
    const w = Math.max(1, combatState.wave || 1);
    const pads = Object.values(rpgState.towerPads || {});
    const emptyPads = pads.filter((p) => !p || !p.type).length;
    const totalPadsPower = pads.filter((p) => p && p.type).length;
    const enh = Math.max(0, rpgState.weaponEnhance || 0);
    const gold = Math.floor(rpgState.gold || 0);
    const diag = [];

    if (emptyPads >= 2 && gold >= 120) {
      diag.push({
        severity: 95,
        title: `비어있는 포탑 슬롯 방치 (${emptyPads}/5칸 비어있음)`,
        detail: `보유 ${gold.toLocaleString()}G로 패드를 클릭해 즉시 포탑을 건설할 수 있었습니다.`,
        badge: '🗼 포탑 추가 건설',
        ctaLabel: '🗼 포탑 관리',
        action: 'towers',
      });
    }
    if (enh < w * 1.2) {
      diag.push({
        severity: 90,
        title: `주력 무기 강화 부족 (+${enh}강 / 권장 +${Math.ceil(w * 1.2)}강+)`,
        detail: `현재 영웅 공격력(${combatState.heroAtk})이 Stage ${w} 적 방어력 대비 부족합니다.`,
        badge: '⚒️ 무기 강화 필요',
        ctaLabel: '⚒️ 대장간 강화',
        action: 'forge',
      });
    }
    if ((rpgState.turrets?.barricade || 0) <= 1 && (tel.baseDmgTaken || 0) >= combatState.baseMaxHp * 0.4) {
      diag.push({
        severity: 86,
        title: '성소 바리케이드 방어력 부족',
        detail: `성소 누적 피해 ${Math.round(tel.baseDmgTaken || 0)}. 바리케이드 강화 시 피해 감소율이 크게 오릅니다.`,
        badge: '🛡️ 바리케이드 강화',
        ctaLabel: '🗼 포탑 관리',
        action: 'towers',
      });
    }
    const frostBuilt = pads.some((p) => p && p.type === 'frost');
    if (!frostBuilt && ((takenSrc.vanguard || 0) > 120 || (takenSrc.support_shaman || 0) > 40)) {
      diag.push({
        severity: 80,
        title: '감속·치유저지(서리 프리즘) 미배치',
        detail: '돌격병 러시 및 주술사 회복을 늦추는 ❄️ 서리 프리즘 건설이 효과적입니다.',
        badge: '❄️ 서리 포탑 추천',
        ctaLabel: '🗼 포탑 관리',
        action: 'towers',
      });
    }
    const pierceBuilt = pads.some((p) => p && (p.type === 'arc' || p.type === 'sniper'));
    if (!pierceBuilt && ((takenSrc.shield_tank || 0) > 90 || (takenSrc.boss || 0) > 120)) {
      diag.push({
        severity: 78,
        title: '중장갑/보스 관통 화력 부족',
        detail: '방패병·보스 상대로는 ⚡ 번개 파일런 또는 🎯 별빛 스나이퍼가 핵심입니다.',
        badge: '⚡/🎯 관통 포탑',
        ctaLabel: '🗼 포탑 관리',
        action: 'towers',
      });
    }
    const skTot = (tel.skillsUsed?.Q || 0) + (tel.skillsUsed?.W || 0) + (tel.skillsUsed?.E || 0);
    if (skTot === 0) {
      diag.push({
        severity: 74,
        title: '전술 스킬 [Q/W/E] 미사용',
        detail: '위기 시 [Q] 유성우, [W] 성소 보호막+수리, [E] 거대화로 적 웨이브를 끊으세요.',
        badge: '☄️ 스킬 적극 활용',
        ctaLabel: '🔄 즉시 재도전',
        action: 'retry',
      });
    }
    const totBentos = Object.values(rpgState.bentos || {}).reduce((a, b) => a + (b || 0), 0);
    if (totBentos === 0 && (rpgState.consumables?.hp_potion || 0) <= 0) {
      diag.push({
        severity: 70,
        title: '전투 도시락·생명 포션 고갈',
        detail: '농장 수확·낚시 요리로 도시락을 비축하면 체력 45% 이하에서 자동 섭취합니다.',
        badge: '🍳 도시락 보충',
        ctaLabel: '🍳 주방/농장',
        action: 'kitchen',
      });
    }
    if (getTypingLevelInfo().level <= 1 && w >= 3) {
      diag.push({
        severity: 66,
        title: '타이핑 각성 레벨 Lv.1 (영구 보너스 0%)',
        detail: `키보드 10,000타 달성 시 Lv.2 각성! 영웅·파트너·성소 영구 버프를 획득합니다.`,
        badge: '⌨️ 타이핑 성장',
        ctaLabel: '🔄 즉시 재도전',
        action: 'retry',
      });
    }

    if (diag.length < 3 && totalPadsPower < 5) {
      diag.push({
        severity: 62,
        title: `빈 방어 패드 활용 (${totalPadsPower}/5칸 배치됨)`,
        detail: '빈 패드를 클릭해 ❄️ 서리·⚡ 번개·🎯 스나이퍼 조합을 완성하면 시너지가 극대화됩니다.',
        badge: '🗼 포탑 확장',
        ctaLabel: '🗼 포탑 관리',
        action: 'towers',
      });
    }
    if (diag.length < 3) {
      diag.push({
        severity: 58,
        title: `타이핑 각성 Lv.${getTypingLevelInfo().level} → Lv.${getTypingLevelInfo().level + 1} 성장 목표`,
        detail: `다음 타이핑 레벨 달성 시 영웅·${PARTNER_NAME_KR}·포탑 공격력이 영구 상승합니다.`,
        badge: '✨ 타자 성장',
        ctaLabel: '🔄 즉시 재도전',
        action: 'retry',
      });
    }
    if (diag.length < 3) {
      diag.push({
        severity: 55,
        title: '보스 패턴 [클릭 차단] & 전술 소모품 활용',
        detail: '붉은 보스 장판이 뜰 때 화면을 2회 클릭해 기절시키거나 물약·비약을 활용하세요.',
        badge: '🎯 패턴 파훼',
        ctaLabel: '🍳 주방/농장',
        action: 'kitchen',
      });
    }

    diag.sort((a, b) => b.severity - a.severity);
    const heroDmg = dmgSrc.hero || 0;
    const partnerDmg = dmgSrc.partner || 0;
    const towerDmg = (dmgSrc.ballista || 0) + (dmgSrc.cannon || 0) + (dmgSrc.frost || 0) + (dmgSrc.arc || 0) + (dmgSrc.sniper || 0);
    const skillDmg = dmgSrc.skill || 0;
    const sumBuckets = heroDmg + partnerDmg + towerDmg + skillDmg;
    const totalDmg = Math.max(1, sumBuckets || tel.totalDamageDealt || 1);
    const pctVal = (v) => Math.round((v / totalDmg) * 100);
    const durationSec = Math.max(1, Math.round(((Date.now() - (tel.waveStartMs || Date.now())) / 1000)));
    const rdy = computeDefenseReadiness();
    const topCauses = diag.slice(0, 3);
    return {
      wave: w,
      durationSec,
      totalDmg: Math.round(sumBuckets || tel.totalDamageDealt || 0),
      actualDps: Math.round((sumBuckets || tel.totalDamageDealt || 0) / durationSec),
      reqDps: rdy.waveNeed,
      heroPct: pctVal(heroDmg),
      partnerPct: pctVal(partnerDmg),
      towerPct: pctVal(towerDmg),
      skillPct: pctVal(skillDmg),
      breaches: (tel.baseBreaches || []).slice(-4),
      damageTakenBySource: takenSrc,
      topCauses,
      recommendations: topCauses.map((c) => ({ text: `${c.title} — ${c.badge}`, action: c.action })),
    };
  }

  function hideDefenseDefeatReport() {
    if (typeof document === 'undefined') return;
    const rep = document.getElementById('defense-defeat-report');
    if (rep) rep.style.display = 'none';
  }

  function openDefenseDefeatReport(diag) {
    if (typeof document === 'undefined' || !diag) return;
    const rep = document.getElementById('defense-defeat-report');
    if (!rep) return;

    const causeCards = (diag.topCauses || []).map((c, idx) => (
      `<div class="def-diag-card">`
      + `<div style="flex:1;"><div style="font-size:12px;font-weight:900;color:#fef08a;">#${idx + 1} ${c.title}</div>`
      + `<div style="font-size:11px;color:#cbd5e1;margin-top:2px;line-height:1.35;">${c.detail}</div></div>`
      + `<button class="def-diag-cta" data-defeat-act="${c.action}">${c.ctaLabel}</button>`
      + `</div>`
    )).join('');

    const takenEntries = Object.entries(diag.damageTakenBySource || {})
      .filter(([, v]) => v > 0)
      .sort((a, b) => b[1] - a[1]);
    const roleLabel = { vanguard: '⚔️돌격병', shield_tank: '🛡️방패병', arcane_ranger: '🔮마도사', support_shaman: '🚩주술사', boss: '👑보스' };
    const breachChips = takenEntries.length > 0
      ? takenEntries.map(([k, v]) => `<span style="padding:2px 8px;border-radius:99px;background:rgba(244,63,94,0.22);border:1px solid rgba(244,63,94,0.45);font-size:10.5px;color:#fecdd3;">${roleLabel[k] || k} -${Math.round(v)}</span>`).join(' ')
      : '<span style="font-size:10.5px;color:#94a3b8;">집계된 피해 없음</span>';

    rep.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;">`
      + `<div><div style="font-size:11px;font-weight:800;color:#fb7185;letter-spacing:0.6px;">BATTLE AUTOPSY · STAGE ${diag.wave}</div>`
      + `<div style="font-size:16px;font-weight:900;color:#fde047;">💥 성소 방어선 분석 리포트 (${diag.durationSec}초 생존)</div></div>`
      + `<button id="def-rep-close" style="background:none;border:none;color:#94a3b8;font-size:17px;cursor:pointer;">✕</button></div>`
      + `<div style="margin-top:10px;padding:8px 10px;border-radius:10px;background:rgba(2,6,23,0.65);border:1px solid rgba(148,163,184,0.2);">`
      + `<div style="font-size:11px;font-weight:800;color:#e2e8f0;margin-bottom:4px;">총 피해량 ${diag.totalDmg.toLocaleString()} 기여도 · 퐁퐁 ${diag.heroPct}% | ${PARTNER_NAME_KR} ${diag.partnerPct}% | 포탑 ${diag.towerPct}% | 스킬 ${diag.skillPct}%</div>`
      + `<div style="display:flex;height:8px;border-radius:99px;overflow:hidden;background:#0f172a;">`
      + `<div style="width:${diag.heroPct}%;background:#4ade80;"></div>`
      + `<div style="width:${diag.partnerPct}%;background:#facc15;"></div>`
      + `<div style="width:${diag.towerPct}%;background:#38bdf8;"></div>`
      + `<div style="width:${diag.skillPct}%;background:#f97316;"></div>`
      + `</div></div>`
      + `<div style="margin-top:8px;display:flex;flex-wrap:wrap;align-items:center;gap:6px;"><span style="font-size:11px;font-weight:800;color:#fda4af;">주요 돌파 적군:</span>${breachChips}</div>`
      + `<div style="margin-top:10px;font-size:11.5px;font-weight:900;color:#f8fafc;">🎯 부족 요소 TOP 3 & 즉시 보완 행동</div>`
      + `${causeCards}`
      + `<div style="display:flex;justify-content:flex-end;gap:8px;margin-top:12px;">`
      + `<button id="def-rep-retry" class="def-diag-cta" style="background:linear-gradient(180deg,#0284c7,#0369a1);border-color:#7dd3fc;color:#e0f2fe;">🔄 Stage ${diag.wave} 재도전</button>`
      + `<button id="def-rep-dismiss" class="def-diag-cta" style="background:rgba(51,65,85,0.9);border-color:#64748b;color:#e2e8f0;">닫기</button>`
      + `</div>`;

    rep.style.display = 'block';
    const handleAct = (act) => {
      hideDefenseDefeatReport();
      if (act === 'retry') {
        if (typeof window.emitPpongSync === 'function') {
          window.emitPpongSync({ type: 'retry_wave', wave: diag.wave });
        } else {
          startWaveDefense(diag.wave);
        }
      } else {
        stopCombatAndDefense();
        if (typeof window.emitPpongSync === 'function') {
          window.emitPpongSync({ type: 'defeat_action', action: act, wave: diag.wave });
        }
      }
    };
    const btnClose = rep.querySelector('#def-rep-close');
    const btnDismiss = rep.querySelector('#def-rep-dismiss');
    const btnRetry = rep.querySelector('#def-rep-retry');
    if (btnClose) btnClose.onclick = () => handleAct('close');
    if (btnDismiss) btnDismiss.onclick = () => handleAct('close');
    if (btnRetry) btnRetry.onclick = () => handleAct('retry');
    rep.querySelectorAll('[data-defeat-act]').forEach((b) => {
      b.onclick = () => handleAct(b.getAttribute('data-defeat-act'));
    });
  }

  // ===========================================================================
  // 4. CC0 Professional 3D .glb Character/Weapon Asset Pipeline & Skeletal FSM
  // ===========================================================================
  const gltfLoader = GLTFLoader ? new GLTFLoader() : null;
  // Note: All 37 CC0 .glb and 5 fallback .glb assets are uncompressed glTF 2.0 binaries.
  if (gltfLoader && DRACOLoader && false) {
    const dracoLoader = new DRACOLoader();
    gltfLoader.setDRACOLoader(dracoLoader);
  }

  const GLB_TEMPLATE_CACHE = new Map();
  const GLB_RESOLVED_CACHE = new Map();

  const ENEMY_ANIM_PACK_URLS = {
    rig_medium_move: './assets/enemies/anim_rig_medium_move.glb',
    rig_medium_melee: './assets/enemies/anim_rig_medium_melee.glb',
    rig_medium_ranged: './assets/enemies/anim_rig_medium_ranged.glb',
    rig_medium_general: './assets/enemies/anim_rig_medium_general.glb',
    rig_large_move: './assets/enemies/anim_rig_large_move.glb',
    rig_large_melee: './assets/enemies/anim_rig_large_melee.glb',
    rig_large_general: './assets/enemies/anim_rig_large_general.glb',
  };

  const HERO_WEAPON_GLB_URLS = {
    sword_t1: './assets/weapons/hero_sword_tier1.glb',
    sword_t2: './assets/weapons/hero_sword_tier2.glb',
    sword_t3: './assets/weapons/hero_sword_tier3.glb',
    sword_katana: './assets/weapons/hero_sword_katana.glb',
    gun_t1: './assets/weapons/hero_gun_tier1.glb',
    gun_t2: './assets/weapons/hero_gun_tier2.glb',
    gun_t3: './assets/weapons/hero_gun_tier3.glb',
    bow_golden: './assets/weapons/hero_bow_golden.glb',
    arrow_golden: './assets/weapons/hero_arrow_golden.glb',
  };

  const ENEMY_GEAR_PROP_URLS = {
    sword: './assets/enemies/gear_sword_golden.glb',
    shield_heater: './assets/enemies/gear_shield_heater.glb',
    shield_celtic: './assets/enemies/gear_shield_celtic.glb',
    spear: './assets/enemies/gear_spear.glb',
    hammer: './assets/enemies/gear_hammer_double.glb',
    bow: './assets/enemies/gear_bow_evil.glb',
    scythe: './assets/enemies/gear_scythe.glb',
  };

  const ENEMY_BRACKET_ROLE_MODELS = {
    0: {
      vanguard: [
        { url: './assets/enemies/b0_vanguard_werewolf.glb', fallbackUrl: './assets/models/Fox.glb', rigFamily: 'Rig_Medium', targetHeight: 1.48, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.42 },
        { url: './assets/enemies/b0_vanguard_wolf.glb', fallbackUrl: './assets/models/Fox.glb', rigFamily: 'Self', targetHeight: 1.36, facingYawOffset: 0, isQuadruped: true, hitFrameRatio: 0.42 },
      ],
      shield_tank: [
        { url: './assets/enemies/b0_tank_orc_raider.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Rig_Medium', targetHeight: 1.60, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
        { url: './assets/enemies/b0_tank_spider.glb', fallbackUrl: './assets/models/Fox.glb', rigFamily: 'Self', targetHeight: 1.36, facingYawOffset: 0, isQuadruped: true, hitFrameRatio: 0.45 },
      ],
      arcane_ranger: [
        { url: './assets/enemies/b0_ranger_plant.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.48, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      support_shaman: [
        { url: './assets/enemies/b0_shaman_witch.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.50, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      boss: [
        { url: './assets/enemies/b0_boss_orc_brute.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Rig_Large', targetHeight: 2.52, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
      ],
    },
    1: {
      vanguard: [
        { url: './assets/enemies/b1_vanguard_robot.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Rig_Medium', targetHeight: 1.50, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.42 },
      ],
      shield_tank: [
        { url: './assets/enemies/b1_tank_combat_mech.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Rig_Medium', targetHeight: 1.66, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
      ],
      arcane_ranger: [
        { url: './assets/enemies/b1_ranger_drone.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Self', targetHeight: 1.48, facingYawOffset: 0, isQuadruped: true, hitFrameRatio: 0.48 },
      ],
      support_shaman: [
        { url: './assets/enemies/b1_shaman_mecha_large.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Self', targetHeight: 1.62, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      boss: [
        { url: './assets/enemies/b1_boss_clanker.glb', fallbackUrl: './assets/models/RobotExpressive.glb', rigFamily: 'Rig_Large', targetHeight: 2.58, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
      ],
    },
    2: {
      vanguard: [
        { url: './assets/enemies/b2_vanguard_skel_rogue.glb', fallbackUrl: './assets/models/Soldier.glb', rigFamily: 'Rig_Medium', targetHeight: 1.52, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.42 },
      ],
      shield_tank: [
        { url: './assets/enemies/b2_tank_skel_warrior.glb', fallbackUrl: './assets/models/Soldier.glb', rigFamily: 'Rig_Medium', targetHeight: 1.62, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
      ],
      arcane_ranger: [
        { url: './assets/enemies/b2_ranger_skel_mage.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.52, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      support_shaman: [
        { url: './assets/enemies/b2_shaman_necromancer.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.55, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      boss: [
        { url: './assets/enemies/b2_boss_skel_golem.glb', fallbackUrl: './assets/models/Soldier.glb', rigFamily: 'Rig_Large', targetHeight: 2.60, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
      ],
    },
    3: {
      vanguard: [
        { url: './assets/enemies/b3_vanguard_tiefling.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.54, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.42 },
      ],
      shield_tank: [
        { url: './assets/enemies/b3_tank_black_knight.glb', fallbackUrl: './assets/models/Soldier.glb', rigFamily: 'Rig_Large', targetHeight: 1.78, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
      ],
      arcane_ranger: [
        { url: './assets/enemies/b3_ranger_vampire.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.52, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      support_shaman: [
        { url: './assets/enemies/b3_shaman_lorekeeper.glb', fallbackUrl: './assets/models/Xbot.glb', rigFamily: 'Rig_Medium', targetHeight: 1.56, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.50 },
      ],
      boss: [
        { url: './assets/enemies/b3_boss_frost_golem.glb', fallbackUrl: './assets/models/BrainStem.glb', rigFamily: 'Rig_Large', targetHeight: 2.65, facingYawOffset: 0, isQuadruped: false, hitFrameRatio: 0.48 },
        { url: './assets/enemies/b3_boss_apex_trex.glb', fallbackUrl: './assets/models/Fox.glb', rigFamily: 'Self', targetHeight: 2.48, facingYawOffset: 0, isQuadruped: true, hitFrameRatio: 0.46 },
      ],
    },
  };

  function loadGlbTemplateCached(url) {
    if (!gltfLoader || !url) return Promise.resolve(null);
    if (GLB_RESOLVED_CACHE.has(url)) return Promise.resolve(GLB_RESOLVED_CACHE.get(url));
    if (GLB_TEMPLATE_CACHE.has(url)) return GLB_TEMPLATE_CACHE.get(url);

    const p = gltfLoader.loadAsync(url).then((gltf) => {
      const entry = { scene: gltf.scene, animations: gltf.animations || [] };
      GLB_RESOLVED_CACHE.set(url, entry);
      return entry;
    }).catch((err) => {
      GLB_TEMPLATE_CACHE.delete(url);
      console.warn('[WorldRPGDefense] GLB load failed:', url, err);
      return null;
    });
    GLB_TEMPLATE_CACHE.set(url, p);
    return p;
  }

  let preloadedAllOnce = false;
  const preloadedBracketPromises = new Map();

  function getBracketRequiredUrls(bracketIdx) {
    const brIdx = Math.max(0, Math.min(3, parseInt(bracketIdx, 10) || 0));
    const roleMap = ENEMY_BRACKET_ROLE_MODELS[brIdx] || ENEMY_BRACKET_ROLE_MODELS[0];
    const urls = new Set([
      ...Object.values(HERO_WEAPON_GLB_URLS),
      ...Object.values(ENEMY_GEAR_PROP_URLS),
    ]);
    let needMed = false;
    let needLarge = false;
    Object.values(roleMap).forEach((list) => {
      list.forEach((entry) => {
        urls.add(entry.url);
        if (entry.rigFamily === 'Rig_Medium') needMed = true;
        if (entry.rigFamily === 'Rig_Large') needLarge = true;
      });
    });
    if (needMed) {
      urls.add(ENEMY_ANIM_PACK_URLS.rig_medium_move);
      urls.add(ENEMY_ANIM_PACK_URLS.rig_medium_melee);
      urls.add(ENEMY_ANIM_PACK_URLS.rig_medium_ranged);
      urls.add(ENEMY_ANIM_PACK_URLS.rig_medium_general);
    }
    if (needLarge) {
      urls.add(ENEMY_ANIM_PACK_URLS.rig_large_move);
      urls.add(ENEMY_ANIM_PACK_URLS.rig_large_melee);
      urls.add(ENEMY_ANIM_PACK_URLS.rig_large_general);
    }
    return Array.from(urls);
  }

  function preloadBracketEnemyAssets(bracketIdx = 0) {
    if (!gltfLoader) return Promise.resolve();
    const brIdx = Math.max(0, Math.min(3, parseInt(bracketIdx, 10) || 0));
    if (preloadedBracketPromises.has(brIdx)) return preloadedBracketPromises.get(brIdx);
    const p = Promise.all(getBracketRequiredUrls(brIdx).map((u) => loadGlbTemplateCached(u)));
    preloadedBracketPromises.set(brIdx, p);
    return p;
  }

  function preloadAllEnemyGlbAssets() {
    if (preloadedAllOnce || !gltfLoader) return Promise.resolve();
    preloadedAllOnce = true;
    const urls = new Set([
      ...Object.values(HERO_WEAPON_GLB_URLS),
      ...Object.values(ENEMY_ANIM_PACK_URLS),
      ...Object.values(ENEMY_GEAR_PROP_URLS),
      './assets/models/RobotExpressive.glb',
      './assets/models/Fox.glb',
      './assets/models/Soldier.glb',
      './assets/models/Xbot.glb',
      './assets/models/BrainStem.glb',
    ]);
    Object.values(ENEMY_BRACKET_ROLE_MODELS).forEach((roleMap) => {
      Object.values(roleMap).forEach((list) => {
        list.forEach((entry) => urls.add(entry.url));
      });
    });
    return Promise.all(Array.from(urls).map((u) => loadGlbTemplateCached(u)));
  }
  // Lazy-loaded by active bracket on Defense/Skirmish start so Wave 1 meshes load immediately without bandwidth contention!

  function pickEnemyTacticalRole(stageNum, spawnSeq) {
    const roll = ((spawnSeq * 37) % 100) / 100;
    if (stageNum <= 1) return roll < 0.78 ? 'vanguard' : 'shield_tank';
    if (stageNum === 2) {
      if (roll < 0.55) return 'vanguard';
      if (roll < 0.80) return 'shield_tank';
      return 'arcane_ranger';
    }
    if (roll < 0.44) return 'vanguard';
    if (roll < 0.69) return 'shield_tank';
    if (roll < 0.87) return 'arcane_ranger';
    return 'support_shaman';
  }

  function pickEnemyAssetProfile(bracketIdx, roleKey, isBoss, spawnSeq) {
    const br = ENEMY_BRACKET_ROLE_MODELS[bracketIdx] || ENEMY_BRACKET_ROLE_MODELS[0];
    const pool = isBoss ? br.boss : (br[roleKey] || br.vanguard);
    return pool[spawnSeq % pool.length];
  }

  function discoverEnemySkeletonBones(rootObj) {
    const bones = [];
    const skinnedMeshes = [];
    rootObj.traverse((node) => {
      if (node.isSkinnedMesh) {
        node.frustumCulled = false;
        skinnedMeshes.push(node);
      }
      if (node.isBone || node.type === 'Bone') {
        bones.push(node);
      }
    });
    if (skinnedMeshes.length > 0 && skinnedMeshes[0].skeleton) {
      for (const sb of skinnedMeshes[0].skeleton.bones) {
        if (!bones.includes(sb)) bones.push(sb);
      }
    }

    const pick = (rx, exclude = null) => {
      for (let i = 0; i < bones.length; i++) {
        const b = bones[i];
        if (exclude && exclude.test(b.name)) continue;
        if (rx.test(b.name)) return b;
      }
      let hit = null;
      rootObj.traverse((n) => {
        if (hit || !n.name || n.isMesh || n.isSkinnedMesh) return;
        if (exclude && exclude.test(n.name)) return;
        if (rx.test(n.name)) hit = n;
      });
      return hit;
    };

    const rigBones = {
      hips: pick(/^(hips|pelvis|b_hip|torso_joint_1|mixamorighips|b_hip_\d+)$/i, /end/i) || pick(/hips|pelvis|b_hip|^root$/i, /end/i) || bones[0] || null,
      spine: pick(/^(spine|spine01|spine1|abdomen|torso|mixamorigspine|b_spine01_\d+)$/i, /end/i) || pick(/spine|abdomen|torso/i, /end/i),
      chest: pick(/^(chest|spine02|spine2|torso2|shoulders|mixamorigspine2|b_spine02_\d+)$/i, /end/i) || pick(/chest|spine0?2|torso2|shoulders/i, /end/i),
      neck: pick(/^(neck|neck1|mixamorigneck|b_neck_\d+)$/i, /end/i) || pick(/neck/i, /end/i),
      head: pick(/^(head|mixamorighead|b_head_\d+)$/i, /end|top|eye/i) || pick(/head/i, /end|top|eye/i),
      leftArm: pick(/^(upperarm\.?l|leftarm|leftupperarm|mixamorigleftarm|b_leftupperarm(_\d+)?|frontupperleg\.?l|frontleg\.?l)$/i) || pick(/(^|_|mixamorig|b_)left.*(upperarm|arm)|upperarm\.?l/i, /fore|lower|hand|shoulder|thumb|index|end/i),
      rightArm: pick(/^(upperarm\.?r|rightarm|rightupperarm|mixamorigrightarm|b_rightupperarm(_\d+)?|frontupperleg\.?r|frontleg\.?r)$/i) || pick(/(^|_|mixamorig|b_)right.*(upperarm|arm)|upperarm\.?r/i, /fore|lower|hand|shoulder|thumb|index|end/i),
      leftForeArm: pick(/^(lowerarm\.?l|leftforearm|mixamorigleftforearm|b_leftforearm(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)left.*(forearm|lowerarm)|lowerarm\.?l/i, /hand|end/i),
      rightForeArm: pick(/^(lowerarm\.?r|rightforearm|mixamorigrightforearm|b_rightforearm(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)right.*(forearm|lowerarm)|lowerarm\.?r/i, /hand|end/i),
      leftHand: pick(/^(hand\.?l|lefthand|mixamoriglefthand|b_lefthand(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)left.*hand|hand\.?l$/i, /slot|thumb|index|middle|ring|pinky|end/i),
      rightHand: pick(/^(hand\.?r|righthand|mixamorigrighthand|b_righthand(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)right.*hand|hand\.?r$/i, /slot|thumb|index|middle|ring|pinky|end/i),
      handSlotL: pick(/^(handslot\.?l|lefthand|mixamoriglefthand)$/i) || pick(/handslot\.?l/i) || null,
      handSlotR: pick(/^(handslot\.?r|righthand|mixamorigrighthand)$/i) || pick(/handslot\.?r/i) || null,
      leftUpLeg: pick(/^(upperleg\.?l|leftupleg|mixamorigleftupleg|backupperleg\.?l|backupleg\.?l|b_leftleg01(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)left.*(upleg|thigh|upperleg|leg01)|upperleg\.?l/i, /end/i),
      rightUpLeg: pick(/^(upperleg\.?r|rightupleg|mixamorigrightupleg|backupperleg\.?r|backupleg\.?r|b_rightleg01(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)right.*(upleg|thigh|upperleg|leg01)|upperleg\.?r/i, /end/i),
      leftLeg: pick(/^(lowerleg\.?l|leftleg|mixamorigleftleg|backlowerleg\.?l|backlowleg\.?l|b_leftleg02(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)left.*(lowerleg|leg$|calf|shin|leg02)|lowerleg\.?l/i, /up|foot|end/i),
      rightLeg: pick(/^(lowerleg\.?r|rightleg|mixamorigrightleg|backlowerleg\.?r|backlowleg\.?r|b_rightleg02(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)right.*(lowerleg|leg$|calf|shin|leg02)|lowerleg\.?r/i, /up|foot|end/i),
      leftFoot: pick(/^(foot\.?l|leftfoot|mixamorigleftfoot|frontfoot\.?l|backfoot\.?l|b_leftfoot01(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)left.*foot|foot\.?l$/i, /toe|end/i),
      rightFoot: pick(/^(foot\.?r|rightfoot|mixamorigrightfoot|frontfoot\.?r|backfoot\.?r|b_rightfoot01(_\d+)?)$/i) || pick(/(^|_|mixamorig|b_)right.*foot|foot\.?r$/i, /toe|end/i),
      tailBase: pick(/tail/i, /end/i),
    };
    if (!rigBones.chest && rigBones.spine) rigBones.chest = rigBones.spine;
    if (!rigBones.handSlotL) rigBones.handSlotL = rigBones.leftHand;
    if (!rigBones.handSlotR) rigBones.handSlotR = rigBones.rightHand;

    for (let i = 0; i < bones.length; i++) {
      const b = bones[i];
      b.userData.restPos = b.position.clone();
      b.userData.restQuat = b.quaternion.clone();
      b.userData.restScale = b.scale.clone();
      b.userData.postMixerPos = b.position.clone();
      b.userData.postMixerQuat = b.quaternion.clone();
      b.userData.postMixerScale = b.scale.clone();
      b.userData.hasPostMixerSnap = false;
    }

    return { rigBones, allBones: bones, skinnedMeshes };
  }

  function normalizeClonedGlbScene(clonedRoot, targetHeight = 1.55, facingYawOffset = 0) {
    clonedRoot.position.set(0, 0, 0);
    clonedRoot.rotation.set(0, facingYawOffset, 0);
    clonedRoot.scale.setScalar(1.0);
    clonedRoot.traverse((node) => {
      if (node.isLight || node.isCamera) {
        node.visible = false;
        if (typeof node.intensity === 'number') node.intensity = 0;
      }
      if (node.isMesh || node.isSkinnedMesh) {
        node.frustumCulled = false;
        node.castShadow = false;
        node.receiveShadow = false;
        node.userData.sharedGeo = true;
      }
    });
    clonedRoot.updateMatrixWorld(true);

    const box = new THREE.Box3();
    clonedRoot.traverse((node) => {
      if ((node.isMesh || node.isSkinnedMesh) && node.geometry) {
        if (!node.geometry.boundingBox) node.geometry.computeBoundingBox();
        const mBox = node.geometry.boundingBox.clone();
        mBox.applyMatrix4(node.matrixWorld);
        box.union(mBox);
      }
    });

    const normWrap = new THREE.Group();
    if (box.isEmpty()) {
      normWrap.add(clonedRoot);
      return { normWrap, actualHeight: targetHeight, normScale: 1.0 };
    }

    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);

    const rawH = Math.max(0.001, size.y);
    const normScale = targetHeight / rawH;
    clonedRoot.scale.setScalar(normScale);
    clonedRoot.position.set(
      -center.x * normScale,
      -box.min.y * normScale,
      -center.z * normScale
    );
    normWrap.add(clonedRoot);
    return { normWrap, actualHeight: targetHeight, normScale };
  }

  function upgradeGlbMaterialsForDefense(clonedRoot, spec, roleKey, isBoss) {
    const instanceMats = [];
    const roleColorHex = isBoss
      ? 0xf43f5e
      : ((typeof TACTICAL_ROLE_SPECS !== 'undefined' && TACTICAL_ROLE_SPECS[roleKey]?.hpBarColor) || spec.rimHex);
    const rimCol = new THREE.Color(spec.rimHex).lerp(new THREE.Color(roleColorHex), isBoss ? 0.72 : 0.38);
    const sssCol = new THREE.Color(spec.sssHex);
    const tintCol = new THREE.Color(spec.bodyHex);
    const rimStrength = isBoss ? 0.48 : 0.28;

    clonedRoot.traverse((node) => {
      if (!node.isMesh && !node.isSkinnedMesh) return;
      const srcList = Array.isArray(node.material) ? node.material : [node.material];
      const outList = srcList.map((origMat) => {
        if (!origMat) return makeSoftVinylMat({ color: spec.bodyHex });
        let mat;
        if (origMat.isMeshBasicMaterial) {
          mat = new THREE.MeshStandardMaterial({
            color: origMat.color ? origMat.color.clone() : new THREE.Color(0xffffff),
            map: origMat.map || null,
            vertexColors: Boolean(origMat.vertexColors),
            roughness: 0.48,
            metalness: 0.10,
          });
        } else {
          mat = origMat.clone();
          const curMetal = typeof mat.metalness === 'number' ? mat.metalness : 0.12;
          mat.metalness = Math.min(0.72, Math.max(0.04, curMetal));
          const isMetallic = mat.metalness >= 0.38;
          if (typeof mat.roughness === 'number') {
            mat.roughness = Math.min(0.72, Math.max(isMetallic ? 0.30 : 0.42, mat.roughness));
          } else {
            mat.roughness = isMetallic ? 0.36 : 0.50;
          }
          if (typeof mat.envMapIntensity === 'number') {
            mat.envMapIntensity = isMetallic ? 0.58 : 0.28;
          }
        }

        if (mat.color) {
          mat.color.offsetHSL(0, 0.12, -0.03);
          mat.color.lerp(tintCol, mat.map ? 0.08 : 0.22);
        }
        mat.emissive = new THREE.Color(isBoss ? 0xf43f5e : spec.rimHex);
        mat.emissiveIntensity = isBoss ? 0.10 : 0.0;
        const cacheFlags = `${Boolean(mat.map)}_${Boolean(mat.vertexColors)}`;
        mat.customProgramCacheKey = () => `def_enemy_vinyl_v2_${cacheFlags}`;

        mat.onBeforeCompile = (shader) => {
          shader.uniforms.uSssColor = { value: sssCol };
          shader.uniforms.uSssStrength = { value: 0.22 };
          shader.uniforms.uRimColor = { value: rimCol };
          shader.uniforms.uRimStrength = { value: rimStrength };

          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <common>',
            `#include <common>
             uniform vec3 uSssColor;
             uniform float uSssStrength;
             uniform vec3 uRimColor;
             uniform float uRimStrength;`
          );
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <tonemapping_fragment>',
            `
            vec3 viewDirNorm = normalize(vViewPosition);
            vec3 keyDirView = normalize(vec3(0.42, 0.68, 0.60));
            float ndl = dot(normal, keyDirView);
            float sssBand = smoothstep(-0.65, 0.35, ndl) * (1.0 - smoothstep(0.05, 0.75, ndl));
            gl_FragColor.rgb += uSssColor * (sssBand * uSssStrength);
            float fresnel = pow(1.0 - clamp(dot(normal, viewDirNorm), 0.0, 1.0), 2.8);
            gl_FragColor.rgb += uRimColor * (fresnel * uRimStrength);
            #include <tonemapping_fragment>
            `
          );
        };
        mat.needsUpdate = true;
        instanceMats.push(mat);
        return mat;
      });
      node.material = Array.isArray(node.material) ? outList : outList[0];
    });

    return instanceMats;
  }

  function normalizePropGlb(templateScene, targetSize = 0.85, localEulerRot = [Math.PI * 0.48, 0, 0]) {
    const clone = templateScene.clone(true);
    clone.traverse((n) => {
      if (n.isMesh) n.userData.sharedGeo = true;
    });
    clone.position.set(0, 0, 0);
    clone.rotation.set(0, 0, 0);
    clone.scale.setScalar(1.0);
    clone.updateMatrixWorld(true);

    const box = new THREE.Box3().setFromObject(clone);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);

    const maxDim = Math.max(0.001, size.x, size.y, size.z);
    const s = targetSize / maxDim;
    clone.scale.setScalar(s);
    clone.position.set(-center.x * s, -box.min.y * s - size.y * s * 0.18, -center.z * s);

    const propWrap = new THREE.Group();
    const rotInner = new THREE.Group();
    rotInner.rotation.set(localEulerRot[0], localEulerRot[1], localEulerRot[2]);
    rotInner.add(clone);
    propWrap.add(rotInner);
    return propWrap;
  }

  function attachRoleGearPropsToEnemy(e, profile, spec, roleKey, isBoss) {
    if (!e || !e.actionWrap) return;
    const propsWrap = e.propsWrap || new THREE.Group();
    if (!e.propsWrap) {
      e.propsWrap = propsWrap;
      e.actionWrap.add(propsWrap);
    }
    while (propsWrap.children.length > 0) propsWrap.remove(propsWrap.children[0]);
    e.propBindings = [];
    e.shieldMesh = null;

    const rigB = e.rigBones || {};
    const bindPropToBone = (propObj, bone) => {
      if (!propObj || !bone) return null;
      harmonizePropGlbMaterials(propObj, 'enemy_gear');
      propObj.traverse((node) => {
        if (node.material) {
          const ms = Array.isArray(node.material) ? node.material : [node.material];
          ms.forEach((m) => { if (m) e.ownedPropMats.push(m); });
        }
      });
      propsWrap.add(propObj);
      e.propBindings.push({ propMesh: propObj, bone });
      return propObj;
    };

    const handR = rigB.handSlotR || rigB.rightHand;
    const handL = rigB.handSlotL || rigB.leftHand;

    if (!profile.isQuadruped) {
      if (isBoss) {
        const swordTpl = GLB_RESOLVED_CACHE.get(ENEMY_GEAR_PROP_URLS.sword);
        if (swordTpl && handR) {
          bindPropToBone(normalizePropGlb(swordTpl.scene, 1.38, [Math.PI * 0.45, 0, 0]), handR);
        }
        const shTpl = GLB_RESOLVED_CACHE.get(ENEMY_GEAR_PROP_URLS.shield_celtic);
        if (shTpl && handL) {
          e.shieldMesh = bindPropToBone(normalizePropGlb(shTpl.scene, 1.05, [0, -Math.PI * 0.45, 0]), handL);
        }
      } else if (roleKey === 'shield_tank') {
        const hamTpl = GLB_RESOLVED_CACHE.get(ENEMY_GEAR_PROP_URLS.hammer);
        if (hamTpl && handR) {
          bindPropToBone(normalizePropGlb(hamTpl.scene, 0.96, [Math.PI * 0.45, 0, 0]), handR);
        }
        const shTpl = GLB_RESOLVED_CACHE.get(ENEMY_GEAR_PROP_URLS.shield_heater);
        if (shTpl && handL) {
          e.shieldMesh = bindPropToBone(normalizePropGlb(shTpl.scene, 0.86, [0, -Math.PI * 0.45, 0]), handL);
        }
      } else if (roleKey === 'vanguard') {
        const brk = spec && typeof spec.bracket === 'number' ? spec.bracket : e.bracketIdx;
        const spearUrl = brk === 0 || brk === 3 ? ENEMY_GEAR_PROP_URLS.spear : ENEMY_GEAR_PROP_URLS.sword;
        const wepTpl = GLB_RESOLVED_CACHE.get(spearUrl);
        if (wepTpl && handR) {
          bindPropToBone(normalizePropGlb(wepTpl.scene, spearUrl === ENEMY_GEAR_PROP_URLS.spear ? 1.18 : 0.88, [Math.PI * 0.48, 0, 0]), handR);
        }
      } else if (roleKey === 'arcane_ranger') {
        const bowTpl = GLB_RESOLVED_CACHE.get(ENEMY_GEAR_PROP_URLS.bow);
        if (bowTpl && handR) {
          bindPropToBone(normalizePropGlb(bowTpl.scene, 0.92, [0, Math.PI * 0.5, Math.PI * 0.15]), handR);
        }
      } else if (roleKey === 'support_shaman') {
        const scTpl = GLB_RESOLVED_CACHE.get(ENEMY_GEAR_PROP_URLS.scythe);
        if (scTpl && handR) {
          bindPropToBone(normalizePropGlb(scTpl.scene, 1.08, [Math.PI * 0.45, 0, 0]), handR);
        }
      }
    }

    if ((roleKey === 'shield_tank' || isBoss) && !e.shieldMesh) {
      const aegisMat = makeDefenseCrystalMat({ color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.45, opacity: 0.46 });
      aegisMat.depthWrite = false;
      const aegis = new THREE.Mesh(SHARED_GEO.orb, aegisMat);
      aegis.scale.set(2.2, 2.5, 2.2);
      aegis.position.set(0, (e.height || 1.4) * 0.48, 0.42);
      aegis.userData.sharedGeo = true;
      propsWrap.add(aegis);
      e.shieldMesh = aegis;
      e.ownedPropMats.push(aegisMat);
    }
    if (e.shieldMesh && typeof e.shieldHp === 'number' && e.shieldHp <= 0) {
      e.shieldMesh.visible = false;
    }

    if (roleKey === 'arcane_ranger') {
      const orbMat = makeDefenseCrystalMat({ color: 0xe879f9, emissive: 0xa855f7, emissiveIntensity: 0.72, opacity: 0.92 });
      const orbHaloMat = makeAdditiveHaloMat(0xc084fc, 0.52, 2.0);
      const orb = new THREE.Mesh(SHARED_GEO.orb, orbMat);
      orb.scale.setScalar(0.96);
      orb.userData.sharedGeo = true;
      const orbHalo = new THREE.Mesh(SHARED_GEO.orb, orbHaloMat);
      orbHalo.scale.setScalar(1.52);
      orbHalo.userData.sharedGeo = true;
      orb.add(orbHalo);
      propsWrap.add(orb);
      e.floatingOrb = orb;
      e.ownedPropMats.push(orbMat, orbHaloMat);
    }

    if (roleKey === 'support_shaman') {
      const totemMat = makeDefenseCrystalMat({ color: 0x4ade80, emissive: 0x16a34a, emissiveIntensity: 0.65, opacity: 0.88 });
      const totem = new THREE.Mesh(SHARED_GEO.orbRing, totemMat);
      totem.rotation.x = Math.PI * 0.36;
      totem.userData.sharedGeo = true;
      propsWrap.add(totem);
      e.shamanTotem = totem;
      e.ownedPropMats.push(totemMat);
    }
  }

  function resolveKayKitClips(rigFamily, roleKey, isBoss) {
    const out = { IDLE: null, WALK: null, RUN: null, ATTACK: null, HIT: null, DEATH: null };
    const findByName = (packUrl, names) => {
      const tpl = GLB_RESOLVED_CACHE.get(packUrl);
      if (!tpl || !tpl.animations) return null;
      for (const nm of names) {
        const hit = tpl.animations.find((c) => c.name === nm || c.name.includes(nm));
        if (hit) return hit;
      }
      return null;
    };

    if (rigFamily === 'Rig_Large') {
      out.IDLE = findByName(ENEMY_ANIM_PACK_URLS.rig_large_general, ['Idle_A', 'Idle_B']);
      out.WALK = findByName(ENEMY_ANIM_PACK_URLS.rig_large_move, ['Walking_A']);
      out.RUN = findByName(ENEMY_ANIM_PACK_URLS.rig_large_move, ['Running_A']) || out.WALK;
      const atkNames = isBoss
        ? ['Melee_2H_Slam', 'Melee_Dualwield_SlashCombo', 'Melee_2H_Attack']
        : (roleKey === 'shield_tank' ? ['Melee_Block_Attack', 'Melee_2H_Attack', 'Melee_1H_Slash'] : ['Melee_1H_Slash', 'Melee_Unarmed_Smash']);
      out.ATTACK = findByName(ENEMY_ANIM_PACK_URLS.rig_large_melee, atkNames);
      out.HIT = findByName(ENEMY_ANIM_PACK_URLS.rig_large_general, ['Hit_A']);
      out.DEATH = findByName(ENEMY_ANIM_PACK_URLS.rig_large_general, ['Death_A']);
    } else {
      out.IDLE = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_general, ['Idle_A', 'Idle_B']);
      out.WALK = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_move, ['Walking_A', 'Walking_B', 'Walking_C']);
      out.RUN = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_move, ['Running_A', 'Running_B']) || out.WALK;
      if (roleKey === 'arcane_ranger') {
        out.ATTACK = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_ranged, ['Ranged_Bow_Release', 'Ranged_Magic_Shoot', 'Ranged_1H_Shoot']);
      } else if (roleKey === 'support_shaman') {
        out.ATTACK = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_ranged, ['Ranged_Magic_Spellcasting', 'Ranged_Magic_Summon', 'Ranged_Magic_Raise']);
      } else if (roleKey === 'shield_tank' || isBoss) {
        out.ATTACK = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_melee, ['Melee_Block_Attack', 'Melee_2H_Attack_Chop', 'Melee_1H_Attack_Chop']);
      } else {
        out.ATTACK = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_melee, ['Melee_1H_Attack_Chop', 'Melee_1H_Attack_Jump_Chop', 'Melee_1H_Attack_Slice_Diagonal']);
      }
      out.HIT = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_general, ['Hit_A', 'Hit_B']);
      out.DEATH = findByName(ENEMY_ANIM_PACK_URLS.rig_medium_general, ['Death_A', 'Death_B']);
    }
    return out;
  }

  function classifyEmbeddedGlbClips(clips = []) {
    const pick = (rxList) => {
      for (const rx of rxList) {
        const hit = clips.find((c) => rx.test(c.name));
        if (hit) return hit;
      }
      return null;
    };
    const walk = pick([/\|walk$/i, /walking/i, /walk/i, /flying/i, /anim_0/i]) || clips[0] || null;
    const run = pick([/\|run$/i, /running/i, /gallop$/i, /gallop/i, /run/i]) || walk;
    const idle = pick([/\|idle$/i, /idle$/i, /survey/i, /standing/i, /idle/i]) || walk;
    const attack = pick([/bite_front/i, /attack/i, /shoot/i, /punch/i, /slash/i, /bite/i, /jump/i]);
    const hit = pick([/hitrecieve/i, /hitreact/i, /no$/i, /headshake/i]);
    const death = pick([/death/i, /dead/i, /die/i]);
    return { IDLE: idle, WALK: walk, RUN: run, ATTACK: attack, HIT: hit, DEATH: death };
  }

  function makeRelativeQuatTrack(bone, times, eulerDeltas) {
    const values = [];
    const restQ = (bone.userData && bone.userData.restQuat) ? bone.userData.restQuat : bone.quaternion.clone();
    const eul = new THREE.Euler();
    const qD = new THREE.Quaternion();
    let prev = null;
    for (let i = 0; i < eulerDeltas.length; i++) {
      const [rx, ry, rz] = eulerDeltas[i];
      eul.set(rx, ry, rz, 'ZYX');
      qD.setFromEuler(eul);
      const q = restQ.clone().multiply(qD);
      if (prev && prev.dot(q) < 0) q.set(-q.x, -q.y, -q.z, -q.w);
      prev = q.clone();
      values.push(q.x, q.y, q.z, q.w);
    }
    return new THREE.QuaternionKeyframeTrack(`${bone.name}.quaternion`, times, values);
  }

  function synthesizeMissingEnemyClip(stateKey, rigBones, isQuadruped) {
    const b = rigBones || {};
    const tracks = [];
    if (stateKey === 'HIT') {
      const times = [0, 0.08, 0.20, 0.36];
      if (b.spine) tracks.push(makeRelativeQuatTrack(b.spine, times, [[0, 0, 0], [-0.36, 0, 0.14], [-0.15, 0, -0.06], [0, 0, 0]]));
      if (b.head) tracks.push(makeRelativeQuatTrack(b.head, times, [[0, 0, 0], [-0.42, 0.18, 0], [-0.14, -0.08, 0], [0, 0, 0]]));
      return new THREE.AnimationClip('Synth_HIT', 0.36, tracks);
    }
    if (stateKey === 'DEATH') {
      const times = [0, 0.18, 0.52, 0.78];
      if (b.hips) tracks.push(makeRelativeQuatTrack(b.hips, times, [[0, 0, 0], [-0.28, 0, 0.16], [-1.25, 0.25, 0.45], [-1.45, 0.25, 0.52]]));
      if (b.spine) tracks.push(makeRelativeQuatTrack(b.spine, times, [[0, 0, 0], [-0.35, 0, 0], [0.22, 0, 0], [0.26, 0, 0]]));
      if (b.head) tracks.push(makeRelativeQuatTrack(b.head, times, [[0, 0, 0], [-0.45, 0, 0], [0.35, 0.2, 0], [0.40, 0.2, 0]]));
      return new THREE.AnimationClip('Synth_DEATH', 0.78, tracks);
    }
    const times = [0, 0.22, 0.44, 0.72];
    if (isQuadruped) {
      if (b.spine) tracks.push(makeRelativeQuatTrack(b.spine, times, [[0, 0, 0], [-0.24, 0, 0], [0.32, 0, 0], [0, 0, 0]]));
      if (b.head) tracks.push(makeRelativeQuatTrack(b.head, times, [[0, 0, 0], [-0.28, 0, 0], [0.46, 0, 0], [0, 0, 0]]));
    } else {
      if (b.spine) tracks.push(makeRelativeQuatTrack(b.spine, times, [[0, 0, 0], [-0.22, -0.45, 0], [0.34, 0.55, 0], [0, 0, 0]]));
      if (b.rightArm) tracks.push(makeRelativeQuatTrack(b.rightArm, times, [[0, 0, 0], [-1.55, 0, -0.35], [0.65, 0, 0.20], [0, 0, 0]]));
    }
    return new THREE.AnimationClip('Synth_ATTACK', 0.72, tracks);
  }

  function setEnemyAnimState(e, nextState, fadeDuration = 0.18) {
    const fsm = e.animFsm;
    if (!fsm || !fsm.mixer) return;
    if (fsm.state === 'DEATH' && nextState !== 'DEATH') return;
    if (fsm.state === nextState && nextState !== 'ATTACK' && nextState !== 'HIT') return;

    const nextAction = fsm.actions[nextState] || fsm.actions.IDLE || fsm.actions.WALK;
    if (!nextAction) return;

    const prevState = fsm.state;
    const prevAction = fsm.currentAction;
    fsm.state = nextState;

    nextAction.enabled = true;
    nextAction.setEffectiveWeight(1.0);
    if (nextState === 'ATTACK' || nextState === 'HIT' || nextState === 'DEATH') {
      nextAction.reset();
      nextAction.setLoop(THREE.LoopOnce, 1);
      nextAction.clampWhenFinished = true;
    } else {
      nextAction.setLoop(THREE.LoopRepeat, Infinity);
      nextAction.clampWhenFinished = false;
      if (prevAction !== nextAction) nextAction.reset();
    }

    nextAction.play();
    if (prevAction && prevAction !== nextAction) {
      const warp = (prevState === 'WALK' && nextState === 'RUN') || (prevState === 'RUN' && nextState === 'WALK');
      prevAction.crossFadeTo(nextAction, fadeDuration, warp);
    }
    fsm.currentAction = nextAction;
  }

  function bindEnemyAnimationFSM(e, clonedRoot, modelClips, profile, roleKey, isBoss) {
    const mixer = new THREE.AnimationMixer(clonedRoot);
    let clipMap;
    if (profile.rigFamily === 'Rig_Medium' || profile.rigFamily === 'Rig_Large') {
      clipMap = resolveKayKitClips(profile.rigFamily, roleKey, isBoss);
      const emb = classifyEmbeddedGlbClips(modelClips);
      for (const st of ['IDLE', 'WALK', 'RUN', 'ATTACK', 'HIT', 'DEATH']) {
        if (!clipMap[st]) clipMap[st] = emb[st];
      }
    } else {
      clipMap = classifyEmbeddedGlbClips(modelClips);
    }

    for (const st of ['ATTACK', 'HIT', 'DEATH']) {
      if (!clipMap[st]) {
        clipMap[st] = synthesizeMissingEnemyClip(st, e.rigBones, profile.isQuadruped);
      }
    }
    if (!clipMap.WALK && clipMap.IDLE) clipMap.WALK = clipMap.IDLE;
    if (!clipMap.RUN && clipMap.WALK) clipMap.RUN = clipMap.WALK;
    if (!clipMap.IDLE && clipMap.WALK) clipMap.IDLE = clipMap.WALK;

    const actions = {};
    Object.entries(clipMap).forEach(([k, clip]) => {
      if (clip) actions[k] = mixer.clipAction(clip);
    });

    const fsm = { mixer, actions, state: 'NONE', currentAction: null };
    mixer.addEventListener('finished', (ev) => {
      if (e.dyingTimer >= 0) return;
      if (ev.action === actions.ATTACK || ev.action === actions.HIT) {
        if (e.pendingAttackHit && ev.action === actions.ATTACK && typeof e.onAttackHitCallback === 'function') {
          e.pendingAttackHit = false;
          e.onAttackHitCallback();
        }
        fsm.state = 'NONE';
        setEnemyAnimState(e, 'IDLE', 0.16);
      }
    });

    e.animFsm = fsm;
    const initState = e.dyingTimer >= 0 ? 'DEATH' : (e.stunTimer > 0 ? 'HIT' : 'WALK');
    setEnemyAnimState(e, initState, 0.05);
  }

  const tmpDeltaEuler = new THREE.Euler();
  const tmpDeltaQuat = new THREE.Quaternion();
  const tmpBonePos = new THREE.Vector3();
  const tmpBoneQuat = new THREE.Quaternion();
  const tmpScaleOne = new THREE.Vector3(1, 1, 1);
  const tmpScaleDummy = new THREE.Vector3(1, 1, 1);
  const tmpInvParentMat = new THREE.Matrix4();
  const tmpWorldMat = new THREE.Matrix4();

  function applyEnemyBoneEulerDelta(bone, rx, ry, rz) {
    if (!bone) return;
    tmpDeltaEuler.set(rx, ry, rz, 'ZYX');
    tmpDeltaQuat.setFromEuler(tmpDeltaEuler);
    bone.quaternion.multiply(tmpDeltaQuat);
  }

  function syncEnemyAttachedProps(e, elapsed) {
    if (!e || !e.actionWrap) return;
    if (e.propBindings && e.propBindings.length > 0) {
      e.actionWrap.updateMatrixWorld(true);
      tmpInvParentMat.copy(e.actionWrap.matrixWorld).invert();
      for (let i = 0; i < e.propBindings.length; i++) {
        const pb = e.propBindings[i];
        if (!pb.bone || !pb.propMesh || !pb.propMesh.visible) continue;
        pb.bone.getWorldPosition(tmpBonePos);
        pb.bone.getWorldQuaternion(tmpBoneQuat);
        tmpWorldMat.compose(tmpBonePos, tmpBoneQuat, tmpScaleOne);
        tmpWorldMat.premultiply(tmpInvParentMat);
        tmpWorldMat.decompose(pb.propMesh.position, pb.propMesh.quaternion, tmpScaleDummy);
      }
    }
    if (e.floatingOrb) {
      const h = e.height || 1.45;
      e.floatingOrb.position.set(0.42, h * 0.65 + Math.sin(elapsed * 5.2 + e.stridePhase) * 0.09, 0.25);
      e.floatingOrb.rotation.y += 0.06;
    }
    if (e.shamanTotem) {
      e.shamanTotem.position.set(0, 0.06, 0);
      e.shamanTotem.rotation.z += 0.04;
      const pulse = 2.8 + Math.sin(elapsed * 4.5 + e.stridePhase) * 0.35;
      e.shamanTotem.scale.setScalar(pulse);
    }
  }

  function updateEnemyAnimationSystem(e, dt, elapsed, isMoving, spdMult, lookDx, lookDy, lookDist) {
    const fsm = e.animFsm;
    if (!fsm || !fsm.mixer) {
      if (e.portalPlaceholder) {
        e.portalPlaceholder.rotation.z += dt * 4.5;
        e.portalPlaceholder.scale.setScalar(0.95 + Math.sin(elapsed * 8.0) * 0.14);
      }
      if (e.pendingAttackHit) {
        e.attackFallbackTimer -= dt;
        if (e.attackFallbackTimer <= 0 && typeof e.onAttackHitCallback === 'function') {
          e.pendingAttackHit = false;
          e.onAttackHitCallback();
        }
      }
      return;
    }

    const b = e.rigBones || {};
    const allBones = e.allBones || [];

    for (let i = 0; i < allBones.length; i++) {
      const bone = allBones[i];
      if (bone.userData && bone.userData.hasPostMixerSnap) {
        bone.position.copy(bone.userData.postMixerPos);
        bone.quaternion.copy(bone.userData.postMixerQuat);
        bone.scale.copy(bone.userData.postMixerScale);
      }
    }

    if (e.dyingTimer >= 0) {
      if (fsm.state !== 'DEATH') setEnemyAnimState(e, 'DEATH', 0.08);
      if (fsm.currentAction) fsm.currentAction.setEffectiveTimeScale(1.0);
    } else if (e.stunTimer > 0) {
      if (fsm.state !== 'HIT') setEnemyAnimState(e, 'HIT', 0.06);
      if (fsm.currentAction) fsm.currentAction.setEffectiveTimeScale(0.35);
    } else if (fsm.state !== 'ATTACK' && fsm.state !== 'HIT') {
      if (isMoving) {
        const useRun = (e.roleKey === 'vanguard' || e.phase2Triggered) && e.slowTimer <= 0;
        const targetLoco = useRun && fsm.actions.RUN ? 'RUN' : 'WALK';
        setEnemyAnimState(e, targetLoco, 0.20);
        const refSpeed = targetLoco === 'RUN' ? 2.05 : 1.15;
        const worldSpd = (e.speed || 1.2) * spdMult;
        const locoScale = THREE.MathUtils.clamp(worldSpd / (refSpeed * Math.max(0.75, (e.height || 1.5) / 1.5)), 0.45, 2.35);
        if (fsm.currentAction) fsm.currentAction.setEffectiveTimeScale(locoScale);
      } else {
        setEnemyAnimState(e, 'IDLE', 0.20);
        if (fsm.currentAction) fsm.currentAction.setEffectiveTimeScale(1.0);
      }
    }

    fsm.mixer.update(dt);

    if (e.pendingAttackHit) {
      if (fsm.state === 'ATTACK' && fsm.currentAction) {
        const clipDur = Math.max(0.05, fsm.currentAction.getClip().duration);
        const u = fsm.currentAction.time / clipDur;
        if (u >= (e.hitFrameRatio || 0.45)) {
          e.pendingAttackHit = false;
          if (typeof e.onAttackHitCallback === 'function') e.onAttackHitCallback();
        }
      } else {
        e.attackFallbackTimer -= dt;
        if (e.attackFallbackTimer <= 0 && typeof e.onAttackHitCallback === 'function') {
          e.pendingAttackHit = false;
          e.onAttackHitCallback();
        }
      }
    }

    for (let i = 0; i < allBones.length; i++) {
      const bone = allBones[i];
      bone.userData.postMixerPos.copy(bone.position);
      bone.userData.postMixerQuat.copy(bone.quaternion);
      bone.userData.postMixerScale.copy(bone.scale);
      bone.userData.hasPostMixerSnap = true;
    }

    if (e.dyingTimer >= 0) {
      syncEnemyAttachedProps(e, elapsed);
      return;
    }

    const desiredYaw = THREE.MathUtils.clamp(Math.atan2(lookDx, 0.85) - e.modelHolder.rotation.y, -0.62, 0.62);
    const desiredPitch = THREE.MathUtils.clamp((lookDy / Math.max(0.8, lookDist)) * 0.28, -0.28, 0.28);
    const lookAlpha = 1.0 - Math.exp(-9.0 * dt);
    e.lookYawSmoothed = (e.lookYawSmoothed || 0) + (desiredYaw - (e.lookYawSmoothed || 0)) * lookAlpha;
    e.lookPitchSmoothed = (e.lookPitchSmoothed || 0) + (desiredPitch - (e.lookPitchSmoothed || 0)) * lookAlpha;

    if (b.spine) applyEnemyBoneEulerDelta(b.spine, e.lookPitchSmoothed * 0.15, e.lookYawSmoothed * 0.15, 0);
    if (b.chest && b.chest !== b.spine) applyEnemyBoneEulerDelta(b.chest, e.lookPitchSmoothed * 0.25, e.lookYawSmoothed * 0.25, 0);
    if (b.neck) applyEnemyBoneEulerDelta(b.neck, e.lookPitchSmoothed * 0.25, e.lookYawSmoothed * 0.25, 0);
    if (b.head) applyEnemyBoneEulerDelta(b.head, e.lookPitchSmoothed * 0.35, e.lookYawSmoothed * 0.35, -e.lookYawSmoothed * 0.08);

    if (e.hitFlashTimer > 0) {
      const uHit = e.hitFlashTimer / 0.16;
      const imp = Math.sin(uHit * Math.PI) * Math.exp(-3.5 * (1.0 - uHit));
      if (b.spine) applyEnemyBoneEulerDelta(b.spine, -0.34 * imp, 0, 0.16 * imp);
      if (b.head) applyEnemyBoneEulerDelta(b.head, -0.38 * imp, 0, 0.20 * imp);
      if (b.leftArm) applyEnemyBoneEulerDelta(b.leftArm, 0, 0, 0.28 * imp);
      if (b.rightArm) applyEnemyBoneEulerDelta(b.rightArm, 0, 0, -0.28 * imp);
    }

    if (e.stunTimer > 0) {
      const wobX = 0.18 + Math.sin(elapsed * 11.5) * 0.13;
      const wobZ = Math.cos(elapsed * 11.5) * 0.16;
      if (b.chest) applyEnemyBoneEulerDelta(b.chest, wobX * 0.45, 0, wobZ * 0.45);
      if (b.head) applyEnemyBoneEulerDelta(b.head, wobX, Math.sin(elapsed * 7.0) * 0.22, wobZ);
    }

    if (e.isBoss) {
      if (e.phase2Triggered && b.chest) {
        const pulse = 1.0 + 0.09 * Math.sin(elapsed * 7.5);
        b.chest.scale.set(b.chest.scale.x * pulse, b.chest.scale.y * (1.0 + 0.045 * Math.sin(elapsed * 7.5)), b.chest.scale.z * pulse);
      }
      if (e.enrageRoarTimer > 0) {
        e.enrageRoarTimer = Math.max(0, e.enrageRoarTimer - dt);
        const rEnv = Math.sin((e.enrageRoarTimer / 1.1) * Math.PI);
        if (b.chest) applyEnemyBoneEulerDelta(b.chest, -0.32 * rEnv, 0, 0);
        if (b.head) applyEnemyBoneEulerDelta(b.head, -0.44 * rEnv, Math.sin(elapsed * 18.0) * 0.12 * rEnv, 0);
      }
      if (e.telegraphCastTimer > 0) {
        e.telegraphCastTimer = Math.max(0, e.telegraphCastTimer - dt);
        const cEnv = Math.sin(Math.min(1.0, e.telegraphCastTimer / 1.4) * Math.PI);
        if (b.leftArm) applyEnemyBoneEulerDelta(b.leftArm, -1.25 * cEnv, 0, 0.30 * cEnv);
        if (b.rightArm) applyEnemyBoneEulerDelta(b.rightArm, -1.25 * cEnv, 0, -0.30 * cEnv);
      }
    }

    syncEnemyAttachedProps(e, elapsed);
  }

  function mountGlbRigIntoEnemy(e, tpl, profile, spec, roleKey, isBoss) {
    if (!e || e.disposed || !tpl || !tpl.scene) return;
    if (e.portalPlaceholder) {
      e.actionWrap.remove(e.portalPlaceholder);
      if (e.portalPlaceholder.material) e.portalPlaceholder.material.dispose();
      e.portalPlaceholder = null;
    }

    const clonedRoot = SkeletonUtils && typeof SkeletonUtils.clone === 'function'
      ? SkeletonUtils.clone(tpl.scene)
      : tpl.scene.clone(true);

    const targetH = isBoss ? Math.max(2.35, profile.targetHeight || 2.55) : (profile.targetHeight || 1.50);
    const { normWrap, actualHeight } = normalizeClonedGlbScene(clonedRoot, targetH, profile.facingYawOffset || 0);
    e.bodyMats = upgradeGlbMaterialsForDefense(clonedRoot, spec, roleKey, isBoss);
    const { rigBones, allBones } = discoverEnemySkeletonBones(clonedRoot);

    e.clonedRoot = clonedRoot;
    e.normWrap = normWrap;
    e.rigBones = rigBones;
    e.allBones = allBones;
    e.height = actualHeight;
    e.actionWrap.add(normWrap);

    if (e.hpBarMesh) {
      e.hpBarMesh.position.y = Math.max(1.85, actualHeight + 0.36);
    }

    bindEnemyAnimationFSM(e, clonedRoot, tpl.animations || [], profile, roleKey, isBoss);
    attachRoleGearPropsToEnemy(e, profile, spec, roleKey, isBoss);
    const isActiveMove = (typeof e.dyingTimer !== 'number' || e.dyingTimer < 0) && (!e.stunTimer || e.stunTimer <= 0);
    updateEnemyAnimationSystem(e, 0.016, 0, isActiveMove, 1.0, 0, 0, 1.0);
  }

  let monsterSpawnCounter = 0;

  function createEnemyGlbHolder(spec, isBoss = false, forcedRoleKey = null) {
    const seq = monsterSpawnCounter++;
    const roleKey = isBoss ? 'boss' : (forcedRoleKey || pickEnemyTacticalRole(combatState.wave || 1, seq));
    const roleSpec = TACTICAL_ROLE_SPECS[roleKey] || TACTICAL_ROLE_SPECS.vanguard;
    const profile = pickEnemyAssetProfile(spec.bracket || 0, roleKey, isBoss, seq);

    const modelHolder = new THREE.Group();
    const actionWrap = new THREE.Group();
    modelHolder.add(actionWrap);

    const riftMat = new THREE.MeshBasicMaterial({ color: isBoss ? 0xf43f5e : spec.rimHex, transparent: true, opacity: 0.78, side: THREE.DoubleSide, depthWrite: false, toneMapped: false });
    const riftMesh = new THREE.Mesh(SHARED_GEO.orbRing, riftMat);
    riftMesh.position.y = 0.55;
    actionWrap.add(riftMesh);

    const enemyObj = {
      modelHolder,
      actionWrap,
      portalPlaceholder: riftMesh,
      profile,
      roleKey,
      roleSpec,
      clonedRoot: null,
      normWrap: null,
      rigBones: {},
      allBones: [],
      animFsm: null,
      propsWrap: null,
      propBindings: [],
      shieldMesh: null,
      floatingOrb: null,
      shamanTotem: null,
      bodyMats: [],
      ownedPropMats: [riftMat],
      hitFrameRatio: profile.hitFrameRatio || 0.45,
      pendingAttackHit: false,
      attackFallbackTimer: 0,
      onAttackHitCallback: null,
      stridePhase: Math.random() * Math.PI * 2,
      lookYawSmoothed: 0,
      lookPitchSmoothed: 0,
      enrageRoarTimer: 0,
      telegraphCastTimer: 0,
      disposed: false,
      height: profile.targetHeight || 1.55,
    };

    const rolePropUrls = roleKey === 'vanguard'
      ? [ENEMY_GEAR_PROP_URLS.sword, ENEMY_GEAR_PROP_URLS.shield_celtic]
      : roleKey === 'shield_tank'
        ? [ENEMY_GEAR_PROP_URLS.hammer, ENEMY_GEAR_PROP_URLS.shield_heater]
        : roleKey === 'arcane_ranger'
          ? [ENEMY_GEAR_PROP_URLS.spear, ENEMY_GEAR_PROP_URLS.sword, ENEMY_GEAR_PROP_URLS.bow]
          : roleKey === 'support_shaman'
            ? [ENEMY_GEAR_PROP_URLS.scythe, ENEMY_GEAR_PROP_URLS.bow]
            : Object.values(ENEMY_GEAR_PROP_URLS);
    const reqUrls = [profile.url, ...rolePropUrls];
    if (profile.rigFamily === 'Rig_Medium') {
      reqUrls.push(ENEMY_ANIM_PACK_URLS.rig_medium_move, ENEMY_ANIM_PACK_URLS.rig_medium_melee, ENEMY_ANIM_PACK_URLS.rig_medium_ranged, ENEMY_ANIM_PACK_URLS.rig_medium_general);
    } else if (profile.rigFamily === 'Rig_Large') {
      reqUrls.push(ENEMY_ANIM_PACK_URLS.rig_large_move, ENEMY_ANIM_PACK_URLS.rig_large_melee, ENEMY_ANIM_PACK_URLS.rig_large_general);
    }

    const allCached = GLB_RESOLVED_CACHE.has(profile.url) && reqUrls.every((u) => GLB_RESOLVED_CACHE.has(u));
    if (allCached) {
      mountGlbRigIntoEnemy(enemyObj, GLB_RESOLVED_CACHE.get(profile.url), profile, spec, roleKey, isBoss);
    } else {
      Promise.all(reqUrls.map((u) => loadGlbTemplateCached(u))).then((res) => {
        if (enemyObj.disposed) return;
        const primaryTpl = res[0];
        if (primaryTpl) {
          mountGlbRigIntoEnemy(enemyObj, primaryTpl, profile, spec, roleKey, isBoss);
        } else if (profile.fallbackUrl) {
          loadGlbTemplateCached(profile.fallbackUrl).then((fbTpl) => {
            if (!enemyObj.disposed && fbTpl) {
              const fbProfile = { ...profile, rigFamily: 'Self', isQuadruped: profile.fallbackUrl.includes('Fox') };
              mountGlbRigIntoEnemy(enemyObj, fbTpl, fbProfile, spec, roleKey, isBoss);
            }
          });
        }
      });
    }

    return enemyObj;
  }

  // ===========================================================================
  // 5. Sculpted 3D Hero Weapons ('fist', 'sword', 'bow', 'gun')
  // ===========================================================================
  const heroRightHandGroup = new THREE.Group();
  heroRightHandGroup.name = 'HeroRightHandWeapon';
  heroRightHandGroup.visible = false;
  worldRoot.add(heroRightHandGroup);

  const heroLeftHandGroup = new THREE.Group();
  heroLeftHandGroup.name = 'HeroLeftHandWeapon';
  heroLeftHandGroup.visible = false;
  worldRoot.add(heroLeftHandGroup);

  const heroBackQuiverGroup = new THREE.Group();
  heroBackQuiverGroup.name = 'HeroBackQuiver';
  heroBackQuiverGroup.visible = false;
  worldRoot.add(heroBackQuiverGroup);

  let gunMuzzleFlashMesh = null;

  const slashArcMat = new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(0x38bdf8) },
      uOpacity: { value: 0.0 },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        vec2 p = vUv * 2.0 - 1.0;
        float r = length(p);
        float ang = atan(p.y, p.x);
        float angMask = smoothstep(-1.45, -0.15, ang) * (1.0 - smoothstep(0.15, 1.45, ang));
        float thick = mix(0.05, 0.24, pow(max(0.0, cos(ang * 0.9)), 1.3));
        float rMid = 0.64;
        float d = abs(r - rMid) / max(0.02, thick);
        float body = exp(-d * d * 2.4) * smoothstep(1.0, 0.72, d);
        float core = exp(-d * d * 9.0) * 0.75;
        float alpha = (body + core) * angMask * uOpacity;
        if (alpha < 0.01) discard;
        vec3 col = mix(uColor, vec3(1.0), core * 0.72);
        gl_FragColor = vec4(col, alpha);
      }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
    side: THREE.DoubleSide,
  });
  slashArcMat.customProgramCacheKey = () => 'def_sdf_slash_v1';
  const slashArcMesh = new THREE.Mesh(SHARED_GEO.shockwaveQuad, slashArcMat);
  slashArcMesh.visible = false;
  slashArcMesh.userData.sharedGeo = true;
  worldRoot.add(slashArcMesh);

  const whirlwindMat = new THREE.ShaderMaterial({
    uniforms: {
      uColor: { value: new THREE.Color(0xfacc15) },
      uOpacity: { value: 0.0 },
    },
    vertexShader: `
      varying vec2 vUv;
      void main() {
        vUv = uv;
        gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
      }
    `,
    fragmentShader: `
      uniform vec3 uColor;
      uniform float uOpacity;
      varying vec2 vUv;
      void main() {
        vec2 p = vUv * 2.0 - 1.0;
        float r = length(p);
        if (r > 1.0 || r < 0.26) discard;
        float ang = atan(p.y, p.x);
        float vane = pow(0.5 + 0.5 * cos(ang * 3.0 + r * 5.0), 1.4);
        float radial = smoothstep(0.28, 0.48, r) * (1.0 - smoothstep(0.76, 0.98, r));
        float rim = exp(-pow((r - 0.76) * 9.5, 2.0)) * 0.85;
        float alpha = (radial * (0.40 + 0.60 * vane) + rim * vane) * uOpacity;
        vec3 col = mix(uColor, vec3(1.0, 0.98, 0.85), rim * 0.65);
        gl_FragColor = vec4(col, alpha);
      }
    `,
    transparent: true,
    blending: THREE.AdditiveBlending,
    depthWrite: false,
    toneMapped: false,
    side: THREE.DoubleSide,
  });
  whirlwindMat.customProgramCacheKey = () => 'def_sdf_whirlwind_v1';
  const whirlwindMesh = new THREE.Mesh(SHARED_GEO.shockwaveQuad, whirlwindMat);
  whirlwindMesh.visible = false;
  whirlwindMesh.userData.sharedGeo = true;
  worldRoot.add(whirlwindMesh);

  function clearGroupChildren(grp) {
    while (grp.children.length > 0) {
      const ch = grp.children[0];
      grp.remove(ch);
      ch.traverse((node) => {
        if (node.geometry && !node.userData?.sharedGeo && typeof node.geometry.dispose === 'function') {
          node.geometry.dispose();
        }
        if (!node.material) return;
        const mats = Array.isArray(node.material) ? node.material : [node.material];
        for (let i = 0; i < mats.length; i++) {
          if (mats[i] && !node.userData?.sharedMat && typeof mats[i].dispose === 'function') mats[i].dispose();
        }
      });
    }
  }

  let heroWeaponBuildSeq = 0;
  let lastBuiltWeaponSig = '';

  function normalizeHeroWeaponGlb(templateScene, targetSize, opts = {}) {
    const clone = templateScene.clone(true);
    clone.traverse((n) => {
      if (n.isMesh) n.userData.sharedGeo = true;
    });
    clone.position.set(0, 0, 0);
    clone.rotation.set(0, 0, 0);
    clone.scale.setScalar(1.0);
    clone.updateMatrixWorld(true);

    const box = new THREE.Box3().setFromObject(clone);
    const size = new THREE.Vector3();
    const center = new THREE.Vector3();
    box.getSize(size);
    box.getCenter(center);

    const maxDim = Math.max(0.001, size.x, size.y, size.z);
    const s = targetSize / maxDim;
    clone.scale.setScalar(s);

    const anchorMode = opts.anchorMode || 'grip_y';
    if (anchorMode === 'grip_y') {
      // Sword: grip near bottom (+16% from pommel), blade extends along +Y
      clone.position.set(-center.x * s, -box.min.y * s - size.y * s * 0.16, -center.z * s);
    } else if (anchorMode === 'gun_x_to_z') {
      // Sci-Fi Gun: raw barrel points +X; anchor near grip & rotate -90 deg Y so barrel points +Z
      clone.position.set(-center.x * s + size.x * s * 0.16, -center.y * s + size.y * s * 0.12, -center.z * s);
    } else {
      clone.position.set(-center.x * s, -center.y * s, -center.z * s);
    }

    // Upgrade PBR sheen & emissive highlights on collected weapon meshes
    clone.traverse((child) => {
      if (child.isMesh && child.material) {
        const mats = Array.isArray(child.material) ? child.material : [child.material];
        const nextMats = mats.map((m) => {
          const clonedMat = m.clone();
          if (clonedMat.isMeshStandardMaterial) {
            clonedMat.roughness = Math.min(clonedMat.roughness ?? 0.45, 0.32);
            clonedMat.metalness = Math.max(clonedMat.metalness ?? 0.35, opts.metalness ?? 0.62);
            if (opts.emissiveHex && opts.emissiveIntensity) {
              clonedMat.emissive = new THREE.Color(opts.emissiveHex);
              clonedMat.emissiveIntensity = opts.emissiveIntensity;
            }
          }
          return clonedMat;
        });
        child.material = Array.isArray(child.material) ? nextMats : nextMats[0];
      }
    });

    const wrap = new THREE.Group();
    const rot = opts.rot || [0, 0, 0];
    wrap.rotation.set(rot[0], rot[1], rot[2]);
    wrap.add(clone);
    return wrap;
  }

  function rebuildHeroWeapon(forceRebuild = false) {
    const wepType = rpgState.equippedWeapon || 'fist';
    const tier = Math.max(1, Math.min(4, rpgState.weaponTier || 1));
    const sig = `${wepType}|${tier}|${rpgState.worldview}`;
    if (!forceRebuild && sig === lastBuiltWeaponSig && (heroRightHandGroup.children.length > 0 || heroLeftHandGroup.children.length > 0)) {
      return;
    }
    lastBuiltWeaponSig = sig;
    heroWeaponBuildSeq += 1;
    const seq = heroWeaponBuildSeq;
    clearGroupChildren(heroRightHandGroup);
    clearGroupChildren(heroLeftHandGroup);
    clearGroupChildren(heroBackQuiverGroup);
    gunMuzzleFlashMesh = null;

    const theme = WORLDVIEW_THEMES[rpgState.worldview] || WORLDVIEW_THEMES.fantasy;
    const colHex = theme.weaponColor[tier - 1] || 0x38bdf8;
    if (slashArcMat.uniforms?.uColor) slashArcMat.uniforms.uColor.value.setHex(colHex);

    if (wepType === 'fist') {
      const auraMat = new THREE.MeshBasicMaterial({ color: 0xfacc15, transparent: true, opacity: 0.85, toneMapped: false });
      const knuckleMat = new THREE.MeshStandardMaterial({ color: 0xf59e0b, metalness: 0.85, roughness: 0.22, emissive: 0xd97706, emissiveIntensity: 0.3 });
      const rGlove = new THREE.Group();
      rGlove.add(new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.018, 10, 22), auraMat));
      rGlove.add(new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 12), knuckleMat));
      const lGlove = new THREE.Group();
      lGlove.add(new THREE.Mesh(new THREE.TorusGeometry(0.11, 0.018, 10, 22), auraMat.clone()));
      lGlove.add(new THREE.Mesh(new THREE.SphereGeometry(0.075, 12, 12), knuckleMat.clone()));
      heroRightHandGroup.add(rGlove);
      heroLeftHandGroup.add(lGlove);
      return;
    }

    if (wepType === 'sword') {
      const swordUrl = rpgState.worldview === 'cyberpunk'
        ? HERO_WEAPON_GLB_URLS.sword_katana
        : (tier >= 3 ? HERO_WEAPON_GLB_URLS.sword_t3 : (tier === 2 ? HERO_WEAPON_GLB_URLS.sword_t2 : HERO_WEAPON_GLB_URLS.sword_t1));
      const targetLen = 1.05 + tier * 0.12;

      const mountSwordGlb = (tpl) => {
        if (seq !== heroWeaponBuildSeq || !tpl || !tpl.scene) return;
        clearGroupChildren(heroRightHandGroup);
        const swordObj = normalizeHeroWeaponGlb(tpl.scene, targetLen, {
          anchorMode: 'grip_y',
          rot: [0.06, 0, 0],
          metalness: 0.72,
          emissiveHex: colHex,
          emissiveIntensity: tier >= 2 ? 0.24 : 0.10,
        });
        // Add subtle radiant rune collar aura at the hilt
        const hiltGlow = new THREE.Mesh(
          new THREE.TorusGeometry(0.075, 0.012, 8, 20),
          new THREE.MeshBasicMaterial({ color: colHex, transparent: true, opacity: 0.75, toneMapped: false })
        );
        hiltGlow.rotation.x = Math.PI / 2;
        hiltGlow.position.y = 0.08;
        swordObj.add(hiltGlow);
        heroRightHandGroup.add(swordObj);
      };

      const cached = GLB_RESOLVED_CACHE.get(swordUrl);
      if (cached) {
        mountSwordGlb(cached);
      } else {
        // Brief procedural placeholder until CC0 .glb finishes loading (<5ms locally)
        const metalMat = new THREE.MeshStandardMaterial({ color: colHex, metalness: 0.82, roughness: 0.20, emissive: colHex, emissiveIntensity: 0.28 });
        const goldMat = new THREE.MeshStandardMaterial({ color: 0xfacc15, metalness: 0.88, roughness: 0.22 });
        const ph = new THREE.Group();
        ph.add(new THREE.Mesh(new THREE.BoxGeometry(0.075, targetLen * 0.78, 0.024), metalMat));
        ph.children[0].position.y = targetLen * 0.42;
        const guard = new THREE.Mesh(new THREE.BoxGeometry(0.26, 0.042, 0.058), goldMat);
        guard.position.y = 0.08;
        ph.add(guard);
        heroRightHandGroup.add(ph);
        loadGlbTemplateCached(swordUrl).then(mountSwordGlb);
      }
      return;
    }

    if (wepType === 'bow') {
      const bowUrl = HERO_WEAPON_GLB_URLS.bow_golden;
      const mountBowGlb = (tpl) => {
        if (seq !== heroWeaponBuildSeq || !tpl || !tpl.scene) return;
        clearGroupChildren(heroLeftHandGroup);
        const bowObj = normalizeHeroWeaponGlb(tpl.scene, 1.05, {
          anchorMode: 'center',
          rot: [0, -Math.PI * 0.5, 0],
          metalness: 0.65,
          emissiveHex: 0x4ade80,
          emissiveIntensity: 0.16,
        });
        heroLeftHandGroup.add(bowObj);
      };
      const cachedBow = GLB_RESOLVED_CACHE.get(bowUrl);
      if (cachedBow) {
        mountBowGlb(cachedBow);
      } else {
        const bowWoodMat = new THREE.MeshStandardMaterial({ color: 0xca8a04, roughness: 0.35, metalness: 0.65 });
        const bowCurve = new THREE.CatmullRomCurve3([
          new THREE.Vector3(0, -0.42, -0.08),
          new THREE.Vector3(0, -0.24, 0.10),
          new THREE.Vector3(0, 0.0, 0.16),
          new THREE.Vector3(0, 0.24, 0.10),
          new THREE.Vector3(0, 0.42, -0.08),
        ]);
        heroLeftHandGroup.add(new THREE.Mesh(new THREE.TubeGeometry(bowCurve, 24, 0.024, 8, false), bowWoodMat));
        loadGlbTemplateCached(bowUrl).then(mountBowGlb);
      }
      // Preload golden arrow GLB for projectiles
      loadGlbTemplateCached(HERO_WEAPON_GLB_URLS.arrow_golden);
      const quiverMat = new THREE.MeshStandardMaterial({ color: 0x78350f, roughness: 0.55, metalness: 0.25 });
      const quiver = new THREE.Mesh(new THREE.CylinderGeometry(0.062, 0.048, 0.40, 12), quiverMat);
      quiver.rotation.z = -0.35;
      heroBackQuiverGroup.add(quiver);
      return;
    }

    if (wepType === 'gun') {
      const gunUrl = tier >= 3
        ? HERO_WEAPON_GLB_URLS.gun_t3
        : (tier === 2 ? HERO_WEAPON_GLB_URLS.gun_t2 : HERO_WEAPON_GLB_URLS.gun_t1);
      const targetLen = tier >= 3 ? 0.96 : (tier === 2 ? 0.84 : 0.72);
      const muzzleZ = targetLen * 0.64;

      const buildMuzzleFlash = () => {
        const flashGrp = new THREE.Group();
        const coreMat = new THREE.MeshBasicMaterial({ color: 0xfef08a, transparent: true, opacity: 0.0, toneMapped: false });
        const ringMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.0, toneMapped: false });
        const star = new THREE.Mesh(new THREE.OctahedronGeometry(0.11, 0), coreMat);
        star.scale.set(0.8, 0.8, 1.8);
        const shock = new THREE.Mesh(new THREE.TorusGeometry(0.10, 0.02, 8, 16), ringMat);
        flashGrp.add(star, shock);
        flashGrp.position.set(0, 0.06, muzzleZ);
        flashGrp.userData.mats = [coreMat, ringMat];
        return flashGrp;
      };

      const mountGunGlb = (tpl) => {
        if (seq !== heroWeaponBuildSeq || !tpl || !tpl.scene) return;
        clearGroupChildren(heroRightHandGroup);
        const gunHolder = new THREE.Group();
        const gunObj = normalizeHeroWeaponGlb(tpl.scene, targetLen, {
          anchorMode: 'gun_x_to_z',
          rot: [0, -Math.PI * 0.5, 0],
          metalness: 0.78,
          emissiveHex: colHex,
          emissiveIntensity: 0.20,
        });
        gunHolder.add(gunObj);

        // Glowing plasma barrel energy ring
        const plasmaCoil = new THREE.Mesh(
          new THREE.TorusGeometry(0.048, 0.012, 8, 18),
          new THREE.MeshBasicMaterial({ color: colHex, transparent: true, opacity: 0.85, toneMapped: false })
        );
        plasmaCoil.position.set(0, 0.06, muzzleZ * 0.72);
        gunHolder.add(plasmaCoil);

        gunMuzzleFlashMesh = buildMuzzleFlash();
        gunHolder.add(gunMuzzleFlashMesh);
        heroRightHandGroup.add(gunHolder);
      };

      const cachedGun = GLB_RESOLVED_CACHE.get(gunUrl);
      if (cachedGun) {
        mountGunGlb(cachedGun);
      } else {
        const chassisMat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.82, roughness: 0.25 });
        const barrelMat = new THREE.MeshStandardMaterial({ color: 0x94a3b8, metalness: 0.9, roughness: 0.2 });
        const gunHolder = new THREE.Group();
        const receiver = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.11, targetLen * 0.55), chassisMat);
        receiver.position.set(0, 0.04, targetLen * 0.16);
        const barrel = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.030, targetLen * 0.45, 10), barrelMat);
        barrel.rotation.x = Math.PI / 2;
        barrel.position.set(0, 0.06, targetLen * 0.45);
        gunHolder.add(receiver, barrel);
        gunMuzzleFlashMesh = buildMuzzleFlash();
        gunHolder.add(gunMuzzleFlashMesh);
        heroRightHandGroup.add(gunHolder);
        loadGlbTemplateCached(gunUrl).then(mountGunGlb);
      }
    }
  }

  // ===========================================================================
  // 6. Combat State, Desktop World Bounds & VFX Containers
  // ===========================================================================
  const activeEnemies = [];
  const activeProjectiles = [];
  const activeEnemyProjectiles = [];
  const activeBossTelegraphs = [];
  const activeMeteors = [];
  const activeParticles = [];
  const activeFloatTexts = [];

  const combatState = {
    mode: 'PEACE',
    wave: 1,
    bossSpawnedThisWave: false,
    enemiesToSpawn: 0,
    spawnTimer: 0,
    heroHp: 280,
    heroMaxHp: 280,
    heroReviveTimer: 0,
    partnerHp: 240,
    partnerMaxHp: 240,
    partnerAtk: 18,
    partnerReviveTimer: 0,
    partnerCooldown: 0,
    partnerNovaCd: 3.5,
    baseHp: 750,
    baseMaxHp: 750,
    heroAtk: 22,
    heroAps: 1.0,
    attackCooldown: 0,
    comboStep: 0,
    slashAnimTimer: 0,
    slashAnimDur: 0.80,
    pendingAttack: null,
    aimPitch: 0,
    whirlwindTimer: 0,
    muzzleFlashTimer: 0,
    heroLeapTimer: 0,
    bentoBuffTimer: 0,
    bentoAtkMult: 1.0,
    bentoSpdMult: 1.0,
    hasteBuffTimer: 0,
    rageBuffTimer: 0,
    luckBuffTimer: 0,
    shieldBuffTimer: 0,
    overdriveTimer: 0,
    skillCdQ: 0,
    skillCdW: 0,
    skillCdE: 0,
    lockedTarget: null,
    turretCooldowns: { ballista: 0, cannon: 0, frost: 0, arc: 0, sniper: 0 },
    selectedPadId: null,
    hudThrottleTimer: 0,
    smiteCooldown: 0,
    telegraphClickCd: 0,
    bentoCooldown: 0,
    heroInvulnTimer: 0,
    partnerInvulnTimer: 0,
    retargetTimer: 0,
    camShake: 0,
    spawnQueue: [],
    telemetry: {
      waveStartMs: 0,
      totalDamageDealt: 0,
      dmgBySource: { hero: 0, partner: 0, ballista: 0, cannon: 0, frost: 0, arc: 0, sniper: 0, skill: 0 },
      killsBySource: { hero: 0, partner: 0, ballista: 0, cannon: 0, frost: 0, arc: 0, sniper: 0, skill: 0 },
      damageTakenBySource: { vanguard: 0, shield_tank: 0, arcane_ranger: 0, support_shaman: 0, boss: 0 },
      baseDmgTaken: 0,
      baseBreaches: [],
      skillsUsed: { Q: 0, W: 0, E: 0 },
      tipsShown: {},
    },
  };

  function triggerCameraShake(intensity = 0.14) {
    combatState.camShake = Math.min(0.32, Math.max(combatState.camShake || 0, Number(intensity) || 0));
  }

  function applyDefenseCameraMode(enableDefense) {
    if (!camera) return;
    combatState.camShake = 0;
    const pos = enableDefense ? DEFENSE_CAMERA_POS : NORMAL_CAMERA_POS;
    camera.position.set(pos.x, pos.y, pos.z);
    camera.lookAt(0, pos.lookY, 0);
    camera.updateProjectionMatrix();
  }

  function getDesktopWorldBounds() {
    const aspect = Math.max(0.55, (window.innerWidth || 1920) / Math.max(1, window.innerHeight || 1080));
    const camZ = combatState.mode === 'PEACE' ? NORMAL_CAMERA_POS.z : DEFENSE_CAMERA_POS.z;
    const fovRad = THREE.MathUtils.degToRad(camera?.fov || 27);
    const halfH = camZ * Math.tan(fovRad * 0.5);
    const halfW = halfH * aspect;

    const xMin = -halfW;
    const xMax = halfW;
    const yMin = DEFENSE_CAMERA_POS.lookY - halfH;
    const yMax = DEFENSE_CAMERA_POS.lookY + halfH;
    const width = xMax - xMin;
    const height = yMax - yMin;

    const baseX = xMin + width * 0.045;
    const baseY = yMin + height * 0.055;

    return { xMin, xMax, yMin, yMax, width, height, baseX, baseY };
  }

  function getDesktopDirectionalSpawnPoint(zoneIdx = null) {
    const { xMin, xMax, yMin, yMax, width, height } = getDesktopWorldBounds();
    const zone = zoneIdx !== null ? ((zoneIdx % 4 + 4) % 4) : Math.floor(Math.random() * 4);
    const rand = (a, b) => a + Math.random() * (b - a);
    const padX = width * 0.05;
    const padY = height * 0.09;

    if (zone === 0) return { x: rand(xMin + width * 0.25, xMax - width * 0.16), y: yMax - padY * 1.35, zone };
    if (zone === 1) return { x: rand(xMax - width * 0.20, xMax - padX), y: rand(yMin + height * 0.60, yMax - padY * 1.2), zone };
    if (zone === 2) return { x: xMax - padX, y: rand(yMin + height * 0.28, yMin + height * 0.64), zone };
    return { x: rand(xMin + width * 0.48, xMax - padX), y: rand(yMin + padY, yMin + height * 0.26), zone };
  }

  function getStageBracketInfo(stageNum = 1) {
    const s = Math.max(1, parseInt(stageNum, 10) || 1);
    const bracketIdx = Math.min(STAGE_BRACKET_SPECS.length - 1, Math.floor((s - 1) / 10));
    const inBracketIdx = bracketIdx === STAGE_BRACKET_SPECS.length - 1
      ? (s - 1 - bracketIdx * 10)
      : ((s - 1) % 10);
    return { stage: s, bracketIdx, inBracketIdx, spec: STAGE_BRACKET_SPECS[bracketIdx] };
  }

  let floatTextSeq = 0;
  const floatTextTexCache = new Map();
  const FLOAT_TEXT_CACHE_MAX = 48;

  function getCachedFloatTextTexture(text, colorStr) {
    const cacheKey = `${text}|${colorStr}`;
    if (floatTextTexCache.has(cacheKey)) {
      const hit = floatTextTexCache.get(cacheKey);
      floatTextTexCache.delete(cacheKey);
      floatTextTexCache.set(cacheKey, hit);
      return hit;
    }
    const canvas = document.createElement('canvas');
    const c2d = canvas.getContext('2d');
    const font = '700 32px "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI Variable", "Malgun Gothic", "Segoe UI Emoji", sans-serif';
    c2d.font = font;
    const measuredW = Math.ceil(c2d.measureText(text).width);
    const isCompactHit = text.length <= 10 && (text.startsWith('-') || text.startsWith('+') || text.includes('CRIT'));
    const leftPad = isCompactHit ? 24 : 34;
    const rightPad = 24;
    canvas.width = Math.max(96, measuredW + leftPad + rightPad);
    canvas.height = 64;

    const bx = 4;
    const by = 6;
    const bw = canvas.width - 8;
    const bh = canvas.height - 12;
    const r = bh * 0.5; // Full Cupertino / Material minimal capsule pill

    const tracePill = (x, y, w, h, rad) => {
      c2d.beginPath();
      if (typeof c2d.roundRect === 'function') {
        c2d.roundRect(x, y, w, h, rad);
      } else {
        c2d.rect(x, y, w, h);
      }
    };

    // 1. Flat / Minimal ambient elevation + Dark-Mode Glassmorphic capsule fill
    c2d.save();
    c2d.shadowColor = 'rgba(2, 6, 23, 0.36)';
    c2d.shadowBlur = 7;
    c2d.shadowOffsetY = 2;
    const bgGrad = c2d.createLinearGradient(0, by, 0, by + bh);
    bgGrad.addColorStop(0, 'rgba(17, 24, 39, 0.84)');
    bgGrad.addColorStop(1, 'rgba(10, 15, 28, 0.91)');
    tracePill(bx, by, bw, bh, r);
    c2d.fillStyle = bgGrad;
    c2d.fill();
    c2d.restore();

    // 2. Neumorphic dual-tone inner highlight (top specular + bottom recess)
    const rimGrad = c2d.createLinearGradient(0, by, 0, by + bh);
    rimGrad.addColorStop(0, 'rgba(255, 255, 255, 0.24)');
    rimGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.08)');
    rimGrad.addColorStop(1, 'rgba(2, 6, 23, 0.52)');
    tracePill(bx + 0.75, by + 0.75, bw - 1.5, bh - 1.5, r - 0.75);
    c2d.lineWidth = 1.25;
    c2d.strokeStyle = rimGrad;
    c2d.stroke();

    // 3. Cupertino / Material left semantic accent indicator pill (for status/skill/loot boxes)
    if (!isCompactHit) {
      const ax = bx + 13;
      const ay = by + (bh - 20) * 0.5;
      tracePill(ax - 1, ay - 1, 6, 22, 3);
      c2d.fillStyle = 'rgba(2, 6, 23, 0.65)';
      c2d.fill();
      tracePill(ax, ay, 4, 20, 2);
      c2d.fillStyle = colorStr;
      c2d.fill();
    }

    // 4. High-contrast crisp Dark-Mode typography (zero heavy cartoon outline)
    c2d.save();
    c2d.font = font;
    c2d.textAlign = 'center';
    c2d.textBaseline = 'middle';
    c2d.shadowColor = 'rgba(2, 6, 23, 0.62)';
    c2d.shadowBlur = 3;
    c2d.shadowOffsetY = 1;
    const textCenterX = bx + leftPad + (bw - leftPad - rightPad) * 0.5;
    c2d.fillStyle = isCompactHit ? colorStr : '#F8FAFC';
    c2d.fillText(text, textCenterX, canvas.height * 0.5 + 0.5);
    c2d.restore();

    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    const entry = { tex, width: canvas.width, height: canvas.height };
    floatTextTexCache.set(cacheKey, entry);

    while (floatTextTexCache.size > FLOAT_TEXT_CACHE_MAX) {
      const oldestKey = floatTextTexCache.keys().next().value;
      const oldestEntry = floatTextTexCache.get(oldestKey);
      floatTextTexCache.delete(oldestKey);
      if (oldestEntry && oldestEntry.tex) {
        const stillActive = activeFloatTexts.some((ft) => ft.sprite && ft.sprite.material && ft.sprite.material.map === oldestEntry.tex);
        if (!stillActive) oldestEntry.tex.dispose();
      }
    }
    return entry;
  }

  function spawnFloatText(text, worldPos, colorStr = '#fde047', scale = 1.0) {
    if (activeFloatTexts.length >= 16) {
      const oldest = activeFloatTexts.shift();
      projectilesGroup.remove(oldest.sprite);
      oldest.sprite.material.dispose();
    }
    const { tex, width: texW, height: texH } = getCachedFloatTextTexture(text, colorStr);
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false });
    const sprite = new THREE.Sprite(mat);
    sprite.renderOrder = 30;

    const worldH = 0.46 * scale;
    const worldW = worldH * (texW / texH);

    // Smart anti-overlap stacking: resolve vertical lane & slight alternating horizontal stagger
    floatTextSeq = (floatTextSeq + 1) % 6;
    const baseStaggerX = ((floatTextSeq % 3) - 1) * 0.42;
    let spawnX = worldPos.x + baseStaggerX;
    let spawnY = worldPos.y + 0.88;
    const minSepY = Math.max(0.50, worldH * 1.12);
    for (let attempt = 0; attempt < 6; attempt++) {
      let collided = false;
      for (let i = 0; i < activeFloatTexts.length; i++) {
        const ft = activeFloatTexts[i];
        if (ft.life > 0.78) continue;
        const otherHalfW = (ft.worldW || 1.2) * 0.5;
        const dx = Math.abs(ft.sprite.position.x - spawnX);
        const dy = Math.abs(ft.sprite.position.y - spawnY);
        if (dx < (worldW * 0.48 + otherHalfW) && dy < minSepY) {
          collided = true;
          break;
        }
      }
      if (!collided) break;
      spawnY += minSepY;
      if (attempt % 2 === 1) {
        spawnX += (attempt % 4 === 1 ? 0.55 : -0.55);
      }
    }
    const { xMin, xMax, yMin, yMax } = getDesktopWorldBounds();
    const halfW = worldW * 0.54;
    spawnX = THREE.MathUtils.clamp(spawnX, xMin + halfW + 0.15, xMax - halfW - 0.15);
    spawnY = THREE.MathUtils.clamp(spawnY, yMin + 0.5, yMax - 0.45);

    sprite.position.set(spawnX, spawnY, 0.25 + floatTextSeq * 0.01);
    sprite.scale.set(worldW, worldH, 1);
    projectilesGroup.add(sprite);

    activeFloatTexts.push({ sprite, worldW, vy: 0.64, life: 0, maxLife: 1.0 });
  }

  const freeParticlePool = [];
  const freeShockwavePool = [];
  const freeRibbonPool = [];
  let vfxPoolsPrimed = false;

  function ensureVfxPoolsPrimed() {
    if (vfxPoolsPrimed) return;
    vfxPoolsPrimed = true;
    for (let i = 0; i < 48; i++) {
      const mat = new THREE.MeshBasicMaterial({
        color: 0xffffff,
        transparent: true,
        opacity: 1.0,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        toneMapped: false,
      });
      const m = new THREE.Mesh(SHARED_GEO.particleSphere, mat);
      m.visible = false;
      m.userData.sharedGeo = true;
      m.userData.pooledKind = 'particle';
      freeParticlePool.push(m);
    }
    for (let i = 0; i < 16; i++) {
      const mat = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: new THREE.Color(0x38bdf8) },
          uProgress: { value: 0.0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uProgress;
          varying vec2 vUv;
          void main() {
            vec2 p = vUv * 2.0 - 1.0;
            float r = length(p);
            if (r > 1.0) discard;
            float frontR = 0.25 + uProgress * 0.65;
            float ring1 = exp(-pow((r - frontR) * 11.0, 2.0));
            float ring2 = exp(-pow((r - frontR * 0.72) * 14.0, 2.0)) * 0.52;
            float fade = (1.0 - uProgress) * (1.0 - uProgress * 0.35);
            float alpha = (ring1 + ring2) * smoothstep(1.0, 0.80, r) * fade;
            vec3 col = mix(uColor, vec3(1.0), ring1 * 0.48);
            gl_FragColor = vec4(col, alpha);
          }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        toneMapped: false,
        side: THREE.DoubleSide,
      });
      mat.customProgramCacheKey = () => 'def_sdf_shockwave_v1';
      const ring = new THREE.Mesh(SHARED_GEO.shockwaveQuad, mat);
      ring.visible = false;
      ring.userData.sharedGeo = true;
      ring.userData.pooledKind = 'shockwave';
      freeShockwavePool.push(ring);
    }
    for (let i = 0; i < 24; i++) {
      const mat = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: new THREE.Color(0x38bdf8) },
          uProgress: { value: 0.0 },
          uIsLaser: { value: 0.0 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uProgress;
          uniform float uIsLaser;
          varying vec2 vUv;
          void main() {
            float d = (vUv.y - 0.5) * 2.0;
            float core = exp(-d * d * (uIsLaser > 0.5 ? 24.0 : 18.0));
            float corona = exp(-d * d * 4.5) * 0.72;
            float ends = smoothstep(0.0, 0.08, vUv.x) * (1.0 - smoothstep(0.92, 1.0, vUv.x));
            float fade = 1.0 - uProgress * uProgress;
            float alpha = (core + corona) * ends * fade;
            vec3 col = mix(uColor, vec3(1.0), core * 0.85);
            gl_FragColor = vec4(col, alpha);
          }
        `,
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
        toneMapped: false,
        side: THREE.DoubleSide,
      });
      mat.customProgramCacheKey = () => 'def_gauss_ribbon_v1';
      const quad = new THREE.Mesh(SHARED_GEO.ribbonQuad, mat);
      quad.visible = false;
      quad.userData.sharedGeo = true;
      quad.userData.pooledKind = 'ribbon';
      freeRibbonPool.push(quad);
    }
  }

  function releasePooledVfxEntry(p) {
    const m = p.mesh;
    if (!m) return;
    projectilesGroup.remove(m);
    const kind = m.userData?.pooledKind;
    if (kind === 'particle') {
      m.visible = false;
      freeParticlePool.push(m);
    } else if (kind === 'shockwave') {
      m.visible = false;
      freeShockwavePool.push(m);
    } else if (kind === 'ribbon') {
      m.visible = false;
      freeRibbonPool.push(m);
    } else {
      if (m.geometry && p.isLine) m.geometry.dispose();
      m.material?.dispose?.();
    }
  }

  function spawnParticleBurst(origin, colorHex = 0x38bdf8, count = 7, speed = 1.1) {
    ensureVfxPoolsPrimed();
    const capCount = Math.min(count, freeParticlePool.length, Math.max(0, 48 - activeParticles.length));
    for (let i = 0; i < capCount; i++) {
      const m = freeParticlePool.pop();
      const useStar = (i % 2 === 0);
      m.geometry = useStar ? SHARED_GEO.particleStar : SHARED_GEO.particleSphere;
      m.material.color.setHex(colorHex);
      m.material.opacity = 1.0;
      m.scale.setScalar(useStar ? (0.85 + Math.random() * 0.55) : (0.80 + Math.random() * 0.50));
      m.rotation.set(0, 0, Math.random() * Math.PI);
      m.position.set(origin.x, origin.y + 0.62, 0.14);
      m.visible = true;
      const a = Math.random() * Math.PI * 2;
      const spd = (0.55 + Math.random() * 1.1) * speed;
      projectilesGroup.add(m);
      activeParticles.push({
        mesh: m,
        isStar: useStar,
        spin: (Math.random() - 0.5) * 14.0,
        vx: Math.cos(a) * spd,
        vy: Math.sin(a) * spd + 0.4,
        life: 0,
        maxLife: 0.42 + Math.random() * 0.24,
      });
    }
  }

  function spawnShockwaveRing(origin, colorHex = 0x38bdf8, maxScale = 1.6) {
    ensureVfxPoolsPrimed();
    if (freeShockwavePool.length === 0) return;
    const ring = freeShockwavePool.pop();
    ring.material.uniforms.uColor.value.setHex(colorHex);
    ring.material.uniforms.uProgress.value = 0.0;
    ring.position.set(origin.x, origin.y + 0.22, 0.10);
    ring.scale.setScalar(0.35);
    ring.visible = true;
    projectilesGroup.add(ring);
    activeParticles.push({ mesh: ring, isRing: true, maxScale, vx: 0, vy: 0, life: 0, maxLife: 0.44 });
  }

  function spawnRibbonSegment(p1, p2, colorHex, width = 0.24, maxLife = 0.24, isLaser = false) {
    ensureVfxPoolsPrimed();
    if (freeRibbonPool.length === 0) return;
    const quad = freeRibbonPool.pop();
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const len = Math.max(0.08, Math.hypot(dx, dy));
    quad.material.uniforms.uColor.value.setHex(colorHex);
    quad.material.uniforms.uProgress.value = 0.0;
    quad.material.uniforms.uIsLaser.value = isLaser ? 1.0 : 0.0;
    quad.position.set((p1.x + p2.x) * 0.5, (p1.y + p2.y) * 0.5, 0.20);
    quad.rotation.set(0, 0, Math.atan2(dy, dx));
    quad.scale.set(len, width, 1.0);
    quad.visible = true;
    projectilesGroup.add(quad);
    activeParticles.push({ mesh: quad, isRibbon: true, vx: 0, vy: 0, life: 0, maxLife });
  }

  function spawnChainLightningVFX(pointsArray, colorHex = 0x38bdf8) {
    for (let i = 0; i < pointsArray.length - 1; i++) {
      const p1 = pointsArray[i];
      const p2 = pointsArray[i + 1];
      let prev = p1;
      for (let s = 1; s <= 3; s++) {
        const f = s / 4;
        const jPt = new THREE.Vector3(
          THREE.MathUtils.lerp(p1.x, p2.x, f) + (Math.random() - 0.5) * 0.30,
          THREE.MathUtils.lerp(p1.y, p2.y, f) + (Math.random() - 0.5) * 0.30,
          0.20
        );
        spawnRibbonSegment(prev, jPt, colorHex, 0.22, 0.24, false);
        prev = jPt;
      }
      spawnRibbonSegment(prev, p2, colorHex, 0.22, 0.24, false);
    }
  }

  function spawnBossTelegraph(targetPos, casterEnemy) {
    const zStagger = Math.min(4, activeBossTelegraphs.length) * 0.004;
    const telMat = new THREE.ShaderMaterial({
      uniforms: {
        uProgress: { value: 0.0 },
        uTime: { value: 0.0 },
        uSmiteRatio: { value: 0.0 },
      },
      vertexShader: `
        varying vec2 vUv;
        void main() {
          vUv = uv;
          gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
        }
      `,
      fragmentShader: `
        uniform float uProgress;
        uniform float uTime;
        uniform float uSmiteRatio;
        varying vec2 vUv;
        void main() {
          vec2 p = vUv * 2.0 - 1.0;
          float r = length(p);
          if (r > 1.0) discard;
          float ang = atan(p.y, p.x);
          float dash = step(0.18, fract(ang * 2.866 + uTime * 0.85));
          float outerRim = smoothstep(0.84, 0.90, r) * (1.0 - smoothstep(0.95, 0.99, r));
          float warnWave = smoothstep(max(0.0, uProgress - 0.06), uProgress, r) * step(r, uProgress + 0.02);
          float innerFill = smoothstep(r - 0.03, r + 0.02, uProgress) * (1.0 - smoothstep(0.88, 0.94, r));
          vec3 baseRed = mix(vec3(0.96, 0.24, 0.36), vec3(0.22, 0.74, 0.98), uSmiteRatio * 0.55);
          vec3 col = mix(baseRed, vec3(1.0, 0.72, 0.35), outerRim * 0.65);
          float alpha = outerRim * (0.55 + 0.40 * dash) + innerFill * 0.28 + warnWave * 0.42;
          gl_FragColor = vec4(col, clamp(alpha, 0.0, 0.92));
        }
      `,
      transparent: true,
      depthWrite: false,
      side: THREE.DoubleSide,
    });
    telMat.customProgramCacheKey = () => 'def_boss_telegraph_v1';
    const mesh = new THREE.Mesh(SHARED_GEO.telegraphQuad, telMat);
    mesh.position.set(targetPos.x, targetPos.y + 0.15, 0.025 + zStagger);
    mesh.userData.sharedGeo = true;
    projectilesGroup.add(mesh);
    spawnFloatText('⚠️ 붉은 장판 회피 / 클릭 차단!', targetPos, '#f43f5e', 1.05);
    activeBossTelegraphs.push({
      mesh,
      mat: telMat,
      caster: casterEnemy,
      elapsed: 0,
      duration: 1.65,
      radius: 1.85,
      smiteHits: 0,
    });
  }

  const roleBadgeTexCache = new Map();
  function getRoleBadgeTexture(iconStr) {
    if (roleBadgeTexCache.has(iconStr)) return roleBadgeTexCache.get(iconStr);
    const c = document.createElement('canvas');
    c.width = 48;
    c.height = 48;
    const ctx2 = c.getContext('2d');
    ctx2.fillStyle = 'rgba(15, 23, 42, 0.85)';
    ctx2.beginPath();
    ctx2.arc(24, 24, 20, 0, Math.PI * 2);
    ctx2.fill();
    ctx2.lineWidth = 2;
    ctx2.strokeStyle = 'rgba(255, 255, 255, 0.30)';
    ctx2.stroke();
    ctx2.font = '24px "Segoe UI Emoji", "Apple Color Emoji", sans-serif';
    ctx2.textAlign = 'center';
    ctx2.textBaseline = 'middle';
    ctx2.fillText(iconStr || '⚔️', 24, 25);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    roleBadgeTexCache.set(iconStr, tex);
    return tex;
  }

  function spawnDesktopStageEnemy(stageNum = 1, zoneIdx = null, forceBoss = false, forcedRoleKey = null) {
    const { stage, inBracketIdx, spec } = getStageBracketInfo(stageNum);
    const isBoss = forceBoss || false;
    if (isBoss) combatState.bossSpawnedThisWave = true;
    const spawnPt = getDesktopDirectionalSpawnPoint(zoneIdx);

    const instanceData = createEnemyGlbHolder(spec, isBoss, isBoss ? 'boss' : forcedRoleKey);
    const roleSpec = instanceData.roleSpec;

    const intraStageMult = Math.pow(1.145, inBracketIdx);
    const maxHp = Math.round(spec.baseHp * intraStageMult * (isBoss ? 6.5 : roleSpec.hpMult));
    const maxShieldHp = isBoss ? Math.round(spec.baseHp * intraStageMult * 1.65) : Math.round(maxHp * (roleSpec.shieldMult || 0));
    const armor = Math.round(spec.baseArmor + (isBoss ? 10 : (roleSpec.armorBonus || 0)));
    const atk = Math.round((spec.baseAtk + inBracketIdx * 2.0) * (isBoss ? 1.85 : roleSpec.atkMult));
    const spd = (spec.baseSpeed + Math.min(18, inBracketIdx) * 0.014) * (isBoss ? 0.78 : roleSpec.spdMult);

    const root = new THREE.Group();
    root.position.set(spawnPt.x, spawnPt.y, 0.0);
    const roleSc = isBoss ? 1.0 : (roleSpec.scaleMult || 1.12);
    root.scale.setScalar(isBoss ? 0.62 : 0.44 * roleSc);
    root.add(instanceData.modelHolder);

    const shadow = new THREE.Mesh(SHARED_GEO.shadowDisc, SHARED_MAT.softContactShadow);
    shadow.rotation.x = -Math.PI * 0.34;
    shadow.position.y = 0.004;
    shadow.scale.setScalar(isBoss ? 2.05 : 1.32);
    shadow.renderOrder = 3;
    shadow.userData.sharedGeo = true;
    shadow.userData.sharedMat = true;
    root.add(shadow);

    let telegraphRing = null;
    if (isBoss || inBracketIdx >= 2 || roleSpec.key === 'support_shaman' || roleSpec.key === 'shield_tank' || roleSpec.key === 'arcane_ranger') {
      const ringCol = new THREE.Color(isBoss ? 0xf43f5e : (roleSpec.hpBarColor || spec.rimHex));
      const ringMat = new THREE.ShaderMaterial({
        uniforms: {
          uColor: { value: ringCol },
          uOpacity: { value: isBoss ? 0.62 : 0.42 },
        },
        vertexShader: `
          varying vec2 vUv;
          void main() {
            vUv = uv;
            gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
          }
        `,
        fragmentShader: `
          uniform vec3 uColor;
          uniform float uOpacity;
          varying vec2 vUv;
          void main() {
            vec2 p = vUv * 2.0 - 1.0;
            float r = length(p);
            if (r > 1.0) discard;
            float outer = smoothstep(0.68, 0.78, r) * (1.0 - smoothstep(0.84, 0.94, r));
            float inner = smoothstep(0.46, 0.52, r) * (1.0 - smoothstep(0.54, 0.60, r)) * 0.45;
            gl_FragColor = vec4(uColor, (outer + inner) * uOpacity);
          }
        `,
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide,
      });
      ringMat.customProgramCacheKey = () => 'def_enemy_role_ring_v1';
      telegraphRing = new THREE.Mesh(SHARED_GEO.shadowDisc, ringMat);
      telegraphRing.rotation.x = -Math.PI * 0.34;
      telegraphRing.position.y = 0.008;
      telegraphRing.scale.setScalar(isBoss ? 2.15 : 1.35);
      telegraphRing.renderOrder = 4;
      telegraphRing.userData.sharedGeo = true;
      root.add(telegraphRing);
    }

    const hpHeight = Math.max(1.85, instanceData.height + 0.36);
    const barW = isBoss ? 1.85 : 1.12;
    const barH = isBoss ? 0.24 : 0.17;
    const hpBarMesh = createRoundedPillBarMesh(
      barW,
      barH,
      isBoss ? 0xf43f5e : roleSpec.hpBarColor,
      maxShieldHp > 0
    );
    hpBarMesh.position.set(0, hpHeight, 0.05);
    root.add(hpBarMesh);

    const roleIconSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({ map: getRoleBadgeTexture(roleSpec.icon || '⚔️'), transparent: true, depthTest: false, depthWrite: false })
    );
    roleIconSprite.scale.set(isBoss ? 0.34 : 0.25, isBoss ? 0.34 : 0.25, 1);
    roleIconSprite.position.set(-barW * 0.5 - (isBoss ? 0.22 : 0.16), hpHeight, 0.06);
    roleIconSprite.renderOrder = 25;
    root.add(roleIconSprite);

    instanceData.modelHolder.rotation.y = -0.78;
    enemiesGroup.add(root);
    spawnShockwaveRing(root.position, isBoss ? 0xf43f5e : spec.rimHex, isBoss ? 1.9 : 1.15);
    if (isBoss) triggerChronicleStoryBanner('boss_intro', stage, { name: `${spec.speciesTitle} 군단장` });

    Object.assign(instanceData, {
      archetype: spec.speciesKey,
      bracketIdx: spec.bracket,
      inBracketIdx,
      lootSpec: spec.loot,
      name: `${spec.speciesTitle} ${isBoss ? '[군단장 보스]' : `[${roleSpec.title} Lv.${inBracketIdx + 1}]`}`,
      isBoss,
      mesh: root,
      hpBarMesh,
      roleIconSprite,
      telegraphRing,
      zoneIdx: spawnPt.zone ?? 0,
      waypointIdx: 0,
      pendingIncomingDmg: 0,
      markedTimer: 0,
      hp: maxHp,
      maxHp,
      shieldHp: maxShieldHp,
      maxShieldHp,
      armor,
      speed: spd,
      atk,
      attackRange: isBoss ? 1.35 : roleSpec.attackRange,
      atkCooldown: 1.25,
      healTimer: roleSpec.healInterval || 0,
      bossAoETimer: isBoss ? 5.2 : 0,
      phase2Triggered: false,
      slowTimer: 0,
      stunTimer: 0,
      hitFlashTimer: 0,
      hitSquash: 0,
      stridePhase: Math.random() * Math.PI * 2,
      attackWindup: 0,
      dyingTimer: -1,
      knockVx: 0,
      knockVy: 0,
    });
    activeEnemies.push(instanceData);
  }

  function disposeEnemy(e) {
    if (!e) return;
    e.disposed = true;
    if (e.animFsm && e.animFsm.mixer) {
      e.animFsm.mixer.stopAllAction();
      if (e.clonedRoot) e.animFsm.mixer.uncacheRoot(e.clonedRoot);
    }
    if (e.mesh) {
      enemiesGroup.remove(e.mesh);
      e.mesh.traverse((node) => {
        if (node.geometry && !node.userData?.sharedGeo && typeof node.geometry.dispose === 'function') {
          node.geometry.dispose();
        }
        if (node.isSprite && node.material && typeof node.material.dispose === 'function') {
          node.material.dispose();
        }
      });
    }
    if (e.hpBarMesh && e.hpBarMesh.material) e.hpBarMesh.material.dispose();
    if (e.telegraphRing && e.telegraphRing.material) e.telegraphRing.material.dispose();
    if (e.bodyMats) {
      for (let i = 0; i < e.bodyMats.length; i++) {
        if (e.bodyMats[i] && typeof e.bodyMats[i].dispose === 'function') e.bodyMats[i].dispose();
      }
    }
    if (e.ownedPropMats) {
      for (let i = 0; i < e.ownedPropMats.length; i++) {
        if (e.ownedPropMats[i] && typeof e.ownedPropMats[i].dispose === 'function') e.ownedPropMats[i].dispose();
      }
    }
  }

  function disposeProjectileMesh(mesh) {
    if (!mesh) return;
    projectilesGroup.remove(mesh);
    mesh.traverse((node) => {
      if (node.geometry && !node.userData?.sharedGeo && typeof node.geometry.dispose === 'function') {
        node.geometry.dispose();
      }
      if (node.material && !node.userData?.sharedMat && typeof node.material.dispose === 'function') {
        node.material.dispose();
      }
    });
  }

  function clearAllEnemies() {
    while (activeEnemies.length > 0) disposeEnemy(activeEnemies.pop());
    while (activeProjectiles.length > 0) {
      const p = activeProjectiles.pop();
      disposeProjectileMesh(p.mesh);
    }
    while (activeEnemyProjectiles.length > 0) {
      const ep = activeEnemyProjectiles.pop();
      disposeProjectileMesh(ep.mesh);
    }
    while (activeBossTelegraphs.length > 0) {
      const bt = activeBossTelegraphs.pop();
      projectilesGroup.remove(bt.mesh);
      bt.mat?.dispose?.();
    }
    while (activeMeteors.length > 0) {
      const m = activeMeteors.pop();
      projectilesGroup.remove(m.mesh);
      if (m.coreMat) m.coreMat.dispose();
      if (m.rockMat) m.rockMat.dispose();
      if (m.haloMat) m.haloMat.dispose();
    }
    while (activeParticles.length > 0) {
      releasePooledVfxEntry(activeParticles.pop());
    }
    combatState.lockedTarget = null;
  }

  // ===========================================================================
  // 7. TTK Combat Damage (Armor, Front Shield Break, Boss Cap & Phase 2 Enrage)
  // ===========================================================================
  function damageEnemy(idx, rawDmg, isCrit = false, slowSec = 0, stunSec = 0, knockbackForce = 0.55, armorPen = 0.0, sourceKey = 'hero', extraFlags = null) {
    const e = activeEnemies[idx];
    if (!e || e.dyingTimer >= 0) return;

    // Frost Lv.3+ Brittle (+20%), Ballista Lv.5 Mark (+15%), Arc vs Ranger/Shaman (+35%) & Frozen Shatter (+25%)
    const brittleMult = (e.brittleTimer || 0) > 0 ? 1.20 : 1.0;
    const markMult = (e.markedTimer || 0) > 0 ? 1.15 : 1.0;
    let roleCounterMult = 1.0;
    if (sourceKey === 'arc') {
      if (e.roleKey === 'arcane_ranger' || e.roleKey === 'support_shaman') roleCounterMult *= 1.35;
      if (extraFlags?.arcShatter && (e.slowTimer || 0) > 0) roleCounterMult *= 1.25;
    }

    // 1. Armor Mitigation Formula
    const effectiveArmor = Math.max(0, (e.armor || 0) * (1.0 - Math.min(1.0, armorPen)));
    const armorMitigation = 100 / (100 + effectiveArmor * 6.5);
    let finalDmg = Math.max(2, Math.round(rawDmg * brittleMult * markMult * roleCounterMult * armorMitigation));

    // 2. Boss Single-Hit Damage Cap (guarantees 25~45 hits multi-phase boss battle)
    if (e.isBoss) {
      finalDmg = Math.min(finalDmg, Math.max(8, Math.round(e.maxHp * 0.042)));
    }

    // 3. Front Shield Absorption & Guard Break (Cannon deals 1.65x bonus shield-breaker damage!)
    let shieldAbsorbed = false;
    if (e.shieldHp > 0) {
      shieldAbsorbed = true;
      const shieldMult = sourceKey === 'cannon' ? 1.65 : 0.85;
      const shDmg = Math.max(1, Math.round(finalDmg * shieldMult));
      if (e.shieldHp >= shDmg) {
        e.shieldHp -= shDmg;
        finalDmg = 0;
      } else {
        const overflow = shDmg - e.shieldHp;
        e.shieldHp = 0;
        finalDmg = overflow;
        triggerCameraShake(0.14);
        spawnFloatText('🛡️ 방패 파괴!! (BREAK!)', e.mesh.position, '#38bdf8', 1.15);
        spawnShockwaveRing(e.mesh.position, 0x38bdf8, 1.55);
        if (e.shieldMesh) e.shieldMesh.visible = false;
        e.stunTimer = Math.max(e.stunTimer, 0.85);
        setEnemyAnimState(e, 'HIT', 0.06);
      }
      if (e.hpBarMesh) {
        setPillBarValues(
          e.hpBarMesh,
          e.hp / Math.max(1, e.maxHp),
          e.maxShieldHp > 0 ? e.shieldHp / e.maxShieldHp : 0,
          e.shieldHp > 0
        );
      }
    }

    e.hp = Math.max(0, e.hp - finalDmg);
    if (combatState.telemetry && finalDmg > 0) {
      combatState.telemetry.totalDamageDealt = (combatState.telemetry.totalDamageDealt || 0) + finalDmg;
      const bucket = combatState.telemetry.dmgBySource;
      if (bucket) bucket[sourceKey] = (bucket[sourceKey] || 0) + finalDmg;
    }
    e.hitFlashTimer = 0.16;
    e.hitSquash = e.roleKey === 'shield_tank' && e.shieldHp > 0 ? -0.10 : -0.26;
    if (slowSec > 0) e.slowTimer = Math.max(e.slowTimer, slowSec);
    if (extraFlags && extraFlags.brittleSec > 0) e.brittleTimer = Math.max(e.brittleTimer || 0, extraFlags.brittleSec);
    if (extraFlags && extraFlags.antiHealSec > 0) e.antiHealTimer = Math.max(e.antiHealTimer || 0, extraFlags.antiHealSec);
    if (extraFlags && extraFlags.markSec > 0) e.markedTimer = Math.max(e.markedTimer || 0, extraFlags.markSec);
    if (stunSec > 0 && !(e.roleKey === 'shield_tank' && e.shieldHp > 0)) {
      const effStun = e.isBoss ? stunSec * 0.5 : stunSec;
      e.stunTimer = Math.max(e.stunTimer, effStun);
    }

    const dxOut = e.mesh.position.x - stageGroup.position.x;
    const dyOut = e.mesh.position.y - stageGroup.position.y;
    const distOut = Math.hypot(dxOut, dyOut) || 1.0;
    const kbResist = (e.roleKey === 'shield_tank' && e.shieldHp > 0) ? 0.25 : 1.0;
    const kb = (e.isBoss ? knockbackForce * 0.28 : knockbackForce) * kbResist * (isCrit ? 1.25 : 1.0);
    e.knockVx = (dxOut / distOut) * kb;
    e.knockVy = (dyOut / distOut) * kb;

    if (e.hpBarMesh) {
      setPillBarValues(
        e.hpBarMesh,
        e.hp / Math.max(1, e.maxHp),
        e.maxShieldHp > 0 ? e.shieldHp / e.maxShieldHp : 0,
        e.shieldHp > 0
      );
    }

    if (shieldAbsorbed && finalDmg === 0) {
      spawnFloatText(`🛡️ 막음`, e.mesh.position, '#38bdf8', 0.85);
    } else {
      spawnFloatText(isCrit ? `💥 CRIT -${finalDmg}!` : `-${finalDmg}`, e.mesh.position, isCrit ? '#facc15' : '#ffffff', isCrit ? 1.12 : 0.90);
    }
    spawnParticleBurst(e.mesh.position, shieldAbsorbed ? 0x38bdf8 : (isCrit ? 0xfacc15 : 0xf43f5e), isCrit ? 8 : 5, 1.0);

    // 4. Boss Phase 2 Enrage at <=50% HP
    if (e.isBoss && !e.phase2Triggered && e.hp <= e.maxHp * 0.50 && e.hp > 0) {
      e.phase2Triggered = true;
      e.enrageRoarTimer = 1.10;
      e.speed *= 1.22;
      e.atk = Math.round(e.atk * 1.26);
      e.shieldHp = Math.round(e.maxHp * 0.22);
      e.maxShieldHp = e.shieldHp;
      if (e.hpBarMesh) {
        setPillBarValues(e.hpBarMesh, e.hp / Math.max(1, e.maxHp), 1.0, true);
      }
      if (e.shieldMesh) e.shieldMesh.visible = true;
      spawnShockwaveRing(e.mesh.position, 0xf43f5e, 2.8);
      triggerChronicleStoryBanner('boss_phase2', combatState.wave, e);
    }

    if (e.hp <= 0) {
      const luckMult = combatState.luckBuffTimer > 0 ? 2 : 1;
      const goldReward = (e.isBoss ? 140 : 18 + combatState.wave * 3) * luckMult;
      const xpReward = e.isBoss ? 95 : 18;
      const coreDrop = (e.isBoss ? 3 : 1) * luckMult;
      const lootSpec = e.lootSpec || { name: '침입자 마력 핵', icon: '💎', tier: 'Common' };

      rpgState.gold = (rpgState.gold || 0) + goldReward;
      e.pendingIncomingDmg = 0;
      spawnFloatText(`+${goldReward}G · ${lootSpec.icon}${lootSpec.name}`, e.mesh.position, '#4ade80', 1.0);
      spawnShockwaveRing(e.mesh.position, e.isBoss ? 0xfacc15 : 0x4ade80, e.isBoss ? 2.1 : 1.25);

      if (typeof window.emitPpongSync === 'function') {
        window.emitPpongSync({
          type: 'enemy_defeated',
          archetype: e.archetype,
          isBoss: e.isBoss,
          goldReward,
          xpReward,
          coreDrop,
          lootName: lootSpec.name,
          lootIcon: lootSpec.icon,
          lootTier: lootSpec.tier,
        });
      }

      if (combatState.telemetry && combatState.telemetry.killsBySource) {
        combatState.telemetry.killsBySource[sourceKey] = (combatState.telemetry.killsBySource[sourceKey] || 0) + 1;
      }
      if (combatState.lockedTarget === e) combatState.lockedTarget = null;
      e.dyingTimer = 0.78;
      e.pendingAttackHit = false;
      setEnemyAnimState(e, 'DEATH', 0.08);
    }
  }

  function checkWaveOrSkirmishVictory() {
    const aliveCount = activeEnemies.filter((en) => en.dyingTimer < 0).length;
    if (combatState.enemiesToSpawn <= 0 && aliveCount === 0) {
      if (combatState.mode === 'SKIRMISH') finishSkirmishVictory();
      else if (combatState.mode === 'WAVE_DEFENSE') finishWaveDefense(true);
    }
  }

  // ===========================================================================
  // 8. Weapon, Turret & Enemy Projectiles (Cached Shared Materials)
  // ===========================================================================
  let projMatPool = null;

  function getProjMatPool() {
    if (projMatPool) return projMatPool;
    projMatPool = {
      arrowShaft: makeDefenseSatinMetalMat({ color: 0xfde047, emissive: 0xca8a04, emissiveIntensity: 0.45 }),
      arrowHead: makeDefenseCrystalMat({ color: 0x4ade80, emissive: 0x22c55e, emissiveIntensity: 0.85, opacity: 0.96 }),
      arrowFeather: makeSoftVinylMat({ color: 0xffffff, sssColor: 0xe0f2fe, rimColor: 0xbae6fd }),
      frostCore: makeDefenseCrystalMat({ color: 0x7dd3fc, emissive: 0x0ea5e9, emissiveIntensity: 0.72, opacity: 0.92 }),
      frostHalo: makeAdditiveHaloMat(0x38bdf8, 0.56, 1.9),
      plasmaCore: makeDefenseCrystalMat({ color: 0xfb923c, emissive: 0xea580c, emissiveIntensity: 0.85, opacity: 0.95 }),
      plasmaHalo: makeAdditiveHaloMat(0xf97316, 0.62, 1.8),
      cannonCore: makeDefenseSatinMetalMat({ color: 0x334155, roughness: 0.34, metalness: 0.68, emissive: 0xf97316, emissiveIntensity: 0.45 }),
      cannonHalo: makeAdditiveHaloMat(0xf97316, 0.58, 2.0),
      bulletCore: new THREE.MeshStandardMaterial({ color: 0xfda4af, emissive: 0xf43f5e, emissiveIntensity: 1.15, roughness: 0.22, metalness: 0.3 }),
      starComet: makeDefenseCrystalMat({ color: 0xfde047, emissive: 0xf59e0b, emissiveIntensity: 0.85, opacity: 0.96 }),
      starCometHalo: makeAdditiveHaloMat(0xfef08a, 0.64, 1.7),
      enemyBoltCore: makeDefenseCrystalMat({ color: 0xd8b4fe, emissive: 0x9333ea, emissiveIntensity: 0.88, opacity: 0.95 }),
      enemyBoltHalo: makeAdditiveHaloMat(0xc084fc, 0.62, 1.8),
    };
    return projMatPool;
  }

  function makeSharedProjMesh(geo, mat, scale = 1.0) {
    const m = new THREE.Mesh(geo, mat);
    if (scale !== 1.0) m.scale.setScalar(scale);
    m.userData.sharedGeo = true;
    m.userData.sharedMat = true;
    return m;
  }

  function spawnBowArrowProjectile(startPos, targetEnemy, dmg, isCrit, armorPen = 0.20, sourceKey = 'hero') {
    const pm = getProjMatPool();
    const arrowGroup = new THREE.Group();
    arrowGroup.add(
      makeSharedProjMesh(SHARED_GEO.arrowShaft, pm.arrowShaft),
      makeSharedProjMesh(SHARED_GEO.arrowHead, pm.arrowHead),
      makeSharedProjMesh(SHARED_GEO.arrowFeather, pm.arrowFeather)
    );
    arrowGroup.position.copy(startPos);
    projectilesGroup.add(arrowGroup);

    const dist = Math.hypot(targetEnemy.mesh.position.x - startPos.x, targetEnemy.mesh.position.y - startPos.y);
    targetEnemy.pendingIncomingDmg = Math.max(0, (targetEnemy.pendingIncomingDmg || 0)) + dmg * 0.75;
    activeProjectiles.push({
      isParabolicArrow: true,
      mesh: arrowGroup,
      startPos: startPos.clone(),
      target: targetEnemy,
      lastX: targetEnemy.mesh.position.x,
      lastY: targetEnemy.mesh.position.y,
      elapsed: 0,
      duration: Math.max(0.20, Math.min(0.55, dist / 14.0)),
      arcHeight: Math.min(1.1, dist * 0.14),
      dmg,
      pendingContrib: dmg * 0.75,
      isCrit,
      slowSec: 0,
      knockback: WEAPON_SPECS.bow.knockback,
      armorPen,
      sourceKey,
    });
  }

  function spawnGunBulletProjectile(startPos, targetEnemy, dmg, isCrit, isExplosiveThirdShot = false, slowSec = 0, armorPen = 0.35, sourceKey = 'hero', splashRadius = 1.65, stunOverride = 0, extraFlags = null) {
    const pm = getProjMatPool();
    let projObj;
    if (sourceKey === 'cannon') {
      projObj = new THREE.Group();
      projObj.add(
        makeSharedProjMesh(SHARED_GEO.cannonShell, pm.cannonCore),
        makeSharedProjMesh(SHARED_GEO.cannonHalo, pm.cannonHalo)
      );
    } else if (slowSec > 0) {
      projObj = new THREE.Group();
      projObj.add(
        makeSharedProjMesh(SHARED_GEO.frostOrb, pm.frostCore),
        makeSharedProjMesh(SHARED_GEO.cannonHalo, pm.frostHalo, 0.85)
      );
    } else if (isExplosiveThirdShot) {
      projObj = new THREE.Group();
      projObj.add(
        makeSharedProjMesh(SHARED_GEO.plasmaOrb, pm.plasmaCore),
        makeSharedProjMesh(SHARED_GEO.cannonHalo, pm.plasmaHalo, 0.78)
      );
    } else {
      projObj = makeSharedProjMesh(SHARED_GEO.bulletTracer, pm.bulletCore);
    }
    projObj.position.copy(startPos);
    projObj.lookAt(targetEnemy.mesh.position.x, targetEnemy.mesh.position.y + 0.65, 0.12);
    projectilesGroup.add(projObj);

    targetEnemy.pendingIncomingDmg = Math.max(0, (targetEnemy.pendingIncomingDmg || 0)) + dmg * 0.75;
    activeProjectiles.push({
      isParabolicArrow: false,
      isExplosive: isExplosiveThirdShot,
      isFrostSplash: slowSec > 0,
      isCannon: sourceKey === 'cannon',
      splashRadius,
      mesh: projObj,
      target: targetEnemy,
      lastX: targetEnemy.mesh.position.x,
      lastY: targetEnemy.mesh.position.y,
      speed: slowSec > 0 ? 12.5 : (isExplosiveThirdShot ? 14.5 : 21.0),
      dmg,
      pendingContrib: dmg * 0.75,
      isCrit,
      slowSec,
      stunSec: stunOverride > 0 ? stunOverride : (isExplosiveThirdShot ? 0.45 : 0),
      knockback: WEAPON_SPECS.gun.knockback,
      armorPen,
      sourceKey,
      extraFlags,
    });
  }

  function spawnPartnerStarProjectile(startPos, targetEnemy, dmg) {
    const pm = getProjMatPool();
    const g = new THREE.Group();
    g.add(
      makeSharedProjMesh(SHARED_GEO.starComet, pm.starComet, 1.15),
      makeSharedProjMesh(SHARED_GEO.cannonHalo, pm.starCometHalo, 1.05)
    );
    g.position.copy(startPos);
    projectilesGroup.add(g);
    targetEnemy.pendingIncomingDmg = Math.max(0, (targetEnemy.pendingIncomingDmg || 0)) + dmg * 0.70;
    activeProjectiles.push({
      isParabolicArrow: false,
      isExplosive: false,
      isFrostSplash: false,
      isStar: true,
      mesh: g,
      target: targetEnemy,
      lastX: targetEnemy.mesh.position.x,
      lastY: targetEnemy.mesh.position.y,
      speed: 14.5,
      dmg,
      pendingContrib: dmg * 0.70,
      isCrit: Math.random() < (getTypingLevelInfo().critChance || 0.22),
      slowSec: 0.6,
      stunSec: 0,
      knockback: 0.42,
      armorPen: 0.25,
      sourceKey: 'partner',
    });
  }

  function spawnSniperBeamVFX(startPos, endPos) {
    const p1 = new THREE.Vector3(startPos.x, startPos.y + 0.55, 0.22);
    const p2 = new THREE.Vector3(endPos.x, endPos.y + 0.65, 0.22);
    spawnRibbonSegment(p1, p2, 0xe879f9, 0.42, 0.30, true);
    spawnParticleBurst(endPos, 0xf0abfc, 4, 1.0);
  }

  function spawnEnemyMagicProjectile(startPos, targetPos, targetType, dmg) {
    const pm = getProjMatPool();
    const g = new THREE.Group();
    g.add(
      makeSharedProjMesh(SHARED_GEO.enemyBolt, pm.enemyBoltCore),
      makeSharedProjMesh(SHARED_GEO.cannonHalo, pm.enemyBoltHalo, 0.85)
    );
    g.position.set(startPos.x, startPos.y + 0.85, 0.16);
    projectilesGroup.add(g);
    activeEnemyProjectiles.push({
      mesh: g,
      targetType,
      targetX: targetPos.x,
      targetY: targetPos.y + 0.5,
      speed: 7.5,
      dmg,
    });
  }

  // ===========================================================================
  // 9. Public Actions, Tactical Skills [Q/W/E] & Mode Transitions
  // ===========================================================================
  let sharedMeteorMats = null;
  function getSharedMeteorMats() {
    if (sharedMeteorMats) return sharedMeteorMats;
    const rockMat = new THREE.MeshStandardMaterial({
      color: 0x3b180e,
      emissive: 0xea580c,
      emissiveIntensity: 0.65,
      roughness: 0.58,
      metalness: 0.12,
    });
    rockMat.customProgramCacheKey = () => 'def_meteor_rock_v1';
    rockMat.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader.replace(
        '#include <common>',
        `#include <common>\nvarying vec3 vLocalPos;`
      ).replace(
        '#include <begin_vertex>',
        `#include <begin_vertex>\nvLocalPos = position;`
      );
      shader.fragmentShader = shader.fragmentShader.replace(
        '#include <common>',
        `#include <common>\nvarying vec3 vLocalPos;`
      ).replace(
        '#include <tonemapping_fragment>',
        `float crack = smoothstep(0.55, 0.92, abs(sin(vLocalPos.x * 16.0 + vLocalPos.y * 13.0) * cos(vLocalPos.z * 15.0 - vLocalPos.y * 11.0)));
         gl_FragColor.rgb += vec3(1.15, 0.42, 0.08) * crack;
         #include <tonemapping_fragment>`
      );
    };
    const coreMat = new THREE.MeshBasicMaterial({ color: 0xfef08a, toneMapped: false });
    const haloMat = makeAdditiveHaloMat(0xf97316, 0.72, 1.85);
    sharedMeteorMats = { rockMat, coreMat, haloMat };
    return sharedMeteorMats;
  }

  function spawnMeteorBarrage(count = 4) {
    const { xMin, xMax, yMin, yMax, baseX, baseY } = getDesktopWorldBounds();
    const alive = activeEnemies.filter((en) => en.dyingTimer < 0);
    const mats = getSharedMeteorMats();
    for (let i = 0; i < count; i++) {
      const te = alive.length > 0 ? alive[i % alive.length] : null;
      let tx, ty;
      if (te) {
        const dxB = baseX - te.mesh.position.x;
        const dyB = baseY - te.mesh.position.y;
        const dB = Math.max(0.1, Math.hypot(dxB, dyB));
        const leadDist = (te.stunTimer > 0 ? 0 : (te.speed || 1.3)) * 0.55;
        const scatterA = i * 2.1;
        const scatterR = i >= alive.length ? 0.55 : 0.15;
        tx = THREE.MathUtils.clamp(te.mesh.position.x + (dxB / dB) * leadDist + Math.cos(scatterA) * scatterR, xMin + 0.8, xMax - 0.8);
        ty = THREE.MathUtils.clamp(te.mesh.position.y + (dyB / dB) * leadDist + Math.sin(scatterA) * scatterR, yMin + 0.6, yMax - 0.8);
      } else {
        tx = THREE.MathUtils.lerp(xMin * 0.3, xMax * 0.8, Math.random());
        ty = THREE.MathUtils.lerp(yMin * 0.4, yMax * 0.6, Math.random());
      }
      const mGroup = new THREE.Group();
      const rockMesh = makeSharedProjMesh(SHARED_GEO.meteorRock, mats.rockMat);
      const coreMesh = makeSharedProjMesh(SHARED_GEO.meteorCore, mats.coreMat);
      const haloMesh = makeSharedProjMesh(SHARED_GEO.meteorHalo, mats.haloMat);
      mGroup.add(rockMesh, coreMesh, haloMesh);
      mGroup.position.set(tx - 1.5, yMax + 1.2 + i * 0.72, 0.1);
      projectilesGroup.add(mGroup);
      activeMeteors.push({ mesh: mGroup, sharedMats: true, targetX: tx, targetY: ty, speed: 10.4, trailCd: 0.02 });
    }
  }

  function syncStatsFromRpgState() {
    const tInfo = getTypingLevelInfo();
    const lv = Math.max(1, tInfo.level || rpgState.petLevel || 1);
    rpgState.petLevel = lv;
    const enh = Math.max(0, rpgState.weaponEnhance || 0);
    const tier = enh >= 10 ? 4 : enh >= 7 ? 3 : enh >= 3 ? 2 : 1;
    rpgState.weaponTier = tier;

    const wepSpec = WEAPON_SPECS[rpgState.equippedWeapon] || WEAPON_SPECS.fist;
    const baseWep = 6 + tier * 4;
    const feverMult = tInfo.feverActive ? 1.12 : 1.0;
    combatState.heroAtk = Math.round((10 + 4 * lv + baseWep * (1 + 0.13 * enh)) * wepSpec.atkMult * tInfo.atkMult * feverMult);
    combatState.heroMaxHp = Math.round(240 + 55 * lv + enh * 25 + (rpgState.turrets.barricade || 0) * 140);
    combatState.partnerAtk = Math.round(combatState.heroAtk * 0.78);
    combatState.partnerMaxHp = Math.round(combatState.heroMaxHp * 0.85 + Math.max(0, lv - 1) * 35);
    combatState.baseMaxHp = Math.round(750 + 85 * lv + (rpgState.turrets.barricade || 0) * 260);

    const levelApsBonus = (lv - 1) * 0.025 + enh * 0.015;
    combatState.heroAps = (0.58 + Math.min(0.42, levelApsBonus)) * wepSpec.apsMult * (tInfo.cpmHasteMult || 1.0);

    if (combatState.mode !== 'PEACE') {
      rebuildHeroWeapon();
      refreshTurretMeshesVisibility();
    }
    if (combatState.mode === 'SKIRMISH' || combatState.mode === 'WAVE_DEFENSE') {
      const wepType = rpgState.equippedWeapon || 'fist';
      if (heroRightHandGroup) heroRightHandGroup.visible = true;
      if (heroLeftHandGroup) heroLeftHandGroup.visible = (wepType === 'fist' || wepType === 'bow');
      if (heroBackQuiverGroup) heroBackQuiverGroup.visible = (wepType === 'bow');
    }
  }

  function setWeaponType(wepKey) {
    if (!WEAPON_SPECS[wepKey]) return false;
    const unlocked = Array.isArray(rpgState.unlockedWeapons) && rpgState.unlockedWeapons.length > 0
      ? rpgState.unlockedWeapons
      : ['fist'];
    if (!unlocked.includes(wepKey)) {
      showLiveCoachingToast(`🔒 [${WEAPON_SPECS[wepKey].name}] 미해금! 적 처치 또는 사령부에서 해금하세요.`);
      return false;
    }
    rpgState.equippedWeapon = wepKey;
    syncStatsFromRpgState();
    spawnFloatText(`⚔️ 무장: ${WEAPON_SPECS[wepKey].name}`, stageGroup.position, '#fde047', 1.1);
    if (typeof window.emitPpongSync === 'function') {
      window.emitPpongSync({ type: 'weapon_equipped', weapon: wepKey });
    }
    updateTacticalHudVisibility(combatState.mode === 'SKIRMISH' || combatState.mode === 'WAVE_DEFENSE');
    return true;
  }

  function tryUseBattleQuickItem(itemKey) {
    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return false;
    const cnt = parseInt((rpgState.consumables && rpgState.consumables[itemKey]) || 0, 10);
    if (cnt <= 0) {
      showLiveCoachingToast('⚠️ 보유한 비약/포션이 없습니다! 사령부 가방에서 연성하세요.');
      return false;
    }
    rpgState.consumables[itemKey] = Math.max(0, cnt - 1);
    useConsumableItem(itemKey);
    if (typeof window.emitPpongSync === 'function') {
      window.emitPpongSync({ type: 'consumable_used_in_js', itemKey });
    }
    updateTacticalHudVisibility(true);
    return true;
  }

  function retreatFromDefense() {
    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return false;
    stopCombatAndDefense();
    if (typeof window.emitPpongSync === 'function') {
      window.emitPpongSync({ type: 'defeat_action', action: 'close', wave: combatState.wave || 1 });
    }
    return true;
  }

  function triggerTacticalSkill(skillKey) {
    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return false;
    const key = String(skillKey || '').toUpperCase();
    const heroPos = stageGroup.position.clone();
    const tInfo = getTypingLevelInfo();
    const cdMult = tInfo.skillCdMult || 1.0;

    if (key === 'Q') {
      if (combatState.skillCdQ > 0) return false;
      combatState.skillCdQ = Number((18.0 * cdMult).toFixed(1));
      if (combatState.telemetry?.skillsUsed) combatState.telemetry.skillsUsed.Q += 1;
      const count = combatState.overdriveTimer > 0 ? 5 : 4;
      spawnFloatText(`☄️ 합동 유성우 폭격 (${count}발)!!`, heroPos, '#f97316', 1.25);
      spawnMeteorBarrage(count);
      // Dual-Hero Synergy [Q]: Partner launches 3 Star-Comets!
      if (partnerStageGroup?.visible && combatState.partnerHp > 0 && activeEnemies.length > 0) {
        const alive = activeEnemies.filter((en) => en.dyingTimer < 0);
        for (let k = 0; k < Math.min(3, alive.length); k++) {
          spawnPartnerStarProjectile(partnerStageGroup.position.clone(), alive[k % alive.length], combatState.partnerAtk * 1.45);
        }
        spawnShockwaveRing(partnerStageGroup.position, 0xfde047, 1.5);
      }
      updateTacticalHudVisibility(true);
      return true;
    }

    if (key === 'W') {
      if (combatState.skillCdW > 0) return false;
      combatState.skillCdW = Number((15.0 * cdMult).toFixed(1));
      if (combatState.telemetry?.skillsUsed) combatState.telemetry.skillsUsed.W += 1;
      combatState.shieldBuffTimer = Math.max(combatState.shieldBuffTimer, 5.5);
      const healBase = Math.round(combatState.baseMaxHp * 0.15);
      combatState.baseHp = Math.min(combatState.baseMaxHp, combatState.baseHp + healBase);
      combatState.heroHp = Math.min(combatState.heroMaxHp, combatState.heroHp + 90);
      if (partnerStageGroup?.visible && combatState.partnerHp > 0) {
        combatState.partnerHp = Math.min(combatState.partnerMaxHp, combatState.partnerHp + 120);
        spawnShockwaveRing(partnerStageGroup.position, 0x4ade80, 2.2);
        spawnFloatText(`🌟 ${PARTNER_NAME_KR} 별빛 개화 +120HP!`, partnerStageGroup.position, '#4ade80', 1.05);
      }
      if (towerHpBar) setPillBarValues(towerHpBar, combatState.baseHp / Math.max(1, combatState.baseMaxHp));
      spawnShockwaveRing(defenseTowerGroup.position, 0x38bdf8, 2.5);
      spawnFloatText(`🛡️ 성소 절대방어막 + 수리 +${healBase}!`, defenseTowerGroup.position, '#38bdf8', 1.15);
      updateTacticalHudVisibility(true);
      return true;
    }

    if (key === 'E') {
      if (combatState.skillCdE > 0) return false;
      combatState.skillCdE = Number((22.0 * cdMult).toFixed(1));
      if (combatState.telemetry?.skillsUsed) combatState.telemetry.skillsUsed.E += 1;
      combatState.overdriveTimer = 10.0;
      spawnShockwaveRing(heroPos, 0xfacc15, 2.4);
      spawnFloatText('🔥 합동 거대화 싱크로 오버드라이브!!', heroPos, '#facc15', 1.3);
      if (typeof playAnimation === 'function') playAnimation('HappySpin', { emotion: 'proud' });
      if (partnerStageGroup?.visible && typeof playPartnerAnimation === 'function') playPartnerAnimation('HappySpin');
      updateTacticalHudVisibility(true);
      return true;
    }
    return false;
  }

  function enterDefenseArenaSetup(stageNum) {
    ensureDefenseDomOverlays();
    ensureDefenseTowerBuilt();
    ensureBuildPadsInitialized();
    hideBuildPadPopover();
    hideDefenseDefeatReport();
    rebuildHeroWeapon();
    const { spec: _enterSpec } = getStageBracketInfo(stageNum);
    preloadBracketEnemyAssets(_enterSpec.bracket);
    combatState.wave = stageNum;
    applyDefenseCameraMode(true);
    if (typeof setHeroAnimTimeScale === 'function') setHeroAnimTimeScale(0.88);

    const { baseX, baseY } = getDesktopWorldBounds();
    if (hemiLight) hemiLight.intensity = 1.18;
    if (keyLight) keyLight.intensity = 1.62;
    if (backRimLight) backRimLight.intensity = 0.46;
    if (fillLight) fillLight.intensity = 0.84;
    defenseTowerGroup.position.set(baseX, baseY, -0.15);
    defenseTowerGroup.scale.setScalar(0.40);
    defenseTowerGroup.visible = true;
    padTowersGroup.visible = true;
    refreshTurretMeshesVisibility();
    heroCombatShadow.visible = true;
    heroCombatShadow.scale.setScalar(0.42);

    combatState.heroHp = combatState.heroMaxHp;
    combatState.heroReviveTimer = 0;
    combatState.partnerHp = combatState.partnerMaxHp;
    combatState.partnerReviveTimer = 0;
    combatState.partnerCooldown = 0.4;
    combatState.partnerNovaCd = 3.5;
    combatState.baseHp = combatState.baseMaxHp;
    combatState.overdriveTimer = 0;
    combatState.pendingAttack = null;
    combatState.slashAnimTimer = 0;
    combatState.skillCdQ = 0;
    combatState.skillCdW = 0;
    combatState.skillCdE = 0;
    combatState.telemetry = {
      waveStartMs: Date.now(),
      totalDamageDealt: 0,
      dmgBySource: { hero: 0, partner: 0, ballista: 0, cannon: 0, frost: 0, arc: 0, sniper: 0, skill: 0 },
      killsBySource: { hero: 0, partner: 0, ballista: 0, cannon: 0, frost: 0, arc: 0, sniper: 0, skill: 0 },
      damageTakenBySource: { vanguard: 0, shield_tank: 0, arcane_ranger: 0, support_shaman: 0, boss: 0 },
      baseDmgTaken: 0,
      baseBreaches: [],
      skillsUsed: { Q: 0, W: 0, E: 0 },
      tipsShown: {},
    };
    if (towerHpBar) setPillBarValues(towerHpBar, 1.0);

    characterPivot.position.set(0, 0, 0);
    stageGroup.position.set(baseX + 0.95, baseY + 0.08, 0.0);
    stageGroup.scale.setScalar(0.42);
    if (typeof setStageYawOverride === 'function') setStageYawOverride(0.95);

    if (typeof ensurePartnerRigReady === 'function') ensurePartnerRigReady();
    if (partnerStageGroup && rpgState.dualHeroEnabled !== false) {
      if (partnerPivot) partnerPivot.position.set(0, 0, 0);
      partnerStageGroup.position.set(baseX + 2.35, baseY + 1.45, 0.0);
      partnerStageGroup.rotation.set(0, 0.72, 0);
      partnerStageGroup.scale.setScalar(0.42);
      partnerStageGroup.visible = true;
      partnerCombatShadow.visible = true;
      partnerCombatShadow.position.set(baseX + 2.35, baseY + 1.45, 0.0);
      partnerCombatShadow.scale.setScalar(0.40);
      if (partnerStaffOrb) partnerStaffOrb.visible = true;
      if (partnerAuraRing) partnerAuraRing.visible = true;
    }

    const wepType = rpgState.equippedWeapon || 'fist';
    heroRightHandGroup.visible = true;
    heroLeftHandGroup.visible = (wepType === 'fist' || wepType === 'bow');
    heroBackQuiverGroup.visible = (wepType === 'bow');
    heroRightHandGroup.scale.setScalar(0.46);
    heroLeftHandGroup.scale.setScalar(0.46);
    heroBackQuiverGroup.scale.setScalar(0.46);
    updateTacticalHudVisibility(true);
  }

  function restorePeaceModeSetup() {
    combatState.mode = 'PEACE';
    combatState.overdriveTimer = 0;
    applyDefenseCameraMode(false);
    if (hemiLight) hemiLight.intensity = 1.35;
    if (keyLight) keyLight.intensity = 1.45;
    if (backRimLight) backRimLight.intensity = 0.52;
    if (fillLight) fillLight.intensity = 0.68;
    if (typeof setHeroAnimTimeScale === 'function') setHeroAnimTimeScale(1.0);
    if (typeof setStageYawOverride === 'function') setStageYawOverride(null);

    defenseTowerGroup.visible = false;
    padTowersGroup.visible = false;
    hideBuildPadPopover();
    if (towerShieldDomeMesh) towerShieldDomeMesh.visible = false;
    heroCombatShadow.visible = false;
    partnerCombatShadow.visible = false;
    if (synchroBeamMesh) synchroBeamMesh.visible = false;
    if (partnerStaffOrb) partnerStaffOrb.visible = false;
    if (partnerAuraRing) partnerAuraRing.visible = false;
    if (partnerStageGroup) {
      partnerStageGroup.visible = false;
      partnerStageGroup.position.set(0, 0, 0);
      partnerStageGroup.rotation.set(0, 0, 0);
      partnerStageGroup.scale.setScalar(1.0);
    }
    heroRightHandGroup.visible = false;
    heroLeftHandGroup.visible = false;
    heroBackQuiverGroup.visible = false;
    slashArcMesh.visible = false;
    whirlwindMesh.visible = false;
    excavationGroup.visible = false;

    characterPivot.position.set(0, 0, 0);
    stageGroup.position.set(0, 0, 0);
    stageGroup.rotation.set(0, 0, 0);
    stageGroup.scale.setScalar(1.0);
    hideDefenseStoryBanner();
    updateTacticalHudVisibility(false);
  }

  let combatSessionSeq = 0;

  function hideDefenseStoryBanner() {
    if (storyBannerTimer) {
      clearTimeout(storyBannerTimer);
      storyBannerTimer = null;
    }
    if (typeof document !== 'undefined') {
      const banner = document.getElementById('defense-story-banner');
      if (banner) {
        banner.classList.remove('visible');
        banner.style.opacity = '0';
      }
    }
  }

  function prepareDefenseArena() {
    combatSessionSeq += 1;
    clearAllEnemies();
    combatState.mode = 'PREPARING';
    combatState.enemiesToSpawn = 0;
    combatState.lockedTarget = null;
    combatState.hudThrottleTimer = 0;
    hideDefenseStoryBanner();
    if (typeof document !== 'undefined') {
      const badge = document.getElementById('status-badge');
      if (badge) {
        badge.className = '';
        badge.style.opacity = '0';
      }
    }
    const w = Math.max(1, rpgState.highestWave || 1);
    const { spec } = getStageBracketInfo(w);
    preloadBracketEnemyAssets(spec.bracket);
    return true;
  }

  function startSkirmish() {
    combatSessionSeq += 1;
    const mySeq = combatSessionSeq;
    hideDefenseDefeatReport();
    hideBuildPadPopover();
    clearAllEnemies();
    combatState.bossSpawnedThisWave = false;
    syncStatsFromRpgState();
    const stageNum = Math.max(1, rpgState.highestWave || 1);
    const { spec } = getStageBracketInfo(stageNum);
    const preloadP = preloadBracketEnemyAssets(spec.bracket);
    combatState.mode = 'SKIRMISH';
    enterDefenseArenaSetup(stageNum);

    combatState.enemiesToSpawn = 8;
    combatState.spawnTimer = 0.85 + Math.random() * 1.1;
    triggerChronicleStoryBanner('intro', stageNum);

    Promise.race([
      preloadP,
      new Promise((resolve) => setTimeout(resolve, 220)),
    ]).then(() => {
      if (combatSessionSeq !== mySeq || combatState.mode !== 'SKIRMISH') return;
      if (combatState.enemiesToSpawn > 0) {
        combatState.enemiesToSpawn -= 1;
        spawnDesktopStageEnemy(stageNum, 2, false);
        updateMiniHudBadge(true);
      }
    });

    if (typeof triggerEmotionEmote === 'function') triggerEmotionEmote('excited');
    updateMiniHudBadge(true);
    return true;
  }

  function buildTacticalSpawnQueue(waveNum, totalCount) {
    const q = [];
    const isBossWave = waveNum % 5 === 0;
    const bossIndex = isBossWave ? Math.max(2, Math.floor(totalCount * 0.38)) : -1;
    for (let i = 0; i < totalCount; i++) {
      const squadIdx = Math.floor(i / 4);
      const posInSquad = i % 4;
      const zone = (waveNum + squadIdx) % 4;
      const isBoss = (i === bossIndex);
      let role = null;
      if (!isBoss) {
        if (i === bossIndex - 1 || i === bossIndex + 1) {
          role = i === bossIndex - 1 ? 'shield_tank' : 'support_shaman';
        } else if (posInSquad === 0 && waveNum >= 2) {
          role = 'shield_tank';
        } else if (posInSquad === 2 && waveNum >= 3) {
          role = 'arcane_ranger';
        } else if (posInSquad === 3 && waveNum >= 4 && squadIdx % 2 === 1) {
          role = 'support_shaman';
        } else {
          role = 'vanguard';
        }
      }
      const gap = posInSquad === 3 ? (1.85 + Math.random() * 0.55) : (0.52 + Math.random() * 0.36);
      q.push({ zone, isBoss, role, delayAfter: gap });
    }
    return q;
  }

  function startWaveDefense(waveNumber = 1) {
    combatSessionSeq += 1;
    const mySeq = combatSessionSeq;
    hideDefenseDefeatReport();
    hideBuildPadPopover();
    clearAllEnemies();
    combatState.bossSpawnedThisWave = false;
    syncStatsFromRpgState();
    const w = Math.max(1, parseInt(waveNumber, 10) || 1);
    const tInfo = getTypingLevelInfo();
    if (tInfo.waveStartGoldBonus > 0) {
      rpgState.gold = (rpgState.gold || 0) + tInfo.waveStartGoldBonus;
    }
    const { spec } = getStageBracketInfo(w);
    const preloadP = preloadBracketEnemyAssets(spec.bracket);
    combatState.mode = 'WAVE_DEFENSE';
    enterDefenseArenaSetup(w);

    const totalCount = 24 + (w - 1) * 4;
    combatState.spawnQueue = buildTacticalSpawnQueue(w, totalCount);
    combatState.enemiesToSpawn = combatState.spawnQueue.length;
    combatState.spawnTimer = 0.65;
    combatState.bentoCooldown = 0;
    combatState.heroInvulnTimer = 0;
    combatState.partnerInvulnTimer = 0;

    triggerChronicleStoryBanner('intro', w);

    Promise.race([
      preloadP,
      new Promise((resolve) => setTimeout(resolve, 220)),
    ]).then(() => {
      if (combatSessionSeq !== mySeq || combatState.mode !== 'WAVE_DEFENSE') return;
      if (combatState.spawnQueue.length > 0) {
        const first = combatState.spawnQueue.shift();
        combatState.enemiesToSpawn = combatState.spawnQueue.length;
        spawnDesktopStageEnemy(w, first.zone, first.isBoss, first.role);
        updateMiniHudBadge(true);
      }
    });

    if (typeof triggerEmotionEmote === 'function') triggerEmotionEmote('proud');
    updateMiniHudBadge(true);
    return true;
  }

  function finishSkirmishVictory() {
    combatSessionSeq += 1;
    clearAllEnemies();
    restorePeaceModeSetup();
    triggerChronicleStoryBanner('victory', combatState.wave);
    if (typeof playAnimation === 'function') playAnimation('HappySpin', { durationMs: 2600, emotion: 'proud' });
    updateMiniHudBadge(true);

    if (typeof window.emitPpongSync === 'function') {
      window.emitPpongSync({ type: 'skirmish_victory', bonusGold: 45, bonusXp: 35 });
    }
  }

  function finishWaveDefense(victory) {
    combatSessionSeq += 1;
    const w = combatState.wave;
    const diag = !victory ? buildDefeatDiagnosis() : null;
    clearAllEnemies();
    restorePeaceModeSetup();

    if (victory) {
      if (w >= rpgState.highestWave) rpgState.highestWave = w + 1;
      triggerChronicleStoryBanner('victory', w);
      if (typeof playAnimation === 'function') playAnimation('HappySpin', { durationMs: 3200, emotion: 'proud' });
      const { spec: nextSpec } = getStageBracketInfo(w + 1);
      preloadBracketEnemyAssets(nextSpec.bracket);
    } else {
      showDefenseStoryBanner('💥 성소 방어선 돌파', `STAGE ${w} 방어 실패`, '대장간 무기 강화·포탑 건설·전술 스킬로 다시 도전하세요!', '#ef4444', 4500);
      if (typeof playAnimation === 'function') playAnimation('Sad', { durationMs: 3000, emotion: 'sad' });
      if (diag) openDefenseDefeatReport(diag);
    }
    updateMiniHudBadge(true);

    if (typeof window.emitPpongSync === 'function') {
      const kills = Object.values(combatState.telemetry?.killsBySource || {}).reduce((a, b) => a + (b || 0), 0);
      const consolationGold = Math.min(35, kills * 2);
      const consolationXp = Math.min(20, kills);
      window.emitPpongSync({
        type: 'wave_defense_result',
        victory,
        wave: w,
        goldReward: victory ? 95 + w * 40 : consolationGold,
        xpReward: victory ? 55 + w * 18 : consolationXp,
        coreReward: victory ? (w % 5 === 0 ? 3 : 1) : 0,
        defeatReport: diag,
      });
    }
  }

  function stopCombatAndDefense() {
    combatSessionSeq += 1;
    clearAllEnemies();
    hideDefenseStoryBanner();
    hideDefenseDefeatReport();
    hideBuildPadPopover();
    restorePeaceModeSetup();
    updateMiniHudBadge(true);
  }

  const raycaster = new THREE.Raycaster();
  const screenPlaneMath = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  const rayHitPoint = new THREE.Vector3();
  const ndcVec = new THREE.Vector2();

  function tryHandleBuildPadClick(nx, ny) {
    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return false;
    syncBuildPadsToRpgState();
    ndcVec.set(nx, ny);
    raycaster.setFromCamera(ndcVec, camera);
    const hasHit = raycaster.ray.intersectPlane(screenPlaneMath, rayHitPoint);
    if (!hasHit) return false;

    let bestPad = null;
    let bestDist = 1.25;
    for (let i = 0; i < buildPads.length; i++) {
      const p = buildPads[i];
      const d = Math.hypot(p.group.position.x - rayHitPoint.x, p.group.position.y - rayHitPoint.y);
      if (d <= bestDist) {
        bestDist = d;
        bestPad = p;
      }
    }
    if (bestPad) {
      openBuildPadPopover(bestPad.id);
      return true;
    }
    if (combatState.selectedPadId) {
      hideBuildPadPopover();
    }
    return false;
  }

  function triggerCursorSmite(nx, ny) {
    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return false;

    ndcVec.set(nx, ny);
    raycaster.setFromCamera(ndcVec, camera);
    const hasHit = raycaster.ray.intersectPlane(screenPlaneMath, rayHitPoint);

    // 1. Check if clicking inside a Boss Red Telegraph AoE circle to interrupt it (fast 0.10s debounce so rapid 2-click works!)
    if (hasHit && activeBossTelegraphs.length > 0 && (combatState.telegraphClickCd || 0) <= 0) {
      for (let t = activeBossTelegraphs.length - 1; t >= 0; t--) {
        const bt = activeBossTelegraphs[t];
        const dTel = Math.hypot(bt.mesh.position.x - rayHitPoint.x, bt.mesh.position.y - rayHitPoint.y);
        if (dTel <= bt.radius * 1.25) {
          combatState.telegraphClickCd = 0.10;
          bt.smiteHits += 1;
          if (bt.mat?.uniforms?.uSmiteRatio) {
            bt.mat.uniforms.uSmiteRatio.value = Math.min(1.0, bt.smiteHits / 2);
          }
          spawnShockwaveRing(bt.mesh.position, 0x38bdf8, 1.5);
          if (bt.smiteHits >= 2) {
            triggerCameraShake(0.16);
            spawnFloatText('💥 보스 패턴 차단!! (STUN)', bt.mesh.position, '#38bdf8', 1.25);
            if (bt.caster) bt.caster.stunTimer = Math.max(bt.caster.stunTimer, 1.4);
            projectilesGroup.remove(bt.mesh);
            bt.mat?.dispose?.();
            activeBossTelegraphs.splice(t, 1);
            return true;
          }
          spawnFloatText('⚡ 패턴 저지 (1/2)! 한 번 더 클릭!', bt.mesh.position, '#facc15', 1.0);
          return true;
        }
      }
    }

    if (combatState.smiteCooldown > 0) return false;
    if (activeEnemies.length === 0) return false;
    let bestIdx = -1;
    let bestDist = 2.65;
    for (let i = 0; i < activeEnemies.length; i++) {
      const e = activeEnemies[i];
      if (e.dyingTimer >= 0) continue;
      const d = hasHit ? Math.hypot(e.mesh.position.x - rayHitPoint.x, e.mesh.position.y - rayHitPoint.y) : 0;
      if (d <= bestDist) {
        bestDist = d;
        bestIdx = i;
      }
    }

    if (bestIdx === -1) {
      if (hasHit) spawnShockwaveRing(rayHitPoint, 0x94a3b8, 0.55);
      return false;
    }
    combatState.smiteCooldown = 0.55;
    const target = activeEnemies[bestIdx];
    const smiteOrigin = target.mesh.position;
    const skyOrigin = { x: smiteOrigin.x, y: smiteOrigin.y + 3.2 };
    const hitCenter = { x: smiteOrigin.x, y: smiteOrigin.y + 0.55 };
    const tInfo = getTypingLevelInfo();
    const isCrit = Math.random() < (tInfo.critChance || 0.20);
    const smiteDmg = Math.max(8, Math.round(combatState.heroAtk * 0.56 * (isCrit ? (tInfo.critMult || 1.35) : 1.0)));
    spawnRibbonSegment(skyOrigin, hitCenter, 0xfde047, 0.34, 0.22, true);
    spawnShockwaveRing(smiteOrigin, 0xfacc15, 1.35);
    spawnParticleBurst(smiteOrigin, 0xfef08a, 8, 1.2);
    damageEnemy(bestIdx, smiteDmg, isCrit, 0, 0.25, 0.45, 0.25, 'hero');
    return true;
  }

  function useConsumableItem(itemKey) {
    const heroPos = stageGroup.position.clone();
    if (itemKey === 'hp_potion') {
      combatState.heroHp = Math.min(combatState.heroMaxHp, combatState.heroHp + 220);
      combatState.partnerHp = Math.min(combatState.partnerMaxHp, combatState.partnerHp + 180);
      combatState.baseHp = Math.min(combatState.baseMaxHp, combatState.baseHp + 150);
      if (towerHpBar) setPillBarValues(towerHpBar, combatState.baseHp / Math.max(1, combatState.baseMaxHp));
      spawnShockwaveRing(heroPos, 0x4ade80, 1.6);
      spawnFloatText('🧪 생명 포션! 영웅·동료·성소 회복', heroPos, '#4ade80', 1.1);
      return true;
    }
    if (itemKey === 'haste_elixir') {
      combatState.hasteBuffTimer = 25.0;
      spawnShockwaveRing(heroPos, 0x38bdf8, 1.7);
      spawnFloatText('⚡ 질풍 비약! 공속·이속 +50%', heroPos, '#38bdf8', 1.1);
      return true;
    }
    if (itemKey === 'rage_elixir') {
      combatState.rageBuffTimer = 25.0;
      spawnShockwaveRing(heroPos, 0xf43f5e, 1.7);
      spawnFloatText('🔥 광전사 비약! 영웅·포탑 공격력 +65%', heroPos, '#f43f5e', 1.1);
      return true;
    }
    if (itemKey === 'shield_scroll') {
      combatState.heroHp = combatState.heroMaxHp;
      combatState.partnerHp = combatState.partnerMaxHp;
      combatState.baseHp = Math.min(combatState.baseMaxHp, combatState.baseHp + 350);
      if (towerHpBar) setPillBarValues(towerHpBar, combatState.baseHp / Math.max(1, combatState.baseMaxHp));
      combatState.shieldBuffTimer = 12.0;
      spawnShockwaveRing(heroPos, 0x38bdf8, 2.0);
      spawnFloatText('🛡️ 절대방어! 12초 무적 & 성소+350!', heroPos, '#38bdf8', 1.15);
      return true;
    }
    if (itemKey === 'luck_potion') {
      combatState.luckBuffTimer = 45.0;
      spawnShockwaveRing(heroPos, 0xfacc15, 1.7);
      spawnFloatText('🍀 황금 행운! 45초간 보상 2배!', heroPos, '#facc15', 1.1);
      return true;
    }
    if (itemKey === 'meteor_scroll') {
      spawnFloatText('☄️ 메테오 주문서 6연속 폭격!!', heroPos, '#f97316', 1.25);
      spawnMeteorBarrage(6);
      return true;
    }
    return false;
  }

  function tryConsumeBattleBento() {
    if ((combatState.bentoCooldown || 0) > 0) return false;
    const order = [
      { key: 'star_emperor', name: '🍱 별빛 황제 도시락', heal: 500, atk: 1.45, spd: 1.25 },
      { key: 'carp_stew', name: '🍲 황금 잉어 매운탕', heal: 280, atk: 1.35, spd: 1.18 },
      { key: 'trout_steak', name: '🍣 무지개 송어 스테이크', heal: 180, atk: 1.20, spd: 1.20 },
      { key: 'potato_fish', name: '🥔 감자 생선구이', heal: 120, atk: 1.12, spd: 1.10 },
    ];
    for (const item of order) {
      if ((rpgState.bentos[item.key] || 0) > 0) {
        rpgState.bentos[item.key] -= 1;
        combatState.bentoCooldown = 8.0;
        combatState.heroHp = Math.min(combatState.heroMaxHp, combatState.heroHp + item.heal);
        combatState.partnerHp = Math.min(combatState.partnerMaxHp, combatState.partnerHp + Math.round(item.heal * 0.8));
        combatState.bentoBuffTimer = 18.0;
        combatState.bentoAtkMult = item.atk;
        combatState.bentoSpdMult = item.spd;
        spawnFloatText(`${item.name} 섭취! (HP+${item.heal})`, stageGroup.position, '#facc15', 1.1);
        spawnShockwaveRing(stageGroup.position, 0xfacc15, 1.6);
        if (typeof window.emitPpongSync === 'function') window.emitPpongSync({ type: 'bento_consumed', bentoKey: item.key });
        return true;
      }
    }
    return false;
  }

  function applyWorldviewTheme(themeKey, silent = false) {
    const t = WORLDVIEW_THEMES[themeKey] || WORLDVIEW_THEMES.fantasy;
    rpgState.worldview = t.key;
    if (hemiLight) {
      hemiLight.color.setHex(t.hemiSky);
      hemiLight.groundColor.setHex(t.hemiGround);
    }
    if (keyLight) keyLight.color.setHex(t.keyColor);
    if (backRimLight) backRimLight.color.setHex(t.rimColor);
    if (fillLight && t.fillColor) fillLight.color.setHex(t.fillColor);
    if (combatState.mode !== 'PEACE') {
      rebuildHeroWeapon();
    }
    if (!silent) {
      spawnFloatText(`🌌 세계관: ${t.name}`, stageGroup.position, '#38bdf8', 1.1);
    }
    return t.key;
  }

  function updateMiniHudBadge(force = false) {
    if (!force && combatState.hudThrottleTimer > 0) return;
    combatState.hudThrottleTimer = 0.25;
    const badge = document.getElementById('status-badge');
    if (badge) {
      badge.className = '';
      badge.style.opacity = '0';
    }
    const inCombat = combatState.mode === 'WAVE_DEFENSE' || combatState.mode === 'SKIRMISH';
    updateTacticalHudVisibility(inCombat);
  }

  function syncTypingHudPulse(typingStats) {
    if (!typingStats || typeof typingStats !== 'object') return false;
    rpgState.typingStats = Object.assign({}, rpgState.typingStats || {}, typingStats);
    syncStatsFromRpgState();
    prevHudSnap = null;
    updateTacticalHudVisibility(combatState.mode === 'WAVE_DEFENSE' || combatState.mode === 'SKIRMISH');
    return true;
  }

  function syncRPGStateFromPython(newState) {
    if (!newState || typeof newState !== 'object') return;
    const prevWv = rpgState.worldview;
    const prevEnh = rpgState.weaponEnhance;
    const prevWep = rpgState.equippedWeapon;
    Object.assign(rpgState, newState);
    if (newState.turrets) Object.assign(rpgState.turrets, newState.turrets);
    if (newState.bentos) Object.assign(rpgState.bentos, newState.bentos);
    if (newState.consumables) Object.assign(rpgState.consumables, newState.consumables);
    if (newState.farm) Object.assign(rpgState.farm, newState.farm);
    if (newState.typingStats) rpgState.typingStats = Object.assign({}, rpgState.typingStats || {}, newState.typingStats);
    if (newState.towerPads && typeof newState.towerPads === 'object') {
      const nextPads = {};
      PAD_SLOT_SPECS.forEach((slot) => {
        const v = newState.towerPads[slot.id];
        nextPads[slot.id] = (v && typeof v === 'object' && v.type)
          ? { type: v.type, level: Math.max(1, Math.min(5, parseInt(v.level || 1, 10) || 1)) }
          : { type: null, level: 0 };
      });
      rpgState.towerPads = nextPads;
    }

    syncStatsFromRpgState();
    syncBuildPadsToRpgState();

    if (newState.worldview && newState.worldview !== prevWv) {
      applyWorldviewTheme(newState.worldview, true);
    } else if (combatState.mode !== 'PEACE' && (newState.weaponEnhance !== prevEnh || newState.equippedWeapon !== prevWep)) {
      rebuildHeroWeapon();
    }
  }

  if (typeof window !== 'undefined' && !window.__ppongDefenseKeysBound) {
    window.__ppongDefenseKeysBound = true;
    window.addEventListener('keydown', (e) => {
      if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return;
      if (e.key === 'Escape') {
        if (combatState.selectedPadId) hideBuildPadPopover();
        else retreatFromDefense();
        return;
      }
      const k = e.key.toUpperCase();
      if (k === 'Q' || k === 'W' || k === 'E') triggerTacticalSkill(k);
      else if (e.key === '1') setWeaponType('fist');
      else if (e.key === '2') setWeaponType('sword');
      else if (e.key === '3') setWeaponType('bow');
      else if (e.key === '4') setWeaponType('gun');
      else if (e.key === '5') tryUseBattleQuickItem('hp_potion');
      else if (e.key === '6') tryUseBattleQuickItem('haste_elixir');
    });
  }

  // ===========================================================================
  // 10. Main 60 FPS Combat, Turrets, Enemy Projectiles & Boss Telegraph Loop
  // ===========================================================================
  const tmpHandR = new THREE.Vector3();
  const tmpHandL = new THREE.Vector3();
  const tmpChest = new THREE.Vector3();

  function updateWorldRPGDefense(dt, elapsed) {
    if (combatState.hudThrottleTimer > 0) combatState.hudThrottleTimer -= dt;
    if (combatState.smiteCooldown > 0) combatState.smiteCooldown -= dt;
    if (combatState.telegraphClickCd > 0) combatState.telegraphClickCd = Math.max(0, combatState.telegraphClickCd - dt);
    if (combatState.bentoCooldown > 0) combatState.bentoCooldown = Math.max(0, combatState.bentoCooldown - dt);
    if (combatState.heroInvulnTimer > 0) combatState.heroInvulnTimer = Math.max(0, combatState.heroInvulnTimer - dt);
    if (combatState.partnerInvulnTimer > 0) combatState.partnerInvulnTimer = Math.max(0, combatState.partnerInvulnTimer - dt);
    if (combatState.retargetTimer > 0) combatState.retargetTimer = Math.max(0, combatState.retargetTimer - dt);
    if (combatState.skillCdQ > 0) combatState.skillCdQ = Math.max(0, combatState.skillCdQ - dt);
    if (combatState.skillCdW > 0) combatState.skillCdW = Math.max(0, combatState.skillCdW - dt);
    if (combatState.skillCdE > 0) combatState.skillCdE = Math.max(0, combatState.skillCdE - dt);
    if (combatState.overdriveTimer > 0) combatState.overdriveTimer = Math.max(0, combatState.overdriveTimer - dt);
    if (combatState.bentoBuffTimer > 0) {
      combatState.bentoBuffTimer -= dt;
      if (combatState.bentoBuffTimer <= 0) {
        combatState.bentoAtkMult = 1.0;
        combatState.bentoSpdMult = 1.0;
      }
    }
    if (combatState.hasteBuffTimer > 0) combatState.hasteBuffTimer -= dt;
    if (combatState.rageBuffTimer > 0) combatState.rageBuffTimer -= dt;
    if (combatState.luckBuffTimer > 0) combatState.luckBuffTimer -= dt;
    if (combatState.shieldBuffTimer > 0) combatState.shieldBuffTimer -= dt;
    if (combatState.camShake > 0) {
      combatState.camShake = Math.max(0, combatState.camShake - dt * 1.45);
      if (camera && (combatState.mode === 'SKIRMISH' || combatState.mode === 'WAVE_DEFENSE')) {
        const s = combatState.camShake;
        camera.position.set(
          DEFENSE_CAMERA_POS.x + (Math.random() - 0.5) * s * 0.45,
          DEFENSE_CAMERA_POS.y + (Math.random() - 0.5) * s * 0.45,
          DEFENSE_CAMERA_POS.z
        );
      }
    } else if (camera && (combatState.mode === 'SKIRMISH' || combatState.mode === 'WAVE_DEFENSE')) {
      camera.position.copy(DEFENSE_CAMERA_POS);
    }
    if (combatState.mode === 'SKIRMISH' || combatState.mode === 'WAVE_DEFENSE') {
      const nowHud = (typeof performance !== 'undefined') ? performance.now() : Date.now();
      if (nowHud - lastHudSyncAt >= 150) {
        updateTacticalHudVisibility(true);
      }
    }

    // 1. Floating Texts (maps cached in floatTextTexCache LRU)
    for (let i = activeFloatTexts.length - 1; i >= 0; i--) {
      const ft = activeFloatTexts[i];
      ft.life += dt;
      const u = ft.life / ft.maxLife;
      if (u >= 1.0) {
        projectilesGroup.remove(ft.sprite);
        ft.sprite.material.dispose();
        activeFloatTexts.splice(i, 1);
        continue;
      }
      ft.sprite.position.y += ft.vy * dt;
      ft.sprite.material.opacity = 1.0 - u * u;
    }

    // 2. Pooled Starburst Particles, SDF Shockwaves & Volumetric Ribbons
    for (let i = activeParticles.length - 1; i >= 0; i--) {
      const p = activeParticles[i];
      p.life += dt;
      const u = p.life / p.maxLife;
      if (u >= 1.0) {
        releasePooledVfxEntry(p);
        activeParticles.splice(i, 1);
        continue;
      }
      if (p.isRibbon) {
        if (p.mesh.material?.uniforms?.uProgress) p.mesh.material.uniforms.uProgress.value = u;
      } else if (p.isLine) {
        p.mesh.material.opacity = 1.0 - u;
      } else if (p.isRing) {
        p.mesh.scale.setScalar(0.35 + u * p.maxScale * 1.15);
        if (p.mesh.material?.uniforms?.uProgress) p.mesh.material.uniforms.uProgress.value = u;
      } else {
        p.mesh.position.x += p.vx * dt;
        p.mesh.position.y += p.vy * dt;
        p.vy -= 2.2 * dt;
        if (p.spin) p.mesh.rotation.z += p.spin * dt;
        p.mesh.material.opacity = 1.0 - u;
      }
    }

    // 3. Volcanic Cracked Meteors (Pooled materials)
    for (let i = activeMeteors.length - 1; i >= 0; i--) {
      const m = activeMeteors[i];
      const dx = m.targetX - m.mesh.position.x;
      const dy = m.targetY - m.mesh.position.y;
      const dist = Math.hypot(dx, dy);
      m.mesh.rotation.x += dt * 7.0;
      m.mesh.rotation.y += dt * 5.0;
      m.trailCd = (m.trailCd || 0) - dt;
      if (m.trailCd <= 0) {
        m.trailCd = 0.055;
        spawnParticleBurst(m.mesh.position, 0xf97316, 1, 0.45);
      }
      if (dist <= m.speed * dt + 0.25) {
        const impactPos = new THREE.Vector3(m.targetX, m.targetY, 0.08);
        spawnShockwaveRing(impactPos, 0xf97316, 2.3);
        spawnParticleBurst(impactPos, 0xfde047, 10, 1.5);
        triggerCameraShake(0.16);
        for (let j = activeEnemies.length - 1; j >= 0; j--) {
          const e = activeEnemies[j];
          if (e.dyingTimer >= 0) continue;
          if (Math.hypot(e.mesh.position.x - m.targetX, e.mesh.position.y - m.targetY) <= 2.35) {
            damageEnemy(j, combatState.heroAtk * 2.4, true, 0, 0.5, 0.85, 0.4, 'skill');
          }
        }
        projectilesGroup.remove(m.mesh);
        if (!m.sharedMats) {
          m.rockMat?.dispose?.();
          m.coreMat?.dispose?.();
          m.haloMat?.dispose?.();
        }
        activeMeteors.splice(i, 1);
      } else {
        m.mesh.position.x += (dx / dist) * m.speed * dt;
        m.mesh.position.y += (dy / dist) * m.speed * dt;
      }
    }

    if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return;

    updateMiniHudBadge(false);
    const { xMin, xMax, yMin, yMax, baseX, baseY } = getDesktopWorldBounds();

    // Anchor Defense Tower & Animate Shield Dome / Crystal
    defenseTowerGroup.position.set(baseX, baseY, -0.15);
    towerSquash += (0 - towerSquash) * Math.min(1, dt * 12.0);
    const tSy = Math.max(0.72, 1.0 + towerSquash);
    const tSxz = 1.0 / Math.sqrt(tSy);
    towerVisualWrap.scale.set(tSxz, tSy, tSxz);

    if (towerCrystalMesh) {
      towerCrystalMesh.position.y = 2.66 + Math.sin(elapsed * 2.6) * 0.08;
      towerCrystalMesh.rotation.y += dt * 1.4;
    }
    if (towerHaloRing) {
      towerHaloRing.position.y = towerCrystalMesh ? towerCrystalMesh.position.y : 2.66;
      towerHaloRing.rotation.x = Math.sin(elapsed * 1.8) * 0.45;
      towerHaloRing.rotation.y += dt * 2.0;
    }
    if (towerOuterRing) {
      towerOuterRing.position.y = towerCrystalMesh ? towerCrystalMesh.position.y : 2.66;
      towerOuterRing.rotation.z = Math.cos(elapsed * 1.4) * 0.35;
      towerOuterRing.rotation.y -= dt * 1.4;
    }
    if (towerLanternHalo) {
      const lp = 0.90 + 0.14 * Math.sin(elapsed * 5.2);
      towerLanternHalo.scale.setScalar(lp);
    }
    if (towerRangeRingMesh && towerRangeRingMesh.material?.uniforms?.uTime) {
      towerRangeRingMesh.material.uniforms.uTime.value = elapsed;
    }
    if (towerShieldDomeMesh) {
      towerShieldDomeMesh.visible = combatState.shieldBuffTimer > 0;
      if (towerShieldDomeMesh.visible) {
        towerShieldDomeMesh.rotation.y += dt * 0.7;
        if (towerShieldDomeMesh.material?.uniforms?.uTime) {
          towerShieldDomeMesh.material.uniforms.uTime.value = elapsed;
        }
      }
    }

    // 4. Desktop 5-Pad Build Grid Turrets Combat AI (Ballista, Cannon, Frost, Arc, Sniper Lv.1~5)
    const aliveEnemies = activeEnemies.filter((en) => en.dyingTimer < 0);
    const tInfoLoop = getTypingLevelInfo();
    const turretSpdBuff = (combatState.hasteBuffTimer > 0 ? 1.5 : 1.0) * (tInfoLoop.towerSpdMult || 1.0) * (tInfoLoop.cpmHasteMult || 1.0);
    const turretAtkBuff = (combatState.rageBuffTimer > 0 ? 1.5 : 1.0) * (tInfoLoop.towerDmgMult || 1.0);
    if (!buildPadsInitialized || combatState._lastBoundsW !== (window.innerWidth || 1920) || combatState._lastBoundsH !== (window.innerHeight || 1080)) {
      combatState._lastBoundsW = window.innerWidth || 1920;
      combatState._lastBoundsH = window.innerHeight || 1080;
      syncBuildPadsToRpgState();
    }

    for (let pi = 0; pi < buildPads.length; pi++) {
      const pad = buildPads[pi];
      if (pad.runeMat?.uniforms?.uTime) pad.runeMat.uniforms.uTime.value = elapsed + pi * 0.7;
      if (pad.beaconGroup && pad.beaconGroup.visible) {
        pad.beaconGroup.rotation.y = elapsed * 1.8 + pi;
        pad.beaconGroup.position.y = 0.24 + Math.sin(elapsed * 3.0 + pi) * 0.05;
      }
      const wantRange = (pad.id === hoveredPadId && !!pad.type) || (pad.id === combatState.selectedPadId && (!!pad.type || (pad.previewRange || 0) > 0));
      pad.rangeAlpha = THREE.MathUtils.lerp(pad.rangeAlpha || 0, wantRange ? 1.0 : 0.0, Math.min(1, dt * 10.0));
      if (pad.rangeField) {
        pad.rangeField.visible = pad.rangeAlpha > 0.02;
        if (pad.rangeField.visible && pad.rangeFieldMat?.uniforms) {
          pad.rangeFieldMat.uniforms.uAlpha.value = pad.rangeAlpha;
          pad.rangeFieldMat.uniforms.uTime.value = elapsed;
        }
      }
      if (pad.orbMesh) {
        pad.orbMesh.rotation.y = elapsed * 2.2 + pi;
        pad.orbMesh.position.y = (pad.type === 'arc' ? 0.92 : 0.74) + Math.sin(elapsed * 3.4 + pi) * 0.04;
      }
      if (pad.orbitGroup) pad.orbitGroup.rotation.y -= dt * 2.1;
      if (pad.crownGroup) {
        pad.crownGroup.rotation.y += dt * 1.5;
        pad.crownGroup.position.y = (pad.type === 'sniper' || pad.type === 'arc' ? 1.18 : 1.02) + Math.sin(elapsed * 2.6 + pi) * 0.035;
      }
      if (pad.recoil > 0) {
        pad.recoil *= Math.exp(-14.0 * dt);
        if (pad.recoil < 0.01) pad.recoil = 0;
      }
      const bScale = pad.baseScale || 0.80;
      const rSq = pad.recoil || 0;
      pad.turretRoot.scale.set(bScale * (1.0 - 0.05 * rSq), bScale * (1.0 + 0.09 * rSq), bScale * (1.0 - 0.05 * rSq));
      if (pad.pitchGroup) pad.pitchGroup.position.x = -0.10 * rSq;

      if (!pad.type || pad.level <= 0 || !TOWER_DEFS[pad.type]) continue;
      const spec = TOWER_DEFS[pad.type];
      const lv = Math.max(1, Math.min(5, pad.level));
      const effRange = getEffectiveTowerRange(pad.type, lv);

      pad.cooldown = Math.max(0, (pad.cooldown || 0) - dt * turretSpdBuff);
      if (aliveEnemies.length === 0) continue;

      const px = pad.group.position.x;
      const py = pad.group.position.y;
      const tMode = pad.targetMode || (pad.type === 'sniper' ? 'strong' : 'first');
      const inRange = [];
      for (let ei = 0; ei < aliveEnemies.length; ei++) {
        const en = aliveEnemies[ei];
        const dPad = Math.hypot(en.mesh.position.x - px, en.mesh.position.y - py);
        if (dPad <= effRange) {
          const dBase = Math.hypot(en.mesh.position.x - baseX, en.mesh.position.y - baseY);
          const pendingKillBias = ((en.pendingIncomingDmg || 0) >= (en.hp + (en.shieldHp || 0))) ? 25.0 : 0.0;
          let modeScore = dBase;
          if (tMode === 'strong') {
            modeScore = -en.maxHp * 0.01 + (en.isBoss ? -50 : 0) + dBase * 0.25;
          } else if (tMode === 'support') {
            const supBias = (en.roleKey === 'support_shaman' || en.roleKey === 'arcane_ranger') ? -30.0 : 0.0;
            modeScore = dBase + supBias;
          } else if (tMode === 'shield') {
            const shBias = (en.shieldHp > 0 || en.roleKey === 'shield_tank') ? -30.0 : 0.0;
            modeScore = dBase + shBias;
          }
          inRange.push({ en, score: modeScore + pendingKillBias });
        }
      }
      if (inRange.length === 0) continue;
      inRange.sort((a, b) => a.score - b.score);
      const target = inRange[0].en;
      if (pad.turretHead && pad.pitchGroup) {
        const tdx = target.mesh.position.x - px;
        const tdy = target.mesh.position.y - py;
        const faceRight = tdx >= 0;
        const wantY = faceRight ? 0.32 : (Math.PI - 0.32);
        pad.turretHead.rotation.y = THREE.MathUtils.lerp(pad.turretHead.rotation.y, wantY, Math.min(1, dt * 12.0));
        const pitchA = THREE.MathUtils.clamp(Math.atan2(tdy, Math.max(0.30, Math.abs(tdx))), -0.52, 0.62);
        const signedPitch = faceRight ? pitchA : -pitchA;
        pad.pitchGroup.rotation.z = THREE.MathUtils.lerp(pad.pitchGroup.rotation.z, signedPitch, Math.min(1, dt * 12.0));
      }

      if (pad.cooldown <= 0) {
        pad.cooldown = 1.0 / Math.max(0.2, spec.rate[lv - 1]);
        pad.recoil = 1.0;
        const baseDmg = combatState.heroAtk * spec.dmgMult[lv - 1] * turretAtkBuff;
        const pen = spec.armorPen + (tInfoLoop.armorPenBonus || 0);
        const fireOrigin = new THREE.Vector3(px, py + 0.42, 0.25);

        if (pad.type === 'ballista') {
          const isCrit = Math.random() < (0.18 + (tInfoLoop.critChance || 0) * 0.5);
          const extraFlags = lv >= 5 ? { markSec: 4.0 } : null;
          spawnBowArrowProjectile(fireOrigin, target, Math.round(baseDmg), isCrit, pen, 'ballista', extraFlags);
          if (lv >= 3) {
            const secondTarget = (inRange.length > 1 ? inRange[1].en : target);
            const twinOrigin = new THREE.Vector3(px + 0.14, py + 0.46, 0.25);
            spawnBowArrowProjectile(twinOrigin, secondTarget, Math.round(baseDmg * 0.72), isCrit, pen, 'ballista', extraFlags);
          }
        } else if (pad.type === 'cannon') {
          const splashRad = (spec.splashRadius || 2.2) + (lv >= 5 ? 0.45 : 0.0);
          const clusterDmg = Math.round(baseDmg * (lv >= 5 ? 1.22 : 1.0));
          spawnGunBulletProjectile(fireOrigin, target, clusterDmg, true, true, 0, pen, 'cannon', splashRad, lv >= 3 ? 0.35 : 0);
        } else if (pad.type === 'frost') {
          spawnGunBulletProjectile(fireOrigin, target, Math.round(baseDmg), false, false, spec.slowSec || 3.0, pen, 'frost', 2.0, 0, {
            brittleSec: lv >= 3 ? 3.5 : 0,
            antiHealSec: lv >= 5 ? 4.0 : 0,
          });
        } else if (pad.type === 'arc') {
          const maxChains = spec.chains[lv - 1] || 3;
          const chainHopRange = 3.8;
          const visited = new Set([target]);
          const targets = [target];
          let currentNode = target;
          while (targets.length < maxChains) {
            let nextBest = null;
            let nextBestDist = chainHopRange;
            for (let ci = 0; ci < aliveEnemies.length; ci++) {
              const cand = aliveEnemies[ci];
              if (visited.has(cand)) continue;
              const dHop = Math.hypot(cand.mesh.position.x - currentNode.mesh.position.x, cand.mesh.position.y - currentNode.mesh.position.y);
              if (dHop <= nextBestDist) {
                nextBestDist = dHop;
                nextBest = cand;
              }
            }
            if (!nextBest) break;
            visited.add(nextBest);
            targets.push(nextBest);
            currentNode = nextBest;
          }
          const linePts = [fireOrigin];
          targets.forEach((tg) => {
            linePts.push(new THREE.Vector3(tg.mesh.position.x, tg.mesh.position.y + 0.55, 0.18));
            const idx = activeEnemies.indexOf(tg);
            if (idx !== -1) {
              damageEnemy(idx, Math.round(baseDmg), true, 0, 0.30, 0.25, lv >= 3 ? 0.68 : pen, 'arc', {
                arcShatter: lv >= 4,
              });
            }
          });
          if (linePts.length > 1) spawnChainLightningVFX(linePts, spec.accentHex);
        } else if (pad.type === 'sniper') {
          const sniperPen = Math.min(1.0, 0.85 + (lv - 1) * 0.0375 + (tInfoLoop.armorPenBonus || 0));
          spawnSniperBeamVFX(fireOrigin, target.mesh.position);
          spawnShockwaveRing(target.mesh.position, 0xe879f9, 1.35);
          const idx = activeEnemies.indexOf(target);
          if (idx !== -1) damageEnemy(idx, Math.round(baseDmg), true, 0, 0.22, 0.60, sniperPen, 'sniper');
        }
      }
    }

    // Live 1-line Contextual Coaching Toast Check
    combatState.coachEvalTimer = (combatState.coachEvalTimer || 0) + dt;
    if (combatState.coachEvalTimer >= 2.8) {
      combatState.coachEvalTimer = 0;
      const tips = combatState.telemetry?.tipsShown || {};
      const emptyCount = buildPads.filter((p) => !p.type).length;
      const hasFrost = buildPads.some((p) => p.type === 'frost');
      const hasPierce = buildPads.some((p) => p.type === 'arc' || p.type === 'sniper');
      if (!tips.emptyPad && emptyCount >= 2 && (rpgState.gold || 0) >= 120) {
        tips.emptyPad = true;
        showLiveCoachingToast('💡 바닥의 빛나는 패드를 클릭해 포탑을 추가 건설하세요!');
      } else if (!tips.shieldTip && !hasPierce && aliveEnemies.some((e) => e.roleKey === 'shield_tank' && e.shieldHp > 0)) {
        tips.shieldTip = true;
        showLiveCoachingToast('🛡️ 방패병 돌진! ⚡ 번개 또는 🎯 스나이퍼 포탑이 유리합니다.');
      } else if (!tips.shamanTip && !hasFrost && aliveEnemies.some((e) => e.roleKey === 'support_shaman')) {
        tips.shamanTip = true;
        showLiveCoachingToast('🚩 주술사 회복 중! ❄️ 서리 프리즘이나 [Q] 유성우로 끊으세요.');
      }
    }

    // 4A. Spawn Remaining Wave Enemies from Sub-Wave Tactical Squad Queue
    if (combatState.enemiesToSpawn > 0) {
      combatState.spawnTimer -= dt;
      if (combatState.spawnTimer <= 0) {
        combatState.enemiesToSpawn -= 1;
        const nextSpec = (combatState.spawnQueue && combatState.spawnQueue.length > 0)
          ? combatState.spawnQueue.shift()
          : { zoneIdx: Math.floor(Math.random() * 4), isBoss: false, roleKey: null, delay: 1.05 };
        combatState.spawnTimer = nextSpec.delay || (0.65 + Math.random() * 1.15);
        spawnDesktopStageEnemy(combatState.wave, nextSpec.zoneIdx, !!nextSpec.isBoss, nextSpec.roleKey);
      }
    }

    const recordTaken = (roleKey, dmg, toBase = false) => {
      if (!combatState.telemetry) return;
      const rk = roleKey || 'vanguard';
      const tbl = combatState.telemetry.damageTakenBySource;
      if (tbl) tbl[rk] = (tbl[rk] || 0) + dmg;
      if (toBase) {
        combatState.telemetry.baseDmgTaken = (combatState.telemetry.baseDmgTaken || 0) + dmg;
        combatState.telemetry.baseBreaches.push({ role: rk, wave: combatState.wave, dmg });
      }
    };

    const triggerCheckDualDefeat = () => {
      const partnerAlive = !!(partnerStageGroup && partnerStageGroup.visible && combatState.partnerHp > 0);
      if (combatState.baseHp <= 0) {
        finishWaveDefense(false);
        return true;
      }
      if (combatState.heroHp <= 0 && !partnerAlive) {
        finishWaveDefense(false);
        return true;
      }
      return false;
    };

    const applyHeroHit = (rawDmg, roleKey, col = '#f87171') => {
      if (combatState.heroHp <= 0) return false;
      if (combatState.heroInvulnTimer > 0) {
        spawnFloatText('✨ 부활 무적!', stageGroup.position, '#38bdf8', 0.85);
        return false;
      }
      combatState.heroHp = Math.max(0, combatState.heroHp - rawDmg);
      recordTaken(roleKey, rawDmg, false);
      spawnFloatText(`-${rawDmg}`, stageGroup.position, col, 0.90);
      if (combatState.heroHp > 0 && combatState.heroHp <= combatState.heroMaxHp * 0.45) tryConsumeBattleBento();
      if (combatState.heroHp <= 0) {
        if (partnerStageGroup && partnerStageGroup.visible && combatState.partnerHp > 0 && combatState.baseHp > 0) {
          combatState.heroReviveTimer = 8.0;
          spawnFloatText('💫 영웅 부활 대기 (8s)', stageGroup.position, '#fbbf24', 1.05);
          return false;
        }
        return triggerCheckDualDefeat();
      }
      return false;
    };

    const applyPartnerHit = (rawDmg, roleKey, col = '#fb923c') => {
      if (!partnerStageGroup || !partnerStageGroup.visible || combatState.partnerHp <= 0) return false;
      if (combatState.partnerInvulnTimer > 0) {
        spawnFloatText('✨ 부활 무적!', partnerStageGroup.position, '#38bdf8', 0.85);
        return false;
      }
      combatState.partnerHp = Math.max(0, combatState.partnerHp - rawDmg);
      recordTaken(roleKey, rawDmg, false);
      spawnFloatText(`-${rawDmg}`, partnerStageGroup.position, col, 0.90);
      if (combatState.partnerHp > 0 && combatState.partnerHp <= combatState.partnerMaxHp * 0.40) tryConsumeBattleBento();
      if (combatState.partnerHp <= 0) {
        if (combatState.heroHp > 0 && combatState.baseHp > 0) {
          combatState.partnerReviveTimer = 8.0;
          spawnFloatText(`💫 ${PARTNER_NAME_KR} 부활 대기 (8s)`, partnerStageGroup.position, '#fde047', 1.05);
          return false;
        }
        return triggerCheckDualDefeat();
      }
      return false;
    };

    const applyBaseHit = (rawDmg, roleKey, col = '#f87171', label = '🏰 기지') => {
      combatState.baseHp = Math.max(0, combatState.baseHp - rawDmg);
      recordTaken(roleKey, rawDmg, true);
      towerSquash = -0.18;
      triggerCameraShake(0.18);
      if (towerHpBar) setPillBarValues(towerHpBar, combatState.baseHp / Math.max(1, combatState.baseMaxHp));
      spawnFloatText(`${label} -${rawDmg}`, defenseTowerGroup.position, col, 0.95);
      spawnShockwaveRing(defenseTowerGroup.position, 0xf43f5e, 1.2);
      return triggerCheckDualDefeat();
    };

    // 4A-2. Boss Red Telegraph AoE Countdown & Explosion
    for (let t = activeBossTelegraphs.length - 1; t >= 0; t--) {
      const bt = activeBossTelegraphs[t];
      bt.elapsed += dt;
      const p = Math.min(1.0, bt.elapsed / bt.duration);
      if (bt.mat?.uniforms) {
        bt.mat.uniforms.uProgress.value = p;
        bt.mat.uniforms.uTime.value = elapsed;
      }
      if (p >= 1.0) {
        const tx = bt.mesh.position.x;
        const ty = bt.mesh.position.y;
        spawnShockwaveRing(bt.mesh.position, 0xef4444, 2.5);
        spawnParticleBurst(bt.mesh.position, 0xf97316, 12, 1.5);
        triggerCameraShake(0.24);
        const blastDmg = bt.caster ? Math.round(bt.caster.atk * 2.1) : 28;

        if (combatState.shieldBuffTimer <= 0) {
          if (Math.hypot(stageGroup.position.x - tx, stageGroup.position.y - ty) <= bt.radius) {
            if (applyHeroHit(blastDmg, 'boss', '#ef4444')) return;
          }
          if (partnerStageGroup && partnerStageGroup.visible && Math.hypot(partnerStageGroup.position.x - tx, partnerStageGroup.position.y - ty) <= bt.radius) {
            if (applyPartnerHit(blastDmg, 'boss', '#ef4444')) return;
          }
          if (Math.hypot(baseX - tx, baseY - ty) <= bt.radius + 0.5) {
            if (applyBaseHit(blastDmg, 'boss', '#ef4444', '🔥 성소 피격')) return;
          }
        }
        projectilesGroup.remove(bt.mesh);
        bt.mat?.dispose?.();
        activeBossTelegraphs.splice(t, 1);
      }
    }

    // 4A-3. Enemy Ranged Projectiles
    for (let i = activeEnemyProjectiles.length - 1; i >= 0; i--) {
      const ep = activeEnemyProjectiles[i];
      if (ep.targetType === 'hero' && (combatState.heroHp <= 0 || combatState.heroReviveTimer > 0)) {
        if (partnerStageGroup && partnerStageGroup.visible && combatState.partnerHp > 0) {
          ep.targetType = 'partner';
        } else {
          disposeProjectileMesh(ep.mesh);
          activeEnemyProjectiles.splice(i, 1);
          continue;
        }
      } else if (ep.targetType === 'partner' && (!partnerStageGroup || !partnerStageGroup.visible || combatState.partnerHp <= 0 || combatState.partnerReviveTimer > 0)) {
        if (combatState.heroHp > 0) {
          ep.targetType = 'hero';
        } else {
          disposeProjectileMesh(ep.mesh);
          activeEnemyProjectiles.splice(i, 1);
          continue;
        }
      }
      const tx = ep.targetType === 'hero' ? stageGroup.position.x : (ep.targetType === 'partner' && partnerStageGroup ? partnerStageGroup.position.x : baseX);
      const ty = ep.targetType === 'hero' ? stageGroup.position.y + 0.65 : (ep.targetType === 'partner' && partnerStageGroup ? partnerStageGroup.position.y + 0.65 : baseY + 0.65);
      const dx = tx - ep.mesh.position.x;
      const dy = ty - ep.mesh.position.y;
      const dist = Math.hypot(dx, dy);
      if (dist <= ep.speed * dt + 0.25) {
        if (combatState.shieldBuffTimer > 0) {
          const sPos = ep.targetType === 'hero' ? stageGroup.position : (ep.targetType === 'partner' && partnerStageGroup ? partnerStageGroup.position : defenseTowerGroup.position);
          spawnFloatText('🛡️ 절대방어!', sPos, '#38bdf8', 0.85);
        } else {
          const armorMult = Math.max(0.45, 1.0 - (rpgState.turrets.barricade || 0) * 0.08);
          const taken = Math.max(1, Math.round(ep.dmg * armorMult));
          if (ep.targetType === 'hero') {
            if (applyHeroHit(taken, 'arcane_ranger', '#c084fc')) return;
          } else if (ep.targetType === 'partner') {
            if (applyPartnerHit(taken, 'arcane_ranger', '#c084fc')) return;
          } else {
            if (applyBaseHit(taken, 'arcane_ranger', '#c084fc', '🏰')) return;
          }
        }
        disposeProjectileMesh(ep.mesh);
        activeEnemyProjectiles.splice(i, 1);
      } else {
        ep.mesh.position.x += (dx / dist) * ep.speed * dt;
        ep.mesh.position.y += (dy / dist) * ep.speed * dt;
        ep.mesh.rotation.z += dt * 8;
        ep.mesh.rotation.y += dt * 5;
      }
    }

    // 4B. Update 22-Joint Articulated Monsters
    for (let i = activeEnemies.length - 1; i >= 0; i--) {
      const e = activeEnemies[i];

      if (e.dyingTimer >= 0) {
        e.dyingTimer -= dt;
        e.mesh.position.x += e.knockVx * dt * 1.4;
        e.mesh.position.y += e.knockVy * dt * 1.4;
        e.knockVx *= Math.pow(0.08, dt);
        e.knockVy *= Math.pow(0.08, dt);
        updateEnemyAnimationSystem(e, dt, elapsed, false, 0, 0, 0, 1.0);
        if (e.dyingTimer < 0.22) {
          e.mesh.scale.setScalar(Math.max(0.01, e.dyingTimer / 0.22));
        }
        if (e.dyingTimer <= 0) {
          disposeEnemy(e);
          activeEnemies.splice(i, 1);
          checkWaveOrSkirmishVictory();
        }
        continue;
      }

      if (e.slowTimer > 0) e.slowTimer -= dt;
      if (e.stunTimer > 0) e.stunTimer -= dt;
      if ((e.brittleTimer || 0) > 0) e.brittleTimer -= dt;
      if ((e.antiHealTimer || 0) > 0) e.antiHealTimer -= dt;
      if ((e.markedTimer || 0) > 0) e.markedTimer -= dt;

      if (e.hitFlashTimer > 0) {
        e.hitFlashTimer = Math.max(0, e.hitFlashTimer - dt);
        const flashIntensity = e.hitFlashTimer > 0
          ? Math.min(0.55, (e.hitFlashTimer / 0.14) * 0.55)
          : (e.isBoss ? 0.14 : 0.0);
        for (let m = 0; m < e.bodyMats.length; m++) {
          if (e.bodyMats[m] && e.bodyMats[m].emissive) e.bodyMats[m].emissiveIntensity = flashIntensity;
        }
      }

      e.hitSquash += (0 - e.hitSquash) * Math.min(1, dt * 12.0);
      if (e.attackWindup > 0) e.attackWindup = Math.max(0, e.attackWindup - dt * 2.8);

      if (Math.abs(e.knockVx) > 0.01 || Math.abs(e.knockVy) > 0.01) {
        e.mesh.position.x = Math.max(xMin + 0.5, Math.min(xMax - 0.5, e.mesh.position.x + e.knockVx * dt * 3.5));
        e.mesh.position.y = Math.max(yMin + 0.4, Math.min(yMax - 0.9, e.mesh.position.y + e.knockVy * dt * 3.5));
        e.knockVx *= Math.pow(0.05, dt);
        e.knockVy *= Math.pow(0.05, dt);
      }

      // Shaman Support AoE Heal Wave (only triggers when at least 1 injured ally is in range!)
      if (e.roleKey === 'support_shaman' && e.stunTimer <= 0) {
        e.healTimer -= dt;
        if (e.healTimer <= 0) {
          const injuredAllies = [];
          for (let j = 0; j < activeEnemies.length; j++) {
            const ally = activeEnemies[j];
            if (ally.dyingTimer >= 0 || ally.hp >= ally.maxHp) continue;
            if (Math.hypot(ally.mesh.position.x - e.mesh.position.x, ally.mesh.position.y - e.mesh.position.y) <= 2.9) {
              injuredAllies.push(ally);
            }
          }
          if (injuredAllies.length === 0) {
            e.healTimer = 0.35; // Hold heal wave ready until an ally is hurt
          } else {
            e.healTimer = 3.5;
            spawnShockwaveRing(e.mesh.position, 0x4ade80, 2.3);
            let healedCount = 0;
            for (let k = 0; k < injuredAllies.length; k++) {
              const ally = injuredAllies[k];
              const antiMult = ((ally.antiHealTimer || 0) > 0 || (e.antiHealTimer || 0) > 0) ? 0.5 : 1.0;
              const healAmt = Math.max(1, Math.round(ally.maxHp * 0.12 * antiMult));
              ally.hp = Math.min(ally.maxHp, ally.hp + healAmt);
              if (ally.hpBarMesh) {
                setPillBarValues(
                  ally.hpBarMesh,
                  ally.hp / Math.max(1, ally.maxHp),
                  ally.maxShieldHp > 0 ? ally.shieldHp / ally.maxShieldHp : 0,
                  ally.shieldHp > 0
                );
              }
              healedCount++;
            }
            if (healedCount > 0) spawnFloatText(`💚 군단 치유 x${healedCount}`, e.mesh.position, '#4ade80', 0.95);
          }
        }
      }

      // Boss Red Telegraph Cast Timer (targets Partner or chokepoint if Hero is reviving)
      if (e.isBoss && e.stunTimer <= 0) {
        e.bossAoETimer -= dt;
        if (e.bossAoETimer <= 0) {
          e.bossAoETimer = e.phase2Triggered ? 3.8 : 5.2;
          e.telegraphCastTimer = 1.40;
          const teleTarget = (combatState.heroHp > 0 && combatState.heroReviveTimer <= 0)
            ? stageGroup.position
            : ((partnerStageGroup && partnerStageGroup.visible && combatState.partnerHp > 0)
              ? partnerStageGroup.position
              : { x: baseX + 2.5, y: baseY + 1.5 });
          spawnBossTelegraph(teleTarget, e);
        }
      }

      const heroAlive = combatState.heroHp > 0 && combatState.heroReviveTimer <= 0;
      const partnerAlive = !!(partnerStageGroup && partnerStageGroup.visible && combatState.partnerHp > 0 && combatState.partnerReviveTimer <= 0);
      const dxHero = stageGroup.position.x - e.mesh.position.x;
      const dyHero = stageGroup.position.y - e.mesh.position.y;
      const distToHero = heroAlive ? Math.hypot(dxHero, dyHero) : 999;

      const dxPartner = partnerStageGroup ? (partnerStageGroup.position.x - e.mesh.position.x) : 999;
      const dyPartner = partnerStageGroup ? (partnerStageGroup.position.y - e.mesh.position.y) : 999;
      const distToPartner = partnerAlive ? Math.hypot(dxPartner, dyPartner) : 999;

      const dxBase = baseX - e.mesh.position.x;
      const dyBase = baseY - e.mesh.position.y;
      const distToBase = Math.hypot(dxBase, dyBase);

      const engageRange = e.attackRange || 0.95;
      const attackingHero = heroAlive && distToHero <= engageRange && distToHero <= distToPartner;
      const attackingPartner = !attackingHero && partnerAlive && distToPartner <= engageRange;
      const attackingBase = !attackingHero && !attackingPartner && distToBase <= (e.roleKey === 'arcane_ranger' ? engageRange : (e.isBoss ? 1.35 : 1.05));
      const isMoving = !attackingHero && !attackingPartner && !attackingBase && e.stunTimer <= 0;
      const spdMult = e.stunTimer > 0 ? 0.0 : (e.slowTimer > 0 ? 0.52 : 1.0);

      let facingSign = 1;
      let moveDirX = attackingHero ? dxHero : (attackingPartner ? dxPartner : dxBase);
      let moveDirY = attackingHero ? dyHero : (attackingPartner ? dyPartner : dyBase);
      if (isMoving) {
        const steerToPartner = partnerAlive && distToPartner < 3.6 && distToPartner <= distToHero;
        const steerToHero = heroAlive && !steerToPartner && distToHero < 3.4;

        // Chokepoint Waypoint Routing through build-pad kill-zone (#11) + Shaman Rear-Support Trailing (#13)
        let navGoalX = baseX;
        let navGoalY = baseY;
        const lanePts = LANE_WAYPOINTS[e.zoneIdx || 0] || LANE_WAYPOINTS[0];
        if (!e.waypointReached && lanePts && lanePts.length > 0) {
          const wp = lanePts[0];
          const wpX = THREE.MathUtils.lerp(xMin, xMax, wp.u);
          const wpY = THREE.MathUtils.lerp(yMin, yMax, wp.v);
          if (Math.hypot(wpX - e.mesh.position.x, wpY - e.mesh.position.y) <= 1.55 || distToBase <= Math.hypot(wpX - baseX, wpY - baseY)) {
            e.waypointReached = true;
          } else {
            navGoalX = wpX;
            navGoalY = wpY;
          }
        }
        if (e.roleKey === 'support_shaman') {
          let frontAlly = null;
          let bestFrontDist = 999;
          for (let j = 0; j < activeEnemies.length; j++) {
            const ally = activeEnemies[j];
            if (ally === e || ally.dyingTimer >= 0 || ally.roleKey === 'support_shaman') continue;
            const dAll = Math.hypot(ally.mesh.position.x - e.mesh.position.x, ally.mesh.position.y - e.mesh.position.y);
            if (dAll < 4.5 && dAll < bestFrontDist) {
              bestFrontDist = dAll;
              frontAlly = ally;
            }
          }
          if (frontAlly) {
            const toBaseLen = Math.max(0.1, Math.hypot(baseX - frontAlly.mesh.position.x, baseY - frontAlly.mesh.position.y));
            navGoalX = frontAlly.mesh.position.x - ((baseX - frontAlly.mesh.position.x) / toBaseLen) * 1.8;
            navGoalY = frontAlly.mesh.position.y - ((baseY - frontAlly.mesh.position.y) / toBaseLen) * 1.8;
          }
        }

        const dxGoal = navGoalX - e.mesh.position.x;
        const dyGoal = navGoalY - e.mesh.position.y;
        const targetDx = steerToPartner ? dxPartner : (steerToHero ? dxHero : dxGoal);
        const targetDy = steerToPartner ? dyPartner : (steerToHero ? dyPartner : dyGoal);
        const targetDist = Math.max(0.001, Math.hypot(targetDx, targetDy));

        let sepX = 0, sepY = 0;
        for (let j = 0; j < activeEnemies.length; j++) {
          if (i === j) continue;
          const other = activeEnemies[j];
          if (other.dyingTimer >= 0) continue;
          const sx = e.mesh.position.x - other.mesh.position.x;
          const sy = e.mesh.position.y - other.mesh.position.y;
          const sd = Math.hypot(sx, sy);
          if (sd > 0.001 && sd < 1.15) {
            sepX += (sx / sd) * 0.45;
            sepY += (sy / sd) * 0.45;
          }
        }
        const sepMag = Math.hypot(sepX, sepY);
        if (sepMag > 0.58) {
          sepX = (sepX / sepMag) * 0.58;
          sepY = (sepY / sepMag) * 0.58;
        }

        const dirX = targetDx / targetDist + sepX;
        const dirY = targetDy / targetDist + sepY;
        moveDirX = dirX;
        moveDirY = dirY;
        const dirLen = Math.hypot(dirX, dirY) || 1.0;
        const moveStep = e.speed * spdMult * dt;

        e.mesh.position.x = Math.max(xMin + 0.5, Math.min(xMax - 0.5, e.mesh.position.x + (dirX / dirLen) * moveStep));
        e.mesh.position.y = Math.max(yMin + 0.4, Math.min(yMax - 0.9, e.mesh.position.y + (dirY / dirLen) * moveStep));
        e.mesh.position.z = 0.0;

        facingSign = dirX >= 0 ? 1 : -1;
        const desiredYaw = facingSign * (0.85 - THREE.MathUtils.clamp(dirY / dirLen, -0.35, 0.35) * 0.22);
        e.modelHolder.rotation.y = THREE.MathUtils.lerp(e.modelHolder.rotation.y, desiredYaw, Math.min(1, dt * 8.0));
      } else {
        const lookDx = attackingHero ? dxHero : (attackingPartner ? dxPartner : dxBase);
        facingSign = lookDx >= 0 ? 1 : -1;
        e.modelHolder.rotation.y = THREE.MathUtils.lerp(e.modelHolder.rotation.y, facingSign * 0.85, Math.min(1, dt * 10));

        e.atkCooldown -= dt;
        if (e.atkCooldown <= 0 && e.stunTimer <= 0) {
          e.atkCooldown = e.roleKey === 'arcane_ranger' ? 2.2 : (e.isBoss ? 1.45 : 1.65);
          e.attackWindup = 1.0;
          setEnemyAnimState(e, 'ATTACK', 0.10);
          if (e.animFsm && e.animFsm.currentAction) {
            e.animFsm.currentAction.setEffectiveTimeScale(1.18);
          }

          const impactAttackingHero = attackingHero;
          const impactAttackingPartner = attackingPartner;
          const impactAttackingBase = attackingBase;
          const atkRole = e.isBoss ? 'boss' : (e.roleKey || 'vanguard');
          const runImpact = () => {
            if (e.disposed || e.dyingTimer >= 0 || (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE')) return;
            if (e.roleKey === 'arcane_ranger') {
              const tType = impactAttackingHero ? 'hero' : (impactAttackingPartner ? 'partner' : 'base');
              const tPos = impactAttackingHero ? stageGroup.position : (impactAttackingPartner && partnerStageGroup ? partnerStageGroup.position : { x: baseX, y: baseY });
              spawnEnemyMagicProjectile(e.mesh.position, tPos, tType, e.atk);
            } else if (combatState.shieldBuffTimer > 0) {
              const sPos = impactAttackingHero ? stageGroup.position : (impactAttackingPartner && partnerStageGroup ? partnerStageGroup.position : defenseTowerGroup.position);
              spawnFloatText('🛡️ 절대방어!', sPos, '#38bdf8', 0.85);
            } else {
              const armorMult = Math.max(0.45, 1.0 - (rpgState.turrets.barricade || 0) * 0.08);
              const taken = Math.max(1, Math.round(e.atk * armorMult));

              if (impactAttackingBase) {
                applyBaseHit(taken, atkRole, '#f87171', '🏰 기지');
              } else if (impactAttackingPartner) {
                applyPartnerHit(taken, atkRole, '#fb923c');
              } else {
                applyHeroHit(taken, atkRole, '#f87171');
              }
            }
          };

          e.pendingAttackHit = true;
          e.attackFallbackTimer = 0.34;
          e.onAttackHitCallback = runImpact;
        }
      }

      // Drive Skeletal AnimationMixer FSM + Post-Mixer Additive Bone Layering + Weapon Sockets
      updateEnemyAnimationSystem(e, dt, elapsed, isMoving, spdMult, moveDirX, moveDirY, Math.hypot(moveDirX, moveDirY) || 1.0);
      if (combatState.mode !== 'SKIRMISH' && combatState.mode !== 'WAVE_DEFENSE') return;
    }

    // 4C. Ppong-ppong-i Hunter-Seeker Combat AI + Overdrive [E] Scaling
    const bones = typeof getRigBones === 'function' ? getRigBones() : null;
    const wepSpec = WEAPON_SPECS[rpgState.equippedWeapon] || WEAPON_SPECS.fist;
    const isOverdrive = combatState.overdriveTimer > 0;
    const hasteMult = (combatState.hasteBuffTimer > 0 ? 1.4 : 1.0) * (isOverdrive ? 1.55 : 1.0) * (tInfoLoop.cpmHasteMult || 1.0);
    const rageMult = (combatState.rageBuffTimer > 0 ? 1.65 : 1.0) * (isOverdrive ? 1.45 : 1.0);

    const desiredHeroScale = combatState.heroReviveTimer > 0 ? 0.24 : (isOverdrive ? 0.58 : 0.42);
    stageGroup.scale.setScalar(THREE.MathUtils.lerp(stageGroup.scale.x, desiredHeroScale, Math.min(1, dt * 8.0)));
    heroRightHandGroup.scale.setScalar(stageGroup.scale.x * 1.05);
    heroLeftHandGroup.scale.setScalar(stageGroup.scale.x * 1.05);
    heroBackQuiverGroup.scale.setScalar(stageGroup.scale.x * 1.05);

    if (combatState.heroReviveTimer > 0) {
      combatState.heroReviveTimer = Math.max(0, combatState.heroReviveTimer - dt);
      if (typeof playAnimation === 'function') playAnimation('Idle');
      stageGroup.position.set(baseX + 0.95, baseY + 0.08, 0.0);
      if (combatState.heroReviveTimer <= 0) {
        combatState.heroHp = Math.round(combatState.heroMaxHp * 0.60);
        combatState.heroInvulnTimer = 2.2;
        spawnShockwaveRing(stageGroup.position, 0x4ade80, 1.6);
        spawnFloatText('💚 영웅 부활!! (2.2s 무적)', stageGroup.position, '#4ade80', 1.15);
      }
    }
    let targetEnemy = combatState.heroReviveTimer > 0 ? null : combatState.lockedTarget;
    if (combatState.heroReviveTimer <= 0 && (combatState.retargetTimer <= 0 || !targetEnemy || targetEnemy.hp <= 0 || targetEnemy.dyingTimer >= 0 || !activeEnemies.includes(targetEnemy))) {
      combatState.retargetTimer = 0.55;
      targetEnemy = null;
      let bestScore = 9999;
      for (let i = 0; i < activeEnemies.length; i++) {
        const cand = activeEnemies[i];
        if (cand.dyingTimer >= 0) continue;
        const dHero = Math.hypot(cand.mesh.position.x - stageGroup.position.x, cand.mesh.position.y - stageGroup.position.y);
        const dBase = Math.hypot(cand.mesh.position.x - baseX, cand.mesh.position.y - baseY);
        const rolePriority = (cand.roleKey === 'support_shaman' || cand.roleKey === 'arcane_ranger') ? -1.4 : 0.0;
        const breachEmergency = dBase < 3.6 ? -3.2 : 0.0;
        const score = dHero * 0.55 + dBase * 0.45 + rolePriority + breachEmergency;
        if (score < bestScore) {
          bestScore = score;
          targetEnemy = cand;
        }
      }
      combatState.lockedTarget = targetEnemy;
    }

    // Helper: fire actual weapon impact / projectile right at the animation Hit-Frame!
    const executeHeroAttackImpact = (pa) => {
      if (!pa) return;
      const tEnemy = (pa.target && pa.target.hp > 0 && pa.target.dyingTimer < 0 && activeEnemies.includes(pa.target))
        ? pa.target
        : targetEnemy;
      if (!tEnemy) return;
      const targetIdx = activeEnemies.indexOf(tEnemy);
      const dirS = (tEnemy.mesh.position.x - stageGroup.position.x) >= 0 ? 1 : -1;
      const wSpec = WEAPON_SPECS[pa.wepKey] || wepSpec;

      if (pa.wepKey === 'fist') {
        if (pa.isThirdCombo || pa.isOverdrive) {
          combatState.heroLeapTimer = 0.42;
          spawnShockwaveRing(tEnemy.mesh.position, 0xfacc15, pa.isOverdrive ? 1.85 : 1.35);
          if (pa.isThirdCombo) spawnFloatText('👊 승룡권 어퍼컷!!', stageGroup.position, '#facc15', 1.05);
          for (let j = activeEnemies.length - 1; j >= 0; j--) {
            if (activeEnemies[j].dyingTimer >= 0) continue;
            const dAoE = Math.hypot(activeEnemies[j].mesh.position.x - tEnemy.mesh.position.x, activeEnemies[j].mesh.position.y - tEnemy.mesh.position.y);
            if (dAoE <= (pa.isOverdrive ? 2.0 : 1.6)) damageEnemy(j, pa.dmg, true, 0, 0.25, wSpec.knockback * 1.2, wSpec.armorPen);
          }
        } else if (targetIdx !== -1) {
          spawnShockwaveRing(tEnemy.mesh.position, 0xfde047, 0.95);
          damageEnemy(targetIdx, pa.dmg, pa.isCrit, 0, 0, wSpec.knockback, wSpec.armorPen);
        }
      } else if (pa.wepKey === 'sword') {
        slashArcMesh.visible = true;
        if (slashArcMat.uniforms?.uOpacity) slashArcMat.uniforms.uOpacity.value = 0.94;
        slashArcMesh.position.set(stageGroup.position.x + dirS * 0.65, stageGroup.position.y + 0.62, 0.16);
        slashArcMesh.rotation.set(0, 0, pa.comboStep === 1 ? -0.85 : (pa.comboStep === 2 ? 0.15 : 0.72));
        slashArcMesh.scale.setScalar(pa.isThirdCombo ? 1.25 : 0.95);

        if (pa.isThirdCombo || pa.isOverdrive) {
          combatState.whirlwindTimer = 0.48;
          combatState.heroLeapTimer = 0.44;
          whirlwindMesh.visible = true;
          if (whirlwindMat.uniforms?.uOpacity) whirlwindMat.uniforms.uOpacity.value = 0.95;
          whirlwindMesh.position.set(stageGroup.position.x, stageGroup.position.y + 0.58, 0.16);
          if (pa.isThirdCombo) spawnFloatText('⚔️ 초승달 회전 참격!!', stageGroup.position, '#38bdf8', 1.08);
          for (let j = activeEnemies.length - 1; j >= 0; j--) {
            if (activeEnemies[j].dyingTimer >= 0) continue;
            const dAoE = Math.hypot(activeEnemies[j].mesh.position.x - stageGroup.position.x, activeEnemies[j].mesh.position.y - stageGroup.position.y);
            if (dAoE <= (pa.isOverdrive ? 2.4 : 2.0)) damageEnemy(j, pa.dmg, true, 0, 0.22, wSpec.knockback * 1.25, wSpec.armorPen);
          }
        } else if (targetIdx !== -1) {
          damageEnemy(targetIdx, pa.dmg, pa.isCrit, 0, 0, wSpec.knockback, wSpec.armorPen);
        }
      } else if (pa.wepKey === 'bow') {
        const launchOrigin = new THREE.Vector3();
        if (heroLeftHandGroup) heroLeftHandGroup.getWorldPosition(launchOrigin);
        else launchOrigin.set(stageGroup.position.x + dirS * 0.35, stageGroup.position.y + 0.68, 0.12);
        if (pa.isThirdCombo || pa.isOverdrive) {
          if (pa.isThirdCombo) spawnFloatText('🏹 멀티샷 3연발!!', stageGroup.position, '#4ade80', 1.05);
          let shots = 0;
          for (let j = 0; j < activeEnemies.length && shots < 3; j++) {
            if (activeEnemies[j].dyingTimer < 0) {
              spawnBowArrowProjectile(launchOrigin, activeEnemies[j], pa.dmg * 0.85, true, wSpec.armorPen);
              shots++;
            }
          }
          while (shots < 3) {
            spawnBowArrowProjectile(launchOrigin, tEnemy, pa.dmg * 0.65, true, wSpec.armorPen);
            shots++;
          }
        } else {
          spawnBowArrowProjectile(launchOrigin, tEnemy, pa.dmg, pa.isCrit, wSpec.armorPen);
        }
      } else if (pa.wepKey === 'gun') {
        combatState.muzzleFlashTimer = 0.16;
        const muzzleOrigin = new THREE.Vector3();
        if (gunMuzzleFlashMesh) {
          gunMuzzleFlashMesh.getWorldPosition(muzzleOrigin);
        } else {
          muzzleOrigin.set(stageGroup.position.x + dirS * 0.50, stageGroup.position.y + 0.66, 0.14);
        }
        spawnParticleBurst(muzzleOrigin, 0xfde047, 7, 1.1);
        if (pa.isThirdCombo) spawnFloatText('🔫 플라즈마 폭발탄!!', stageGroup.position, '#f43f5e', 1.08);
        spawnGunBulletProjectile(muzzleOrigin, tEnemy, pa.dmg, pa.isCrit, pa.isThirdCombo || pa.isOverdrive, 0, wSpec.armorPen);
      }
    };

    if (targetEnemy) {
      const dx = targetEnemy.mesh.position.x - stageGroup.position.x;
      const dy = targetEnemy.mesh.position.y - stageGroup.position.y;
      const dist = Math.hypot(dx, dy);
      const dirSign = dx >= 0 ? 1 : -1;
      const desiredYaw = dirSign * (1.08 - THREE.MathUtils.clamp(dy / Math.max(0.5, dist), -0.35, 0.35) * 0.18);
      if (typeof setStageYawOverride === 'function') setStageYawOverride(desiredYaw);

      // Smoothly track target vertical elevation for aimed Gun & Bow shots
      const targetAimPitch = THREE.MathUtils.clamp(Math.atan2(dy, Math.max(0.6, Math.abs(dx))), -0.68, 0.68);
      combatState.aimPitch = THREE.MathUtils.lerp(combatState.aimPitch || 0, targetAimPitch, Math.min(1, dt * 10.0));

      const shouldKiteBack = wepSpec.isRanged && dist < 2.25 && combatState.slashAnimTimer <= 0 && (stageGroup.position.x > xMin + 1.4);
      if (dist > wepSpec.engageRange && combatState.slashAnimTimer <= 0) {
        if (typeof playAnimation === 'function') playAnimation('Run');
        if (typeof setHeroAnimTimeScale === 'function') setHeroAnimTimeScale(0.92);
        const heroMoveSpeed = 4.65 * Math.min(1.55, hasteMult) * combatState.bentoSpdMult;
        const step = Math.min(dist - wepSpec.engageRange * 0.88, heroMoveSpeed * dt);
        stageGroup.position.x = Math.max(xMin + 0.6, Math.min(xMax - 0.6, stageGroup.position.x + (dx / dist) * step));
        stageGroup.position.y = Math.max(yMin + 0.4, Math.min(yMax - 0.9, stageGroup.position.y + (dy / dist) * step));
        stageGroup.position.z = 0.0;
      } else {
        if (shouldKiteBack && dist > 0.05) {
          const kiteStep = 2.15 * dt;
          stageGroup.position.x = Math.max(xMin + 0.6, Math.min(xMax - 0.6, stageGroup.position.x - (dx / dist) * kiteStep));
          stageGroup.position.y = Math.max(yMin + 0.4, Math.min(yMax - 0.9, stageGroup.position.y - (dy / dist) * kiteStep * 0.5));
        }
        if (typeof setHeroAnimTimeScale === 'function') setHeroAnimTimeScale(1.0);
        if (typeof playAnimation === 'function' && combatState.slashAnimTimer <= 0) playAnimation(shouldKiteBack ? 'Walk' : 'Idle');
        const effectiveRate = Math.min(2.60, combatState.bentoSpdMult * hasteMult);
        combatState.attackCooldown -= dt * effectiveRate;
        if (combatState.attackCooldown <= 0 && combatState.slashAnimTimer <= 0) {
          combatState.attackCooldown = 1.0 / Math.max(0.35, combatState.heroAps);
          combatState.comboStep = (combatState.comboStep + 1) % 3;
          const isThirdCombo = combatState.comboStep === 2;
          const critChance = 0.20 + (tInfoLoop.critChance || 0);
          const critMult = Math.max(1.25, tInfoLoop.critMult || 1.50);
          const isCrit = isThirdCombo || Math.random() < critChance;
          const dmg = combatState.heroAtk * combatState.bentoAtkMult * rageMult * (isThirdCombo ? Math.max(1.42, critMult) : (isCrit ? critMult : 1.0));
          const animDur = (wepSpec.animDur || 0.80) / Math.min(1.65, Math.sqrt(effectiveRate));
          combatState.slashAnimDur = animDur;
          combatState.slashAnimTimer = animDur;
          combatState.pendingAttack = {
            fired: false,
            hitRatio: wepSpec.hitRatio ?? 0.42,
            wepKey: wepSpec.key,
            comboStep: combatState.comboStep,
            isThirdCombo,
            isCrit,
            isOverdrive,
            dmg,
            target: targetEnemy,
          };
        }
      }
    } else {
      const homeX = baseX + 0.95;
      const homeY = baseY + 0.08;
      if (combatState.heroReviveTimer <= 0) {
        const dxHome = homeX - stageGroup.position.x;
        const dyHome = homeY - stageGroup.position.y;
        const dHome = Math.hypot(dxHome, dyHome);
        if (dHome > 0.25) {
          if (typeof setHeroAnimTimeScale === 'function') setHeroAnimTimeScale(1.0);
          if (typeof playAnimation === 'function') playAnimation('Walk');
          const step = Math.min(dHome, 2.4 * dt);
          stageGroup.position.x += (dxHome / dHome) * step;
          stageGroup.position.y += (dyHome / dHome) * step;
          stageGroup.position.z = 0.0;
          if (typeof setStageYawOverride === 'function') setStageYawOverride(dxHome >= 0 ? 0.95 : -0.95);
        } else {
          if (typeof setHeroAnimTimeScale === 'function') setHeroAnimTimeScale(1.0);
          if (typeof playAnimation === 'function') playAnimation('Idle');
          if (typeof setStageYawOverride === 'function') setStageYawOverride(0.95);
        }
      }
    }

    heroCombatShadow.position.set(stageGroup.position.x, stageGroup.position.y + 0.004, 0.0);

    // 4D-2. Dual-Hero Partner Sanctuary Star-Orb Guardian AI & [E] Synchro Tether
    if (partnerStageGroup && partnerStageGroup.visible) {
      const guardX = baseX + 2.35;
      const guardY = baseY + 1.45;
      if (partnerStaffOrb) {
        partnerStaffOrb.rotation.y += dt * 2.4;
        partnerStaffOrb.position.y = 1.48 + Math.sin(elapsed * 3.1) * 0.10;
      }
      if (partnerAuraRing) {
        partnerAuraRing.rotation.z -= dt * 1.1;
      }

      if (combatState.partnerReviveTimer > 0) {
        combatState.partnerReviveTimer = Math.max(0, combatState.partnerReviveTimer - dt);
        partnerStageGroup.scale.setScalar(THREE.MathUtils.lerp(partnerStageGroup.scale.x, 0.24, Math.min(1, dt * 8.0)));
        partnerStageGroup.position.set(guardX, guardY, 0.0);
        if (typeof playPartnerAnimation === 'function') playPartnerAnimation('Idle');
        if (combatState.partnerReviveTimer <= 0) {
          combatState.partnerHp = Math.round(combatState.partnerMaxHp * 0.60);
          combatState.partnerInvulnTimer = 2.2;
          spawnShockwaveRing(partnerStageGroup.position, 0x4ade80, 1.6);
          spawnFloatText(`💚 ${PARTNER_NAME_KR} 부활!! (2.2s 무적)`, partnerStageGroup.position, '#fde047', 1.15);
        }
      } else {
        const wantPScale = isOverdrive ? 0.56 : 0.42;
        partnerStageGroup.scale.setScalar(THREE.MathUtils.lerp(partnerStageGroup.scale.x, wantPScale, Math.min(1, dt * 8.0)));

        // Pick closest enemy threatening sanctuary within 12.5u leash, or assist Hero's lockedTarget!
        let pTarget = null;
        let pBest = 9999;
        for (let ei = 0; ei < aliveEnemies.length; ei++) {
          const en = aliveEnemies[ei];
          const dBaseEn = Math.hypot(en.mesh.position.x - baseX, en.mesh.position.y - baseY);
          if (dBaseEn <= 12.5 && dBaseEn < pBest) {
            pBest = dBaseEn;
            pTarget = en;
          }
        }
        if (!pTarget && targetEnemy && targetEnemy.dyingTimer < 0) {
          pTarget = targetEnemy;
          pBest = Math.hypot(pTarget.mesh.position.x - baseX, pTarget.mesh.position.y - baseY);
        }

        if (pTarget) {
          const isThreatCloseToBase = pBest < 4.5;
          const desiredX = isThreatCloseToBase
            ? THREE.MathUtils.lerp(baseX, pTarget.mesh.position.x, 0.45)
            : THREE.MathUtils.clamp(pTarget.mesh.position.x - 2.1, baseX + 0.5, baseX + 10.5);
          const desiredY = isThreatCloseToBase
            ? THREE.MathUtils.lerp(baseY, pTarget.mesh.position.y, 0.45)
            : THREE.MathUtils.clamp(pTarget.mesh.position.y, yMin + 0.6, baseY + 8.0);
          const pdx = desiredX - partnerStageGroup.position.x;
          const pdy = desiredY - partnerStageGroup.position.y;
          const pDist = Math.hypot(pdx, pdy);
          if (pDist > 0.35) {
            const pStep = Math.min(pDist, (isThreatCloseToBase ? 4.4 : 3.6) * dt);
            partnerStageGroup.position.x += (pdx / pDist) * pStep;
            partnerStageGroup.position.y += (pdy / pDist) * pStep;
            if (typeof playPartnerAnimation === 'function') playPartnerAnimation('Run');
          } else if (typeof playPartnerAnimation === 'function') {
            playPartnerAnimation('Idle');
          }
          const faceDx = pTarget.mesh.position.x - partnerStageGroup.position.x;
          partnerStageGroup.rotation.y = THREE.MathUtils.lerp(partnerStageGroup.rotation.y, faceDx >= 0 ? 0.85 : -0.85, Math.min(1, dt * 8.0));

          combatState.partnerCooldown = Math.max(0, (combatState.partnerCooldown || 0) - dt * hasteMult);
          if (combatState.partnerCooldown <= 0) {
            combatState.partnerCooldown = 0.80;
            const orbOrigin = partnerStageGroup.position.clone().add(new THREE.Vector3(0, 0.65, 0.15));
            spawnPartnerStarProjectile(orbOrigin, pTarget, combatState.partnerAtk * rageMult);
          }
        } else {
          const escortX = combatState.heroHp > 0 ? THREE.MathUtils.clamp(stageGroup.position.x - 1.6, baseX + 1.2, baseX + 7.5) : guardX;
          const escortY = combatState.heroHp > 0 ? THREE.MathUtils.clamp(stageGroup.position.y + 0.55, yMin + 0.6, yMax - 1.2) : guardY;
          const pdx = escortX - partnerStageGroup.position.x;
          const pdy = escortY - partnerStageGroup.position.y;
          const pDist = Math.hypot(pdx, pdy);
          if (pDist > 0.25) {
            const pStep = Math.min(pDist, 2.8 * dt);
            partnerStageGroup.position.x += (pdx / pDist) * pStep;
            partnerStageGroup.position.y += (pdy / pDist) * pStep;
            if (typeof playPartnerAnimation === 'function') playPartnerAnimation('Walk');
          } else if (typeof playPartnerAnimation === 'function') {
            playPartnerAnimation('Idle');
          }
          partnerStageGroup.rotation.y = THREE.MathUtils.lerp(partnerStageGroup.rotation.y, 0.72, Math.min(1, dt * 8.0));
        }

        // Starfall Nova AoE Slow + Team/Nexus 3.5% Heal every 6.5s
        combatState.partnerNovaCd = Math.max(0, (combatState.partnerNovaCd || 0) - dt);
        if (combatState.partnerNovaCd <= 0) {
          let nearCount = 0;
          for (let ei = 0; ei < aliveEnemies.length; ei++) {
            const en = aliveEnemies[ei];
            if (Math.hypot(en.mesh.position.x - partnerStageGroup.position.x, en.mesh.position.y - partnerStageGroup.position.y) <= 3.8) {
              nearCount++;
            }
          }
          if (nearCount >= 2) {
            combatState.partnerNovaCd = 6.5;
            const novaDmg = combatState.partnerAtk * (getTypingLevelInfo().level >= 5 ? 1.85 : 1.25);
            spawnShockwaveRing(partnerStageGroup.position, 0x4ade80, 2.6);
            spawnFloatText(`🌟 ${PARTNER_NAME_KR} 별빛 파동!`, partnerStageGroup.position, '#fde047', 1.08);
            combatState.heroHp = Math.min(combatState.heroMaxHp, combatState.heroHp + Math.round(combatState.heroMaxHp * 0.035));
            combatState.partnerHp = Math.min(combatState.partnerMaxHp, combatState.partnerHp + Math.round(combatState.partnerMaxHp * 0.035));
            combatState.baseHp = Math.min(combatState.baseMaxHp, combatState.baseHp + Math.round(combatState.baseMaxHp * 0.035));
            if (towerHpBar) setPillBarValues(towerHpBar, combatState.baseHp / Math.max(1, combatState.baseMaxHp));
            for (let j = activeEnemies.length - 1; j >= 0; j--) {
              if (activeEnemies[j].dyingTimer >= 0) continue;
              if (Math.hypot(activeEnemies[j].mesh.position.x - partnerStageGroup.position.x, activeEnemies[j].mesh.position.y - partnerStageGroup.position.y) <= 3.8) {
                damageEnemy(j, Math.round(novaDmg), true, 2.2, 0, 0.6, 0.3, 'partner');
              }
            }
          }
        }
      }
      partnerCombatShadow.position.set(partnerStageGroup.position.x, partnerStageGroup.position.y + 0.004, 0.0);

      // Synchro Rainbow-Gold Tether Beam between Hero and Partner during [E] Overdrive!
      if (synchroBeamMesh) {
        const showSync = isOverdrive && combatState.heroHp > 0 && combatState.partnerHp > 0;
        synchroBeamMesh.visible = showSync;
        if (showSync) {
          const hx = stageGroup.position.x;
          const hy = stageGroup.position.y + 0.55;
          const ppx = partnerStageGroup.position.x;
          const ppy = partnerStageGroup.position.y + 0.55;
          const bDist = Math.hypot(ppx - hx, ppy - hy);
          synchroBeamMesh.position.set((hx + ppx) * 0.5, (hy + ppy) * 0.5, 0.16);
          synchroBeamMesh.scale.set(1.0, Math.max(0.1, bDist), 1.0);
          synchroBeamMesh.rotation.z = Math.atan2(ppy - hy, ppx - hx) - Math.PI / 2;
        }
      }
    }

    // 4D. Hero Leap Arc + Full-Body Multi-Phase Combat Choreography & Dynamic Weapon Rotation
    if (combatState.heroLeapTimer > 0) {
      combatState.heroLeapTimer -= dt;
      const u = 1.0 - Math.max(0, combatState.heroLeapTimer) / 0.44;
      characterPivot.position.y = Math.sin(u * Math.PI) * 0.46;
    } else {
      characterPivot.position.y = THREE.MathUtils.lerp(characterPivot.position.y, 0, 1.0 - Math.exp(-14 * dt));
    }

    const smoothStep = (e0, e1, x) => {
      const t = Math.max(0, Math.min(1, (x - e0) / Math.max(0.0001, e1 - e0)));
      return t * t * (3 - 2 * t);
    };

    // Per-frame weapon dynamic orientation offsets (applied to heroRightHandGroup / heroLeftHandGroup)
    let wepPitchOffset = 0.18;
    let wepYawOffset = 0.0;
    let wepRollOffset = 0.0;
    let bowPitchOffset = 0.0;

    if (bones && addBoneEulerOffset) {
      if (combatState.slashAnimTimer > 0) {
        combatState.slashAnimTimer = Math.max(0, combatState.slashAnimTimer - dt);
        const dur = Math.max(0.25, combatState.slashAnimDur || 0.80);
        const p = Math.max(0, Math.min(1, 1.0 - combatState.slashAnimTimer / dur));

        // Trigger weapon damage / slash / gunshot / arrow release at exact Hit-Frame!
        if (combatState.pendingAttack && !combatState.pendingAttack.fired && p >= combatState.pendingAttack.hitRatio) {
          combatState.pendingAttack.fired = true;
          executeHeroAttackImpact(combatState.pendingAttack);
        }
        if (combatState.slashAnimTimer <= 0) {
          combatState.pendingAttack = null;
        }

        if (wepSpec.key === 'sword') {
          // 3-Phase Natural Sword Cleave: Wind-Up (0..0.32) -> Explosive Slash (0.32..0.58) -> Follow-Through & Recover (0.58..1.0)
          const wind = smoothStep(0.0, 0.30, p) * (1.0 - smoothStep(0.30, 0.42, p));
          const cleave = smoothStep(0.30, 0.56, p) * (1.0 - smoothStep(0.68, 1.0, p));
          const combo = combatState.comboStep;
          if (combo === 0) {
            // Overhead Right-to-Left Diagonal Cleave
            if (bones.spine) addBoneEulerOffset(bones.spine, -0.18 * wind + 0.24 * cleave, -0.42 * wind + 0.46 * cleave, 0);
            if (bones.chest) addBoneEulerOffset(bones.chest, -0.12 * wind + 0.18 * cleave, -0.32 * wind + 0.40 * cleave, 0);
            if (bones.head) addBoneEulerOffset(bones.head, 0.08 * wind - 0.10 * cleave, 0.32 * wind - 0.32 * cleave, 0);
            if (bones.rightArm) addBoneEulerOffset(bones.rightArm, -0.18 * wind + 0.10 * cleave, 0.52 * wind - 1.32 * cleave, 1.35 * wind - 0.55 * cleave);
            if (bones.rightForeArm) addBoneEulerOffset(bones.rightForeArm, 0, -0.95 * wind - 0.35 * cleave, 0);
            if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, -0.35 * wind + 0.45 * cleave, 0.42 * cleave);
            wepPitchOffset = -0.78 * wind + 1.55 * cleave;
            wepYawOffset = -0.35 * wind + 0.72 * cleave;
            wepRollOffset = -0.45 * wind + 0.55 * cleave;
          } else if (combo === 1) {
            // Reverse Sweeping Horizontal Backhand Slash
            if (bones.spine) addBoneEulerOffset(bones.spine, 0.10 * wind + 0.16 * cleave, 0.48 * wind - 0.52 * cleave, 0);
            if (bones.chest) addBoneEulerOffset(bones.chest, 0.08 * cleave, 0.36 * wind - 0.44 * cleave, 0);
            if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -1.25 * wind + 0.65 * cleave, 0.15 * wind + 0.42 * cleave);
            if (bones.rightForeArm) addBoneEulerOffset(bones.rightForeArm, 0, -0.75 * wind - 0.25 * cleave, 0);
            wepPitchOffset = 1.15 * (wind + cleave * 0.9);
            wepYawOffset = 0.95 * wind - 1.15 * cleave;
            wepRollOffset = 1.25 * (wind * 0.5 + cleave);
          } else {
            // Finisher: 360° Leaping Whirlwind Overhead Slam
            const spinA = smoothStep(0.18, 0.78, p) * Math.PI * 2.0;
            if (bones.hips) addBoneEulerOffset(bones.hips, 0, spinA, 0);
            if (bones.spine) addBoneEulerOffset(bones.spine, -0.25 * wind + 0.34 * cleave, 0, 0);
            if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -0.95 * cleave, 1.55 * wind - 0.42 * cleave);
            if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, 0.85 * cleave, -0.85 * wind);
            wepPitchOffset = -0.55 * wind + 1.85 * cleave;
            wepYawOffset = spinA * 0.35;
            wepRollOffset = 0.65 * cleave;
          }
        } else if (wepSpec.key === 'gun') {
          // 3-Phase Natural Gun Aim -> Fire & Recoil Kick -> Smooth Sight Settle
          const aim = smoothStep(0.0, 0.24, p) * (1.0 - smoothStep(0.76, 1.0, p));
          const recoil = smoothStep(0.32, 0.42, p) * (1.0 - smoothStep(0.42, 0.72, p));
          const aimP = combatState.aimPitch || 0;
          if (bones.spine) addBoneEulerOffset(bones.spine, -0.14 * recoil, -0.26 * aim, 0);
          if (bones.chest) addBoneEulerOffset(bones.chest, -0.12 * recoil, -0.22 * aim, 0);
          if (bones.head) addBoneEulerOffset(bones.head, -0.06 * recoil - aimP * 0.35 * aim, 0.36 * aim, 0);
          // Raise right arm straight ahead on target, kick upward on recoil
          if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -1.18 * aim + 0.16 * recoil, (0.18 + aimP * 0.65) * aim + 0.46 * recoil);
          if (bones.rightForeArm) addBoneEulerOffset(bones.rightForeArm, 0, -0.22 * aim - 0.35 * recoil, 0);
          // Left arm braces steadily across chest
          if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, 0.92 * aim, -0.12 * aim + 0.15 * recoil);
          if (bones.leftForeArm) addBoneEulerOffset(bones.leftForeArm, 0, 0.58 * aim, 0);
          wepPitchOffset = -aimP * aim - 0.42 * recoil;
          wepYawOffset = 0.06 * aim;
          wepRollOffset = 0.0;
        } else if (wepSpec.key === 'bow') {
          // 3-Phase Bow Draw -> Hold -> Crisp Release Snap
          const draw = smoothStep(0.0, 0.44, p) * (1.0 - smoothStep(0.46, 0.60, p));
          const holdPose = smoothStep(0.0, 0.22, p) * (1.0 - smoothStep(0.78, 1.0, p));
          const releaseSnap = smoothStep(0.46, 0.56, p) * (1.0 - smoothStep(0.62, 0.95, p));
          const aimP = combatState.aimPitch || 0;
          if (bones.spine) addBoneEulerOffset(bones.spine, 0, 0.38 * holdPose, 0);
          if (bones.chest) addBoneEulerOffset(bones.chest, 0, 0.30 * holdPose, 0);
          if (bones.head) addBoneEulerOffset(bones.head, -aimP * 0.3 * holdPose, -0.52 * holdPose, 0);
          // Left arm extends Bow_Golden straight toward target
          if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, 1.18 * holdPose, (-0.15 - aimP * 0.5) * holdPose);
          // Right arm draws bowstring back to cheek, then snaps open
          if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -0.45 * holdPose + 0.72 * draw + 0.45 * releaseSnap, 0.38 * draw);
          if (bones.rightForeArm) addBoneEulerOffset(bones.rightForeArm, 0, -1.25 * draw - 0.35 * releaseSnap, 0);
          bowPitchOffset = -aimP * holdPose;
        } else {
          // Fist: Crisp 1-2-Uppercut Boxing Combo with torso snap
          const wind = smoothStep(0.0, 0.28, p) * (1.0 - smoothStep(0.28, 0.40, p));
          const punch = smoothStep(0.28, 0.50, p) * (1.0 - smoothStep(0.62, 1.0, p));
          if (combatState.comboStep === 0) {
            if (bones.chest) addBoneEulerOffset(bones.chest, 0.14 * punch, -0.32 * wind + 0.44 * punch, 0);
            if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, -0.35 * wind + 1.38 * punch, -0.25 * punch);
            if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -0.55 * punch, 0.22);
          } else if (combatState.comboStep === 1) {
            if (bones.chest) addBoneEulerOffset(bones.chest, 0.16 * punch, 0.35 * wind - 0.48 * punch, 0);
            if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, 0.35 * wind - 1.42 * punch, 0.28 * punch);
            if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, 0.55 * punch, -0.22);
          } else {
            // Dragon Uppercut
            if (bones.spine) addBoneEulerOffset(bones.spine, 0.24 * wind - 0.28 * punch, -0.36 * punch, 0);
            if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -1.15 * punch, -0.35 * wind + 1.55 * punch);
            if (bones.leftArm) addBoneEulerOffset(bones.leftArm, 0, 0.65 * punch, -0.65 * punch);
          }
        }
      } else if (wepSpec.key === 'gun' && targetEnemy) {
        // Ready-aim tactical gun stance between shots
        if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -0.82, 0.10 + (combatState.aimPitch || 0) * 0.4);
        wepPitchOffset = -(combatState.aimPitch || 0) * 0.65;
      } else if (wepSpec.key === 'sword' && targetEnemy) {
        // Ready knight combat guard stance
        if (bones.rightArm) addBoneEulerOffset(bones.rightArm, 0, -0.38, 0.22);
        wepPitchOffset = 0.28;
      }

      if (bones.rightHand) {
        bones.rightHand.getWorldPosition(tmpHandR);
        heroRightHandGroup.position.copy(tmpHandR);
        heroRightHandGroup.rotation.order = 'YXZ';
        heroRightHandGroup.rotation.set(wepPitchOffset, stageGroup.rotation.y + wepYawOffset, wepRollOffset);
      }
      if (bones.leftHand) {
        bones.leftHand.getWorldPosition(tmpHandL);
        heroLeftHandGroup.position.copy(tmpHandL);
        heroLeftHandGroup.rotation.order = 'YXZ';
        heroLeftHandGroup.rotation.set(bowPitchOffset, stageGroup.rotation.y, 0);
      }
      if (bones.chest && heroBackQuiverGroup.visible) {
        bones.chest.getWorldPosition(tmpChest);
        heroBackQuiverGroup.position.set(tmpChest.x - Math.sin(stageGroup.rotation.y) * 0.20, tmpChest.y + 0.04, tmpChest.z - Math.cos(stageGroup.rotation.y) * 0.20);
        heroBackQuiverGroup.rotation.y = stageGroup.rotation.y;
      }
    }

    if (gunMuzzleFlashMesh) {
      const fMats = gunMuzzleFlashMesh.userData.mats || (gunMuzzleFlashMesh.material ? [gunMuzzleFlashMesh.material] : []);
      if (combatState.muzzleFlashTimer > 0) {
        combatState.muzzleFlashTimer -= dt;
        const fOp = Math.min(1.0, combatState.muzzleFlashTimer / 0.14);
        fMats.forEach((m) => { if (m) m.opacity = 0.95 * fOp; });
        gunMuzzleFlashMesh.scale.setScalar(0.85 + Math.random() * 0.65);
        gunMuzzleFlashMesh.rotation.z += dt * 24.0;
      } else {
        fMats.forEach((m) => { if (m) m.opacity = 0.0; });
      }
    }

    if (slashArcMesh.visible) {
      const nextOp = (slashArcMat.uniforms?.uOpacity?.value || 0) - dt * 3.2;
      if (slashArcMat.uniforms?.uOpacity) slashArcMat.uniforms.uOpacity.value = Math.max(0, nextOp);
      if (nextOp <= 0) slashArcMesh.visible = false;
    }
    if (whirlwindMesh.visible) {
      whirlwindMesh.rotation.z += dt * 16.0;
      const nextWh = (whirlwindMat.uniforms?.uOpacity?.value || 0) - dt * 2.5;
      if (whirlwindMat.uniforms?.uOpacity) whirlwindMat.uniforms.uOpacity.value = Math.max(0, nextWh);
      if (nextWh <= 0) whirlwindMesh.visible = false;
    }

    // 4E. Update Projectiles (Hero & Turrets) — AoE shells detonate at last coordinates even if target dies mid-flight!
    const releaseProjectileReservation = (proj) => {
      if (proj && proj.reservedDmg && proj.target) {
        proj.target.pendingIncomingDmg = Math.max(0, (proj.target.pendingIncomingDmg || 0) - proj.reservedDmg);
        proj.reservedDmg = 0;
      }
    };

    for (let i = activeProjectiles.length - 1; i >= 0; i--) {
      const p = activeProjectiles[i];
      const targetAlive = !!(p.target && p.target.hp > 0 && p.target.dyingTimer < 0 && activeEnemies.includes(p.target));
      if (targetAlive) {
        p.lastX = p.target.mesh.position.x;
        p.lastY = p.target.mesh.position.y;
      } else if (!p.isFrostSplash && !p.isExplosive) {
        releaseProjectileReservation(p);
        disposeProjectileMesh(p.mesh);
        activeProjectiles.splice(i, 1);
        continue;
      }

      if (p.isParabolicArrow) {
        p.elapsed += dt;
        const u = Math.min(1.0, p.elapsed / p.duration);
        const endX = targetAlive ? p.target.mesh.position.x : (p.lastX ?? p.startPos.x);
        const endY = targetAlive ? p.target.mesh.position.y : (p.lastY ?? p.startPos.y);
        const curX = THREE.MathUtils.lerp(p.startPos.x, endX, u);
        const curY = THREE.MathUtils.lerp(p.startPos.y, endY + 0.65, u) + 4.0 * p.arcHeight * u * (1.0 - u);

        const nextU = Math.min(1.0, u + 0.05);
        const nextX = THREE.MathUtils.lerp(p.startPos.x, endX, nextU);
        const nextY = THREE.MathUtils.lerp(p.startPos.y, endY + 0.65, nextU) + 4.0 * p.arcHeight * nextU * (1.0 - nextU);

        p.mesh.position.set(curX, curY, 0.14);
        p.mesh.lookAt(nextX, nextY, 0.14);

        if (u >= 1.0) {
          releaseProjectileReservation(p);
          const idx = targetAlive ? activeEnemies.indexOf(p.target) : -1;
          if (idx !== -1) damageEnemy(idx, p.dmg, p.isCrit, p.slowSec, 0, p.knockback, p.armorPen || 0.20, p.sourceKey || 'hero', p.extraFlags || null);
          disposeProjectileMesh(p.mesh);
          activeProjectiles.splice(i, 1);
        }
      } else {
        const tx = targetAlive ? p.target.mesh.position.x : (p.lastX ?? p.mesh.position.x);
        const tyGround = targetAlive ? p.target.mesh.position.y : (p.lastY ?? p.mesh.position.y);
        const ty = tyGround + 0.65;
        const dx = tx - p.mesh.position.x;
        const dy = ty - p.mesh.position.y;
        const dist = Math.hypot(dx, dy);

        if (dist <= p.speed * dt + 0.22) {
          releaseProjectileReservation(p);
          const idx = targetAlive ? activeEnemies.indexOf(p.target) : -1;
          const sKey = p.sourceKey || 'hero';
          const impactVec = new THREE.Vector3(tx, tyGround, 0.08);
          if (p.isFrostSplash) {
            spawnShockwaveRing(impactVec, 0x38bdf8, p.splashRadius || 1.85);
            for (let j = activeEnemies.length - 1; j >= 0; j--) {
              if (activeEnemies[j].dyingTimer >= 0) continue;
              if (Math.hypot(activeEnemies[j].mesh.position.x - tx, activeEnemies[j].mesh.position.y - tyGround) <= (p.splashRadius || 1.75)) {
                damageEnemy(j, p.dmg, false, p.slowSec || 3.2, 0, 0.25, p.armorPen || 0.25, sKey, p.extraFlags || null);
              }
            }
          } else if (p.isExplosive) {
            spawnShockwaveRing(impactVec, 0xfacc15, p.splashRadius || 1.65);
            for (let j = activeEnemies.length - 1; j >= 0; j--) {
              if (activeEnemies[j].dyingTimer >= 0) continue;
              if (Math.hypot(activeEnemies[j].mesh.position.x - tx, activeEnemies[j].mesh.position.y - tyGround) <= (p.splashRadius || 1.65)) {
                damageEnemy(j, p.dmg, true, 0, p.stunSec, p.knockback * 1.2, p.armorPen || 0.35, sKey, p.extraFlags || null);
              }
            }
          } else if (idx !== -1) {
            damageEnemy(idx, p.dmg, p.isCrit, p.slowSec, p.stunSec, p.knockback, p.armorPen || 0.35, sKey, p.extraFlags || null);
          }
          disposeProjectileMesh(p.mesh);
          activeProjectiles.splice(i, 1);
        } else {
          p.mesh.position.x += (dx / dist) * p.speed * dt;
          p.mesh.position.y += (dy / dist) * p.speed * dt;
          p.mesh.position.z = 0.14;
          if (p.isFrostSplash || p.isCannon || p.isStar) {
            p.mesh.rotation.z += dt * 9.0;
            p.mesh.rotation.y += dt * 6.0;
          }
        }
      }
    }
  }

  return {
    prepareDefenseArena,
    startSkirmish,
    startWaveDefense,
    stopCombatAndDefense,
    showDefenseNotice,
    preloadDefenseEnemyAssets: preloadAllEnemyGlbAssets,
    triggerCursorSmite,
    tryHandleBuildPadClick,
    updateBuildPadHover,
    triggerTacticalSkill,
    useConsumableItem,
    setWeaponType,
    applyWorldviewTheme,
    syncRPGStateFromPython,
    syncTypingHudPulse,
    getDesktopBuildPads,
    openBuildPadPopover,
    applyPadTowerAction,
    buildDefeatDiagnosis,
    openDefenseDefeatReport,
    hideDefenseDefeatReport,
    getDefenseTelemetry: () => combatState.telemetry,
    getRPGState: () => rpgState,
    isCombatActive: () => combatState.mode === 'SKIRMISH' || combatState.mode === 'WAVE_DEFENSE',
    updateWorldRPGDefense,
  };
}
