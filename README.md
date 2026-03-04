# ruth-and-nora-dressup
Dress-up prototype for Ruth and Nora using React + TypeScript + PixiJS. The app now includes a pixelized animation pipeline, automatic idle/action animation scheduling, and inventory-based item equip/unequip with rendered overlays.

## Current Stack
- React 18
- TypeScript 5
- Vite 7
- PixiJS 7 (`pixi.js`)
- `@pixi/react` for Pixi scene rendering in React
- Python + Pillow script for sprite/atlas preprocessing

## How To Run
Install dependencies:
```bash
npm install
```

Start local dev:
```bash
npm run dev
```

Build production bundle:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

Type-check only:
```bash
npm run typecheck
```

Regenerate pixelized atlases from source repacked sheets:
```bash
npm run generate:sprites
```

## What The App Does Today
- Loads Ruth and Nora sprite atlases generated for pixel style.
- Splits animation into separate `idle` and `action` sequences.
- Plays `action` automatically every 5 idle loops.
- Supports character switching.
- Includes side dropdown menus:
  - Left: Shop (catalog placeholder, currently all items treated as owned)
  - Right: Inventory (equip/unequip controls)
- Renders equipped items as static overlay textures anchored to body/head coordinates.

## Equip System (Current)
- Ownership assumption: all listed inventory items are owned.
- Slot model: items equip into fixed slots (`head`, `body`); one item per slot.
- First implemented item: `Classic Ball Cap` (`/public/items/ball_cap.png`).
- Per-character placement offsets are defined in app config and rendered by `SpriteActor` as accessory layers.
- Equip/unequip is immediate and visible on sprite.

## Animation + Sprite Pipeline
Source files:
- `src/sprites/ruth_sheet_repacked.png`
- `src/sprites/ruth_sheet_repacked.json`
- `src/sprites/nora_sheet_repacked.png`
- `src/sprites/nora_sheet_repacked.json`

Generation script:
- `scripts/generate_pixel_atlases.py`

Pipeline details:
- Frame extraction from source atlas JSON
- Target cell fit: `128x128` (bottom-centered)
- Pixel forcing pass: nearest-neighbor down/up
- Palette reduction: 24 colors
- Sequence split rules:
  - Ruth idle: first 3 source frames, action: remaining frames
  - Nora idle: first 6 source frames, action: remaining frames
- Interpolation pass inserts variable in-between frames based on frame disparity
- Generated output in `public/sprites` with sequence metadata in atlas `meta.sequences`

## Project Structure
- `index.html`: Vite entry HTML with root mount
- `src/main.tsx`: React bootstrap
- `src/App.tsx`: page layout, animation schedule logic, inventory/shop UI, equip state
- `src/components/SpriteActor.tsx`: Pixi Stage + AnimatedSprite + accessory overlay rendering
- `styles.css`: UI and layout styles
- `scripts/generate_pixel_atlases.py`: sprite processing pipeline
- `public/sprites`: generated runtime atlases (`*_pixel128_c24_i.*`)
- `public/items`: static item textures (first item: ball cap)
- `DESIGN.md`: rendering and system design notes

## Guidance For This Stack
Rendering and pixel quality:
- Keep `antialias: false` and nearest-neighbor texture handling.
- Use integer-friendly coordinates and `roundPixels` for pixel stability.
- Keep generated atlases in `public/` so they are fetchable at runtime.

State architecture:
- Keep animation mode, loop counting, and equip state in React state.
- Keep rendering concerns in `SpriteActor` and pass declarative props from `App`.
- Keep equip items config-driven (texture path + per-character offsets + slot).

Asset workflow:
- Treat source repacked sheets as editable inputs.
- Regenerate runtime atlases via `npm run generate:sprites` after source updates.
- Add new items under `public/items` and register config entries in `App`.

## Future Aspirations
Near-term:
- Add more wearable slots and items (shirts, collars, accessories, room props).
- Add precise per-frame attachment offsets (instead of static per-character offsets).
- Add item layer ordering (behind body, over body, over head).
- Build inventory data model beyond local UI state.

Economy/integration:
- Introduce actual ownership and point economy rules.
- Connect inventory to persisted user data (DB + auth).
- Integrate with habit-tracker point earning loop.

Animation/art quality:
- Improve interpolation method beyond blended in-betweens with silhouette-aware transitions.
- Add dedicated authored animation cycles for cleaner pixel readability.
- Expand environmental backdrops and room interaction layers.
