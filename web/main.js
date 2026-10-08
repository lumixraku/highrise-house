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

scene.add(new THREE.HemisphereLight('#f4f7ed', '#7e8d83', 0.9));
const keyLight = new THREE.DirectionalLight('#fff8e5', 2.2);
keyLight.position.set(160, 360, -180);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight('#c3d9e5', 0.8);
fillLight.position.set(-200, 170, 120);
scene.add(fillLight);

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
        for (const material of materials) {
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
