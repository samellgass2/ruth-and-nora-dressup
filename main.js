const sprite = document.getElementById("sprite");
const currentName = document.getElementById("current-name");
const switchButton = document.getElementById("switch");

const SPRITE_CONFIG = {
  Ruth: {
    sheet: "src/sprites/ruth-dressup-spritesheet.png",
    columns: 6,
    rows: 4,
  },
  Nora: {
    sheet: "src/sprites/nora-dress-up-spritesheet.png",
    columns: 6,
    rows: 4,
  },
};

const FRAME_WIDTH = 256;
const FRAME_HEIGHT = 256;
const FRAME_DURATION = 120;

let activeName = "Ruth";
let frameIndex = 0;
let animationId = null;
let lastFrameTime = 0;
const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
let prefersReducedMotion = motionQuery.matches;

function applySprite(name) {
  const config = SPRITE_CONFIG[name];
  const totalFrames = config.columns * config.rows;

  sprite.style.backgroundImage = `url(${config.sheet})`;
  sprite.style.backgroundSize = `${FRAME_WIDTH * config.columns}px ${
    FRAME_HEIGHT * config.rows
  }px`;

  frameIndex = 0;
  renderFrame(frameIndex, config);
  currentName.textContent = name;
  sprite.setAttribute("aria-label", `${name} sprite`);
  switchButton.textContent = `Switch to ${name === "Ruth" ? "Nora" : "Ruth"}`;
}

function renderFrame(frame, config) {
  const column = frame % config.columns;
  const row = Math.floor(frame / config.columns);

  const x = -(column * FRAME_WIDTH);
  const y = -(row * FRAME_HEIGHT);

  sprite.style.backgroundPosition = `${x}px ${y}px`;
}

function advanceFrame(totalFrames) {
  const config = SPRITE_CONFIG[activeName];
  renderFrame(frameIndex, config);
  frameIndex = (frameIndex + 1) % totalFrames;
}

function startAnimation() {
  stopAnimation();
  if (prefersReducedMotion) {
    return;
  }

  const totalFrames =
    SPRITE_CONFIG[activeName].columns * SPRITE_CONFIG[activeName].rows;

  const tick = (timestamp) => {
    if (!lastFrameTime) {
      lastFrameTime = timestamp;
    }
    const elapsed = timestamp - lastFrameTime;
    if (elapsed >= FRAME_DURATION) {
      const steps = Math.floor(elapsed / FRAME_DURATION);
      for (let i = 0; i < steps; i += 1) {
        advanceFrame(totalFrames);
      }
      lastFrameTime += steps * FRAME_DURATION;
    }
    animationId = window.requestAnimationFrame(tick);
  };

  animationId = window.requestAnimationFrame(tick);
}

function stopAnimation() {
  if (animationId) {
    window.cancelAnimationFrame(animationId);
    animationId = null;
  }
  lastFrameTime = 0;
}

switchButton.addEventListener("click", () => {
  activeName = activeName === "Ruth" ? "Nora" : "Ruth";
  applySprite(activeName);
  startAnimation();
});

applySprite(activeName);
startAnimation();

motionQuery.addEventListener("change", (event) => {
  prefersReducedMotion = event.matches;
  applySprite(activeName);
  startAnimation();
});
