import * as THREE from 'three/webgpu';
import { attribute, materialColor, mix, vec3 } from 'three/tsl';

// Each ceiling fixture is a source. For every floor vertex we sum the fixtures
// on the ceiling above it, with inverse-square falloff, and store that on the
// vertex. The slab then emits the sum, so the room reads as lit from outside
// the glass. A compute bake was measured on this GPU, but the slab triangles
// are too coarse to sample a light map without turning into slabs of colour.
const CELL = 0.75;

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

function collectFloors(model) {
  let ground = null;
  model.traverse((object) => {
    if (object.name === 'Ground_Site') ground = object;
  });
  if (!ground?.geometry?.getIndex()) return { ground: null, floors: [] };
  const geometry = ground.geometry;
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();
  const matrix = ground.matrixWorld;
  const vertex = new THREE.Vector3();
  const facing = new THREE.Vector3();
  const triangles = [];
  for (let triangle = 0; triangle < index.count; triangle += 3) {
    const ids = [0, 1, 2].map((corner) => index.getX(triangle + corner));
    let ny = 0;
    const corners = [];
    for (const id of ids) {
      facing.fromBufferAttribute(normal, id).transformDirection(matrix);
      ny += facing.y;
      vertex.fromBufferAttribute(position, id).applyMatrix4(matrix);
      corners.push(vertex.clone());
    }
    if (ny / 3 < 0.45) continue;
    const y = (corners[0].y + corners[1].y + corners[2].y) / 3;
    if (y < 8 || y > 335) continue;
    const area = Math.abs(
      (corners[1].x - corners[0].x) * (corners[2].z - corners[0].z)
      - (corners[1].z - corners[0].z) * (corners[2].x - corners[0].x),
    ) * 0.5;
    if (area < 0.15 || area > 30) continue;
    const spread = Math.max(corners[0].y, corners[1].y, corners[2].y)
      - Math.min(corners[0].y, corners[1].y, corners[2].y);
    if (spread > 3.2) continue;
    triangles.push({ y, corners });
  }
  triangles.sort((left, right) => left.y - right.y);
  const floors = [];
  for (const triangle of triangles) {
    const floor = floors.at(-1);
    if (!floor || triangle.y - floor.y > 0.8) floors.push({ y: triangle.y, triangles: [triangle] });
    else floor.triangles.push(triangle);
  }
  return {
    ground,
    floors: floors.filter((floor) => floor.triangles.length > 8),
  };
}

function subdivideFloor(ground) {
  const geometry = ground.geometry;
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();
  if (!index) return null;
  const matrix = ground.matrixWorld;
  const inverse = matrix.clone().invert();
  const uv = geometry.getAttribute('uv');
  const positions = [];
  const normals = [];
  const uvs = [];
  const indices = [];
  const facing = new THREE.Vector3();
  const world = new THREE.Vector3();
  const local = new THREE.Vector3();
  const push = (point, normalVector, id) => {
    local.copy(point).applyMatrix4(inverse);
    positions.push(local.x, local.y, local.z);
    normals.push(normalVector.x, normalVector.y, normalVector.z);
    if (uv && id != null) uvs.push(uv.getX(id), uv.getY(id));
    else uvs.push(0, 0);
    return (positions.length / 3) - 1;
  };
  for (let triangle = 0; triangle < index.count; triangle += 3) {
    const ids = [0, 1, 2].map((corner) => index.getX(triangle + corner));
    const localNormal = new THREE.Vector3().fromBufferAttribute(normal, ids[0]);
    facing.copy(localNormal).transformDirection(matrix);
    const corners = ids.map((id) => world.fromBufferAttribute(position, id).applyMatrix4(matrix).clone());
    const horizontal = Math.abs(facing.y) > 0.45;
    const span = Math.max(
      corners[0].distanceTo(corners[1]),
      corners[1].distanceTo(corners[2]),
      corners[2].distanceTo(corners[0]),
    );
    const steps = horizontal ? Math.min(4, Math.max(1, Math.round(span / 4))) : 1;
    if (steps === 1) {
      indices.push(
        push(corners[0], localNormal, ids[0]),
        push(corners[1], localNormal, ids[1]),
        push(corners[2], localNormal, ids[2]),
      );
      continue;
    }
    const grid = [];
    for (let row = 0; row <= steps; row += 1) {
      grid[row] = [];
      for (let column = 0; column <= steps - row; column += 1) {
        const u = column / steps;
        const v = row / steps;
        const point = corners[0].clone().multiplyScalar(1 - u - v)
          .add(corners[1].clone().multiplyScalar(u))
          .add(corners[2].clone().multiplyScalar(v));
        const id = v > u ? ids[2] : ids[u > 0.5 ? 1 : 0];
        grid[row][column] = push(point, localNormal, id);
      }
    }
    for (let row = 0; row < steps; row += 1) {
      for (let column = 0; column < steps - row; column += 1) {
        indices.push(grid[row][column], grid[row][column + 1], grid[row + 1][column]);
        if (column + row + 1 < steps) {
          indices.push(grid[row][column + 1], grid[row + 1][column + 1], grid[row + 1][column]);
        }
      }
    }
  }
  const next = new THREE.BufferGeometry();
  next.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
  next.setAttribute('normal', new THREE.Float32BufferAttribute(normals, 3));
  if (uv) next.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
  next.setIndex(indices);
  ground.geometry = next;
  return geometry;
}

function paintFloors(ground, spans, lights) {
  const geometry = ground.geometry;
  const position = geometry.getAttribute('position');
  const normal = geometry.getAttribute('normal');
  const index = geometry.getIndex();
  const count = position.count;
  const color = new Float32Array(count * 3);
  const layer = new Float32Array(count);
  const matrix = ground.matrixWorld;
  const vertex = new THREE.Vector3();
  for (let vertexIndex = 0; vertexIndex < count; vertexIndex += 1) {
    const facingY = normal.getY(vertexIndex);
    const upward = facingY > 0.45;
    const downward = facingY < -0.45;
    if (!upward && !downward) continue;
    vertex.fromBufferAttribute(position, vertexIndex).applyMatrix4(matrix);
    if (upward && spans.length) {
      let nearest = spans[0].y;
      let bestGap = Math.abs(vertex.y - nearest);
      for (const span of spans) {
        const gap = Math.abs(vertex.y - span.y);
        if (gap < bestGap) {
          bestGap = gap;
          nearest = span.y;
        }
      }
      if (bestGap < 2.2 && bestGap > 0.02) {
        vertex.y = nearest;
        const moved = vertex.clone().applyMatrix4(matrix.clone().invert());
        position.setXYZ(vertexIndex, moved.x, moved.y, moved.z);
      }
    }
    let best = -1;
    let distance = Infinity;
    for (let floor = 0; floor < spans.length; floor += 1) {
      const gap = upward ? vertex.y - spans[floor].y : spans[floor].y - vertex.y;
      const limit = upward ? 4.8 : 1.2;
      if (gap < -0.15 || gap > limit || Math.abs(gap) >= distance) continue;
      distance = Math.abs(gap);
      best = floor;
    }
    if (best < 0) continue;
    const span = spans[best];
    let red = 0;
    let green = 0;
    let blue = 0;
    for (let lightIndex = span.light0; lightIndex < span.light0 + span.nlights; lightIndex += 1) {
      const light = lights[lightIndex];
      const drop = upward ? light[1] - vertex.y : vertex.y - light[1];
      if (upward && (drop < 0.05 || drop > 4.6)) continue;
      if (!upward && drop > 0.8) continue;
      const dx = light[0] - vertex.x;
      const dz = light[2] - vertex.z;
      const reach = dx * dx + dz * dz;
      if (!upward && reach > 2.25) continue;
      const dist2 = Math.max(reach + drop * drop, upward ? 0.36 : 0.04);
      const lambert = upward ? Math.min(Math.max(drop / Math.sqrt(dist2), 0), 1) : 1;
      const scale = lambert / dist2;
      red += light[4] * light[7] * scale;
      green += light[5] * light[7] * scale;
      blue += light[6] * light[7] * scale;
    }
    const gain = upward ? 4.5 : 0.08;
    color[vertexIndex * 3] = Math.min(red * gain, 12);
    color[vertexIndex * 3 + 1] = Math.min(green * gain, 12);
    color[vertexIndex * 3 + 2] = Math.min(blue * gain, 12);
    layer[vertexIndex] = red + green + blue > 0.002 ? 1 : 0;
  }
  ground.geometry.setAttribute('roomLight', new THREE.BufferAttribute(color, 3));
  ground.geometry.setAttribute('roomLayer', new THREE.BufferAttribute(layer, 1));
  const source = ground.material;
  const material = source.clone();
  const baked = attribute('roomLight', 'vec3');
  const present = attribute('roomLayer', 'float');
  material.colorNode = mix(materialColor, baked, present);
  material.emissiveNode = baked.mul(present);
  material.emissive = new THREE.Color(1, 1, 1);
  material.emissiveIntensity = 1;
  ground.material = material;
  return { object: ground, source };
}

export async function addCeilingGlow(model) {
  model.updateWorldMatrix(true, true);
  const panels = collectLights(model);
  const { ground, floors } = collectFloors(model);
  if (!panels.length || !floors.length || !ground) return null;

  const lights = panels
    .map((panel) => [panel.x, panel.y, panel.z, 1, panel.color[0], panel.color[1], panel.color[2], panel.strength])
    .sort((left, right) => left[1] - right[1]);
  const spans = [];
  for (const floor of floors) {
    let light0 = lights.findIndex((light) => light[1] > floor.y + 0.3);
    if (light0 < 0) light0 = lights.length;
    let light1 = light0;
    while (light1 < lights.length && lights[light1][1] < floor.y + 4.4) light1 += 1;
    if (light1 === light0) continue;
    spans.push({ light0, nlights: light1 - light0, y: floor.y });
  }
  if (!spans.length) return { panels: panels.length, floors: floors.length };
  const previous = subdivideFloor(ground);
  const overlay = paintFloors(ground, spans, lights);
  overlay.previous = previous;
  return { panels: panels.length, floors: spans.length, overlays: [overlay] };
}

export function removeCeilingGlow(state) {
  if (!state?.overlays) return;
  for (const overlay of state.overlays) {
    overlay.object.material = overlay.source;
    if (overlay.previous) {
      overlay.object.geometry.dispose();
      overlay.object.geometry = overlay.previous;
    }
  }
}
