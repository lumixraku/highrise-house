import * as THREE from 'three/webgpu';
import { attribute, float } from 'three/tsl';

// Each lit ceiling fixture fills the air under it with a translucent volume,
// so the occupied room reads as lit from any street angle. The web GLB has no
// real lights; this is a merged mesh of one box per fixture, not a bake
// onto the floor and not a sticker on the facade.
//
// The volumes sit strictly inside the curtain wall — no clamping to the facade
// plane, no outset, no window punching. The apartment-band dark glass is made
// semi-transparent in main.js so the glow reads through it.
const CELL = 0.75;

// Building envelope inset: volumes must not touch the glass skin.
// Blender scene: WIDTH=115, DEPTH=40, FACADE=0.30, GLASS_BACK=0.01, GLASS_T=0.12.
// glTF Y-up: Blender X→X, Blender Y→Z, Blender Z→Y.
// Half-widths of the glass inner face in viewer coordinates:
const HALF_X = 115 / 2 + 0.30 - 0.01 - 0.12; // ~57.67
const HALF_Z = 40 / 2 + 0.30 - 0.01 - 0.12;  // ~20.17
// Keep volumes 0.5 m inside the glass so they never touch the skin.
const INSET = 0.5;
const LIMIT_X = HALF_X - INSET;  // ~57.17
const LIMIT_Z = HALF_Z - INSET;  // ~19.67

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

function storeyHeight(lightY) {
  return lightY < 155 ? 5 : 4;
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

function gardenHeights(panels) {
  const skip = [];
  for (const group of clusterStoreys(panels)) {
    if (group.y > 42 && group.n <= 40) skip.push(group.y);
  }
  return skip;
}

function addLightVolumes(model, panels) {
  const skip = gardenHeights(panels);
  const positions = [];
  const colors = [];
  const indices = [];
  let volumes = 0;
  for (const panel of panels) {
    if (skip.some((y) => Math.abs(y - panel.y) < 0.8)) continue;
    const sh = storeyHeight(panel.y);
    // Full room box: from just below the ceiling fixture down to floor level,
    // wide enough to fill the bay around the fixture. Strictly inside the
    // envelope — no clamping to the facade plane.
    const y1 = panel.y - 0.05;       // just below the fixture
    const y0 = y1 - (sh - 0.35);     // near the floor, leaving a gap
    if (y0 < 1) continue;
    // Room-filling box: 1.6 m half-width at top and bottom (a ~3.2 m bay).
    const half = 1.6;
    const x0 = Math.max(-LIMIT_X, panel.x - half);
    const x1 = Math.min(LIMIT_X, panel.x + half);
    const z0 = Math.max(-LIMIT_Z, panel.z - half);
    const z1 = Math.min(LIMIT_Z, panel.z + half);
    if (x1 - x0 < 0.3 || z1 - z0 < 0.3) continue;
    const corners = [
      [x0, y1, z0], [x1, y1, z0], [x1, y1, z1], [x0, y1, z1],
      [x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1],
    ];
    const gain = Math.min(panel.strength * 0.04, 0.5);
    const red = panel.color[0] * gain;
    const green = panel.color[1] * gain;
    const blue = panel.color[2] * gain;
    const index = positions.length / 3;
    for (const corner of corners) {
      positions.push(corner[0], corner[1], corner[2]);
      colors.push(red, green, blue);
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
  geometry.setAttribute('roomLight', new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  const baked = attribute('roomLight', 'vec3');
  const material = new THREE.MeshStandardNodeMaterial();
  material.colorNode = baked;
  material.emissiveNode = baked;
  material.emissive = new THREE.Color(1, 1, 1);
  material.emissiveIntensity = 1;
  material.metalness = 0;
  material.roughness = 1;
  material.transparent = true;
  material.opacityNode = float(0.32);
  material.depthWrite = false;
  material.side = THREE.DoubleSide;
  material.blending = THREE.AdditiveBlending;
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
