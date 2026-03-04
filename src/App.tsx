import { useEffect, useMemo, useState } from "react";
import { SpriteActor, type AccessoryLayer } from "./components/SpriteActor";

type Character = "Ruth" | "Nora" | "Black Terrier";
type SequenceMode = "idle" | "action";
type ItemSlot = "head" | "body";

type CharacterConfig = {
  atlasUrl: string;
  sheetUrl: string;
};

type AtlasWithSequences = {
  meta?: {
    sequences?: {
      idle?: string[];
      action?: string[];
    };
  };
};

type ItemPlacement = {
  x: number;
  y: number;
  scaleMultiplier: number;
  anchor?: [number, number];
  attachTo?: "head" | "body";
};

type EquipItem = {
  id: string;
  name: string;
  slot: ItemSlot;
  textureUrl: string;
  placements: Record<Character, ItemPlacement>;
};

const CHARACTER_CONFIG: Record<Character, CharacterConfig> = {
  Ruth: {
    atlasUrl: "/sprites/ruth_sheet_pixel128_c24_i.json",
    sheetUrl: "/sprites/ruth_sheet_pixel128_c24_i.png",
  },
  Nora: {
    atlasUrl: "/sprites/nora_sheet_pixel128_c24_i.json",
    sheetUrl: "/sprites/nora_sheet_pixel128_c24_i.png",
  },
  "Black Terrier": {
    atlasUrl: "/sprites/black_terrier_sheet_pixel128_c24_i.json",
    sheetUrl: "/sprites/black_terrier_sheet_pixel128_c24_i.png",
  },
};

const CHARACTER_ROTATION: Character[] = ["Ruth", "Nora", "Black Terrier"];

const INVENTORY_ITEMS: EquipItem[] = [
  {
    id: "baseball-cap-classic",
    name: "Baseball Cap",
    slot: "head",
    textureUrl: "/items/ball_cap.png",
    placements: {
      Ruth: { x: 0, y: -10, scaleMultiplier: 1.08, anchor: [0.5, 1], attachTo: "head" },
      Nora: { x: 0, y: -10, scaleMultiplier: 1.02, anchor: [0.5, 1], attachTo: "head" },
      "Black Terrier": { x: 0, y: -10, scaleMultiplier: 1.08, anchor: [0.5, 1], attachTo: "head" },
    },
  },
  {
    id: "witch-hat-midnight",
    name: "Witch Hat",
    slot: "head",
    textureUrl: "/items/witch_hat.png",
    placements: {
      Ruth: { x: -1, y: -8, scaleMultiplier: 1.08, anchor: [0.5, 1], attachTo: "head" },
      Nora: { x: 0, y: -8, scaleMultiplier: 1.05, anchor: [0.5, 1], attachTo: "head" },
      "Black Terrier": {
        x: 0,
        y: -6,
        scaleMultiplier: 1.12,
        anchor: [0.5, 1],
        attachTo: "head",
      },
    },
  },
  {
    id: "collar-ruby",
    name: "Ruby Collar",
    slot: "body",
    textureUrl: "/items/collar_ruby.png",
    placements: {
      Ruth: { x: 0, y: -6, scaleMultiplier: 1, anchor: [0.5, 0.35], attachTo: "body" },
      Nora: { x: 0, y: -6, scaleMultiplier: 1, anchor: [0.5, 0.35], attachTo: "body" },
      "Black Terrier": { x: 0, y: -10, scaleMultiplier: 1.05, anchor: [0.5, 0.35], attachTo: "body" },
    },
  },
  {
    id: "collar-sky",
    name: "Sky Collar",
    slot: "body",
    textureUrl: "/items/collar_sky.png",
    placements: {
      Ruth: { x: 0, y: -6, scaleMultiplier: 1, anchor: [0.5, 0.35], attachTo: "body" },
      Nora: { x: 0, y: -6, scaleMultiplier: 1, anchor: [0.5, 0.35], attachTo: "body" },
      "Black Terrier": { x: 0, y: -10, scaleMultiplier: 1.05, anchor: [0.5, 0.35], attachTo: "body" },
    },
  },
];

const ACTION_EVERY_IDLE_LOOPS = 5;

export default function App() {
  const [activeCharacter, setActiveCharacter] = useState<Character>("Black Terrier");
  const [sequenceMode, setSequenceMode] = useState<SequenceMode>("idle");
  const [viewportWidth, setViewportWidth] = useState<number>(window.innerWidth);
  const [idleLoops, setIdleLoops] = useState<number>(0);
  const [idleFrameKeys, setIdleFrameKeys] = useState<string[]>([]);
  const [actionFrameKeys, setActionFrameKeys] = useState<string[]>([]);
  const [equippedBySlot, setEquippedBySlot] = useState<Partial<Record<ItemSlot, string>>>({});

  const nextCharacter: Character = useMemo(() => {
    const activeIndex = CHARACTER_ROTATION.indexOf(activeCharacter);
    if (activeIndex === -1) {
      return CHARACTER_ROTATION[0];
    }
    return CHARACTER_ROTATION[(activeIndex + 1) % CHARACTER_ROTATION.length];
  }, [activeCharacter]);

  const characterConfig = useMemo(
    () => CHARACTER_CONFIG[activeCharacter],
    [activeCharacter],
  );

  const stageWidth = viewportWidth >= 980
    ? Math.max(360, Math.min(560, viewportWidth - 560))
    : Math.max(320, Math.min(820, viewportWidth - 96));
  const stageHeight = Math.max(260, Math.round(stageWidth * 0.62));
  const actorScale = stageWidth < 500 ? 1.5 : 1.8;

  const activeFrameKeys = sequenceMode === "idle" ? idleFrameKeys : actionFrameKeys;

  const equippedAccessories: AccessoryLayer[] = useMemo(() => {
    const itemById = new Map(INVENTORY_ITEMS.map((item) => [item.id, item]));

    return Object.values(equippedBySlot)
      .map((itemId) => (itemId ? itemById.get(itemId) : undefined))
      .filter((item): item is EquipItem => Boolean(item))
      .map((item) => {
        const placement = item.placements[activeCharacter];
        return {
          id: item.id,
          textureUrl: item.textureUrl,
          x: placement.x,
          y: placement.y,
          scaleMultiplier: placement.scaleMultiplier,
          anchor: placement.anchor,
          attachTo: placement.attachTo,
        };
      });
  }, [equippedBySlot, activeCharacter]);

  useEffect(() => {
    const onResize = () => {
      setViewportWidth(window.innerWidth);
    };
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    setIdleFrameKeys([]);
    setActionFrameKeys([]);
    setSequenceMode("idle");
    setIdleLoops(0);

    fetch(characterConfig.atlasUrl)
      .then((res) => {
        if (!res.ok) {
          throw new Error(`Failed to load sequence metadata: ${characterConfig.atlasUrl}`);
        }
        return res.json() as Promise<AtlasWithSequences>;
      })
      .then((atlas) => {
        if (cancelled) {
          return;
        }
        const idle = atlas.meta?.sequences?.idle ?? [];
        const action = atlas.meta?.sequences?.action ?? [];
        setIdleFrameKeys(idle);
        setActionFrameKeys(action);
      })
      .catch((error) => {
        console.error(error);
        if (!cancelled) {
          setIdleFrameKeys([]);
          setActionFrameKeys([]);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [characterConfig.atlasUrl]);

  return (
    <main className="page">
      <header className="hero">
        <p className="eyebrow">Dress Up Studio</p>
        <h1>Ruth &amp; Nora</h1>
        <p className="subtitle">
          Pixelized atlas animation with idle/action loops and static wearable overlays.
        </p>
      </header>

      <section className="studio-row" aria-label="Studio layout">
        <aside className="side-menu left" aria-label="Item shop">
          <details open>
            <summary>Shop</summary>
            <div className="side-menu-content">
              <p className="side-label">Catalog (assume owned for now)</p>
              {INVENTORY_ITEMS.map((item) => (
                <div key={`shop-${item.id}`} className="menu-item-row">
                  <span>{item.name}</span>
                  <span className="menu-tag">Owned</span>
                </div>
              ))}
            </div>
          </details>
        </aside>

        <section className="stage" aria-live="polite">
          <div className="sprite-frame">
            {activeFrameKeys.length > 0 ? (
              <SpriteActor
                key={`${activeCharacter}-${sequenceMode}`}
                atlasUrl={characterConfig.atlasUrl}
                sheetUrl={characterConfig.sheetUrl}
                frameKeys={activeFrameKeys}
                fps={sequenceMode === "idle" ? 3 : 6}
                scale={actorScale}
                width={stageWidth}
                height={stageHeight}
                accessories={equippedAccessories}
                loop={sequenceMode === "idle"}
                onLoop={() => {
                  if (sequenceMode !== "idle" || actionFrameKeys.length === 0) {
                    return;
                  }
                  setIdleLoops((count) => {
                    const next = count + 1;
                    if (next >= ACTION_EVERY_IDLE_LOOPS) {
                      setSequenceMode("action");
                      return 0;
                    }
                    return next;
                  });
                }}
                onComplete={() => {
                  if (sequenceMode === "action") {
                    setSequenceMode("idle");
                  }
                }}
              />
            ) : null}
          </div>

          <div className="stage-meta">
            <div className="label">Currently showing</div>
            <div id="current-name" className="name">
              {activeCharacter}
            </div>
            <div className="label">Mode: {sequenceMode}</div>
            <div className="label">Idle loops: {idleLoops}/{ACTION_EVERY_IDLE_LOOPS}</div>
          </div>
        </section>

        <aside className="side-menu right" aria-label="Inventory">
          <details open>
            <summary>Inventory</summary>
            <div className="side-menu-content">
              <p className="side-label">Owned Items</p>
              {INVENTORY_ITEMS.map((item) => {
                const isEquipped = equippedBySlot[item.slot] === item.id;
                return (
                  <button
                    key={item.id}
                    type="button"
                    className={`menu-action ${isEquipped ? "is-equipped" : ""}`}
                    onClick={() => {
                      setEquippedBySlot((current) => {
                        if (current[item.slot] === item.id) {
                          return { ...current, [item.slot]: undefined };
                        }
                        return { ...current, [item.slot]: item.id };
                      });
                    }}
                  >
                    {item.name} - {isEquipped ? "Unequip" : "Equip"}
                  </button>
                );
              })}
            </div>
          </details>
        </aside>
      </section>

      <section className="controls">
        <button
          id="switch"
          className="switch"
          type="button"
          onClick={() => {
            setActiveCharacter(nextCharacter);
            setSequenceMode("idle");
            setIdleLoops(0);
          }}
        >
          Switch to {nextCharacter}
        </button>
      </section>
    </main>
  );
}
