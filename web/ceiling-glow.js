import * as THREE from 'three/webgpu';
import { RectAreaLightTexturesLib } from './vendor/RectAreaLightTexturesLib.js';

// Thousands of ceiling fixtures cannot each be a GPU light. Cluster the
// occupied plates, then keep a handful of large downward rect lights — real
// lighting, not a mesh volume. WebGPU evaluates every area light per pixel.
const CELL = 0.75;
const MASS_PAD = 0.35;
const MASS_LINK = 8;
const LIGHT_INSET = 2.4;
const LIGHT_NITS = 28;
const LIGHT_DROP = 0.25;
const MAX_LIGHTS = 12;
let areaLightsReady = false;

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
      masses.push({ ...orientedMass(bucket, storey.y), panels: bucket });
    }
  }
  return masses;
}

function averageColor(list) {
  let red = 0;
  let green = 0;
  let blue = 0;
  for (const panel of list) {
    red += panel.color[0];
    green += panel.color[1];
    blue += panel.color[2];
  }
  const n = list.length;
  return new THREE.Color(red / n, green / n, blue / n);
}

function buildingBox(model, masses) {
  const box = new THREE.Box3();
  model.traverse((object) => {
    if (!object.isMesh) return;
    if (/ground|site|foliage|trunk|light/i.test(object.name)) return;
    box.expandByObject(object);
  });
  let minY = Infinity;
  for (const mass of masses) {
    if (mass.y < minY) minY = mass.y;
  }
  return {
    minX: box.min.x + LIGHT_INSET,
    maxX: box.max.x - LIGHT_INSET,
    minY,
    maxY: box.max.y,
    minZ: box.min.z + LIGHT_INSET,
    maxZ: box.max.z - LIGHT_INSET,
  };
}

function factorGrid(count, sx, sy, sz) {
  let nx = 1;
  let ny = count;
  let nz = 1;
  let best = Infinity;
  for (let x = 1; x <= count; x += 1) {
    for (let y = 1; x * y <= count; y += 1) {
      if (count % (x * y)) continue;
      const z = count / (x * y);
      const cx = sx / x;
      const cy = sy / y;
      const cz = sz / z;
      const score = Math.max(cx, cy, cz) / Math.min(cx, cy, cz);
      if (score >= best) continue;
      best = score;
      nx = x;
      ny = y;
      nz = z;
    }
  }
  return { nx, ny, nz };
}

function nearestMass(masses, x, y, z) {
  let best = masses[0];
  let bestD = Infinity;
  for (const mass of masses) {
    const dx = mass.cx - x;
    const dy = mass.y - y;
    const dz = mass.cz - z;
    const d = dx * dx + dy * dy + dz * dz;
    if (d >= bestD) continue;
    bestD = d;
    best = mass;
  }
  return best;
}

function ensureAreaLights() {
  if (areaLightsReady) return;
  THREE.RectAreaLightNode.setLTC(RectAreaLightTexturesLib.init());
  areaLightsReady = true;
}

function receiveInteriorLight(model) {
  model.traverse((object) => {
    if (!object.isMesh) return;
    if (/glass|frame|truss|mullion|metal|light|ground|site|foliage|trunk/i.test(object.name)) return;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) {
      if (!material || material.metalness === undefined) continue;
      material.metalness = 0;
      material.needsUpdate = true;
    }
  });
}

function addFloorLights(model, panels) {
  const skip = sparseHeights(panels);
  const masses = clusterMasses(panels).filter(
    (mass) => !skip.some((y) => Math.abs(y - mass.y) < 0.8),
  );
  if (!masses.length) return null;
  const box = buildingBox(model, masses);
  const sx = Math.max(2, box.maxX - box.minX);
  const sy = Math.max(2, box.maxY - box.minY);
  const sz = Math.max(2, box.maxZ - box.minZ);
  const { nx, ny, nz } = factorGrid(MAX_LIGHTS, sx, sy, sz);
  const cellX = sx / nx;
  const cellY = sy / ny;
  const cellZ = sz / nz;
  const group = new THREE.Group();
  group.name = 'CeilingGlow_Lights';
  let lights = 0;
  for (let iy = 0; iy < ny; iy += 1) {
    // Sit on the cell ceiling and shine down, so the crown is covered.
    const y = box.minY + (iy + 1) * cellY - LIGHT_DROP;
    for (let ix = 0; ix < nx; ix += 1) {
      for (let iz = 0; iz < nz; iz += 1) {
        const x = box.minX + (ix + 0.5) * cellX;
        const z = box.minZ + (iz + 0.5) * cellZ;
        const mass = nearestMass(masses, x, y, z);
        const light = new THREE.RectAreaLight(
          averageColor(mass.panels),
          LIGHT_NITS,
          Math.max(2, cellZ - LIGHT_INSET * 2),
          Math.max(2, cellX - LIGHT_INSET * 2),
        );
        light.position.set(x, y, z);
        light.lookAt(x, y - 4, z);
        light.name = 'CeilingGlow_Area';
        group.add(light);
        lights += 1;
      }
    }
  }
  if (!lights) return null;
  model.add(group);
  return { object: group, lights };
}

export async function addCeilingGlow(model) {
  model.updateWorldMatrix(true, true);
  const panels = collectLights(model);
  if (!panels.length) return null;
  ensureAreaLights();
  receiveInteriorLight(model);
  const glow = addFloorLights(model, panels);
  if (!glow) return { panels: panels.length, floors: 0 };
  return {
    panels: panels.length,
    floors: glow.lights,
    overlays: [glow],
  };
}

export function removeCeilingGlow(state) {
  if (!state?.overlays) return;
  for (const overlay of state.overlays) {
    overlay.object.traverse((object) => {
      object.geometry?.dispose();
      object.material?.dispose();
    });
    overlay.object.parent?.remove(overlay.object);
  }
}
