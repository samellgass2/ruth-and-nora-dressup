# Ruth & Nora Dress-Up

## Stack
- React + TypeScript
- PixiJS (`pixi.js`) with `@pixi/react`
- Vite for local dev/build

## Quick Start
```bash
npm install
npm run dev
```

Build and preview:
```bash
npm run build
npm run preview
```

## Project Layout
- `src/main.tsx`: React entry point
- `src/App.tsx`: Page shell and character switch UI
- `src/components/SpriteActor.tsx`: Pixi stage + animated sprite renderer
- `public/sprites`: runtime sprite assets (`.png` + `.json`)

## Asset Format
Each character uses a repacked atlas pair:
- `*_sheet_repacked.png`
- `*_sheet_repacked.json`

Atlas JSON requirements:
- `frames` keyed by frame names (`ruth_00`, `nora_14`, etc.)
- each frame has `frame: { x, y, w, h }`
- optional `anchorHint` metadata for future dress-up alignment logic

Current frame counts:
- Ruth: `12` (`ruth_00` to `ruth_11`)
- Nora: `15` (`nora_00` to `nora_14`)

## Rendering Notes
### Pixel Crispness
`SpriteActor` sets nearest-neighbor scaling with a v7/v8-compatible fallback:
- Pixi v7 style: `PIXI.settings.SCALE_MODE = PIXI.SCALE_MODES.NEAREST`
- Pixi v8 style: `PIXI.TextureStyle.defaultOptions.scaleMode = "nearest"`

Stage options use:
- `antialias: false`
- `backgroundAlpha: 0`
- `autoDensity: true`

### Animation Timing
- `AnimatedSprite` is driven by `animationSpeed = fps / 60`
- default target: `10 fps` (idle-friendly)

## Dress-Up Pipeline Direction
- Keep base actor anchored bottom-center for consistent layering
- Add clothing/accessory layers as additional sprites sharing the same frame index
- Use `anchorHint` to refine alignment if source art needs per-frame offsets
