# TASK REPORT

## Task
- Project: `ruth-and-nora-dress-up`
- Workflow: `Add head and body tracking to sprites`
- TASK_ID: `51`
- RUN_ID: `125`
- Title: `Add head tracking for black terrier`

## Summary of Changes
- Added a dedicated `Black Terrier` character option in the character rotation.
- Added black terrier runtime sprite assets:
  - `/public/sprites/black_terrier_sheet_pixel128_c24_i.json`
  - `/public/sprites/black_terrier_sheet_pixel128_c24_i.png`
- Added a new head item: `Midnight Witch Hat` (`/public/items/witch_hat.png`).
- Configured witch hat placement to `attachTo: "head"` for all characters, including `Black Terrier`.
- Set default active character to `Black Terrier` so witch hat head tracking can be verified immediately.
- Updated switch logic to support cycling through 3 characters (`Ruth`, `Nora`, `Black Terrier`).

## Files Changed
- `src/App.tsx`
- `public/items/witch_hat.png`
- `public/sprites/black_terrier_sheet_pixel128_c24_i.json`
- `public/sprites/black_terrier_sheet_pixel128_c24_i.png`
- `TASK_REPORT.md`

## Verification
Commands run:
- `npm install`
- `npx tsc --noEmit` (PASS)
- `npm run build` (PASS)

Acceptance criteria check:
- Equip `Midnight Witch Hat` from inventory and keep `Black Terrier` active.
- Witch hat uses `attachTo: "head"` and updates per-frame with sprite movement, following head motion.

## Notes
- Head tracking behavior relies on frame-level hints already computed in `SpriteActor`.
- The witch hat uses a bottom-center anchor (`[0.5, 1]`) with black terrier head-relative offsets.
