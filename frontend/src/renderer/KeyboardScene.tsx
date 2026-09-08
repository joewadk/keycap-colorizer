import { Edges, OrbitControls, RoundedBox } from "@react-three/drei";
import { Canvas, useFrame, type ThreeEvent } from "@react-three/fiber";
import { useRef } from "react";
import type { MeshBasicMaterial } from "three";

import type { KeyboardDefinition, KeyColorMap } from "../types/domain";
import { buildKeyTransform, KEYBOARD_UNIT_MM } from "./geometry";

function SelectionHighlight({ size }: { size: [number, number, number] }) {
  const material = useRef<MeshBasicMaterial>(null);
  useFrame(({ clock }) => {
    if (material.current) {
      // One synchronized pulse per second across the entire selection.
      material.current.opacity = 0.08 * (1 + Math.sin(clock.elapsedTime * Math.PI * 2));
    }
  });

  return (
    <RoundedBox args={size} radius={2.2} smoothness={3} scale={1.006} raycast={() => null}>
      <meshBasicMaterial
        ref={material}
        color="#F5DF8C"
        transparent
        opacity={0.08}
        depthWrite={false}
        toneMapped={false}
      />
    </RoundedBox>
  );
}

interface KeyboardSceneProps {
  keyboard: KeyboardDefinition;
  selectedKeyIds: string[];
  keyColorMap: KeyColorMap;
  colors: Record<string, string>;
  onKeyClick: (keyId: string, additive: boolean) => void;
  onKeyHover?: (keyId: string | null) => void;
}

export function KeyboardScene({
  keyboard,
  selectedKeyIds,
  keyColorMap,
  colors,
  onKeyClick,
  onKeyHover,
}: KeyboardSceneProps) {
  const width = Math.max(...keyboard.keys.map((key) => key.x + key.widthU)) * KEYBOARD_UNIT_MM;
  const depth = Math.max(...keyboard.keys.map((key) => key.y + key.heightU)) * KEYBOARD_UNIT_MM;
  const selected = new Set(selectedKeyIds);

  return (
    <div className="keyboard-canvas" aria-label="Interactive 3D keyboard preview">
      <Canvas
        shadows
        camera={{ position: [width * 0.55, width * 0.6, depth * 1.9], fov: 34 }}
        gl={{ antialias: true }}
      >
        <color attach="background" args={["#111615"]} />
        <ambientLight intensity={1.2} />
        <directionalLight castShadow position={[80, 160, 80]} intensity={2.4} />
        <group position={[-width / 2, 0, -depth / 2]}>
          <RoundedBox
            args={[width + 12, 7, depth + 12]}
            radius={6}
            smoothness={4}
            position={[width / 2, -3.5, depth / 2]}
            receiveShadow
          >
            <meshStandardMaterial color={keyboard.case.color} roughness={0.42} metalness={0.2} />
          </RoundedBox>
          {keyboard.keys.map((key) => {
            const transform = buildKeyTransform(key);
            const isSelected = selected.has(key.id);
            const color = colors[keyColorMap[key.id]] ?? "#D8DBD1";
            return (
              <RoundedBox
                key={key.id}
                args={transform.size}
                position={transform.position}
                radius={2.2}
                smoothness={3}
                castShadow
                receiveShadow
                scale={isSelected ? [1, 1.16, 1] : [1, 1, 1]}
                onClick={(event: ThreeEvent<MouseEvent>) => {
                  event.stopPropagation();
                  onKeyClick(key.id, event.nativeEvent.shiftKey);
                }}
                onPointerEnter={() => onKeyHover?.(key.id)}
                onPointerLeave={() => onKeyHover?.(null)}
              >
                {/* Keep palette colors independent of lighting and selection. */}
                <meshBasicMaterial color={color} toneMapped={false} />
                <Edges
                  threshold={15}
                  color={isSelected ? "#F5DF8C" : "#65706A"}
                  lineWidth={isSelected ? 1.5 : 0.5}
                  transparent
                  opacity={isSelected ? 0.55 : 1}
                  toneMapped={false}
                />
                {isSelected && <SelectionHighlight size={transform.size} />}
              </RoundedBox>
            );
          })}
        </group>
        <OrbitControls
          makeDefault
          target={[0, 0, 0]}
          minDistance={180}
          maxDistance={620}
          minPolarAngle={0.25}
          maxPolarAngle={Math.PI / 2.05}
        />
      </Canvas>
    </div>
  );
}
