import { useEffect, useMemo, useState } from "react";
import { Stage, AnimatedSprite, Container, Sprite } from "@pixi/react";
import * as PIXI from "pixi.js";

type AnchorPoint = {
  x: number;
  y: number;
};

type AttachmentHints = {
  head: AnchorPoint;
  neck: AnchorPoint;
  body: AnchorPoint;
};

type AtlasJson = {
  frames: Record<
    string,
    {
      frame: { x: number; y: number; w: number; h: number };
      anchorHint?: { x: number; y: number };
      attachmentHints?: Partial<AttachmentHints>;
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

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function normalizedPointToLocal(point: AnchorPoint, width: number, height: number): AnchorPoint {
  return {
    x: Math.round(point.x - width * 0.5),
    y: Math.round(point.y - height),
  };
}

function deriveNeckHint(head: AnchorPoint, body: AnchorPoint): AnchorPoint {
  // Blend toward the torso to stabilize collars at the neckline across animations.
  return {
    x: Math.round(head.x + (body.x - head.x) * 0.35),
    y: Math.round(head.y + (body.y - head.y) * 0.58),
  };
}

function detectHintsFromTexture(texture: PIXI.Texture): AttachmentHints {
  const frameWidth = Math.max(1, Math.round(texture.frame.width));
  const frameHeight = Math.max(1, Math.round(texture.frame.height));

  const fallbackBody = { x: frameWidth / 2, y: frameHeight };
  const fallbackHead = { x: frameWidth / 2, y: frameHeight * 0.35 };

  const source = (texture.baseTexture.resource as { source?: CanvasImageSource }).source;
  if (!source || typeof document === "undefined") {
    return {
      head: fallbackHead,
      neck: deriveNeckHint(fallbackHead, fallbackBody),
      body: fallbackBody,
    };
  }

  const canvas = document.createElement("canvas");
  canvas.width = frameWidth;
  canvas.height = frameHeight;
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) {
    return {
      head: fallbackHead,
      neck: deriveNeckHint(fallbackHead, fallbackBody),
      body: fallbackBody,
    };
  }

  ctx.clearRect(0, 0, frameWidth, frameHeight);

  const sx = Math.round(texture.frame.x);
  const sy = Math.round(texture.frame.y);
  const sw = frameWidth;
  const sh = frameHeight;

  try {
    ctx.drawImage(source, sx, sy, sw, sh, 0, 0, frameWidth, frameHeight);
    const imageData = ctx.getImageData(0, 0, frameWidth, frameHeight);
    const data = imageData.data;

    const alphaThreshold = 14;
    let minX = frameWidth;
    let minY = frameHeight;
    let maxX = -1;
    let maxY = -1;

    for (let y = 0; y < frameHeight; y += 1) {
      for (let x = 0; x < frameWidth; x += 1) {
        const idx = (y * frameWidth + x) * 4 + 3;
        if (data[idx] > alphaThreshold) {
          if (x < minX) minX = x;
          if (y < minY) minY = y;
          if (x > maxX) maxX = x;
          if (y > maxY) maxY = y;
        }
      }
    }

    if (maxX < minX || maxY < minY) {
      return {
        head: fallbackHead,
        neck: deriveNeckHint(fallbackHead, fallbackBody),
        body: fallbackBody,
      };
    }

    const boundsHeight = maxY - minY + 1;
    const headLimit = clamp(minY + Math.round(boundsHeight * 0.44), minY, maxY);
    const shoulderLine = clamp(minY + Math.round(boundsHeight * 0.7), minY, maxY);

    let headCount = 0;
    let headXSum = 0;
    let headTop = maxY;

    let bodyCount = 0;
    let bodyXSum = 0;
    let bodyYSum = 0;

    for (let y = minY; y <= maxY; y += 1) {
      for (let x = minX; x <= maxX; x += 1) {
        const idx = (y * frameWidth + x) * 4 + 3;
        if (data[idx] <= alphaThreshold) {
          continue;
        }

        if (y <= headLimit) {
          headCount += 1;
          headXSum += x;
          if (y < headTop) {
            headTop = y;
          }
        }

        if (y >= shoulderLine) {
          bodyCount += 1;
          bodyXSum += x;
          bodyYSum += y;
        }
      }
    }

    const head = headCount > 0
      ? {
          x: clamp(Math.round(headXSum / headCount), minX, maxX),
          y: clamp(headTop + 1, minY, maxY),
        }
      : {
          x: Math.round((minX + maxX) / 2),
          y: clamp(minY + Math.round(boundsHeight * 0.24), minY, maxY),
        };

    const body = bodyCount > 0
      ? {
          x: clamp(Math.round(bodyXSum / bodyCount), minX, maxX),
          y: clamp(Math.round(bodyYSum / bodyCount), minY, maxY),
        }
      : {
          x: Math.round((minX + maxX) / 2),
          y: clamp(minY + Math.round(boundsHeight * 0.78), minY, maxY),
        };

    return { head, neck: deriveNeckHint(head, body), body };
  } catch (error) {
    console.warn("Failed to compute attachment hints from texture", error);
    return {
      head: fallbackHead,
      neck: deriveNeckHint(fallbackHead, fallbackBody),
      body: fallbackBody,
    };
  }
}

type SpriteActorProps = {
  atlasUrl: string;
  sheetUrl: string;
  frameKeys: string[];
  fps?: number;
  scale?: number;
  width?: number;
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
  tint?: number;
  attachTo?: keyof AttachmentHints;
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
  const [currentFrameIndex, setCurrentFrameIndex] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setNearestNeighbor();
    setAtlas(null);
    setCurrentFrameIndex(0);

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

  const attachmentHintsByFrame = useMemo(() => {
    if (!atlas || !textures) {
      return null;
    }

    const hints = new Map<string, AttachmentHints>();

    frameKeys.forEach((key, index) => {
      const frameDef = atlas.frames[key];
      const texture = textures[index];

      if (!frameDef || !texture) {
        return;
      }

      const frameWidth = frameDef.frame.w;
      const frameHeight = frameDef.frame.h;

      const fallbackBody = frameDef.anchorHint
        ? {
            x: frameDef.anchorHint.x - frameDef.frame.x,
            y: frameDef.anchorHint.y - frameDef.frame.y,
          }
        : {
            x: frameWidth / 2,
            y: frameHeight,
          };

      const detected = detectHintsFromTexture(texture);

      const bodyHint = frameDef.attachmentHints?.body ?? detected.body ?? fallbackBody;
      const headHint = frameDef.attachmentHints?.head ?? detected.head ?? {
        x: frameWidth / 2,
        y: frameHeight * 0.35,
      };
      const neckHint = frameDef.attachmentHints?.neck ?? detected.neck ?? deriveNeckHint(headHint, bodyHint);

      hints.set(key, {
        head: normalizedPointToLocal(headHint, frameWidth, frameHeight),
        neck: normalizedPointToLocal(neckHint, frameWidth, frameHeight),
        body: normalizedPointToLocal(bodyHint, frameWidth, frameHeight),
      });
    });

    return hints;
  }, [atlas, textures, frameKeys]);

  const activeFrameKey = useMemo(() => {
    if (frameKeys.length === 0) {
      return null;
    }
    const index = currentFrameIndex % frameKeys.length;
    return frameKeys[index] ?? null;
  }, [currentFrameIndex, frameKeys]);

  const activeFrameHints = useMemo(() => {
    if (!activeFrameKey || !attachmentHintsByFrame) {
      return null;
    }
    return attachmentHintsByFrame.get(activeFrameKey) ?? null;
  }, [activeFrameKey, attachmentHintsByFrame]);

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
          onFrameChange={(frame) => {
            setCurrentFrameIndex(frame);
          }}
          // anchor bottom-center (great for dress-up alignment later)
          anchor={[0.5, 1.0]}
          // scale up
          scale={scale}
          roundPixels={true}
        />
        {accessories.map((item) => {
          const hint = item.attachTo && activeFrameHints ? activeFrameHints[item.attachTo] : null;
          const x = Math.round((hint?.x ?? 0) + item.x);
          const y = Math.round((hint?.y ?? 0) + item.y);

          return (
            <Sprite
              key={item.id}
              image={item.textureUrl}
              x={x}
              y={y}
              anchor={item.anchor ?? [0.5, 1]}
              scale={scale * (item.scaleMultiplier ?? 1)}
              tint={item.tint}
              roundPixels={true}
            />
          );
        })}
      </Container>
    </Stage>
  );
}
