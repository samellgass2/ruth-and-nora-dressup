import { useEffect, useMemo, useState } from "react";
import { Stage, AnimatedSprite, Container, Sprite } from "@pixi/react";
import * as PIXI from "pixi.js";

type AtlasJson = {
  frames: Record<
    string,
    {
      frame: { x: number; y: number; w: number; h: number };
      anchorHint?: { x: number; y: number };
    }
  >;
  meta: {
    image: string;
    size: { w: number; h: number };
    cols?: number;
    rows?: number;
    cell?: { w: number; h: number };
  };
};

function setNearestNeighbor() {
  // Pixi v7 / older:
  // @ts-ignore
  if (PIXI.settings && PIXI.SCALE_MODES) {
    // @ts-ignore
    PIXI.settings.SCALE_MODE = PIXI.SCALE_MODES.NEAREST;
  }
  // Pixi v8:
  const pixiAny = PIXI as unknown as {
    TextureStyle?: { defaultOptions?: { scaleMode?: string } };
  };
  if (pixiAny.TextureStyle?.defaultOptions) {
    pixiAny.TextureStyle.defaultOptions.scaleMode = "nearest";
  }
}

async function loadAtlas(atlasUrl: string): Promise<AtlasJson> {
  const res = await fetch(atlasUrl);
  if (!res.ok) throw new Error(`Failed to load atlas: ${atlasUrl}`);
  return res.json();
}

function buildTexturesFromAtlas(sheetUrl: string, atlas: AtlasJson, frameKeys: string[]) {
  const base = PIXI.Texture.from(sheetUrl);

  return frameKeys.map((key) => {
    const f = atlas.frames[key]?.frame;
    if (!f) throw new Error(`Missing frame key: ${key}`);
    const rect = new PIXI.Rectangle(f.x, f.y, f.w, f.h);
    return new PIXI.Texture(base.baseTexture, rect);
  });
}

type SpriteActorProps = {
  atlasUrl: string;     // e.g. "/sprites/ruth_sheet_repacked.json"
  sheetUrl: string;     // e.g. "/sprites/ruth_sheet_repacked.png"
  frameKeys: string[];
  fps?: number;         // animation speed control
  scale?: number;       // render scale (integer preferred for pixel art)
  width?: number;       // stage size (optional if you embed inside a bigger stage)
  height?: number;
  loop?: boolean;
  onComplete?: () => void;
  onLoop?: () => void;
  accessories?: AccessoryLayer[];
};

export type AccessoryLayer = {
  id: string;
  textureUrl: string;
  x: number;
  y: number;
  scaleMultiplier?: number;
  anchor?: [number, number];
};

export function SpriteActor(props: SpriteActorProps) {
  const {
    atlasUrl,
    sheetUrl,
    frameKeys,
    fps = 6,
    scale = 1.1,
    width = 420,
    height = 300,
    loop = true,
    onComplete,
    onLoop,
    accessories = [],
  } = props;

  const [atlas, setAtlas] = useState<AtlasJson | null>(null);

  useEffect(() => {
    let cancelled = false;
    setNearestNeighbor();
    setAtlas(null);
    loadAtlas(atlasUrl)
      .then((data) => {
        if (!cancelled) {
          setAtlas(data);
        }
      })
      .catch((e) => {
        console.error(e);
        if (!cancelled) {
          setAtlas(null);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [atlasUrl]);

  const textures = useMemo(() => {
    if (!atlas || frameKeys.length === 0) return null;
    return buildTexturesFromAtlas(sheetUrl, atlas, frameKeys);
  }, [atlas, sheetUrl, frameKeys]);

  if (!textures) return null;

  // Pixi AnimatedSprite uses `animationSpeed` in "frames per tick" units.
  // A reasonable mapping: fps / 60.
  const animationSpeed = fps / 60;

  return (
    <Stage
      width={width}
      height={height}
      options={{
        backgroundAlpha: 0,
        antialias: false,
        autoDensity: true,
        resolution: window.devicePixelRatio || 1,
      }}
    >
      <Container x={Math.round(width / 2)} y={Math.round(height * 0.9)}>
        <AnimatedSprite
          textures={textures}
          isPlaying={true}
          initialFrame={0}
          animationSpeed={animationSpeed}
          loop={loop}
          onComplete={onComplete}
          onLoop={onLoop}
          // anchor bottom-center (great for dress-up alignment later)
          anchor={[0.5, 1.0]}
          // scale up
          scale={scale}
          roundPixels={true}
        />
        {accessories.map((item) => (
          <Sprite
            key={item.id}
            image={item.textureUrl}
            x={item.x}
            y={item.y}
            anchor={item.anchor ?? [0.5, 1]}
            scale={scale * (item.scaleMultiplier ?? 1)}
            roundPixels={true}
          />
        ))}
      </Container>
    </Stage>
  );
}
