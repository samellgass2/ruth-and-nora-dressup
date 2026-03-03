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
let timerId = null;

function applySprite(name) {
  const config = SPRITE_CONFIG[name];
  const totalFrames = config.columns * config.rows;

  sprite.style.backgroundImage = `url(${config.sheet})`;
  sprite.style.backgroundSize = `${FRAME_WIDTH * config.columns}px ${
    FRAME_HEIGHT * config.rows
  }px`;

  frameIndex = 0;
  updateFrame(totalFrames);
  currentName.textContent = name;
  sprite.setAttribute("aria-label", `${name} sprite`);
  switchButton.textContent = `Switch to ${name === "Ruth" ? "Nora" : "Ruth"}`;
}

function updateFrame(totalFrames) {
  const column = frameIndex % SPRITE_CONFIG[activeName].columns;
  const row = Math.floor(frameIndex / SPRITE_CONFIG[activeName].columns);

  const x = -(column * FRAME_WIDTH);
  const y = -(row * FRAME_HEIGHT);

  sprite.style.backgroundPosition = `${x}px ${y}px`;

  frameIndex = (frameIndex + 1) % totalFrames;
}

function startAnimation() {
  if (timerId) {
    clearInterval(timerId);
  }

  const totalFrames =
    SPRITE_CONFIG[activeName].columns * SPRITE_CONFIG[activeName].rows;

  timerId = setInterval(() => {
    updateFrame(totalFrames);
  }, FRAME_DURATION);
}

switchButton.addEventListener("click", () => {
  activeName = activeName === "Ruth" ? "Nora" : "Ruth";
  applySprite(activeName);
  startAnimation();
});

applySprite(activeName);
startAnimation();
