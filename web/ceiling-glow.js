import * as THREE from 'three/webgpu';

// Each lit ceiling fixture fills the air under it with a translucent volume,
// so the occupied room reads as lit from any street angle. The web GLB has no
// real lights; this is a merged mesh of one box per fixture, not a bake
// onto the floor and not a sticker on the facade.
//
// The volumes sit strictly inside the curtain wall — no clamping to the facade
// plane, no outset, no window punching. The apartment-band dark glass is made
// semi-transparent in main.js so the glow reads through it.
const CELL = 0.75;
// A lantern of light under each fixture, clipped to the glass envelope so an
// outer-ring lamp never pushes past the facade. HALF is half the ~3.5 m lamp
// pitch so neighbouring pools almost meet; DROP is most of a 4 m storey.
const HALF = 1.2;
const DROP = 2.6;
const MASS_PAD = 0.35;
const MASS_LINK = 8;
const TOP_GAIN = 5.5;
const BOTTOM_GAIN = 1.4;

function panelsOf(object, color, strength) {
  const geometry = object.geometry;
  const matrix = object.matrixWorld;
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();
  if (!position || !normal || !index) return [];
  const vertex = new THREE.Vector3();
  const facing = new THREE.Vector3();
  const buckets = new Map();
  for (let triangle = 0; triangle < index.count; triangle += 3) {
    const first = index.getX(triangle);
    facing.fromBufferAttribute(normal, first).transformDirection(matrix);
    if (facing.y > -0.5) continue;
    vertex.fromBufferAttribute(position, first).applyMatrix4(matrix);
    let x = vertex.x;
    let y = vertex.y;
    let z = vertex.z;
    for (let corner = 1; corner < 3; corner += 1) {
      vertex.fromBufferAttribute(position, index.getX(triangle + corner)).applyMatrix4(matrix);
      x += vertex.x;
      y += vertex.y;
      z += vertex.z;
    }
    const key = `${Math.round(x / CELL)}_${Math.round(y)}_${Math.round(z / CELL)}`;
    const bucket = buckets.get(key) ?? { x: 0, y: 0, z: 0, n: 0 };
    bucket.x += x / 3;
    bucket.y += y / 3;
    bucket.z += z / 3;
    bucket.n += 1;
    buckets.set(key, bucket);
  }
  const cells = [...buckets.values()].map((bucket) => ({
    x: bucket.x / bucket.n,
    y: bucket.y / bucket.n,
    z: bucket.z / bucket.n,
  }));
  cells.sort((left, right) => left.y - right.y || left.x - right.x || left.z - right.z);
  const used = new Uint8Array(cells.length);
  const panels = [];
  for (let i = 0; i < cells.length; i += 1) {
    if (used[i]) continue;
    let x = cells[i].x;
    let y = cells[i].y;
    let z = cells[i].z;
    let count = 1;
    used[i] = 1;
    for (let j = i + 1; j < cells.length && cells[j].y - cells[i].y < 0.4; j += 1) {
      if (used[j]) continue;
      const dx = cells[j].x - cells[i].x;
      const dz = cells[j].z - cells[i].z;
      if (dx * dx + dz * dz < 0.64) {
        used[j] = 1;
        x += cells[j].x;
        y += cells[j].y;
        z += cells[j].z;
        count += 1;
      }
    }
    panels.push({ x: x / count, y: y / count, z: z / count, color, strength });
  }
  return panels;
}

function collectLights(model) {
  const panels = [];
  model.traverse((object) => {
    if (!object.isMesh) return;
    if (/arcade|pilotis|street/i.test(object.name)) return;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) {
      const color = material?.emissive ? material.emissive.toArray() : [0, 0, 0];
      const lit = (material?.emissiveIntensity ?? 0) > 1 && color.some((channel) => channel > 0.02);
      if (!lit) continue;
      panels.push(...panelsOf(object, color, material.emissiveIntensity));
    }
  });
  return panels;
}

function clusterStoreys(panels) {
  const sorted = [...panels].sort((left, right) => left.y - right.y);
  const groups = [];
  for (const panel of sorted) {
    const group = groups.at(-1);
    if (!group || panel.y - group.y > 0.6) {
      groups.push({ y: panel.y, n: 1 });
    } else {
      group.n += 1;
      group.y += (panel.y - group.y) / group.n;
    }
  }
  return groups;
}

function sparseHeights(panels) {
  // Refuge gardens and path-lit decks have a handful of lamps; occupied
  // floors have a room grid. Skip a storey when it has under a third of
  // the median fixture count, so the heuristic travels across models.
  const groups = clusterStoreys(panels);
  if (groups.length < 3) return [];
  const ranked = [...groups].sort((left, right) => left.n - right.n);
  const median = ranked[Math.floor(ranked.length / 2)].n;
  return groups.filter((group) => group.n * 3 < median).map((group) => group.y);
}

function orientedMass(group, y) {
  const count = group.length;
  let cx = 0;
  let cz = 0;
  for (const panel of group) {
    cx += panel.x;
    cz += panel.z;
  }
  cx /= count;
  cz /= count;
  let xx = 0;
  let zz = 0;
  let xz = 0;
  for (const panel of group) {
    const dx = panel.x - cx;
    const dz = panel.z - cz;
    xx += dx * dx;
    zz += dz * dz;
    xz += dx * dz;
  }
  const angle = 0.5 * Math.atan2(2 * xz, xx - zz);
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  let minU = Infinity;
  let maxU = -Infinity;
  let minV = Infinity;
  let maxV = -Infinity;
  for (const panel of group) {
    const dx = panel.x - cx;
    const dz = panel.z - cz;
    const u = dx * cos + dz * sin;
    const v = -dx * sin + dz * cos;
    if (u < minU) minU = u;
    if (u > maxU) maxU = u;
    if (v < minV) minV = v;
    if (v > maxV) maxV = v;
  }
  return {
    y,
    cx,
    cz,
    cos,
    sin,
    minU: minU - MASS_PAD,
    maxU: maxU + MASS_PAD,
    minV: minV - MASS_PAD,
    maxV: maxV + MASS_PAD,
  };
}

function clusterMasses(panels) {
  const storeys = [];
  const sorted = [...panels].sort((left, right) => left.y - right.y);
  for (const panel of sorted) {
    const storey = storeys.at(-1);
    if (!storey || panel.y - storey.y > 0.6) {
      storeys.push({ y: panel.y, panels: [panel] });
    } else {
      storey.panels.push(panel);
      storey.y += (panel.y - storey.y) / storey.panels.length;
    }
  }
  const masses = [];
  const link = MASS_LINK * MASS_LINK;
  for (const storey of storeys) {
    const group = storey.panels;
    const parent = group.map((_, index) => index);
    const find = (index) => (parent[index] === index ? index : (parent[index] = find(parent[index])));
    for (let i = 0; i < group.length; i += 1) {
      for (let j = i + 1; j < group.length; j += 1) {
        const dx = group[i].x - group[j].x;
        const dz = group[i].z - group[j].z;
        if (dx * dx + dz * dz > link) continue;
        parent[find(i)] = find(j);
      }
    }
    const buckets = new Map();
    for (let i = 0; i < group.length; i += 1) {
      const root = find(i);
      const list = buckets.get(root);
      if (list) list.push(group[i]);
      else buckets.set(root, [group[i]]);
    }
    for (const bucket of buckets.values()) {
      if (bucket.length < 4) continue;
      masses.push(orientedMass(bucket, storey.y));
    }
  }
  return masses;
}

function massAt(masses, panel) {
  let best = null;
  let bestDist = Infinity;
  for (const mass of masses) {
    if (Math.abs(mass.y - panel.y) > 0.8) continue;
    const dx = panel.x - mass.cx;
    const dz = panel.z - mass.cz;
    const u = dx * mass.cos + dz * mass.sin;
    const v = -dx * mass.sin + dz * mass.cos;
    if (u < mass.minU - 0.5 || u > mass.maxU + 0.5) continue;
    if (v < mass.minV - 0.5 || v > mass.maxV + 0.5) continue;
    const dist = Math.abs(mass.y - panel.y);
    if (dist >= bestDist) continue;
    best = mass;
    bestDist = dist;
  }
  return best;
}

function lanternCorners(panel, mass, y1, y0) {
  const dx = panel.x - mass.cx;
  const dz = panel.z - mass.cz;
  const u = dx * mass.cos + dz * mass.sin;
  const v = -dx * mass.sin + dz * mass.cos;
  const u0 = Math.max(mass.minU, u - HALF);
  const u1 = Math.min(mass.maxU, u + HALF);
  const v0 = Math.max(mass.minV, v - HALF);
  const v1 = Math.min(mass.maxV, v + HALF);
  if (u1 - u0 < 0.2 || v1 - v0 < 0.2) return null;
  const world = (uu, vv) => ({
    x: mass.cx + uu * mass.cos - vv * mass.sin,
    z: mass.cz + uu * mass.sin + vv * mass.cos,
  });
  const a = world(u0, v0);
  const b = world(u1, v0);
  const c = world(u1, v1);
  const d = world(u0, v1);
  return [
    [a.x, y1, a.z], [b.x, y1, b.z], [c.x, y1, c.z], [d.x, y1, d.z],
    [a.x, y0, a.z], [b.x, y0, b.z], [c.x, y0, c.z], [d.x, y0, d.z],
  ];
}

function addLightVolumes(model, panels) {
  const skip = sparseHeights(panels);
  const masses = clusterMasses(panels);
  const positions = [];
  const colors = [];
  const indices = [];
  let volumes = 0;
  for (const panel of panels) {
    if (skip.some((y) => Math.abs(y - panel.y) < 0.8)) continue;
    const y1 = panel.y - 0.05;
    const y0 = y1 - DROP;
    if (y0 < 1) continue;
    const mass = massAt(masses, panel);
    if (!mass) continue;
    const corners = lanternCorners(panel, mass, y1, y0);
    if (!corners) continue;
    const top = [
      panel.color[0] * TOP_GAIN,
      panel.color[1] * TOP_GAIN,
      panel.color[2] * TOP_GAIN,
    ];
    const bottom = [
      panel.color[0] * BOTTOM_GAIN,
      panel.color[1] * BOTTOM_GAIN,
      panel.color[2] * BOTTOM_GAIN,
    ];
    const index = positions.length / 3;
    for (let corner = 0; corner < 8; corner += 1) {
      positions.push(corners[corner][0], corners[corner][1], corners[corner][2]);
      const tint = corner < 4 ? top : bottom;
      colors.push(tint[0], tint[1], tint[2]);
    }
    indices.push(
      // top
      index, index + 1, index + 2, index, index + 2, index + 3,
      // bottom
      index + 4, index + 6, index + 5, index + 4, index + 7, index + 6,
      // sides
      index, index + 4, index + 5, index, index + 5, index + 1,
      index + 1, index + 5, index + 6, index + 1, index + 6, index + 2,
      index + 2, index + 6, index + 7, index + 2, index + 7, index + 3,
      index + 3, index + 7, index + 4, index + 3, index + 4, index,
    );
    volumes += 1;
  }
  if (!indices.length) return null;
  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  const material = new THREE.MeshBasicMaterial({
    vertexColors: true,
    transparent: true,
    depthWrite: false,
    depthTest: true,
    side: THREE.DoubleSide,
    blending: THREE.AdditiveBlending,
    toneMapped: false,
  });
  const object = new THREE.Mesh(geometry, material);
  object.name = 'CeilingGlow_Volumes';
  object.renderOrder = 2;
  model.add(object);
  return { object, volumes };
}

export async function addCeilingGlow(model) {
  model.updateWorldMatrix(true, true);
  const panels = collectLights(model);
  if (!panels.length) return null;
  // No hideApartmentVision — the exterior geometry stays intact.
  // The apartment dark glass is made semi-transparent in main.js so the
  // interior volumes read through it.
  const volumes = addLightVolumes(model, panels);
  if (!volumes) return { panels: panels.length, floors: 0 };
  return {
    panels: panels.length,
    floors: volumes.volumes,
    overlays: [volumes],
  };
}

export function removeCeilingGlow(state) {
  if (!state?.overlays) return;
  for (const overlay of state.overlays) {
    overlay.object.material?.dispose();
    overlay.object.geometry?.dispose();
    overlay.object.parent?.remove(overlay.object);
  }
}
