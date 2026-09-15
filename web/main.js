import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { RectAreaLightUniformsLib } from 'three/addons/lights/RectAreaLightUniformsLib.js';

const viewer = document.querySelector('#viewer');
const status = document.querySelector('#load-status');
const loadingCard = document.querySelector('#loading-card');
const viewButtons = [...document.querySelectorAll('.view-button')];
const resetButton = document.querySelector('#reset-view');

const scene = new THREE.Scene();
scene.background = new THREE.Color('#8e9d93');

const camera = new THREE.PerspectiveCamera(34, 1, 0.5, 1200);
const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: false,
  logarithmicDepthBuffer: true,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 0.82;
viewer.appendChild(renderer.domElement);

// The Blender EEVEE glass uses a node mix that glTF cannot preserve. This
// neutral studio environment gives the reconstructed physical glass something
// real to reflect without adding haze to the camera view.
const pmrem = new THREE.PMREMGenerator(renderer);
const environment = new RoomEnvironment();
scene.environment = pmrem.fromScene(environment, 0.04).texture;
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
scene.environment = reflectionPmrem.fromEquirectangular(reflectionTexture).texture;
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

scene.add(new THREE.HemisphereLight('#f4f7ed', '#7e8d83', 0.9));
const keyLight = new THREE.DirectionalLight('#fff8e5', 2.2);
keyLight.position.set(160, 360, -180);
scene.add(keyLight);
const fillLight = new THREE.DirectionalLight('#c3d9e5', 0.8);
fillLight.position.set(-200, 170, 120);
scene.add(fillLight);

// Large softboxes create readable facade reflections. Point lights would only
// make small hotspots; broad rectangular sources produce the long highlights
// visible on real curtain-wall glass.
RectAreaLightUniformsLib.init();
function addFacadeSoftbox(color, intensity, width, height, position) {
  const light = new THREE.RectAreaLight(color, intensity, width, height);
  light.position.set(...position);
  light.lookAt(0, 145, 0);
  scene.add(light);
}
addFacadeSoftbox('#dff5ff', 9, 180, 420, [260, 230, -260]);
addFacadeSoftbox('#fff0d5', 6, 120, 320, [-220, 300, -80]);

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
let model;
let defaultView;

function webGlassMaterial(material) {
  const frosted = material.name.includes('Frost');
  const dark = material.name.includes('Dark');
  return new THREE.MeshPhysicalMaterial({
    name: material.name,
    color: new THREE.Color(
      frosted ? '#657e80' : dark ? '#182b31' : '#1f414b'
    ),
    roughness: frosted ? 0.16 : 0.028,
    metalness: 0,
    transmission: frosted ? 0.18 : 0.48,
    thickness: 0.12,
    ior: 1.52,
    reflectivity: 0.9,
    clearcoat: frosted ? 0.25 : 0.8,
    clearcoatRoughness: 0.015,
    specularIntensity: 1,
    transparent: true,
    opacity: frosted ? 0.48 : 0.58,
    depthWrite: false,
    side: THREE.DoubleSide,
    envMap: scene.environment,
    envMapIntensity: 2.2,
  });
}

function applyWebMaterials(object) {
  const materials = Array.isArray(object.material) ? object.material : [object.material];
  if (materials.length !== 1 || !materials[0]?.name.startsWith('Stack_Glass_')) return;
  object.material = webGlassMaterial(materials[0]);
}

function applyView(name, instant = false) {
  const view = views[name];
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

new GLTFLoader().load(
  './assets/the_stack.glb',
  (gltf) => {
    model = gltf.scene;
    model.traverse((object) => {
      if (!object.isMesh) return;
      applyWebMaterials(object);
      object.castShadow = true;
      object.receiveShadow = true;
      const materials = Array.isArray(object.material) ? object.material : [object.material];
      materials.forEach((material) => {
        if (material && !material.name.startsWith('Stack_Glass_')) material.envMapIntensity = 0.7;
      });
    });
    scene.add(model);
    frameModel(model);
    status.textContent = 'Model ready';
    loadingCard.classList.add('is-hidden');
  },
  (progress) => {
    if (progress.total) {
      status.textContent = `Loading ${Math.round(progress.loaded / progress.total * 100)}%`;
    }
  },
  (error) => {
    console.error('The Stack model failed to load', error);
    status.textContent = 'Model unavailable';
    loadingCard.innerHTML = '<span>Could not load the GLB asset</span>';
  }
);

viewButtons.forEach((button) => button.addEventListener('click', () => applyView(button.dataset.view)));
resetButton.addEventListener('click', () => {
  if (defaultView) {
    camera.position.copy(defaultView.position);
    controls.target.copy(defaultView.target);
    controls.update();
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

function resize() {
  const width = viewer.clientWidth;
  const height = viewer.clientHeight;
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height, false);
}
window.addEventListener('resize', resize);
resize();

function render() {
  requestAnimationFrame(render);
  controls.update();
  renderer.render(scene, camera);
}
render();
