/**
 * RPG Life-Skill Solo Play System for Ppong-ppong-i (v2)
 * ------------------------------------------------------
 * Each activity is a multi-phase RPG skill sequence:
 *   prepare -> work loop -> climax (hit-stop) -> reward (item drop, EXP, rarity) -> exit
 * Features: smoothed pose blending on real arm/leg axes, held props tracked to the hand bone,
 * pooled particle FX (sparkle, puff, ring, emoji sprites), floating reward text,
 * item drop arc + bounce + magnetize, skill EXP / level-up pillar, rarity rolls.
 *
 * Rig axis notes (built-in rig, bones in T/A-pose with identity frames):
 *   right arm points +X: rz>0 raises it, ry<0 swings it forward.  left arm mirrored.
 *   legs point -Y: rx<0 swings forward.  spine/neck/head: rx>0 leans/nods forward.
 */

export function createSoloPlaySubsystem(ctx) {
  const { THREE, characterPivot, stageGroup, getRigBones, addBoneEulerOffset, playAnimation, triggerEmotionEmote } = ctx;

  const root = new THREE.Group();
  root.name = 'SoloPlayRPG';
  stageGroup.add(root);

  // ---------------------------------------------------------------- utils
  const clamp01 = (x) => Math.max(0, Math.min(1, x));
  const smooth = (x) => { x = clamp01(x); return x * x * (3 - 2 * x); };
  const outBack = (x) => { x = clamp01(x); const c = 1.70158; return 1 + (c + 1) * Math.pow(x - 1, 3) + c * Math.pow(x - 1, 2); };
  const lerp = (a, b, t) => a + (b - a) * t;
  const rand = (a, b) => a + Math.random() * (b - a);
  const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];
  const mat = (color, rough = 0.45, metal = 0.05, extra = {}) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal, ...extra });
  const glow = (color, opacity = 1) => new THREE.MeshBasicMaterial({ color, transparent: true, opacity, depthWrite: false, toneMapped: false });
  const mesh = (geo, m, x = 0, y = 0, z = 0) => { const o = new THREE.Mesh(geo, m); o.position.set(x, y, z); return o; };
  const tmpV = new THREE.Vector3();

  // ------------------------------------------------------- sprite textures (with LRU cap)
  const texCache = new Map();
  const MAX_TEX_CACHE = 80;
  function textTexture(text, color = '#ffffff', fontPx = 64) {
    const key = text + '|' + color + '|' + fontPx;
    if (texCache.has(key)) {
      const hit = texCache.get(key);
      texCache.delete(key);
      texCache.set(key, hit);
      return hit;
    }
    if (texCache.size >= MAX_TEX_CACHE) {
      const oldestKey = texCache.keys().next().value;
      const oldest = texCache.get(oldestKey);
      if (oldest && oldest.tex) oldest.tex.dispose();
      texCache.delete(oldestKey);
    }
    const c = document.createElement('canvas');
    const g = c.getContext('2d');
    const font = `900 ${fontPx}px "Malgun Gothic", "Segoe UI Emoji", sans-serif`;
    g.font = font;
    const w = Math.ceil(g.measureText(text).width) + 40;
    c.width = Math.max(64, w); c.height = Math.ceil(fontPx * 1.5);
    g.font = font; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.lineJoin = 'round'; g.lineWidth = fontPx * 0.16; g.strokeStyle = 'rgba(15,23,42,0.92)';
    g.strokeText(text, c.width / 2, c.height / 2);
    g.fillStyle = color; g.fillText(text, c.width / 2, c.height / 2);
    const tex = new THREE.CanvasTexture(c);
    tex.colorSpace = THREE.SRGBColorSpace;
    const entry = { tex, aspect: c.width / c.height };
    texCache.set(key, entry);
    return entry;
  }
  function makeSprite(text, color, height = 0.18) {
    const { tex, aspect } = textTexture(text, color);
    const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthTest: false, depthWrite: false }));
    s.scale.set(height * aspect, height, 1);
    s.renderOrder = 50;
    s.userData.baseScale = s.scale.clone();
    return s;
  }

  // ------------------------------------------------------------ FX pool
  const fx = [];
  const fxGroup = new THREE.Group();
  root.add(fxGroup);
  const sparkGeo = new THREE.SphereGeometry(0.022, 6, 6);
  const puffGeo = new THREE.SphereGeometry(0.05, 8, 8);
  const ringGeo = new THREE.TorusGeometry(0.3, 0.012, 6, 40);

  function addFx(obj, o) {
    if (fx.length > 220) { const old = fx.shift(); fxGroup.remove(old.obj); }
    fxGroup.add(obj);
    fx.push({ obj, vel: o.vel || new THREE.Vector3(), life: 0, max: o.max || 1, g: o.g || 0, grow: o.grow || 0,
      fade: o.fade !== false, wave: o.wave || 0, spin: o.spin || 0, ring: !!o.ring, item: o.item || null, startScale: obj.scale.clone() });
  }
  function burst(x, y, z, color = 0xfde047, n = 12, speed = 1.2, opts = {}) {
    for (let i = 0; i < n; i++) {
      const m = mesh(sparkGeo, glow(color), x, y, z);
      const a = Math.random() * Math.PI * 2, e = rand(0.2, 1.0);
      addFx(m, { vel: new THREE.Vector3(Math.cos(a) * speed * (1 - e * 0.5), speed * e * (opts.up || 1.2), Math.sin(a) * speed * 0.6), g: opts.g ?? -3.2, max: opts.max || rand(0.5, 0.9) });
    }
  }
  function puff(x, y, z, color = 0xcbd5e1, n = 4, opts = {}) {
    for (let i = 0; i < n; i++) {
      const m = mesh(puffGeo, glow(color, 0.55), x + rand(-0.05, 0.05), y, z + rand(-0.05, 0.05));
      addFx(m, { vel: new THREE.Vector3(rand(-0.15, 0.15), rand(0.15, 0.45) * (opts.up ?? 1), rand(-0.05, 0.1)), grow: opts.grow || 2.2, max: opts.max || rand(0.6, 1.0) });
    }
  }
  function ring(x, y, z, color = 0x38bdf8, opts = {}) {
    const m = mesh(ringGeo, glow(color, 0.9), x, y, z);
    if (opts.flat !== false) m.rotation.x = Math.PI / 2;
    m.scale.setScalar(0.1);
    addFx(m, { ring: true, grow: opts.size || 1.4, max: opts.max || 0.5 });
  }
  function floatEmoji(text, x, y, z, opts = {}) {
    const s = makeSprite(text, opts.color || '#ffffff', opts.size || 0.14);
    s.position.set(x, y, z);
    addFx(s, { vel: new THREE.Vector3(rand(-0.08, 0.08), opts.rise ?? 0.45, 0), wave: opts.wave ?? 0.25, max: opts.max || 1.4 });
  }
  function floatText(text, color = '#fde047', y = 1.75, size = 0.15, max = 1.9) {
    const s = makeSprite(text, color, size);
    s.position.set(0, y, 0.25);
    addFx(s, { vel: new THREE.Vector3(0, 0.28, 0), max });
  }
  function itemDrop(icon, fromY = 0.6) {
    const s = makeSprite(icon, '#ffffff', 0.24);
    const dir = Math.random() < 0.5 ? -1 : 1;
    s.position.set(dir * 0.1, fromY, 0.35);
    addFx(s, { item: { phase: 'arc', vx: dir * 0.55, vy: 2.0, t: 0 }, max: 2.6, fade: false });
  }
  function pillar() {
    const m = mesh(new THREE.CylinderGeometry(0.32, 0.42, 2.6, 24, 1, true), glow(0xfde68a, 0.35), 0, 1.3, 0);
    m.material.side = THREE.DoubleSide;
    addFx(m, { max: 1.4 });
    for (let i = 0; i < 3; i++) setTimeout(() => ring(0, 0.05, 0, 0xfacc15, { size: 2.2, max: 0.7 }), i * 180);
  }

  function updateFx(dt) {
    for (let i = fx.length - 1; i >= 0; i--) {
      const f = fx[i];
      f.life += dt;
      const k = f.life / f.max;
      if (k >= 1) { fxGroup.remove(f.obj); fx.splice(i, 1); continue; }
      const o = f.obj;
      if (f.item) {
        const it = f.item; it.t += dt;
        if (it.phase === 'arc') {
          it.vy += -6.5 * dt; o.position.x += it.vx * dt; o.position.y += it.vy * dt;
          if (o.position.y <= 0.12 && it.vy < 0) { o.position.y = 0.12; it.vy *= -0.42; it.vx *= 0.5; puff(o.position.x, 0.05, o.position.z, 0xe2e8f0, 2, { max: 0.5 });
            if (Math.abs(it.vy) < 0.6) { it.phase = 'rest'; it.t = 0; } }
        } else if (it.phase === 'rest') {
          o.position.y = 0.12 + Math.sin(it.t * 6) * 0.02;
          if (it.t > 0.55) { it.phase = 'magnet'; it.t = 0; }
        } else {
          o.position.lerp(tmpV.set(0, 0.75, 0.1), 1 - Math.exp(-7 * dt));
          o.scale.copy(o.userData.baseScale).multiplyScalar(Math.max(0.05, 1 - it.t * 1.6));
          if (it.t > 0.6) { burst(0, 0.75, 0.15, 0xfde047, 10, 0.8); fxGroup.remove(o); fx.splice(i, 1); }
        }
        continue;
      }
      f.vel.y += f.g * dt;
      o.position.addScaledVector(f.vel, dt);
      if (f.wave) o.position.x += Math.sin(f.life * 6 + i) * f.wave * dt;
      if (f.ring) o.scale.setScalar(0.1 + f.grow * smooth(k));
      else if (f.grow) o.scale.copy(f.startScale).multiplyScalar(1 + f.grow * k);
      if (f.spin) o.rotation.z += f.spin * dt;
      if (f.fade && o.material) o.material.opacity = (o.material.userData.o0 ??= o.material.opacity) * (1 - smooth((k - 0.55) / 0.45));
    }
  }

  // ---------------------------------------------------------- skills / XP
  let skillXP = {};
  let lastResult = null;
  const levelOf = (xp) => Math.floor(Math.sqrt(xp / 20)) + 1;
  const xpForLevel = (lv) => (lv - 1) * (lv - 1) * 20;
  function rollRarity(bonusRare = 0) {
    const r = Math.max(0, Math.random() - bonusRare);
    if (r < 0.08) return { tier: 'Legendary', kr: '전설', color: '#f59e0b', mult: 3 };
    if (r < 0.36) return { tier: 'Rare', kr: '희귀', color: '#38bdf8', mult: 1.6 };
    return { tier: 'Common', kr: '일반', color: '#e2e8f0', mult: 1 };
  }
  function grantReward(S, icon, itemName, baseXP, extraMeta = {}) {
    const toolBonus = (window.ppongRPGState && window.ppongRPGState.toolBonusRare) ? window.ppongRPGState.toolBonusRare : 0;
    const rar = rollRarity(toolBonus);
    const gained = Math.round(baseXP * rar.mult);
    const before = skillXP[S.key] || 0;
    const after = before + gained;
    skillXP[S.key] = after;
    const lvB = levelOf(before), lvA = levelOf(after);
    const into = after - xpForLevel(lvA), span = xpForLevel(lvA + 1) - xpForLevel(lvA);
    const bars = Math.round(clamp01(into / span) * 5);
    itemDrop(icon, 0.9);
    floatText(`${icon} ${itemName}${rar.tier !== 'Common' ? ` (${rar.kr}!)` : ''}`, rar.color, 1.72, 0.14, 2.2);
    setTimeout(() => floatText(`+EXP ${gained}`, '#a3e635', 1.55, 0.13, 1.6), 250);
    setTimeout(() => floatText(`${S.def.skill} Lv.${lvA} ${'▰'.repeat(bars)}${'▱'.repeat(5 - bars)}`, '#f8fafc', 1.4, 0.11, 1.8), 500);
    if (rar.tier !== 'Common') { ring(0, 0.05, 0, rar.tier === 'Legendary' ? 0xf59e0b : 0x38bdf8, { size: 1.8, max: 0.6 }); burst(0, 1.2, 0.2, 0xfde047, 22, 1.6); }
    if (lvA > lvB) { pillar(); setTimeout(() => floatText(`LEVEL UP! ${S.def.skill} Lv.${lvA}`, '#facc15', 1.95, 0.17, 2.2), 700); }
    triggerEmotionEmote && triggerEmotionEmote(rar.tier === 'Common' && lvA === lvB ? 'proud' : 'excited');
    lastResult = {
      key: S.key,
      skill: S.def.skill,
      item: itemName,
      icon,
      rarity: rar.kr,
      tier: rar.tier,
      gained,
      xp: after,
      level: lvA,
      leveledUp: lvA > lvB,
      ...extraMeta
    };
    if (typeof window.emitPpongSync === 'function') {
      window.emitPpongSync({
        type: 'solo_reward',
        ...lastResult
      });
    }
    if (typeof window.onPpongSoloReward === 'function') {
      window.onPpongSoloReward(lastResult);
    }
  }

  // --------------------------------------------------- pose blending core
  const POSE_BONES = ['hips', 'spine', 'chest', 'neck', 'head', 'leftArm', 'rightArm', 'leftForeArm', 'rightForeArm',
    'leftUpLeg', 'rightUpLeg', 'leftLeg', 'rightLeg', 'tailBase', 'leftEar', 'rightEar'];
  const cur = {}, tgt = {};
  POSE_BONES.forEach((b) => { cur[b] = [0, 0, 0]; tgt[b] = [0, 0, 0]; });
  const P = {
    reset() { POSE_BONES.forEach((b) => { tgt[b][0] = tgt[b][1] = tgt[b][2] = 0; }); },
    set(b, x, y, z) { const t = tgt[b]; t[0] = x; t[1] = y; t[2] = z; },
    add(b, x, y, z) { const t = tgt[b]; t[0] += x; t[1] += y; t[2] += z; },
    // semantic arms: up (raise), fwd (swing forward), elbow (forearm bend forward)
    armR(up, fwd = 0, elbow = 0) { P.set('rightArm', 0, -fwd, up); P.set('rightForeArm', 0, -elbow, 0); },
    armL(up, fwd = 0, elbow = 0) { P.set('leftArm', 0, fwd, -up); P.set('leftForeArm', 0, elbow, 0); },
    arms(up, fwd = 0, elbow = 0) { P.armR(up, fwd, elbow); P.armL(up, fwd, elbow); },
    lean(spine, chest = 0) { P.add('spine', spine, 0, 0); P.add('chest', chest, 0, 0); },
    head(nod, turn = 0, tilt = 0) { P.add('head', nod, turn, tilt); },
  };
  let blendRate = 14;
  function applyPose(dt, weight) {
    const b = getRigBones();
    const k = 1 - Math.exp(-blendRate * dt);
    for (const name of POSE_BONES) {
      const c = cur[name], t = tgt[name];
      c[0] += (t[0] * weight - c[0]) * k; c[1] += (t[1] * weight - c[1]) * k; c[2] += (t[2] * weight - c[2]) * k;
      if (b[name] && (Math.abs(c[0]) + Math.abs(c[1]) + Math.abs(c[2]) > 1e-4)) addBoneEulerOffset(b[name], c[0], c[1], c[2]);
    }
  }
  // Local position (in root space) of a hand bone, for attaching held props.
  function handPos(side, out) {
    const b = getRigBones();
    const bone = side === 'L' ? (b.leftHand || b.leftForeArm || b.leftArm) : (b.rightHand || b.rightForeArm || b.rightArm);
    if (!bone) return out.set(side === 'L' ? -0.45 : 0.45, 0.65, 0.1);
    bone.updateWorldMatrix(true, false);
    bone.getWorldPosition(out);
    return root.worldToLocal(out);
  }

  // ------------------------------------------------------------ registry
  const defs = {};
  const S = { active: false, key: '', def: null, t: 0, idx: -1, pt: 0, hitStop: 0, p: null, dur: 0, weight: 0, bounds: [] };

  function register(key, def) {
    let acc = 0;
    def.bounds = def.phases.map((ph) => { const s = acc; acc += ph.dur; return [s, acc]; });
    def.total = acc;
    defs[key] = def;
  }
  function hitStop(sec = 0.07) { S.hitStop = Math.max(S.hitStop, sec); }

  // =====================================================================
  // HERO 1: FISHING (Wait & Catch with cast, bite tell, strike, catch)
  // =====================================================================
  register('fishing', {
    title: '🎣 낚시하기', skill: '낚시', speech: '찌를 던져볼게요... 쉿, 입질 기다리는 중! 🎣',
    build(g) {
      const rod = new THREE.Group();
      const pole = mesh(new THREE.CylinderGeometry(0.008, 0.018, 0.9, 10), mat(0x92400e, 0.5));
      pole.position.y = 0.45; rod.add(pole);
      rod.add(mesh(new THREE.TorusGeometry(0.03, 0.008, 6, 14), mat(0x94a3b8, 0.3, 0.8), 0.02, 0.12, 0));
      const pond = mesh(new THREE.CircleGeometry(0.42, 40), mat(0x0ea5e9, 0.15, 0.1, { transparent: true, opacity: 0.75 }), 0.55, 0.012, 0.35);
      pond.rotation.x = -Math.PI / 2;
      const rim = mesh(new THREE.TorusGeometry(0.42, 0.03, 8, 40), mat(0x78716c, 0.9), 0.55, 0.015, 0.35); rim.rotation.x = Math.PI / 2;
      const bobber = new THREE.Group();
      bobber.add(mesh(new THREE.SphereGeometry(0.035, 12, 12), mat(0xef4444, 0.3)));
      bobber.add(mesh(new THREE.SphereGeometry(0.036, 12, 12, 0, Math.PI * 2, Math.PI / 2, Math.PI / 2), mat(0xffffff, 0.3)));
      const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints(Array.from({ length: 16 }, () => new THREE.Vector3())), glow(0xe0f2fe, 0.85));
      const fish = new THREE.Group();
      const body = mesh(new THREE.SphereGeometry(0.09, 16, 12), mat(0xf59e0b, 0.25, 0.6)); body.scale.set(1.6, 0.9, 0.6); fish.add(body);
      const tail = mesh(new THREE.ConeGeometry(0.07, 0.12, 4), mat(0xfbbf24, 0.3, 0.5), -0.17, 0, 0); tail.rotation.z = Math.PI / 2; fish.add(tail);
      fish.add(mesh(new THREE.SphereGeometry(0.015, 8, 8), mat(0x111827), 0.1, 0.03, 0.04));
      g.add(rod, pond, rim, bobber, line, fish);
      return { rod, pole, pond, bobber, line, fish, tail, tip: new THREE.Vector3(), hand: new THREE.Vector3(), bob: new THREE.Vector3(0.55, 0.03, 0.35) };
    },
    start(p) { p.fish.visible = false; p.bobber.visible = false; p.line.visible = false; p.rod.scale.setScalar(0.01); p.pond.scale.setScalar(0.01); p.species = pick([['🐟', '황금 잉어'], ['🐠', '무지개 송어'], ['🐡', '복어'], ['🦑', '꼬마 오징어'], ['👢', '낡은 장화']]); },
    phases: [
      { name: 'approach', dur: 0.7, anim: 'Idle', update(p, k) { p.rod.scale.setScalar(outBack(k)); p.pond.scale.setScalar(outBack(k)); P.armR(-0.2, 0.6, 0.5); P.armL(-0.8, 0.2); } },
      { name: 'windup', dur: 0.45, update(p, k) { P.armR(1.1 * smooth(k), 0.3, 0.6); P.lean(-0.15 * smooth(k), -0.1); P.head(-0.1); p.rodAngle = lerp(0.2, -1.6, smooth(k)); } },
      { name: 'cast', dur: 0.45, enter(p) { blendRate = 30; p.bobber.visible = true; p.line.visible = true; p.castT = 0; },
        update(p, k) { P.armR(-0.1, 1.0, 0.1); P.lean(0.18, 0.1); P.head(0.12); p.rodAngle = lerp(-1.6, 0.9, outBack(k));
          const s = smooth(k); p.bob.set(lerp(p.tip.x, 0.55, s), lerp(p.tip.y, 0.03, s) + Math.sin(s * Math.PI) * 0.35, lerp(p.tip.z, 0.35, s)); } },
      { name: 'wait', dur: 2.8, anim: 'Sit', enter(p) { blendRate = 10; ring(0.55, 0.03, 0.35, 0xe0f2fe, { size: 0.5 }); burst(0.55, 0.05, 0.35, 0xbae6fd, 8, 0.6); p.nextRipple = 0.9; },
        update(p, k, t, dt) { P.armR(-0.15, 0.9, 0.4); P.armL(-0.7, 0.5, 0.5); P.head(0.12 + Math.sin(t * 2) * 0.04, Math.sin(t * 0.7) * 0.12, 0);
          P.set('tailBase', 0, 0, Math.sin(t * 3) * 0.3); p.rodAngle = 0.9 + Math.sin(t * 1.3) * 0.04;
          p.bob.set(0.55, 0.03 + Math.sin(t * 4) * 0.012, 0.35);
          if ((p.nextRipple -= dt) <= 0) { p.nextRipple = 0.9; ring(0.55, 0.02, 0.35, 0xbae6fd, { size: 0.35, max: 0.8 }); }
          if (k > 0.82) { P.set('leftEar', -0.4, 0, 0); P.set('rightEar', -0.4, 0, 0); p.bob.y -= (Math.sin((k - 0.82) * 60) > 0 ? 0.04 : 0); } } },
      { name: 'tell', dur: 0.35, enter() { floatEmoji('❗', 0, 1.55, 0.2, { size: 0.26, rise: 0.15, max: 0.8, color: '#ef4444' }); triggerEmotionEmote && triggerEmotionEmote('surprised'); hitStop(0.1); },
        update(p) { P.armR(-0.1, 0.9, 0.5); P.head(-0.1); P.set('leftEar', -0.5, 0, 0); P.set('rightEar', -0.5, 0, 0); p.bob.y = -0.02; } },
      { name: 'strike', dur: 1.15, anim: 'Idle', enter() { blendRate = 22; },
        update(p, k, t) { const jerk = Math.sin(t * 30) * 0.12; P.armR(0.5 + jerk, 0.8, 0.9); P.armL(0.3 + jerk, 0.9, 0.9); P.lean(-0.28, -0.12); P.set('leftUpLeg', -0.25, 0, 0);
          p.rodAngle = -0.6 + jerk; p.pole.scale.y = 0.92 + Math.sin(t * 25) * 0.03;
          p.bob.set(0.55 + Math.sin(t * 22) * 0.05, -0.01, 0.35 + Math.cos(t * 19) * 0.04);
          if (Math.random() < 0.3) burst(p.bob.x, 0.03, p.bob.z, 0xbae6fd, 2, 0.7, { max: 0.4 }); } },
      { name: 'catch', dur: 0.6, enter(p) { hitStop(0.09); p.fish.visible = true; p.bobber.visible = false; p.line.visible = false; p.fishFrom = p.bob.clone();
          ring(0.55, 0.03, 0.35, 0xffffff, { size: 0.9 }); burst(0.55, 0.05, 0.35, 0x7dd3fc, 22, 1.8); floatEmoji('💦', 0.55, 0.3, 0.4, { size: 0.2 }); },
        update(p, k, t) { P.arms(1.2, 0.3, 0.3); P.lean(-0.2); const s = smooth(k);
          p.fish.position.set(lerp(p.fishFrom.x, 0, s), lerp(0.05, 1.62, s) + Math.sin(s * Math.PI) * 0.4, lerp(p.fishFrom.z, 0.15, s));
          p.fish.rotation.set(t * 15, 0, Math.sin(t * 20) * 0.5); p.rodAngle = 0.3; } },
      { name: 'reward', dur: 1.6, anim: 'WaveJump', enter(p) { grantReward(S, p.species[0], p.species[1], 30); },
        update(p, k, t) { P.arms(2.4, 0.2, 0.4); P.head(-0.25); p.fish.position.set(0, 1.62 + Math.sin(t * 5) * 0.04, 0.15); p.fish.rotation.set(0, t * 2, Math.sin(t * 12) * 0.2);
          p.tail.rotation.y = Math.sin(t * 20) * 0.5; if (k > 0.7) p.fish.scale.setScalar(Math.max(0.01, 1 - (k - 0.7) / 0.3)); } },
      { name: 'exit', dur: 0.55, anim: 'Idle', update(p, k) { const s = 1 - smooth(k); p.rod.scale.setScalar(Math.max(0.01, s)); p.pond.scale.setScalar(Math.max(0.01, s)); P.armR(-0.6, 0.2); } },
    ],
    frame(p) {
      handPos('R', p.hand);
      p.rod.position.copy(p.hand);
      p.rod.rotation.set(-(p.rodAngle ?? 0.3), 0, -0.25);
      p.rod.updateMatrixWorld(true);
      p.tip.set(0, 0.9 * p.pole.scale.y, 0); p.pole.parent.localToWorld(p.tip); root.worldToLocal(p.tip);
      p.bobber.position.copy(p.bob);
      const pos = p.line.geometry.attributes.position;
      for (let i = 0; i < 16; i++) { const f = i / 15; pos.setXYZ(i, lerp(p.tip.x, p.bob.x, f), lerp(p.tip.y, p.bob.y, f) - Math.sin(f * Math.PI) * 0.08, lerp(p.tip.z, p.bob.z, f)); }
      pos.needsUpdate = true;
    },
  });

  // =====================================================================
  // HERO 2: CAMPING (gather logs -> friction fire -> ignite -> roast -> eat)
  // =====================================================================
  register('camping', {
    title: '🔥 캠핑 & 마시멜로', skill: '캠핑', speech: '장작 모아서 불 피우는 중... 오늘 밤은 캠핑이에요! ⛺',
    build(g) {
      const logs = []; for (let i = 0; i < 3; i++) { const l = mesh(new THREE.CylinderGeometry(0.03, 0.035, 0.3, 10), mat(0x78350f, 0.9)); l.rotation.set(Math.PI / 2, 0, (i * Math.PI) / 3); g.add(l); logs.push(l); }
      const fire = new THREE.Group(); fire.position.set(0, 0.04, 0.42);
      const outer = mesh(new THREE.ConeGeometry(0.1, 0.28, 12), glow(0xf97316, 0.9), 0, 0.14, 0);
      const inner = mesh(new THREE.ConeGeometry(0.055, 0.18, 10), glow(0xfde047, 0.95), 0, 0.1, 0);
      fire.add(outer, inner);
      const light = new THREE.PointLight(0xff9a3c, 0, 2.2); light.position.set(0, 0.25, 0.42);
      const tent = mesh(new THREE.ConeGeometry(0.32, 0.45, 4), mat(0x16a34a, 0.7), -0.55, 0.22, -0.15); tent.rotation.y = Math.PI / 4;
      const stick = new THREE.Group(); stick.add(mesh(new THREE.CylinderGeometry(0.007, 0.007, 0.42, 6), mat(0xa16207), 0, 0.21, 0));
      const mallow = mesh(new THREE.CylinderGeometry(0.03, 0.03, 0.05, 12), mat(0xfffbeb, 0.6), 0, 0.42, 0); stick.add(mallow);
      g.add(fire, light, tent, stick);
      return { logs, fire, outer, inner, light, tent, stick, mallow, hand: new THREE.Vector3() };
    },
    start(p) { p.logs.forEach((l, i) => { l.position.set(0, 1.4, 0.42); l.visible = false; }); p.fire.scale.setScalar(0.01); p.light.intensity = 0; p.tent.scale.setScalar(0.01); p.stick.visible = false; p.mallow.material.color.set(0xfffbeb); p.smokeT = 0; },
    phases: [
      { name: 'gather', dur: 1.0, anim: 'Idle', update(p, k) { p.tent.scale.setScalar(outBack(k * 1.5));
          p.logs.forEach((l, i) => { const lk = clamp01((k - i * 0.25) / 0.4); l.visible = lk > 0; const y = lk < 1 ? lerp(1.4, 0.035, lk * lk) : 0.035; if (l.userData.landed !== true && lk >= 1) { l.userData.landed = true; puff(0, 0.05, 0.42, 0xd6d3d1, 3); } l.position.set(0, y, 0.42); });
          P.armR(0.4, 0.5); P.armL(0.4, 0.5); P.head(0.25); } },
      { name: 'friction', dur: 1.8, anim: 'Sit', update(p, k, t, dt) { const rub = Math.sin(t * 22) * 0.3; P.armR(-0.3, 1.1, 0.6 + rub); P.armL(-0.3, 1.1, 0.6 - rub); P.lean(0.25, 0.1); P.head(0.3);
          if ((p.smokeT -= dt) <= 0) { p.smokeT = lerp(0.35, 0.08, k); puff(0, 0.08, 0.42, 0x94a3b8, 1, { grow: 1.5 }); if (k > 0.5) burst(0, 0.06, 0.42, 0xf97316, 2, 0.5, { max: 0.3 }); } } },
      { name: 'ignite', dur: 0.6, enter(p) { hitStop(0.08); burst(0, 0.15, 0.42, 0xfb923c, 26, 1.6, { up: 1.6 }); ring(0, 0.05, 0.42, 0xf97316, { size: 1.0 }); triggerEmotionEmote && triggerEmotionEmote('surprised'); floatEmoji('🔥', 0, 0.6, 0.45, { size: 0.22 }); },
        update(p, k) { p.fire.scale.setScalar(outBack(k)); p.light.intensity = lerp(3.5, 1.6, k); P.set('hips', -0.12, 0, 0); P.head(-0.35); P.arms(0.6, 0.4); } },
      { name: 'roast', dur: 3.0, enter(p) { p.stick.visible = true; p.emberT = 0; },
        update(p, k, t, dt) { P.armR(-0.1, 1.0, 0.5); P.armL(-0.4, 0.9, 0.9); P.head(0.15, 0, Math.sin(t * 0.8) * 0.15); P.set('tailBase', 0, 0, Math.sin(t * 2) * 0.25);
          p.mallow.material.color.lerpColors(new THREE.Color(0xfffbeb), new THREE.Color(0xb45309), smooth(k));
          if ((p.emberT -= dt) <= 0) { p.emberT = 0.12; burst(rand(-0.05, 0.05), 0.25, 0.42, pick([0xf97316, 0xfde047]), 1, 0.4, { g: 0.4, max: 1.0 }); }
          if (k > 0.85 && !p.toasty) { p.toasty = true; floatEmoji('✨', 0.2, 0.7, 0.45, { size: 0.14 }); } } },
      { name: 'eat', dur: 0.7, update(p, k) { P.armR(0.5 * smooth(k), 1.2, 1.6 * smooth(k)); P.head(lerp(0.2, -0.15, smooth(k)));
          if (k > 0.6 && !p.ate) { p.ate = true; p.mallow.visible = false; for (let i = 0; i < 3; i++) floatEmoji('💗', rand(-0.15, 0.15), 1.3, 0.3, { size: 0.12 }); } } },
      { name: 'reward', dur: 1.5, anim: 'HappySpin', enter() { grantReward(S, '🍡', pick(['노릇한 마시멜로', '황금빛 마시멜로', '스모어 쿠키']), 25); },
        update() { P.arms(1.6, 0.2); } },
      { name: 'exit', dur: 0.7, anim: 'Idle', enter(p) { puff(0, 0.2, 0.42, 0x64748b, 5); },
        update(p, k) { const s = Math.max(0.01, 1 - smooth(k)); p.fire.scale.setScalar(s); p.light.intensity = 1.6 * s; p.tent.scale.setScalar(s); p.logs.forEach((l) => l.scale.setScalar(s)); p.stick.visible = false; } },
    ],
    start2(p) { p.logs.forEach((l) => { l.userData.landed = false; l.scale.setScalar(1); }); p.mallow.visible = true; p.ate = false; p.toasty = false; },
    frame(p, t) {
      p.outer.scale.set(1 + Math.sin(t * 17) * 0.08, 1 + Math.sin(t * 13) * 0.18, 1);
      p.inner.scale.y = 1 + Math.sin(t * 21) * 0.2;
      if (p.light.intensity > 0.2) p.light.intensity += Math.sin(t * 29) * 0.05;
      handPos('R', p.hand); p.stick.position.copy(p.hand); p.stick.rotation.set(1.05, 0, -0.35);
    },
  });

  // =====================================================================
  // HERO 3: BUILD HOUSE (place 4 blocks w/ hammer beats -> roof drop -> showcase)
  // =====================================================================
  register('build_house', {
    title: '🏠 집 짓기', skill: '건축', speech: '설계도 확인 완료! 뚝딱뚝딱 집을 지어볼게요 🔨',
    build(g) {
      const house = new THREE.Group(); house.position.set(-0.42, 0, 0.38); g.add(house);
      const colors = [0xfca5a5, 0x93c5fd, 0xfde68a, 0x86efac];
      const slots = [[-0.08, 0.06], [0.08, 0.06], [-0.08, 0.18], [0.08, 0.18]];
      const blocks = slots.map(([x, y], i) => { const b = mesh(new THREE.BoxGeometry(0.15, 0.12, 0.18), mat(colors[i], 0.65)); b.userData.slot = new THREE.Vector3(x, y, 0); house.add(b); return b; });
      const roof = mesh(new THREE.ConeGeometry(0.24, 0.2, 4), mat(0xb91c1c, 0.55), 0, 0.34, 0); roof.rotation.y = Math.PI / 4; house.add(roof);
      const win = mesh(new THREE.PlaneGeometry(0.06, 0.06), new THREE.MeshStandardMaterial({ color: 0x1e293b, emissive: 0xfde047, emissiveIntensity: 0 }), 0.08, 0.18, 0.091); house.add(win);
      const door = mesh(new THREE.PlaneGeometry(0.05, 0.08), mat(0x7c2d12), -0.08, 0.04, 0.091); house.add(door);
      const pile = new THREE.Group(); pile.position.set(0.5, 0, 0.3); g.add(pile);
      const hammer = new THREE.Group();
      hammer.add(mesh(new THREE.CylinderGeometry(0.012, 0.014, 0.22, 8), mat(0x92400e), 0, 0.11, 0));
      const hh = mesh(new THREE.BoxGeometry(0.1, 0.05, 0.05), mat(0x64748b, 0.35, 0.8), 0, 0.23, 0); hammer.add(hh);
      g.add(hammer);
      return { house, blocks, roof, win, door, pile, hammer, hand: new THREE.Vector3() };
    },
    start(p) { p.blocks.forEach((b) => { b.visible = false; b.scale.setScalar(1); }); p.roof.visible = false; p.win.material.emissiveIntensity = 0; p.door.visible = false; p.house.scale.setScalar(1); p.house.visible = true; p.hammer.visible = false; p.swing = 0; p.placed = -1; },
    phases: [
      { name: 'plan', dur: 0.9, anim: 'Curious', enter() { floatEmoji('📐', -0.42, 0.6, 0.4, { size: 0.18 }); },
        update(p, k, t) { const r = Math.sin(t * 15) * 0.2; P.armR(-0.2, 1.0, 1.0 + r); P.armL(-0.2, 1.0, 1.0 - r); P.head(0.15, 0.35); } },
      { name: 'build', dur: 4.4, anim: 'Idle', enter(p) { p.hammer.visible = true; blendRate = 26; },
        update(p, k, t) {
          const beat = 1.1, i = Math.min(3, Math.floor((k * 4.4) / beat)), bt = ((k * 4.4) % beat) / beat;
          const b = p.blocks[i];
          if (bt < 0.3) { // carry & place
            const s = smooth(bt / 0.3); b.visible = true;
            b.position.set(lerp(0.85, b.userData.slot.x, s), b.userData.slot.y + Math.sin(s * Math.PI) * 0.35, lerp(-0.1, 0, s));
            P.lean(0.35 * (1 - s)); P.armR(-0.3, 0.9); P.armL(-0.3, 0.9); P.head(0.2, 0.4 * s);
            if (s >= 0.999 && p.placed < i) { p.placed = i; b.scale.set(1.1, 0.7, 1.1); puff(-0.42 + b.userData.slot.x, 0.04, 0.4, 0xd6d3d1, 3); }
          } else { // 3 hammer strikes
            const ht = ((bt - 0.3) / 0.7) * 3, local = ht % 1, strike = Math.floor(ht);
            const down = local > 0.55; P.armR(down ? -0.1 : 1.7, 0.9, down ? 0.4 : 1.4); P.armL(-0.5, 0.8, 0.6);
            P.lean(down ? 0.22 : -0.08, down ? 0.12 : 0); P.head(down ? 0.25 : 0.05, 0.45);
            p.swing = down ? -0.4 : 1.4;
            const id = i * 10 + strike;
            if (down && p.lastStrike !== id) { p.lastStrike = id; const bx = -0.42 + b.userData.slot.x, by = b.userData.slot.y + 0.06;
              burst(bx, by, 0.48, 0xfbbf24, 5, 1.0, { max: 0.45 }); if (strike === 2) floatEmoji('쾅!', bx, by + 0.15, 0.5, { size: 0.12, color: '#fde047', max: 0.7 }); hitStop(0.05); }
          }
          p.blocks.forEach((bb) => bb.scale.lerp(tmpV.set(1, 1, 1), 0.2));
        } },
      { name: 'roof', dur: 1.0, anim: 'Jump', enter(p) { p.roof.visible = true; p.hammer.visible = false; blendRate = 14; },
        update(p, k) { const s = clamp01(k / 0.45); p.roof.position.y = s < 1 ? lerp(1.4, 0.34, s * s) : 0.34;
          if (s >= 1 && !p.roofed) { p.roofed = true; hitStop(0.08); p.door.visible = true; ring(-0.42, 0.04, 0.38, 0xfacc15, { size: 1.2 }); burst(-0.42, 0.45, 0.4, 0xf472b6, 24, 1.6); }
          p.house.scale.setScalar(1 + (s >= 1 ? Math.sin((k - 0.45) * 18) * 0.12 * (1 - k) : 0)); p.win.material.emissiveIntensity = smooth((k - 0.45) / 0.55) * 1.2; P.arms(2.0, 0.3); } },
      { name: 'reward', dur: 1.5, anim: 'Idle', enter() { grantReward(S, '🏠', pick(['아늑한 오두막', '알록달록 블록하우스', '동화 속 집']), 40); },
        update() { P.arms(-0.5, -0.3, 1.6); P.lean(-0.18, -0.1); P.head(-0.15, 0.3); } },
      { name: 'exit', dur: 0.8, update(p, k) { p.house.scale.setScalar(Math.max(0.01, 1 - smooth(k))); if (k > 0.95) p.house.visible = false; } },
    ],
    start2(p) { p.roofed = false; p.lastStrike = -1; },
    frame(p) { handPos('R', p.hand); p.hammer.position.copy(p.hand); p.hammer.rotation.set(0.3, 0, -0.6 - p.swing * 0.6); },
  });

  // =====================================================================
  // HERO 4: BARISTA (grind -> brew -> latte art -> present -> rating)
  // =====================================================================
  register('barista', {
    title: '☕ 바리스타', skill: '바리스타', speech: '원두 갈고, 추출하고, 라떼아트까지! 한 잔 내려드릴게요 ☕',
    build(g) {
      const counter = mesh(new THREE.BoxGeometry(0.75, 0.32, 0.26), mat(0x78350f, 0.6), 0, 0.16, 0.45); g.add(counter);
      const top = mesh(new THREE.BoxGeometry(0.78, 0.02, 0.28), mat(0xf5f5f4, 0.3), 0, 0.33, 0.45); g.add(top);
      const machine = new THREE.Group(); machine.position.set(-0.22, 0.34, 0.42); g.add(machine);
      machine.add(mesh(new THREE.BoxGeometry(0.2, 0.22, 0.16), mat(0xb91c1c, 0.3, 0.4), 0, 0.11, 0));
      machine.add(mesh(new THREE.CylinderGeometry(0.02, 0.02, 0.05, 8), mat(0xcbd5e1, 0.2, 0.9), 0.0, 0.03, 0.09));
      const grinder = new THREE.Group(); grinder.position.set(0.22, 0.34, 0.42); g.add(grinder);
      grinder.add(mesh(new THREE.CylinderGeometry(0.05, 0.06, 0.12, 12), mat(0x44403c, 0.4), 0, 0.06, 0));
      const crank = mesh(new THREE.BoxGeometry(0.1, 0.012, 0.012), mat(0xcbd5e1, 0.2, 0.9), 0.05, 0.13, 0); grinder.add(crank);
      const cup = new THREE.Group(); cup.add(mesh(new THREE.CylinderGeometry(0.045, 0.035, 0.07, 16, 1, true), mat(0xffffff, 0.3, 0, { side: THREE.DoubleSide })));
      const coffee = mesh(new THREE.CircleGeometry(0.043, 20), mat(0x6b3a1e, 0.4), 0, 0, 0); coffee.rotation.x = -Math.PI / 2; cup.add(coffee);
      const art = makeSprite('🤍', '#ffffff', 0.05); art.position.y = 0.04; cup.add(art);
      g.add(cup);
      const stream = mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.1, 6), mat(0x3f2210), -0.22, 0.38, 0.51); g.add(stream);
      return { counter, top, machine, grinder, crank, cup, coffee, art, stream, all: [counter, top, machine, grinder, cup, stream] };
    },
    start(p) { p.all.forEach((o) => o.scale.setScalar(0.01)); p.cup.position.set(-0.22, 0.36, 0.51); p.coffee.position.y = -0.03; p.art.visible = false; p.stream.visible = false; p.steamT = 0; },
    phases: [
      { name: 'setup', dur: 0.8, anim: 'Idle', update(p, k) { p.all.forEach((o, i) => { if (o !== p.stream) o.scale.setScalar(outBack(clamp01(k * 1.4 - i * 0.08))); }); P.arms(0.2, 0.6, 0.6); } },
      { name: 'grind', dur: 1.3, update(p, k, t) { const a = t * 11; p.crank.rotation.y = a; P.armR(0.1 + Math.sin(a) * 0.25, 0.9 + Math.cos(a) * 0.2, 0.8); P.armL(-0.3, 0.8, 0.9); P.head(0.25, -0.3);
          p.grinder.position.x = 0.22 + Math.sin(t * 60) * 0.004; if (Math.random() < 0.25) burst(0.22, 0.4, 0.45, 0x78350f, 1, 0.4, { max: 0.5 }); } },
      { name: 'brew', dur: 1.4, enter(p) { p.stream.visible = true; },
        update(p, k, t, dt) { P.lean(0.22, 0.1); P.head(0.3, 0.35); P.armR(-0.2, 1.0, 0.8); P.armL(-0.2, 1.0, 0.8);
          p.stream.scale.set(1, 1 + Math.sin(t * 30) * 0.1, 1); p.coffee.position.y = lerp(-0.03, 0.028, smooth(k));
          if ((p.steamT -= dt) <= 0) { p.steamT = 0.2; puff(-0.22, 0.42, 0.51, 0xf1f5f9, 1, { grow: 1.2, max: 0.8 }); } } },
      { name: 'latteArt', dur: 1.3, enter(p) { p.stream.visible = false; p.art.visible = true; triggerEmotionEmote && triggerEmotionEmote('focused'); },
        update(p, k, t) { p.cup.position.lerp(tmpV.set(0, 0.36, 0.51), 0.15); P.armR(0.1, 1.0, 0.9 + Math.sin(t * 14) * 0.15); P.armL(-0.1, 1.0, 1.0); P.head(0.35, 0, 0.2);
          const s = outBack(k); p.art.scale.copy(p.art.userData.baseScale).multiplyScalar(Math.max(0.01, s)); } },
      { name: 'present', dur: 1.7, anim: 'Idle', enter() { grantReward(S, '☕', pick(['하트 라떼', '로제타 라떼', '백조 라떼아트']), 25); },
        update(p, k, t) { const s = smooth(clamp01(k / 0.4)); p.cup.position.set(0, lerp(0.36, 0.7, s), lerp(0.51, 0.6, s)); P.arms(0.0, 1.3, 1.0); P.head(k > 0.6 ? 0.25 : -0.1);
          [0.2, 0.35, 0.5].forEach((th, i) => { if (k > th && !p['star' + i]) { p['star' + i] = true; floatEmoji('⭐', -0.2 + i * 0.2, 1.0, 0.5, { size: 0.15, rise: 0.25 }); } });
          if (Math.random() < 0.08) floatEmoji('♨️', 0, 0.85, 0.6, { size: 0.1, rise: 0.3, max: 0.9 }); } },
      { name: 'exit', dur: 0.7, update(p, k, t) { P.armL(-0.2, 0.9, 0.5 + Math.sin(t * 9) * 0.3); p.all.forEach((o) => o.scale.setScalar(Math.max(0.01, 1 - smooth(k)))); } },
    ],
    start2(p) { p.star0 = p.star1 = p.star2 = false; },
  });

  // =====================================================================
  // HERO 5: GUITAR (tune -> 120bpm groove -> solo -> power chord -> bow)
  // =====================================================================
  register('music_guitar', {
    title: '🎸 기타 연주', skill: '연주', speech: '튜닝 완료! 120bpm 라이브 갑니다~ 🎸🎶',
    build(g) {
      const gtr = new THREE.Group(); g.add(gtr);
      const body = mesh(new THREE.SphereGeometry(0.13, 18, 14), mat(0xd97706, 0.35)); body.scale.set(1, 1.25, 0.35); gtr.add(body);
      const hole = mesh(new THREE.CircleGeometry(0.04, 18), mat(0x1c1917), 0, 0.02, 0.047); gtr.add(hole);
      const neck = mesh(new THREE.BoxGeometry(0.035, 0.36, 0.02), mat(0x451a03, 0.5), 0, 0.33, 0); gtr.add(neck);
      gtr.add(mesh(new THREE.BoxGeometry(0.05, 0.07, 0.025), mat(0x292524), 0, 0.53, 0));
      const spot = mesh(new THREE.ConeGeometry(0.55, 1.9, 32, 1, true), glow(0xfef9c3, 0.0), 0, 1.0, 0); spot.material.side = THREE.DoubleSide; g.add(spot);
      return { gtr, spot, hand: new THREE.Vector3() };
    },
    start(p) { p.gtr.scale.setScalar(0.01); p.spot.material.opacity = 0; p.noteT = 0; p.lastBeat = -1; },
    phases: [
      { name: 'tune', dur: 0.9, anim: 'Idle', enter() { floatEmoji('♪', 0.2, 0.9, 0.4, { size: 0.14 }); },
        update(p, k) { p.gtr.scale.setScalar(outBack(k)); p.gtr.userData.spin = (1 - smooth(k)) * Math.PI * 2; P.armR(-0.4, 0.8, 0.7); P.armL(0.2, 0.9, 0.3); P.head(0.1, 0, 0.3); } },
      { name: 'groove', dur: 4.0, anim: 'Idle', update(p, k, t) {
          const bpm = 120, beatT = t * bpm / 60, ph = beatT % 1, beat = Math.floor(beatT);
          const strum = ph < 0.3 ? smooth(ph / 0.3) : 1 - smooth((ph - 0.3) / 0.7);
          P.armR(-0.35 + strum * 0.35, 0.8, 0.9 - strum * 0.4); P.armL(0.2 + (beat % 4 < 2 ? 0.05 : -0.05), 0.95, 0.3);
          P.head(0.12 * Math.abs(Math.sin(Math.PI * beatT)), 0, 0.08); P.set('hips', 0, 0, Math.sin(Math.PI * beatT) * 0.06);
          P.set('tailBase', 0, 0, Math.sin(2 * Math.PI * beatT) * 0.45); P.set('rightUpLeg', ph < 0.2 ? -0.18 : 0, 0, 0);
          if (beat !== p.lastBeat) { p.lastBeat = beat; floatEmoji(pick(['♪', '♫', '♬']), rand(0.05, 0.35), 0.75, 0.35, { size: 0.13, color: pick(['#f472b6', '#38bdf8', '#a3e635', '#fde047', '#c084fc']) }); }
        } },
      { name: 'solo', dur: 1.3, enter(p) { ring(0, 0.04, 0, 0xc084fc, { size: 1.6 }); },
        update(p, k, t) { const ph = (t * 4) % 1; P.armR(-0.2 + Math.sin(ph * Math.PI) * 0.4, 0.8, 0.7); P.armL(0.5, 0.9, 0.2); P.lean(-0.3, -0.2); P.head(-0.3);
          p.gtr.userData.tilt = 0.5 * smooth(k); p.spot.material.opacity = 0.18 * smooth(k);
          if (Math.random() < 0.35) floatEmoji(pick(['♪', '♫']), rand(-0.3, 0.4), 0.8, 0.3, { size: 0.12, color: pick(['#f472b6', '#38bdf8', '#fde047']) }); } },
      { name: 'powerChord', dur: 0.7, anim: 'Jump', enter() { hitStop(0.09); for (let i = 0; i < 12; i++) { const a = (i / 12) * Math.PI * 2; floatEmoji('♪', Math.cos(a) * 0.3, 0.8 + Math.sin(a) * 0.3, 0.3, { size: 0.12, color: '#fde047', max: 0.9 }); } ring(0, 0.8, 0.2, 0xfde047, { flat: false, size: 2.0 }); },
        update() { P.armR(2.4, 0.2, 0.2); P.armL(0.4, 0.9, 0.2); P.head(-0.3); } },
      { name: 'bow', dur: 1.5, anim: 'Idle', enter() { grantReward(S, '👏', pick(['앵콜 요청!', '관객 기립박수', '팬 +3명']), 30); for (let i = 0; i < 4; i++) floatEmoji('👏', rand(-0.4, 0.4), 0.9, 0.3, { size: 0.14 }); },
        update(p, k) { P.lean(0.35, 0.15); P.head(0.4); P.armR(-0.6, 0.6); P.armL(-0.4, 0.9, 0.6); p.spot.material.opacity = 0.18 * (1 - k); } },
      { name: 'exit', dur: 0.6, update(p, k) { p.gtr.scale.setScalar(Math.max(0.01, 1 - smooth(k))); } },
    ],
    frame(p) {
      handPos('L', p.hand);
      const ud = p.gtr.userData;
      p.gtr.position.set(0.06, 0.62, 0.3);
      p.gtr.rotation.set(0.15, ud.spin || 0, -0.95 + (ud.tilt || 0));
    },
  });

  // =====================================================================
  // HERO 6: MINING (Sub-Desktop Excavation: prospect -> 4 pickaxe strikes w/ crack decals & dirt mounds -> crystal vein shatter -> restore)
  // =====================================================================
  register('mining', {
    title: '⛏️ 바탕화면 채굴', skill: '채굴', speech: '광맥 반응 감지! 바탕화면 지층을 채굴해 광석과 유물을 캐낼게요! ⛏️💎',
    build(g) {
      // 1. Held 3D Pickaxe
      const pickaxe = new THREE.Group();
      const shaft = mesh(new THREE.CylinderGeometry(0.012, 0.015, 0.48, 10), mat(0x78350f, 0.7), 0, 0.22, 0);
      pickaxe.add(shaft);
      const collar = mesh(new THREE.BoxGeometry(0.048, 0.045, 0.045), mat(0x475569, 0.35, 0.8), 0, 0.42, 0);
      pickaxe.add(collar);
      const bladeL = mesh(new THREE.ConeGeometry(0.028, 0.16, 6), mat(0x38bdf8, 0.25, 0.85), -0.08, 0.42, 0);
      bladeL.rotation.z = Math.PI / 2 + 0.18;
      const bladeR = mesh(new THREE.ConeGeometry(0.028, 0.16, 6), mat(0x38bdf8, 0.25, 0.85), 0.08, 0.42, 0);
      bladeR.rotation.z = -Math.PI / 2 - 0.18;
      pickaxe.add(bladeL, bladeR);
      g.add(pickaxe);

      // 2. Sub-Desktop Pit & Radial Crack Decal Group at (0.36, 0.012, 0.38)
      const site = new THREE.Group();
      site.position.set(0.36, 0.008, 0.38);
      g.add(site);

      const pitDisc = mesh(new THREE.CircleGeometry(0.24, 24), mat(0x0f172a, 0.95), 0, 0.002, 0);
      pitDisc.rotation.x = -Math.PI / 2;
      site.add(pitDisc);

      const cracks = [];
      for (let i = 0; i < 6; i++) {
        const ang = (i / 6) * Math.PI * 2 + 0.2;
        const cr = mesh(new THREE.BoxGeometry(0.26, 0.004, 0.016), glow(0x38bdf8, 0.85), Math.cos(ang) * 0.12, 0.005, Math.sin(ang) * 0.12);
        cr.rotation.y = -ang;
        site.add(cr);
        cracks.push(cr);
      }

      // 3. 8 Bevelled 3D Dirt Mounds around pit rim
      const mounds = [];
      for (let i = 0; i < 8; i++) {
        const ang = (i / 8) * Math.PI * 2;
        const md = mesh(new THREE.DodecahedronGeometry(0.058, 1), mat(0x78350f, 0.92), Math.cos(ang) * 0.22, 0.02, Math.sin(ang) * 0.20);
        md.scale.set(1.2, 0.7, 1.1);
        site.add(md);
        mounds.push(md);
      }

      // 4. Glowing Crystal Ore Vein Cluster emerging from pit center
      const vein = new THREE.Group();
      const crystals = [];
      const cAngles = [[0, 0, 0, 0.19], [-0.06, 0.04, 0.32, 0.14], [0.07, -0.03, -0.28, 0.15], [-0.04, -0.06, -0.22, 0.12], [0.05, 0.05, 0.25, 0.13]];
      cAngles.forEach(([cx, cz, tilt, h]) => {
        const cMat = new THREE.MeshStandardMaterial({ color: 0x38bdf8, emissive: 0x0284c7, emissiveIntensity: 0.75, roughness: 0.18, metalness: 0.7 });
        const shard = mesh(new THREE.OctahedronGeometry(h * 0.45, 0), cMat, cx, h * 0.5, cz);
        shard.scale.set(0.65, 1.45, 0.65);
        shard.rotation.z = tilt;
        vein.add(shard);
        crystals.push(shard);
      });
      site.add(vein);

      // 5. Restoration Sprouts
      const sprouts = new THREE.Group();
      [[-0.06, 0.02], [0.06, -0.02], [0, 0.05]].forEach(([sx, sz]) => {
        const sp = mesh(new THREE.SphereGeometry(0.035, 8, 8), mat(0x4ade80, 0.5), sx, 0.04, sz);
        sprouts.add(sp);
      });
      site.add(sprouts);

      return { pickaxe, bladeL, bladeR, site, pitDisc, cracks, mounds, vein, crystals, sprouts, hand: new THREE.Vector3(), swing: 0 };
    },
    start(p) {
      const theme = (window.ppongRPGState && window.ppongRPGState.worldview) || 'fantasy';
      const oreTable = {
        fantasy: [['⛏️', '철광석'], ['💎', '미스릴 광석'], ['🔮', '마나 수정'], ['👑', '오리할콘 원석'], ['🏺', '고대 왕국 유물']],
        cyberpunk: [['🔩', '티타늄 합금'], ['💾', '실리콘 웨이퍼'], ['⚡', '양자 코어'], ['💠', '네온 크롬 원석'], ['🧠', '구시대 AI 칩']],
        scifi: [['🪨', '운석철'], ['🛸', '타이탄 합금'], ['🌌', '다크매터 결정'], ['⚛️', '헬륨-3 코어'], ['👽', '외계 문명 유물']],
        cozy: [['🪨', '무지개 조약돌'], ['🐚', '고대 암모나이트 화석'], ['⭐', '별의 조각'], ['🌸', '핑크 쿼츠'], ['🧸', '시간의 타임캡슐']]
      };
      const paletteTable = {
        fantasy: [0x38bdf8, 0x0284c7, 0x78350f],
        cyberpunk: [0xf43f5e, 0x22d3ee, 0x1e293b],
        scifi: [0xa855f7, 0x6366f1, 0x334155],
        cozy: [0xfbbf24, 0xf472b6, 0xa16207]
      };
      const pal = paletteTable[theme] || paletteTable.fantasy;
      p.oreEntry = pick(oreTable[theme] || oreTable.fantasy);
      p.fxCol = pal[0];
      p.crystals.forEach((c) => {
        c.material.color.setHex(pal[0]);
        c.material.emissive.setHex(pal[1]);
      });
      p.mounds.forEach((m) => { m.material.color.setHex(pal[2]); m.scale.setScalar(0.01); });
      p.cracks.forEach((c) => { c.material.color.setHex(pal[0]); c.scale.set(0.01, 1, 1); });
      p.pitDisc.scale.setScalar(0.01);
      p.vein.scale.setScalar(0.01);
      p.sprouts.visible = false;
      p.pickaxe.visible = true;
      p.pickaxe.scale.setScalar(0.01);
      p.lastStrike = -1;
      p.shattered = false;
    },
    phases: [
      { name: 'prospect', dur: 0.65, anim: 'Curious',
        enter(p) {
          ring(0.36, 0.02, 0.38, p.fxCol, { size: 0.9, max: 0.55 });
          floatEmoji('❗광맥 발견!', 0.36, 0.55, 0.38, { size: 0.14, color: '#38bdf8', max: 0.9 });
        },
        update(p, k) {
          p.pickaxe.scale.setScalar(outBack(k));
          P.armR(0.3, 0.8, 0.6); P.armL(-0.3, 0.6, 0.5); P.head(0.25, -0.35);
          p.swing = 0.2;
        }
      },
      { name: 'digging', dur: 3.1, anim: 'Idle',
        enter() { blendRate = 26; },
        update(p, k, t) {
          const totalStrikes = 4;
          const ht = k * totalStrikes;
          const strikeIdx = Math.floor(ht);
          const local = ht % 1;
          const down = local > 0.52;

          P.armR(down ? -0.15 : 1.85, 0.95, down ? 0.35 : 1.35);
          P.armL(down ? -0.1 : 1.1, 0.85, 0.7);
          P.lean(down ? 0.28 : -0.14, down ? 0.14 : -0.05);
          P.head(down ? 0.28 : -0.05, -0.32);
          p.swing = down ? -0.55 : 1.45;

          const prog = clamp01((strikeIdx + (down ? 1 : local)) / totalStrikes);
          p.pitDisc.scale.setScalar(Math.max(0.05, smooth(prog)));
          p.cracks.forEach((cr, idx) => {
            const ck = clamp01(prog * 1.3 - idx * 0.08);
            cr.scale.set(Math.max(0.01, ck), 1, 1);
          });
          p.mounds.forEach((md, idx) => {
            const mk = outBack(clamp01(prog * 1.25 - idx * 0.05));
            md.scale.set(1.2 * mk, 0.75 * mk, 1.1 * mk);
          });
          p.vein.scale.setScalar(outBack(clamp01((prog - 0.2) / 0.8)));

          if (down && p.lastStrike !== strikeIdx) {
            p.lastStrike = strikeIdx;
            hitStop(0.065);
            burst(0.36, 0.12, 0.38, p.fxCol, 9, 1.25, { max: 0.55 });
            puff(0.36, 0.05, 0.38, 0x94a3b8, 3, { max: 0.55 });
            floatEmoji(strikeIdx === 3 ? '💥크리티컬!' : '캉!', 0.36 + rand(-0.08, 0.08), 0.38, 0.42, { size: 0.13, color: '#fde047', max: 0.65 });
          }
        }
      },
      { name: 'shatter', dur: 0.65, anim: 'Jump',
        enter(p) {
          hitStop(0.11);
          ring(0.36, 0.04, 0.38, 0xfacc15, { size: 1.65, max: 0.55 });
          ring(0.36, 0.12, 0.38, p.fxCol, { size: 1.25, max: 0.45 });
          burst(0.36, 0.22, 0.38, 0xfde047, 26, 1.85, { up: 1.5 });
          p.vein.scale.setScalar(0.01);
        },
        update(p, k) {
          P.arms(2.1, 0.3, 0.4);
          p.swing = -0.3;
          p.vein.scale.setScalar(Math.max(0.01, 1 - smooth(k * 2)));
        }
      },
      { name: 'reward', dur: 1.35, anim: 'WaveJump',
        enter(p) {
          grantReward(S, p.oreEntry[0], p.oreEntry[1], 35, { category: 'mining' });
        },
        update(p) {
          p.pickaxe.visible = false;
          P.arms(2.2, 0.2, 0.3);
          P.head(-0.2);
        }
      },
      { name: 'restore', dur: 0.65, anim: 'Idle',
        enter(p) {
          p.sprouts.visible = true;
          puff(0.36, 0.05, 0.38, 0x86efac, 4, { max: 0.55 });
        },
        update(p, k) {
          const s = Math.max(0.01, 1 - smooth(k));
          p.pitDisc.scale.setScalar(s);
          p.mounds.forEach((md) => md.scale.setScalar(s));
          p.cracks.forEach((cr) => cr.scale.set(s, 1, 1));
          p.sprouts.scale.setScalar(Math.sin(k * Math.PI));
        }
      }
    ],
    frame(p) {
      handPos('R', p.hand);
      p.pickaxe.position.copy(p.hand);
      p.pickaxe.rotation.set(0.25, 0, -0.55 - p.swing * 0.65);
    }
  });

  // =====================================================================
  // TEMPLATE ENGINE for the remaining 25 activities
  //   A Craft, B Wait&Catch, C Perform, D Transform, E Explore, F Rest
  // =====================================================================
  function heldFollow(p, side, obj, rot) {
    if (!obj) return; handPos(side, p.__hand || (p.__hand = new THREE.Vector3())); obj.position.copy(p.__hand); if (rot) obj.rotation.set(rot[0], rot[1], rot[2]);
  }
  const TEMPLATES = {
    A: (c) => [
      { name: 'prepare', dur: 0.9, anim: 'Idle', update(p, k) { c.show(p, outBack(k)); P.arms(0.1, 0.7, 0.8); P.head(0.2); } },
      { name: 'work', dur: 3.2, anim: c.anim || 'Idle', update(p, k, t) { const beat = (t * 1.6) % 1, down = beat > 0.6;
          P.armR(down ? -0.1 : 1.3, 0.9, down ? 0.5 : 1.3); P.armL(-0.3, 0.9, 0.7); P.lean(down ? 0.2 : 0, down ? 0.1 : 0); P.head(0.25);
          const id = Math.floor(t * 1.6); if (down && p.__beat !== id) { p.__beat = id; burst(c.at[0], c.at[1], c.at[2], c.fxColor, 5, 0.9, { max: 0.5 }); if (c.beatEmoji) floatEmoji(c.beatEmoji, c.at[0], c.at[1] + 0.12, c.at[2], { size: 0.11, max: 0.8 }); }
          c.work && c.work(p, k, t); } },
      { name: 'climax', dur: 0.9, anim: 'Jump', enter(p) { hitStop(0.08); ring(c.at[0], 0.04, c.at[2], c.ringColor || 0xfacc15, { size: 1.2 }); burst(c.at[0], c.at[1] + 0.2, c.at[2], 0xf472b6, 22, 1.5); c.climax && c.climax(p); },
        update(p, k) { P.arms(2.0, 0.3); c.pulse && c.pulse(p, k); } },
      ...tail(c),
    ],
    B: (c) => [
      { name: 'set', dur: 1.0, anim: 'Idle', update(p, k) { c.show(p, outBack(k)); P.armR(0.3, 0.9, 0.5); P.armL(-0.5, 0.6); } },
      { name: 'wait', dur: 2.6, anim: c.waitAnim || 'Idle', update(p, k, t) { P.armR(0.1 + Math.sin(t * 2) * 0.05, 0.9, 0.5); P.armL(-0.4, 0.7, 0.6); P.head(-0.1 + Math.sin(t * 1.5) * 0.06, Math.sin(t * 0.8) * 0.25); P.set('tailBase', 0, 0, Math.sin(t * 3) * 0.3); c.work && c.work(p, k, t); } },
      { name: 'tell', dur: 0.4, enter() { floatEmoji('❗', 0, 1.55, 0.2, { size: 0.24, rise: 0.1, max: 0.7, color: '#ef4444' }); triggerEmotionEmote && triggerEmotionEmote('surprised'); hitStop(0.1); },
        update() { P.set('leftEar', -0.5, 0, 0); P.set('rightEar', -0.5, 0, 0); P.head(-0.15); P.armR(0.2, 0.9, 0.7); } },
      { name: 'burst', dur: 0.8, update(p, k, t) { P.armR(1.6 + Math.sin(t * 28) * 0.15, 0.6, 0.6); P.armL(0.8, 0.8, 0.6); P.lean(-0.2); if (k < 0.1 && !p.__b) { p.__b = true; burst(c.at[0], c.at[1], c.at[2], c.fxColor, 20, 1.6); ring(c.at[0], c.at[1], c.at[2], c.ringColor || 0x38bdf8, { size: 1.0 }); } c.climax && c.climax(p, k); } },
      ...tail(c),
    ],
    C: (c) => [
      { name: 'intro', dur: 0.8, anim: 'Idle', update(p, k) { c.show(p, outBack(k)); P.arms(0.3, 0.8, 0.6); P.head(-0.1); } },
      { name: 'rhythm', dur: 3.2, anim: c.anim || 'Dance', update(p, k, t) { const bt = t * 2, ph = bt % 1;
          P.armR(0.2 + Math.sin(bt * Math.PI) * 0.35, 0.8, 0.6); P.armL(0.2 - Math.sin(bt * Math.PI) * 0.35, 0.8, 0.6); P.head(0.12 * Math.abs(Math.sin(bt * Math.PI)));
          P.set('hips', 0, 0, Math.sin(bt * Math.PI) * 0.07); P.set('tailBase', 0, 0, Math.sin(bt * 2 * Math.PI) * 0.4);
          const id = Math.floor(bt); if (p.__beat !== id) { p.__beat = id; floatEmoji(pick(c.beatFx), rand(-0.3, 0.3), 0.85, 0.3, { size: 0.13, color: pick(['#f472b6', '#38bdf8', '#a3e635', '#fde047']) }); }
          c.work && c.work(p, k, t); } },
      { name: 'solo', dur: 1.0, anim: 'HappySpin', enter() { ring(0, 0.04, 0, c.ringColor || 0xc084fc, { size: 1.6 }); hitStop(0.06); },
        update(p, k, t) { P.arms(1.8, 0.2); P.lean(-0.25); if (Math.random() < 0.4) burst(rand(-0.3, 0.3), 1.0, 0.2, c.fxColor, 2, 1.0); c.climax && c.climax(p, k); } },
      ...tail(c),
    ],
    D: (c) => [
      { name: 'gather', dur: 1.5, anim: 'Idle', update(p, k, t) { c.show(p, outBack(k)); P.arms(0.6 + k * 0.6, 0.7, 0.5); P.head(-0.2);
          if (Math.random() < 0.5) { const a = Math.random() * 6.28; const m = mesh(sparkGeo, glow(c.fxColor), Math.cos(a) * 0.7, rand(0.2, 1.2), Math.sin(a) * 0.4 + 0.2); addFx(m, { vel: new THREE.Vector3(-Math.cos(a) * 0.9, 0.1, -Math.sin(a) * 0.5), max: 0.7 }); }
          c.work && c.work(p, k, t); } },
      { name: 'charge', dur: 1.1, anim: 'HappySpin', update(p, k, t) { P.arms(2.4, 0.1); P.head(-0.3); characterPivot.position.y = Math.sin(k * Math.PI) * 0.12; if (Math.random() < 0.6) burst(0, 0.8, 0.1, c.fxColor, 2, 0.6, { g: 0.5 }); } },
      { name: 'flash', dur: 0.5, enter(p) { hitStop(0.1); ring(0, 0.7, 0.1, c.ringColor || 0xffffff, { flat: false, size: 2.4, max: 0.5 }); ring(0, 0.04, 0, c.fxColor, { size: 2.0 }); burst(0, 0.8, 0.2, c.fxColor, 30, 2.0); c.climax && c.climax(p); },
        update(p, k) { characterPivot.position.y = (1 - k) * 0.12; P.arms(1.2, 0.6, 0.8); } },
      ...tail(c, 'WaveJump'),
    ],
    E: (c) => [
      { name: 'search', dur: 3.0, anim: c.anim || 'Idle', update(p, k, t) { c.show(p, outBack(k * 3)); P.armR(1.0, 0.7, 1.6); P.armL(-0.3, 0.6, 0.4); P.head(0.05, Math.sin(t * 1.8) * 0.5); P.lean(0.08);
          if (Math.random() < 0.06) puff(rand(-0.4, 0.4), 0.04, 0.35, 0xd6d3d1, 1, { max: 0.6 }); c.work && c.work(p, k, t); } },
      { name: 'discover', dur: 0.7, enter() { floatEmoji('❗', 0, 1.55, 0.2, { size: 0.24, rise: 0.1, max: 0.8, color: '#facc15' }); triggerEmotionEmote && triggerEmotionEmote('surprised'); hitStop(0.08); },
        update(p, k) { P.head(0.3); P.lean(0.3); P.arms(-0.2, 1.0, 0.6); c.climax && c.climax(p, k); } },
      ...tail(c, 'Jump'),
    ],
    F: (c) => [
      { name: 'settle', dur: 1.0, anim: 'Sit', update(p, k) { c.show(p, outBack(k)); P.arms(-0.4, 0.8, 0.9); P.head(0.15); } },
      { name: 'calm', dur: 3.4, anim: 'Sit', update(p, k, t) { const br = Math.sin(t * 1.6); P.arms(-0.4, 0.9, 1.0); P.head(c.droop ?? 0.3 + br * 0.04, 0, 0.12); P.lean(0.05 + br * 0.03);
          if (Math.random() < 0.025) floatEmoji(pick(c.beatFx), rand(0, 0.25), 1.2, 0.2, { size: 0.12, rise: 0.25 }); c.work && c.work(p, k, t); } },
      { name: 'wake', dur: 1.0, anim: 'Stretch', enter(p) { c.climax && c.climax(p); }, update() { P.arms(2.4, 0.2); P.lean(-0.2); } },
      ...tail(c, 'Idle'),
    ],
  };
  function tail(c, anim = 'WaveJump') {
    return [
      { name: 'reward', dur: 1.4, anim, enter() { grantReward(S, c.icon, pick(c.items), c.xp || 20); }, update() { P.arms(1.8, 0.3); P.head(-0.2); } },
      { name: 'exit', dur: 0.6, anim: 'Idle', update(p, k) { c.show(p, Math.max(0.01, 1 - smooth(k))); } },
    ];
  }
  function simple(key, cfg) {
    const c = { fxColor: 0xfde047, at: [0, 0.4, 0.4], ...cfg };
    c.show = (p, s) => { p.__root.scale.setScalar(Math.max(0.01, s)); };
    register(key, {
      title: cfg.title, skill: cfg.skill, speech: cfg.speech,
      build(g) { const r = new THREE.Group(); g.add(r); const p = cfg.build ? cfg.build(r) : {}; p.__root = r; if (p.held) { r.remove(p.held); g.add(p.held); } return p; },
      start(p) { p.__root.scale.setScalar(0.01); p.__beat = -1; p.__b = false; cfg.start && cfg.start(p); },
      phases: TEMPLATES[cfg.tmpl](c),
      frame(p, t) { if (p.held) { heldFollow(p, cfg.side || 'R', p.held, cfg.heldRot || [0, 0, -0.4]); p.held.scale.copy(p.__root.scale); } cfg.frame && cfg.frame(p, t); },
    });
  }

  // ------------------------------------------------------------ 25 configs
  simple('hunting', { tmpl: 'B', title: '🦋 곤충 채집', skill: '채집', speech: '살금살금... 나비가 앉을 때까지 기다려요 🦋', icon: '🦋', items: ['무지개 나비', '반딧불이', '장수풍뎅이'], xp: 20, fxColor: 0xa3e635, at: [0.4, 0.6, 0.35],
    build(r) { const held = new THREE.Group(); held.add(mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.5, 6), mat(0x78350f), 0, 0.25, 0)); const net = mesh(new THREE.TorusGeometry(0.09, 0.01, 6, 20), mat(0xf8fafc), 0, 0.55, 0); held.add(net);
      const bfly = makeSprite('🦋', '#fff', 0.16); r.add(bfly); return { held, bfly }; },
    heldRot: [0.4, 0, -0.5], frame(p, t) { p.bfly.position.set(0.4 + Math.sin(t * 2.3) * 0.25, 0.65 + Math.sin(t * 5) * 0.1, 0.35); } });
  simple('explorer', { tmpl: 'E', anim: 'Walk', title: '🧭 탐험하기', skill: '탐험', speech: '미지의 바탕화면 대륙을 수색합니다! 🧭', icon: '🗺️', items: ['보물지도 조각', '고대 나침반', '신비한 화석'], xp: 20,
    build(r) { const hat = new THREE.Group(); hat.add(mesh(new THREE.SphereGeometry(0.2, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), mat(0xd6b370, 0.7))); hat.add(mesh(new THREE.CylinderGeometry(0.3, 0.3, 0.015, 24), mat(0xc8a35a, 0.7))); hat.position.set(0, 1.42, 0); r.add(hat); return {}; } });
  simple('treasure', { tmpl: 'E', title: '💎 보물찾기', skill: '보물찾기', speech: '여기 X 표시! 파보면 뭔가 나올 거예요 💎', icon: '💰', items: ['황금 동전 주머니', '루비 원석', '해적왕의 보석'], xp: 30, fxColor: 0xfacc15,
    build(r) { const chest = mesh(new THREE.BoxGeometry(0.22, 0.14, 0.15), mat(0x92400e, 0.5), 0.35, 0.07, 0.4); const lid = mesh(new THREE.BoxGeometry(0.23, 0.04, 0.16), mat(0xca8a04, 0.3, 0.7), 0.35, 0.16, 0.4); r.add(chest, lid); const x = makeSprite('❌', '#fff', 0.12); x.position.set(0.35, 0.03, 0.45); r.add(x); return { lid }; },
    climax(p, k) { p.lid.rotation.x = -1.2 * smooth(k); if (Math.random() < 0.5) burst(0.35, 0.2, 0.4, 0xfacc15, 2, 1.2, { up: 1.8 }); } });
  simple('detective', { tmpl: 'E', title: '🕵️ 탐정 추리', skill: '추리', speech: '흠... 이 발자국, 수상한데요? 🔍', icon: '🔍', items: ['결정적 단서', '수상한 발자국', '비밀 쪽지'], xp: 20,
    build(r) { const held = new THREE.Group(); held.add(mesh(new THREE.CylinderGeometry(0.01, 0.01, 0.12, 6), mat(0x451a03), 0, 0.06, 0)); held.add(mesh(new THREE.TorusGeometry(0.05, 0.01, 6, 18), mat(0xca8a04, 0.3, 0.8), 0, 0.17, 0)); return { held }; },
    work(p, k, t) { if (Math.random() < 0.04) floatEmoji('👣', rand(-0.4, 0.4), 0.03, 0.4, { size: 0.08, rise: 0, max: 1.5 }); } });
  simple('telescope', { tmpl: 'E', title: '🔭 천체 관측', skill: '천문', speech: '오늘 밤 하늘엔 어떤 별이 있을까? 🔭', icon: '⭐', items: ['북두칠성', '유성우', '새로운 별자리'], xp: 20, fxColor: 0xfef08a,
    build(r) { const tube = mesh(new THREE.CylinderGeometry(0.03, 0.05, 0.42, 14), mat(0x1e3a8a, 0.3, 0.6), -0.35, 0.55, 0.3); tube.rotation.z = -0.8; r.add(tube); for (let i = 0; i < 3; i++) { const l = mesh(new THREE.CylinderGeometry(0.008, 0.008, 0.45, 6), mat(0x64748b), -0.35 + (i - 1) * 0.06, 0.22, 0.3 + (i === 1 ? 0.06 : 0)); r.add(l); } return {}; },
    work() { if (Math.random() < 0.08) floatEmoji('✦', rand(-0.6, 0.6), 1.5, 0, { size: 0.08, rise: 0, max: 0.8, color: '#fef08a' }); } });
  simple('cooking', { tmpl: 'A', title: '🍳 팬케이크 요리', skill: '요리', speech: '반죽 휘휘, 팬에 촤악~ 팬케이크 굽는 중! 🥞', icon: '🥞', items: ['폭신 팬케이크', '허니 버터 팬케이크', '3단 타워 팬케이크'], xp: 25, fxColor: 0xfbbf24, at: [0.25, 0.42, 0.4], beatEmoji: '🔥',
    build(r) { const hat = mesh(new THREE.CylinderGeometry(0.15, 0.12, 0.2, 16), mat(0xffffff, 0.6), 0, 1.52, 0); r.add(hat);
      const held = new THREE.Group(); held.add(mesh(new THREE.CylinderGeometry(0.12, 0.1, 0.03, 18), mat(0x1f2937, 0.3, 0.8), 0.16, 0, 0)); held.add(mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.14, 6), mat(0x111827), 0.04, 0, 0)).rotation.z = Math.PI / 2;
      const cake = mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.02, 16), mat(0xd97706, 0.7), 0.16, 0.03, 0); held.add(cake); return { held, cake }; },
    heldRot: [0, 0, 0], work(p, k, t) { const c = (t * 1.6) % 1; p.cake.position.y = 0.03 + (c < 0.5 ? Math.sin(c * 2 * Math.PI) * 0.25 : 0); p.cake.rotation.x = c < 0.5 ? c * 4 * Math.PI : 0; } });
  simple('gardening', { tmpl: 'A', title: '🌷 정원 가꾸기', skill: '원예', speech: '씨앗 심고 물 주고... 쑥쑥 자라라! 🌱', icon: '🌸', items: ['튤립 꽃다발', '네잎클로버', '황금 해바라기'], xp: 20, fxColor: 0x7dd3fc, at: [-0.3, 0.1, 0.4],
    build(r) { const held = mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.12, 12), mat(0x10b981, 0.4)); const flowers = []; [0xf43f5e, 0xfacc15, 0xa855f7].forEach((col, i) => { const f = new THREE.Group(); f.add(mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.18, 6), mat(0x15803d), 0, 0.09, 0)); f.add(mesh(new THREE.SphereGeometry(0.04, 10, 10), mat(col), 0, 0.19, 0)); f.position.set(-0.45 + i * 0.13, 0, 0.42); r.add(f); flowers.push(f); }); return { held, flowers }; },
    heldRot: [0, 0, -1.0], start(p) { p.flowers.forEach((f) => f.scale.setScalar(0.01)); }, work(p, k) { p.flowers.forEach((f, i) => f.scale.setScalar(Math.max(0.01, outBack(clamp01(k * 3 - i))))); if (Math.random() < 0.4) burst(-0.3, 0.3, 0.42, 0x7dd3fc, 1, 0.3, { g: -4, max: 0.4 }); } });
  simple('painting', { tmpl: 'A', title: '🎨 명작 그리기', skill: '미술', speech: '붓 터치 한 번, 두 번... 명작의 탄생! 🎨', icon: '🖼️', items: ['풍경화', '자화상', '추상화 걸작'], xp: 25, fxColor: 0xf472b6, at: [-0.3, 0.6, 0.42],
    build(r) { const canvas = mesh(new THREE.PlaneGeometry(0.34, 0.26), mat(0xfffbeb, 0.9), -0.3, 0.6, 0.42); r.add(canvas); const legs = mesh(new THREE.BoxGeometry(0.02, 0.6, 0.02), mat(0x92400e), -0.3, 0.3, 0.4); r.add(legs);
      const dabs = []; for (let i = 0; i < 8; i++) { const d = mesh(new THREE.CircleGeometry(0.025, 10), glow(pick([0xf43f5e, 0x38bdf8, 0xfacc15, 0x22c55e])), -0.42 + Math.random() * 0.24, 0.52 + Math.random() * 0.16, 0.425); r.add(d); dabs.push(d); }
      const held = mesh(new THREE.CylinderGeometry(0.006, 0.006, 0.2, 6), mat(0x78350f)); return { held, dabs }; },
    heldRot: [0, 0, 0.8], start(p) { p.dabs.forEach((d) => (d.visible = false)); }, work(p, k) { p.dabs.forEach((d, i) => (d.visible = k * 8 > i)); } });
  simple('snowman', { tmpl: 'A', title: '☃️ 눈사람 만들기', skill: '눈놀이', speech: '데굴데굴 굴려서 쌓고~ 당근 코 콕! ☃️', icon: '⛄', items: ['꼬마 눈사람', '모자 쓴 눈사람', '거대 눈사람'], xp: 25, fxColor: 0xf8fafc, at: [-0.35, 0.2, 0.4],
    build(r) { const a = mesh(new THREE.SphereGeometry(0.15, 16, 16), mat(0xf8fafc, 0.7), -0.35, 0.15, 0.4), b = mesh(new THREE.SphereGeometry(0.1, 16, 16), mat(0xf8fafc, 0.7), -0.35, 0.38, 0.4);
      const nose = mesh(new THREE.ConeGeometry(0.02, 0.08, 8), mat(0xf97316), -0.35, 0.38, 0.52); nose.rotation.x = Math.PI / 2; r.add(a, b, nose); return { a, b, nose }; },
    work(p, k) { p.a.scale.setScalar(Math.max(0.01, smooth(k * 2))); p.b.scale.setScalar(Math.max(0.01, smooth(k * 2 - 1))); p.nose.visible = k > 0.9; if (Math.random() < 0.3) puff(-0.35, 0.05, 0.4, 0xffffff, 1, { max: 0.5 }); } });
  simple('picnic', { tmpl: 'A', title: '🍩 피크닉 간식', skill: '미식', speech: '돗자리 펴고 도넛 냠냠! 피크닉 최고 🧺', icon: '🧺', items: ['딸기 도넛', '샌드위치', '피크닉 세트'], xp: 15, fxColor: 0xf9a8d4, at: [0.2, 0.5, 0.4], beatEmoji: '😋',
    build(r) { const mat0 = mesh(new THREE.PlaneGeometry(0.9, 0.5), mat(0xef4444, 0.9), 0, 0.005, 0.25); mat0.rotation.x = -Math.PI / 2; r.add(mat0); r.add(mesh(new THREE.BoxGeometry(0.2, 0.12, 0.14), mat(0xb45309, 0.8), -0.35, 0.06, 0.35));
      const held = mesh(new THREE.TorusGeometry(0.05, 0.025, 10, 18), mat(0xf472b6, 0.4)); return { held }; }, heldRot: [0, 0, 0] });
  simple('drinking', { tmpl: 'A', title: '🍻 건배 & 음료', skill: '사교', speech: '오늘 하루도 고생했어요! 짠~ 🍻', icon: '🥤', items: ['시원한 생맥주', '레몬 에이드', '특제 밀크쉐이크'], xp: 15, fxColor: 0xfef08a, at: [0.25, 0.75, 0.3], beatEmoji: '🫧',
    build(r) { const held = new THREE.Group(); held.add(mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.13, 14), mat(0xfbbf24, 0.2, 0, { transparent: true, opacity: 0.85 }))); held.add(mesh(new THREE.SphereGeometry(0.052, 12, 8), mat(0xfffbeb, 0.6), 0, 0.07, 0)); return { held }; }, heldRot: [0, 0, 0] });
  simple('paper_plane', { tmpl: 'B', title: '✈️ 종이비행기', skill: '항공', speech: '꼭꼭 접어서... 바람 타이밍을 기다려요 ✈️', icon: '✈️', items: ['최장거리 기록!', '곡예비행 성공', '하늘 끝까지'], xp: 15, fxColor: 0xe0f2fe, at: [0.3, 0.8, 0.3],
    build(r) { const plane = mesh(new THREE.ConeGeometry(0.06, 0.18, 3), mat(0xffffff, 0.5)); plane.rotation.z = -Math.PI / 2; r.add(plane); return { plane }; },
    frame(p, t) { if (!p.__b) p.plane.position.set(0.25, 0.65, 0.3); }, climax(p, k) { p.plane.position.set(0.25 + k * 1.2, 0.65 + Math.sin(k * 6) * 0.25, 0.3); } });
  simple('party_dj', { tmpl: 'C', title: '🎧 파티 DJ', skill: 'DJ', speech: '볼륨 업! 드랍 더 비트~ 🎛️🎧', icon: '🎧', items: ['플로어 대폭발', '앵콜 세트', '전설의 믹스'], xp: 30, fxColor: 0xc084fc, beatFx: ['♪', '♫', '🔊', '✨'],
    build(r) { const deck = mesh(new THREE.BoxGeometry(0.55, 0.08, 0.24), mat(0x111827, 0.3, 0.6), 0, 0.42, 0.42); r.add(deck); const d1 = mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.015, 20), mat(0x334155), -0.13, 0.47, 0.42), d2 = d1.clone(); d2.position.x = 0.13; r.add(d1, d2);
      r.add(mesh(new THREE.BoxGeometry(0.6, 0.38, 0.2), mat(0x1e293b, 0.6), 0, 0.19, 0.44)); return { d1, d2 }; }, frame(p, t) { p.d1.rotation.y = t * 9; p.d2.rotation.y = -t * 9; } });
  simple('gamer', { tmpl: 'C', anim: 'Sit', title: '🎮 프로 게이머', skill: '게임', speech: '보스전 돌입! 콤보 연타 들어갑니다 🎮', icon: '🏆', items: ['최고 기록 갱신', '보스 처치!', '랭킹 1위'], xp: 20, fxColor: 0x22d3ee, beatFx: ['COMBO!', 'x2', 'x5', 'NICE!'],
    build(r) { const held = mesh(new THREE.BoxGeometry(0.2, 0.08, 0.05), mat(0x1e293b, 0.3, 0.6)); const screen = mesh(new THREE.PlaneGeometry(0.42, 0.26), glow(0x22d3ee, 0.6), 0, 0.75, 0.6); screen.rotation.y = Math.PI; r.add(screen); return { held }; }, heldRot: [0.3, 0, 0] });
  simple('fitness', { tmpl: 'C', anim: 'Idle', title: '🏋️ 파워 헬스', skill: '근력', speech: '하나, 둘, 셋... 오늘 3대 500 간다! 💪', icon: '💪', items: ['근력 +1', '신기록 달성', '강철 이두근'], xp: 20, fxColor: 0x7dd3fc, beatFx: ['1', '2', '3', '4', '5', '💦'],
    build(r) { const bar = new THREE.Group(); bar.add(mesh(new THREE.CylinderGeometry(0.012, 0.012, 0.8, 8), mat(0x94a3b8, 0.3, 0.8))).rotation.z = Math.PI / 2; [-0.36, 0.36].forEach((x) => { const w = mesh(new THREE.CylinderGeometry(0.11, 0.11, 0.05, 16), mat(0x111827)); w.rotation.z = Math.PI / 2; w.position.x = x; bar.add(w); }); r.add(bar); return { bar }; },
    frame(p, t) { p.bar.position.set(0, 1.05 + Math.abs(Math.sin(t * 2 * Math.PI / 2)) * 0.25, 0.1); } });
  simple('skateboard', { tmpl: 'C', anim: 'Idle', title: '🛹 스케이트보드', skill: '스케이트', speech: '푸시 푸시~ 킥플립 갑니다! 🛹', icon: '🛹', items: ['킥플립 성공', '알리 360', '전설의 트릭'], xp: 25, fxColor: 0xfde047, beatFx: ['💨', '⚡'],
    build(r) { const board = mesh(new THREE.BoxGeometry(0.6, 0.025, 0.18), mat(0x0284c7, 0.4), 0, 0.04, 0); r.add(board); [-0.22, 0.22].forEach((x) => [-0.07, 0.07].forEach((z) => r.add(mesh(new THREE.CylinderGeometry(0.025, 0.025, 0.02, 10), mat(0xfacc15), x, 0.02, z)).rotation.x = Math.PI / 2)); return { board }; },
    work(p, k, t) { characterPivot.position.y = 0.05 + Math.abs(Math.sin(t * 2.4)) * 0.06; }, climax(p, k) { characterPivot.position.y = Math.sin(k * Math.PI) * 0.3; p.__root.rotation.z = k * Math.PI * 2; } });
  simple('surfing', { tmpl: 'C', anim: 'Idle', title: '🏄 파도타기', skill: '서핑', speech: '빅 웨이브다! 균형 잡고 라이딩~ 🌊', icon: '🌊', items: ['튜브 라이딩', '빅 웨이브 정복', '전설의 파도'], xp: 25, fxColor: 0x7dd3fc, beatFx: ['💦', '🌊'],
    build(r) { const board = mesh(new THREE.CapsuleGeometry(0.09, 0.55, 6, 12), mat(0x06b6d4, 0.3)); board.rotation.z = Math.PI / 2; board.scale.z = 0.25; board.position.y = 0.04; r.add(board); const wave = mesh(new THREE.TorusGeometry(0.6, 0.06, 8, 40, Math.PI), glow(0x38bdf8, 0.5), 0, 0, -0.2); r.add(wave); return { board, wave }; },
    work(p, k, t) { p.__root.rotation.z = Math.sin(t * 3) * 0.12; P.arms(0.3, 0, 0); P.set('hips', 0, 0, Math.sin(t * 3) * 0.12); if (Math.random() < 0.3) burst(rand(-0.3, 0.3), 0.06, 0.1, 0xbae6fd, 1, 0.8, { max: 0.4 }); } });
  simple('kite', { tmpl: 'B', title: '🪁 연날리기', skill: '연날리기', speech: '바람이 불 때까지 기다렸다가... 날려요! 🪁', icon: '🪁', items: ['최고 고도 달성', '연싸움 승리', '구름 위 연'], xp: 15, fxColor: 0xf472b6, at: [0.5, 1.5, 0],
    build(r) { const kite = mesh(new THREE.PlaneGeometry(0.25, 0.25), mat(0xef4444, 0.5, 0, { side: THREE.DoubleSide })); kite.rotation.z = Math.PI / 4; r.add(kite); const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(), new THREE.Vector3()]), glow(0xffffff, 0.8)); r.add(line); return { kite, line, h: new THREE.Vector3() }; },
    frame(p, t) { const hgt = p.__b ? 1.6 : 0.9; p.kite.position.set(0.5 + Math.sin(t * 2) * 0.12, hgt + Math.cos(t * 2.6) * 0.08, 0); handPos('R', p.h); const pos = p.line.geometry.attributes.position; pos.setXYZ(0, p.h.x, p.h.y, p.h.z); pos.setXYZ(1, p.kite.position.x, p.kite.position.y, 0); pos.needsUpdate = true; } });
  simple('bubbles', { tmpl: 'B', title: '🫧 비눗방울', skill: '비눗방울', speech: '후~ 천천히 불어서 왕방울 만들기 도전! 🫧', icon: '🫧', items: ['왕방울 성공', '무지개 방울', '방울 속 방울'], xp: 10, fxColor: 0xbae6fd, at: [0.2, 0.9, 0.3],
    build(r) { const held = mesh(new THREE.TorusGeometry(0.05, 0.008, 6, 18), mat(0xf472b6)); return { held }; }, heldRot: [0, 0, 0],
    work(p) { if (Math.random() < 0.12) { const m = mesh(new THREE.SphereGeometry(rand(0.03, 0.07), 12, 12), glow(pick([0xbae6fd, 0xf9a8d4, 0xc4b5fd]), 0.4), 0.25, 0.85, 0.3); addFx(m, { vel: new THREE.Vector3(rand(0, 0.3), rand(0.2, 0.4), 0), wave: 0.3, max: 2.0 }); } } });
  simple('wizard', { tmpl: 'D', title: '🧙 마법사 변신', skill: '마법', speech: '마나를 모아서... 대마법 시전! 🔮', icon: '✨', items: ['행운의 주문', '별빛 마법', '금단의 대마법'], xp: 30, fxColor: 0xa855f7, ringColor: 0xe9d5ff,
    build(r) { const hat = mesh(new THREE.ConeGeometry(0.2, 0.42, 16), mat(0x6b21a8, 0.4), 0, 1.6, 0); r.add(hat); const rune = mesh(new THREE.RingGeometry(0.38, 0.46, 6), glow(0xa855f7, 0.7), 0, 0.02, 0); rune.rotation.x = -Math.PI / 2; r.add(rune);
      const held = new THREE.Group(); held.add(mesh(new THREE.CylinderGeometry(0.01, 0.014, 0.6, 8), mat(0x92400e), 0, 0.2, 0)); held.add(mesh(new THREE.OctahedronGeometry(0.05), glow(0x38bdf8), 0, 0.52, 0)); return { held, rune }; },
    heldRot: [0, 0, -0.2], frame(p, t) { p.rune.rotation.z = t * 1.5; } });
  simple('ninja', { tmpl: 'D', title: '🥷 닌자 은신술', skill: '인술', speech: '인법! 그림자 분신술... 슉! 💨', icon: '🥷', items: ['그림자 분신', '연막 은신', '비전 수리검'], xp: 25, fxColor: 0x94a3b8, ringColor: 0xef4444,
    build(r) { const band = mesh(new THREE.TorusGeometry(0.2, 0.02, 6, 24), mat(0xdc2626, 0.5), 0, 1.3, 0); band.rotation.x = Math.PI / 2; r.add(band); return {}; },
    climax() { puff(0, 0.6, 0.2, 0x64748b, 10, { grow: 3 }); floatEmoji('💨', 0, 0.8, 0.4, { size: 0.3 }); } });
  simple('astronaut', { tmpl: 'D', title: '🧑‍🚀 우주비행사', skill: '우주', speech: '카운트다운 3, 2, 1... 무중력 유영 시작! 🚀', icon: '🚀', items: ['달 착륙 기념품', '우주 정거장 방문', '외계 운석'], xp: 30, fxColor: 0x60a5fa,
    build(r) { const helm = mesh(new THREE.SphereGeometry(0.36, 20, 16), glow(0xbae6fd, 0.22), 0, 1.2, 0); r.add(helm); const pack = mesh(new THREE.BoxGeometry(0.26, 0.3, 0.12), mat(0xe2e8f0, 0.4), 0, 0.75, -0.3); r.add(pack); return {}; },
    work(p, k, t) { characterPivot.position.y = Math.sin(t * 2) * 0.05; } });
  simple('timemachine', { tmpl: 'D', title: '⏳ 타임머신', skill: '시공간', speech: '다이얼 맞추고... 시공간 점프! 🌀', icon: '⏰', items: ['공룡 시대 사진', '미래 신문', '시간의 모래'], xp: 30, fxColor: 0x22d3ee, ringColor: 0x67e8f9,
    build(r) { const portal = mesh(new THREE.TorusGeometry(0.5, 0.04, 10, 40), glow(0x06b6d4, 0.8), 0, 0.75, -0.15); r.add(portal); return { portal }; }, frame(p, t) { p.portal.rotation.z = -t * 4; } });
  simple('reading', { tmpl: 'F', droop: 0.35, title: '📖 마법서 독서', skill: '지식', speech: '한 장, 한 장... 지식이 쌓이는 중 📖', icon: '📖', items: ['지혜 +1', '고대 주문 해독', '영감 폭발'], xp: 15, beatFx: ['💡', 'A', '가', '✦'],
    build(r) { const book = new THREE.Group(); const l = mesh(new THREE.BoxGeometry(0.15, 0.2, 0.015), mat(0x831843)), rr = l.clone(); l.position.x = -0.075; l.rotation.y = 0.35; rr.position.x = 0.075; rr.rotation.y = -0.35; book.add(l, rr); book.position.set(0, 0.6, 0.38); r.add(book); return { book }; },
    climax() { floatEmoji('💡', 0, 1.6, 0.2, { size: 0.25 }); } });
  simple('sleeping', { tmpl: 'F', droop: 0.5, title: '💤 꿀잠 낮잠', skill: '휴식', speech: '새근새근... 10분만 충전할게요 💤', icon: '💤', items: ['기력 완전 회복', '달콤한 꿈', '꿀잠 보너스'], xp: 10, beatFx: ['Z', 'z', '💤'],
    build(r) { const pillow = mesh(new THREE.BoxGeometry(0.4, 0.1, 0.25), mat(0xe0e7ff, 0.9), 0, 0.05, 0.1); r.add(pillow); const cap = mesh(new THREE.ConeGeometry(0.17, 0.32, 14), mat(0x3b82f6, 0.7), 0.05, 1.5, 0); cap.rotation.z = -0.4; r.add(cap); return {}; } });

  // ------------------------------------------------------------- runner
  function resetCharacter() { characterPivot.position.set(0, 0, 0); characterPivot.scale.set(1, 1, 1); }
  function stopSoloAction() {
    if (S.def && S.p) S.p.__group.visible = false;
    S.active = false; S.key = ''; S.def = null; S.idx = -1; P.reset(); blendRate = 14; resetCharacter();
  }
  function playSoloAction(key, customDuration) {
    const def = defs[key];
    if (!def) return false;
    if (S.def && S.p) S.p.__group.visible = false;
    if (!def.cache) { const g = new THREE.Group(); root.add(g); def.cache = def.build(g); def.cache.__group = g; }
    S.p = def.cache; S.p.__group.visible = true;
    def.start && def.start(S.p); def.start2 && def.start2(S.p);
    S.active = true; S.key = key; S.def = def; S.t = 0; S.idx = -1; S.hitStop = 0; S.weight = 0; blendRate = 14;
    S.speed = customDuration ? def.total / customDuration : 1;
    resetCharacter();
    return { title: def.title, speech: def.speech, duration: def.total };
  }
  function updateSoloPlay(dt) {
    updateFx(dt);
    if (!S.active) { if (S.weight > 0.001) { S.weight = Math.max(0, S.weight - dt * 4); P.reset(); applyPose(dt, S.weight); } return; }
    const def = S.def, p = S.p;
    S.weight = Math.min(1, S.weight + dt * 5);
    if (S.hitStop > 0) { S.hitStop -= dt; } else { S.t += dt * (S.speed || 1); }
    if (S.t >= def.total) { stopSoloAction(); S.weight = 1; playAnimation && playAnimation('Idle'); return; }
    let idx = def.bounds.findIndex(([a, b]) => S.t >= a && S.t < b); if (idx < 0) idx = def.phases.length - 1;
    const ph = def.phases[idx];
    if (idx !== S.idx) { S.idx = idx; if (ph.anim && playAnimation) playAnimation(ph.anim); if (ph.emote && triggerEmotionEmote) triggerEmotionEmote(ph.emote); ph.enter && ph.enter(p); }
    const [a, b] = def.bounds[idx];
    const k = (S.t - a) / (b - a);
    P.reset();
    ph.update && ph.update(p, k, S.t, dt);
    applyPose(dt, S.weight);
    def.frame && def.frame(p, S.t);
  }

  return {
    playSoloAction, stopSoloAction, updateSoloPlay,
    isSoloPlayingActive: () => S.active,
    getActionDef: (k) => defs[k],
    getSoloActionKeys: () => Object.keys(defs),
    getAllActions: () => Object.fromEntries(Object.entries(defs).map(([k, d]) => [k, { title: d.title, skill: d.skill, duration: d.total }])),
    getSkillXP: () => ({ ...skillXP }),
    setSkillXP: (obj) => { skillXP = { ...(obj || {}) }; },
    getLastResult: () => lastResult,
    getPhase: () => (S.active ? S.def.phases[S.idx]?.name : null),
    // Shared FX, Pose & Bone Attachment API for World RPG & Wave Defense
    fxApi: {
      burst, puff, ring, floatEmoji, floatText, itemDrop, pillar, hitStop, handPos, P, applyPose, makeSprite, mat, glow, mesh, root
    }
  };
}
