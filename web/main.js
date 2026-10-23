import * as THREE from 'three/webgpu';
import { WebGPURenderer } from 'three/webgpu';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { addCeilingGlow, removeCeilingGlow } from './ceiling-glow.js';

const viewer = document.querySelector('#viewer');
const status = document.querySelector('#load-status');
const loadingCard = document.querySelector('#loading-card');
const viewButtons = [...document.querySelectorAll('.view-button')];
const resetButton = document.querySelector('#reset-view');
const ceilingGlowButton = document.querySelector('#ceiling-glow');
const modelList = document.querySelector('#model-list');
const modelEyebrow = document.querySelector('#model-eyebrow');
const modelTitle = document.querySelector('#model-title');
const modelIntro = document.querySelector('#model-intro');
const metricHeight = document.querySelector('#metric-height');
const metricStoreys = document.querySelector('#metric-storeys');
const metricFootprint = document.querySelector('#metric-footprint');

const scene = new THREE.Scene();
scene.background = new THREE.Color('#8e9d93');

const camera = new THREE.PerspectiveCamera(34, 1, 0.5, 2500);
const devicePixelRatio = window.devicePixelRatio || 1;
const idlePixelRatio = Math.min(devicePixelRatio, 2);
const interactionPixelRatio = Math.min(devicePixelRatio, 1);
const renderer = new WebGPURenderer({
  antialias: true,
  powerPreference: 'high-performance',
});
await renderer.init();
renderer.setPixelRatio(idlePixelRatio);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.sortObjects = true;
window.__stackDebug = { renderer, scene, camera, renderFrames: 0 };
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.82;
viewer.appendChild(renderer.domElement);

// The Blender EEVEE glass uses a node mix that glTF cannot preserve. This
// neutral studio environment gives the reconstructed physical glass something
// real to reflect without adding haze to the camera view.
const pmrem = new THREE.PMREMGenerator(renderer);
const environment = new RoomEnvironment();
scene.environment = (await pmrem.fromSceneAsync(environment, 0.04)).texture;
scene.environmentIntensity = 0.6;
environment.dispose();
pmrem.dispose();

// RoomEnvironment is intentionally soft, but a uniform room has no readable
// reflection pattern on front-facing glass. Add two high-contrast softbox
// bands to the reflection-only environment; they are not visible as scenery.
const reflectionCanvas = document.createElement('canvas');
reflectionCanvas.width = 1024;
reflectionCanvas.height = 512;
const reflectionContext = reflectionCanvas.getContext('2d');
const reflectionGradient = reflectionContext.createLinearGradient(0, 0, 1024, 0);
reflectionGradient.addColorStop(0, '#13272d');
reflectionGradient.addColorStop(0.24, '#203b42');
reflectionGradient.addColorStop(0.34, '#d9f4f1');
reflectionGradient.addColorStop(0.39, '#35545a');
reflectionGradient.addColorStop(0.62, '#182f36');
reflectionGradient.addColorStop(0.72, '#fff0d3');
reflectionGradient.addColorStop(0.77, '#345057');
reflectionGradient.addColorStop(1, '#102229');
reflectionContext.fillStyle = reflectionGradient;
reflectionContext.fillRect(0, 0, 1024, 512);
const reflectionTexture = new THREE.CanvasTexture(reflectionCanvas);
reflectionTexture.colorSpace = THREE.SRGBColorSpace;
reflectionTexture.mapping = THREE.EquirectangularReflectionMapping;
const reflectionPmrem = new THREE.PMREMGenerator(renderer);
scene.environment = (await reflectionPmrem.fromEquirectangularAsync(reflectionTexture)).texture;
scene.environmentIntensity = 1.0;
reflectionTexture.dispose();
reflectionPmrem.dispose();

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.06;
controls.minDistance = 95;
controls.maxDistance = 720;
// glTF is Y-up: Blender Z becomes Three.js Y after export.
controls.target.set(0, 145, 0);

let renderQueued = false;
let restoreRenderScale;
function requestRender() {
  if (renderQueued) return;
  renderQueued = true;
  requestAnimationFrame(renderFrame);
}
function setRenderScale(scale) {
  renderer.setPixelRatio(scale);
  resize();
  requestRender();
}
function renderFrame() {
  renderQueued = false;
  const dampingActive = controls.update();
  window.__stackDebug.renderFrames += 1;
  renderer.render(scene, camera);
  if (dampingActive) requestRender();
}
controls.addEventListener('change', requestRender);
controls.addEventListener('start', () => {
  clearTimeout(restoreRenderScale);
  setRenderScale(interactionPixelRatio);
});
controls.addEventListener('end', () => {
  clearTimeout(restoreRenderScale);
  restoreRenderScale = setTimeout(
    () => setRenderScale(idlePixelRatio),
    120
  );
});

const hemiLight = new THREE.HemisphereLight('#f4f7ed', '#7e8d83', 0.9);
scene.add(hemiLight);
const keyLight = new THREE.DirectionalLight('#fff8e5', 2.2);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight('#c3d9e5', 0.8);
scene.add(fillLight);
const SUN_DISTANCE = 420;
const DAY_BACKGROUND = new THREE.Color('#8e9d93');
const NIGHT_BACKGROUND = new THREE.Color('#141c22');
const DAY_GROUND = new THREE.Color('#aeb9af');
const NIGHT_GROUND = new THREE.Color('#2a3330');
const SUN_COLOR_NOON = new THREE.Color('#fff8e5');
const SUN_COLOR_HORIZON = new THREE.Color('#ff8a3a');
const SUN_COLOR_NIGHT = new THREE.Color('#8aa4c4');
const FILL_COLOR_DAY = new THREE.Color('#c3d9e5');
const FILL_COLOR_NIGHT = new THREE.Color('#1c2836');
const HEMI_SKY_DAY = new THREE.Color('#f4f7ed');
const HEMI_SKY_NIGHT = new THREE.Color('#1a2430');
const HEMI_GROUND_DAY = new THREE.Color('#7e8d83');
const HEMI_GROUND_NIGHT = new THREE.Color('#12181c');
const SUN_HANDLE_R = 54;
const SUN_CENTER = 70;
let sunHour = 10;

const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(900, 900),
  new THREE.MeshStandardMaterial({ color: '#aeb9af', roughness: 1 })
);
ground.rotation.x = -Math.PI / 2;
ground.position.y = -0.35;
scene.add(ground);
const grid = new THREE.GridHelper(600, 30, '#aebcaf', '#c6d0c3');
grid.position.y = -0.28;
grid.material.transparent = true;
grid.material.opacity = 0.22;
scene.add(grid);

// The Blender scene origin is the building footprint centre at ground level.
// Keep it visible in the viewer instead of relying on the text axis key alone.
const originAxes = new THREE.AxesHelper(24);
originAxes.position.set(0, 0.02, 0);
scene.add(originAxes);
const originMarker = new THREE.Mesh(
  new THREE.RingGeometry(1.3, 1.55, 40),
  new THREE.MeshBasicMaterial({ color: '#202421', side: THREE.DoubleSide })
);
originMarker.rotation.x = -Math.PI / 2;
originMarker.position.y = 0.04;
scene.add(originMarker);

const views = {
  overview: { position: new THREE.Vector3(310, 260, -390), target: new THREE.Vector3(0, 145, 0) },
  garden: { position: new THREE.Vector3(180, 128, -215), target: new THREE.Vector3(0, 118, 0) },
  base: { position: new THREE.Vector3(185, 42, -250), target: new THREE.Vector3(0, 30, 0) },
};
const models = {
  stack: {
    label: 'The Stack', meta: '01 / 301.8 m', asset: './assets/the_stack.optimized.glb',
    eyebrow: 'MVRDV competition proposal / web conversion',
    title: 'A vertical city,<br /><i>stacked in public.</i>',
    intro: 'A vertical sequence of retail, gardens, work and living bands, translated from the procedural Blender study.',
    metrics: ['301.8', '64', '115 × 40'],
  },
  abeno: {
    label: 'Abeno Harukas', meta: '02 / high-rise study', asset: './assets/abeno_harukas.optimized.glb',
    eyebrow: 'Structural facade study / web conversion',
    title: 'A tower of<br /><i>layered structure.</i>',
    intro: 'A procedural high-rise study with continuous curtain wall, truss bands and a linked core reconstruction.',
    metrics: ['300', '60+', '—'],
  },
  pompidou: {
    label: 'Centre Pompidou', meta: '03 / facade study', asset: './assets/centre_pompidou.optimized.glb',
    eyebrow: 'Centre Pompidou study / web conversion',
    title: 'Infrastructure<br /><i>on display.</i>',
    intro: 'A browser-ready study of exposed services, circulation and the building-scale facade language.',
    metrics: ['—', '—', '—'],
  },
  house: {
    label: 'Highrise House', meta: '04 / residential study', asset: './assets/highrise_house.optimized.glb',
    eyebrow: 'Residential tower study / web conversion',
    title: 'Domestic life<br /><i>in the vertical.</i>',
    intro: 'A residential high-rise with planted terraces, a continuous podium and a layered curtain wall.',
    metrics: ['—', '—', '—'],
  },
  office: {
    label: 'Office Tower', meta: '05 / office study', asset: './assets/office_tower.optimized.glb',
    eyebrow: 'Office tower study / web conversion',
    title: 'Workplace<br /><i>as a facade.</i>',
    intro: 'A compact office-tower study with modular glazing, floor plates and a readable interior rhythm.',
    metrics: ['—', '—', '—'],
  },
};
let model;
let ceilingGlow;
let ceilingGlowOn = true;
let activeModelId = 'stack';
let modelBounds;
let defaultView;

function getView(name) {
  if (activeModelId === 'stack' && views[name]) return views[name];
  if (!modelBounds || name === 'overview') return defaultView;
  const { center, size, distance } = modelBounds;
  const targetY = name === 'base'
    ? center.y - size.y * 0.28
    : center.y + size.y * 0.05;
  return {
    position: new THREE.Vector3(
      center.x + distance * 0.68,
      targetY + distance * 0.18,
      center.z - distance * 0.86
    ),
    target: new THREE.Vector3(center.x, targetY, center.z),
  };
}

function applyView(name, instant = false) {
  const view = getView(name);
  if (!view) return;
  viewButtons.forEach((button) => button.classList.toggle('is-active', button.dataset.view === name));
  if (instant) {
    camera.position.copy(view.position);
    controls.target.copy(view.target);
    controls.update();
    return;
  }
  const startPosition = camera.position.clone();
  const startTarget = controls.target.clone();
  const started = performance.now();
  const duration = 700;
  function animateView(now) {
    const progress = Math.min((now - started) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    camera.position.lerpVectors(startPosition, view.position, eased);
    controls.target.lerpVectors(startTarget, view.target, eased);
    controls.update();
    requestRender();
    if (progress < 1) requestAnimationFrame(animateView);
  }
  requestAnimationFrame(animateView);
}

function frameModel(object) {
  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxSize = Math.max(size.x, size.y, size.z);
  const distance = maxSize / (2 * Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) * 1.45;
  modelBounds = { center, size, maxSize, distance };
  controls.target.copy(center);
  camera.position.set(
    center.x + distance * 0.72,
    center.y + distance * 0.26,
    center.z - distance * 0.92
  );
  controls.maxDistance = maxSize * 2.4;
  controls.minDistance = maxSize * 0.24;
  controls.update();
  defaultView = { position: camera.position.clone(), target: center.clone() };
}

const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);
let loadToken = 0;

function clearCeilingGlow() {
  if (ceilingGlow) removeCeilingGlow({ ...ceilingGlow, root: model });
  ceilingGlow = null;
}

function disposeModel(root) {
  root.traverse((object) => {
    if (!object.isMesh) return;
    object.geometry?.dispose();
    const materials = Array.isArray(object.material) ? object.material : [object.material];
    materials.forEach((material) => material?.dispose());
  });
  scene.remove(root);
}

function updateModelMeta(config) {
  modelEyebrow.textContent = config.eyebrow;
  modelTitle.innerHTML = config.title;
  modelIntro.textContent = config.intro;
  metricHeight.textContent = config.metrics[0];
  metricStoreys.textContent = config.metrics[1];
  metricFootprint.textContent = config.metrics[2];
}

function renderModelList() {
  modelList.innerHTML = Object.entries(models).map(([id, config]) => (
    `<button class="model-button${id === activeModelId ? ' is-active' : ''}" data-model="${id}">
      <span>${config.label}</span><small>${config.meta}</small>
    </button>`
  )).join('');
  modelList.querySelectorAll('.model-button').forEach((button) => {
    button.addEventListener('click', () => loadModel(button.dataset.model));
  });
}

function loadModel(id) {
  const config = models[id];
  if (!config) return;
  activeModelId = id;
  updateModelMeta(config);
  renderModelList();
  clearCeilingGlow();
  if (model) {
    disposeModel(model);
    model = null;
  }
  modelBounds = null;
  defaultView = null;
  loadingCard.innerHTML = '<span class="spinner"></span><span>Preparing the building</span>';
  loadingCard.classList.remove('is-hidden');
  status.textContent = `Loading ${config.label}`;
  const token = ++loadToken;
  loader.load(
    config.asset,
    async (gltf) => {
      if (token !== loadToken) {
        disposeModel(gltf.scene);
        return;
      }
      model = gltf.scene;
      scene.add(model);
      frameModel(model);
      model.traverse((object) => {
        if (!object.isMesh) return;
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        const glassName = /glass/i.test(object.name)
          && !/frost/i.test(object.name);
        // Palettized dark vision glass on The Stack was merged into the
        // apartment frame mesh and lost the Glass name.
        const palettizedVision = object.name === 'Web_Stack_Apartment_Frame';
        for (const material of materials) {
          const namedGlass = /glass/i.test(material?.name ?? '')
            && !/frost/i.test(material?.name ?? '');
          if ((material?.transmission ?? 0) > 0.5) {
            // Grazing views turn physical glass into a mirror, which hides every
            // lit room from above. Keep it a thin tinted pane instead.
            material.transmission = 0;
            material.transparent = true;
            material.opacity = 0.08;
            material.depthWrite = false;
            material.metalness = 0;
            material.roughness = 0.08;
            material.metalnessMap = null;
            material.roughnessMap = null;
            material.envMapIntensity = 0.04;
            material.clearcoat = 0;
            material.specularIntensity = 0.04;
            material.needsUpdate = true;
          } else if (glassName || namedGlass || palettizedVision) {
            material.transparent = true;
            material.opacity = 0.35;
            material.depthWrite = false;
            material.needsUpdate = true;
          }
        }
      });
      if (ceilingGlowOn) {
        const started = performance.now();
        const glow = await addCeilingGlow(model);
        if (token !== loadToken) {
          removeCeilingGlow(glow);
          return;
        }
        if (glow) {
          ceilingGlow = glow;
          console.info(
            `Ceiling glow: ${glow.panels} fixtures, ${glow.floors} floors, ${Math.round(performance.now() - started)} ms`,
          );
        }
      }
      requestRender();
      status.textContent = 'Model ready';
      loadingCard.classList.add('is-hidden');
    },
    (progress) => {
      if (progress.total) {
        status.textContent = `${config.label} ${Math.round(progress.loaded / progress.total * 100)}%`;
      }
    },
    (error) => {
      if (token !== loadToken) return;
      console.error(`${config.label} failed to load`, error);
      status.textContent = 'Model unavailable';
      loadingCard.innerHTML = '<span>Could not load the GLB asset</span>';
    }
  );
}

viewButtons.forEach((button) => button.addEventListener('click', () => applyView(button.dataset.view)));
async function setCeilingGlow(enabled) {
  ceilingGlowOn = enabled;
  ceilingGlowButton.classList.toggle('is-active', ceilingGlowOn);
  ceilingGlowButton.querySelector('span').textContent = ceilingGlowOn ? 'on' : 'off';
  clearCeilingGlow();
  if (ceilingGlowOn && model) ceilingGlow = await addCeilingGlow(model);
  requestRender();
}

ceilingGlowButton.addEventListener('click', () => setCeilingGlow(!ceilingGlowOn));
resetButton.addEventListener('click', () => {
  if (defaultView) {
    camera.position.copy(defaultView.position);
    controls.target.copy(defaultView.target);
    controls.update();
    requestRender();
  } else {
    applyView('overview', true);
  }
});

const sunDial = document.querySelector('#sun-dial');
const sunHandle = document.querySelector('#sun-handle');
const sunTime = document.querySelector('#sun-time');
const sunPhase = document.querySelector('#sun-phase');
const sunTicks = document.querySelector('#sun-ticks');
const sunLabels = document.querySelector('#sun-labels');
const scratchColor = new THREE.Color();

function hourAngle(hour) {
  return ((hour - 12) / 24) * Math.PI * 2 - Math.PI / 2;
}

function padHour(hour) {
  const wrapped = ((hour % 24) + 24) % 24;
  const hours = Math.floor(wrapped);
  const minutes = Math.round((wrapped - hours) * 60);
  if (minutes === 60) return `${String((hours + 1) % 24).padStart(2, '0')}:00`;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

function sunPhaseName(hour) {
  if (hour >= 5 && hour < 7) return 'dawn';
  if (hour >= 7 && hour < 11) return 'morning';
  if (hour >= 11 && hour < 14) return 'noon';
  if (hour >= 14 && hour < 17) return 'afternoon';
  if (hour >= 17 && hour < 19.5) return 'dusk';
  return 'night';
}

function drawSunDial() {
  sunTicks.replaceChildren();
  sunLabels.replaceChildren();
  for (let hour = 0; hour < 24; hour += 1) {
    const angle = hourAngle(hour);
    const inner = hour % 6 === 0 ? 46 : 50;
    const tick = document.createElementNS('http://www.w3.org/2000/svg', 'line');
    tick.setAttribute('x1', String(SUN_CENTER + Math.cos(angle) * inner));
    tick.setAttribute('y1', String(SUN_CENTER + Math.sin(angle) * inner));
    tick.setAttribute('x2', String(SUN_CENTER + Math.cos(angle) * SUN_HANDLE_R));
    tick.setAttribute('y2', String(SUN_CENTER + Math.sin(angle) * SUN_HANDLE_R));
    tick.setAttribute('class', hour % 6 === 0 ? 'sun-tick is-major' : 'sun-tick');
    sunTicks.append(tick);
    if (hour % 6 !== 0) continue;
    const label = document.createElementNS('http://www.w3.org/2000/svg', 'text');
    label.setAttribute('class', 'sun-label');
    label.setAttribute('x', String(SUN_CENTER + Math.cos(angle) * 38));
    label.setAttribute('y', String(SUN_CENTER + Math.sin(angle) * 38));
    label.textContent = String(hour);
    sunLabels.append(label);
  }
}

function setSunHour(hour) {
  sunHour = ((hour % 24) + 24) % 24;
  const azimuth = (sunHour / 24) * Math.PI * 2;
  const elevation = Math.sin((sunHour - 6) / 12 * Math.PI) * (70 * Math.PI / 180);
  const cosEl = Math.cos(elevation);
  const x = SUN_DISTANCE * Math.sin(azimuth) * cosEl;
  const y = SUN_DISTANCE * Math.max(Math.sin(elevation), 0.04);
  const z = -SUN_DISTANCE * Math.cos(azimuth) * cosEl;
  keyLight.position.set(x, y, z);
  fillLight.position.set(-x * 0.7, Math.max(y * 0.35, 80), -z * 0.7);

  const above = Math.max(Math.sin(elevation), 0);
  const horizon = Math.max(0, 1 - Math.abs(elevation) / 0.35);
  const night = 1 - above;
  scratchColor.copy(SUN_COLOR_NOON).lerp(SUN_COLOR_HORIZON, horizon * above);
  scratchColor.lerp(SUN_COLOR_NIGHT, night);
  keyLight.color.copy(scratchColor);
  keyLight.intensity = 0.08 + above * 2.2 + horizon * above * 0.4;
  fillLight.color.copy(FILL_COLOR_DAY).lerp(FILL_COLOR_NIGHT, night);
  fillLight.intensity = 0.08 + above * 0.72;
  hemiLight.color.copy(HEMI_SKY_DAY).lerp(HEMI_SKY_NIGHT, night);
  hemiLight.groundColor.copy(HEMI_GROUND_DAY).lerp(HEMI_GROUND_NIGHT, night);
  hemiLight.intensity = 0.18 + above * 0.72;
  scene.background.copy(DAY_BACKGROUND).lerp(NIGHT_BACKGROUND, night);
  ground.material.color.copy(DAY_GROUND).lerp(NIGHT_GROUND, night);
  scene.environmentIntensity = 0.18 + above * 0.82;
  renderer.toneMappingExposure = 0.42 + above * 0.4;

  const angle = hourAngle(sunHour);
  sunHandle.setAttribute('cx', String(SUN_CENTER + Math.cos(angle) * SUN_HANDLE_R));
  sunHandle.setAttribute('cy', String(SUN_CENTER + Math.sin(angle) * SUN_HANDLE_R));
  sunTime.textContent = padHour(sunHour);
  sunPhase.textContent = sunPhaseName(sunHour);
  sunDial.setAttribute('aria-valuenow', sunHour.toFixed(2));
  sunDial.setAttribute('aria-valuetext', `${padHour(sunHour)} ${sunPhaseName(sunHour)}`);
  requestRender();
}

function hourFromPointer(event) {
  const bounds = sunDial.querySelector('svg').getBoundingClientRect();
  const dx = event.clientX - (bounds.left + bounds.width / 2);
  const dy = event.clientY - (bounds.top + bounds.height / 2);
  const svgAngle = Math.atan2(dy, dx);
  return (12 + (svgAngle + Math.PI / 2) / (Math.PI * 2) * 24 + 24) % 24;
}

function bindSunDial() {
  drawSunDial();
  let dragging = false;
  sunDial.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    event.stopPropagation();
    dragging = true;
    sunDial.classList.add('is-dragging');
    sunDial.setPointerCapture(event.pointerId);
    setSunHour(hourFromPointer(event));
  });
  sunDial.addEventListener('pointermove', (event) => {
    if (!dragging) return;
    event.preventDefault();
    setSunHour(hourFromPointer(event));
  });
  const stopDrag = (event) => {
    if (!dragging) return;
    dragging = false;
    sunDial.classList.remove('is-dragging');
    if (sunDial.hasPointerCapture(event.pointerId)) {
      sunDial.releasePointerCapture(event.pointerId);
    }
  };
  sunDial.addEventListener('pointerup', stopDrag);
  sunDial.addEventListener('pointercancel', stopDrag);
  sunDial.addEventListener('keydown', (event) => {
    const step = event.shiftKey ? 1 : 0.25;
    if (event.key === 'ArrowRight' || event.key === 'ArrowUp') {
      event.preventDefault();
      setSunHour(sunHour + step);
    } else if (event.key === 'ArrowLeft' || event.key === 'ArrowDown') {
      event.preventDefault();
      setSunHour(sunHour - step);
    } else if (event.key === 'Home') {
      event.preventDefault();
      setSunHour(12);
    } else if (event.key === 'End') {
      event.preventDefault();
      setSunHour(0);
    }
  });
  setSunHour(sunHour);
}

bindSunDial();
window.addEventListener('keydown', (event) => {
  if (event.key.toLowerCase() === 'r') resetButton.click();
  if (event.key === '1') applyView('overview');
  if (event.key === '2') applyView('garden');
  if (event.key === '3') applyView('base');
});

renderModelList();
updateModelMeta(models[activeModelId]);
loadModel(activeModelId);

function resize() {
  const width = viewer.clientWidth;
  const height = viewer.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
}
window.addEventListener('resize', () => {
  resize();
  requestRender();
});
resize();
requestRender();
