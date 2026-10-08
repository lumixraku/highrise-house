import * as THREE from 'three';

// One downward face of a fixture becomes one light. Optimised GLBs keep both
// faces of a thin panel and split them into triangles, so triangles are grouped
// by location before the two faces of one panel are merged.
const CELL = 0.75;
const FALLOFF = 3.2;
const SIGMA = 1.15;
const TEXELS_PER_METRE = 2;

function panelsOf(geometry, matrix, color, strength) {
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();
  if (!position || !normal || !index) return [];
  const vertex = new THREE.Vector3();
  const facing = new THREE.Vector3();
  const buckets = new Map();
  for (let triangle = 0; triangle < index.count; triangle += 3) {
    const a = index.getX(triangle);
    facing.fromBufferAttribute(normal, a).transformDirection(matrix);
    if (facing.y > -0.5) continue;
    vertex.fromBufferAttribute(position, a).applyMatrix4(matrix);
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
  cells.sort((p, q) => p.y - q.y || p.x - q.x || p.z - q.z);
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

function gainOf(strength) {
  // Exported strengths run from 8 to 360. Compress that so a bright podium
  // fitting does not erase the dimmer room panels.
  return Math.min(1.4, 0.35 * Math.pow(strength, 0.25));
}

function bakeFloor(panels) {
  let minX = Infinity;
  let maxX = -Infinity;
  let minZ = Infinity;
  let maxZ = -Infinity;
  for (const panel of panels) {
    minX = Math.min(minX, panel.x);
    maxX = Math.max(maxX, panel.x);
    minZ = Math.min(minZ, panel.z);
    maxZ = Math.max(maxZ, panel.z);
  }
  const pad = 0.4;
  minX -= pad;
  maxX += pad;
  minZ -= pad;
  maxZ += pad;
  const width = Math.max(1, Math.ceil((maxX - minX) * TEXELS_PER_METRE));
  const height = Math.max(1, Math.ceil((maxZ - minZ) * TEXELS_PER_METRE));
  const red = new Float32Array(width * height);
  const green = new Float32Array(width * height);
  const blue = new Float32Array(width * height);
  for (const panel of panels) {
    const gain = gainOf(panel.strength);
    const x0 = Math.max(0, Math.floor(((panel.x - FALLOFF) - minX) * TEXELS_PER_METRE));
    const x1 = Math.min(width - 1, Math.ceil(((panel.x + FALLOFF) - minX) * TEXELS_PER_METRE));
    const z0 = Math.max(0, Math.floor(((panel.z - FALLOFF) - minZ) * TEXELS_PER_METRE));
    const z1 = Math.min(height - 1, Math.ceil(((panel.z + FALLOFF) - minZ) * TEXELS_PER_METRE));
    for (let z = z0; z <= z1; z += 1) {
      for (let x = x0; x <= x1; x += 1) {
        const worldX = minX + (x + 0.5) / TEXELS_PER_METRE;
        const worldZ = minZ + (z + 0.5) / TEXELS_PER_METRE;
        const distance = Math.hypot(worldX - panel.x, worldZ - panel.z);
        if (distance > FALLOFF) continue;
        const falloff = Math.exp(-(distance * distance) / (2 * SIGMA * SIGMA));
        const texel = z * width + x;
        red[texel] += panel.color[0] * gain * falloff;
        green[texel] += panel.color[1] * gain * falloff;
        blue[texel] += panel.color[2] * gain * falloff;
      }
    }
  }
  let peak = 0;
  for (let i = 0; i < red.length; i += 1) peak = Math.max(peak, red[i], green[i], blue[i]);
  const data = new Uint8Array(width * height * 4);
  const scale = peak > 0 ? 255 / peak : 0;
  for (let i = 0; i < red.length; i += 1) {
    const value = Math.max(red[i], green[i], blue[i]);
    const alpha = value <= 0.05 ? 0 : Math.min(255, Math.round(70 + 185 * (value / peak)));
    data[i * 4] = Math.min(255, Math.round(red[i] * scale));
    data[i * 4 + 1] = Math.min(255, Math.round(green[i] * scale));
    data[i * 4 + 2] = Math.min(255, Math.round(blue[i] * scale));
    data[i * 4 + 3] = alpha;
  }
  const texture = new THREE.DataTexture(data, width, height);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.wrapS = THREE.ClampToEdgeWrapping;
  texture.wrapT = THREE.ClampToEdgeWrapping;
  texture.magFilter = THREE.LinearFilter;
  texture.minFilter = THREE.LinearFilter;
  texture.needsUpdate = true;
  return { texture, bounds: { minX, maxX, minZ, maxZ }, peak };
}

function groupFloors(panels) {
  const floors = [];
  for (const panel of [...panels].sort((a, b) => a.y - b.y)) {
    const floor = floors.at(-1);
    if (!floor || panel.y - floor.y > 1.5) floors.push({ y: panel.y, panels: [panel] });
    else floor.panels.push(panel);
  }
  return floors;
}

export function addCeilingGlow(model) {
  model.updateWorldMatrix(true, true);
  const panels = [];
  model.traverse((object) => {
    if (!object.isMesh) return;
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    for (const material of materials) {
      const color = material?.emissive ? material.emissive.toArray() : [0, 0, 0];
      const lit = (material?.emissiveIntensity ?? 0) > 1
        && color.some((channel) => channel > 0.02);
      if (!lit) continue;
      panels.push(...panelsOf(object.geometry, object.matrixWorld, color, material.emissiveIntensity));
    }
  });
  if (!panels.length) return null;

  const group = new THREE.Group();
  group.name = 'CeilingGlow';
  for (const floor of groupFloors(panels)) {
    const { texture, bounds, peak } = bakeFloor(floor.panels);
    const glow = new THREE.Mesh(
      new THREE.PlaneGeometry(bounds.maxX - bounds.minX, bounds.maxZ - bounds.minZ),
      new THREE.MeshBasicMaterial({
        map: texture,
        transparent: true,
        depthWrite: false,
        side: THREE.DoubleSide,
        toneMapped: false,
      }),
    );
    glow.position.set(
      (bounds.minX + bounds.maxX) / 2,
      floor.y + 2.6,
      (bounds.minZ + bounds.maxZ) / 2,
    );
    glow.rotation.x = Math.PI / 2;
    glow.renderOrder = 2;
    glow.userData.peak = peak;
    group.add(glow);
  }
  model.parent.add(group);
  return { panels: panels.length, floors: group.children.length, group };
}

export function removeCeilingGlow(group) {
  if (!group) return;
  group.removeFromParent();
  for (const glow of group.children) {
    glow.geometry.dispose();
    glow.material.map?.dispose();
    glow.material.dispose();
  }
}
