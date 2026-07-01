'use client';

// =============================================================================
// SplitCube — 4-quadrant cube that splits apart revealing feature labels
// Driven by a 0→1 progress value from the parent scroll handler
// =============================================================================

import { useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { RoundedBox } from '@react-three/drei';
import * as THREE from 'three';

interface QuadrantProps {
  position: [number, number, number];
  targetOffset: [number, number, number];
  color: string;
  progress: React.MutableRefObject<number>;
}

function Quadrant({ position, targetOffset, color, progress }: QuadrantProps) {
  const ref = useRef<THREE.Mesh>(null);

  useFrame(() => {
    if (!ref.current) return;
    const p = progress.current;
    ref.current.position.x = position[0] + targetOffset[0] * p;
    ref.current.position.y = position[1] + targetOffset[1] * p;
    ref.current.position.z = position[2] + targetOffset[2] * p;
  });

  return (
    <RoundedBox ref={ref} args={[1.3, 1.3, 1.3]} radius={0.07} smoothness={4} position={position}>
      <meshStandardMaterial color={color} roughness={0.25} metalness={0.55} />
    </RoundedBox>
  );
}

interface SplitCubeSceneProps {
  progress: React.MutableRefObject<number>;
}

function SplitCubeScene({ progress }: SplitCubeSceneProps) {
  const groupRef = useRef<THREE.Group>(null);

  useFrame((_, delta) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y += delta * 0.12;
  });

  return (
    <group ref={groupRef}>
      {/* Top-left — Repository Scanner */}
      <Quadrant position={[-0.68, 0.68, 0]}  targetOffset={[-1.6, 1.6, 0.8]}  color="#5B4AE8" progress={progress} />
      {/* Top-right — Parser */}
      <Quadrant position={[0.68, 0.68, 0]}   targetOffset={[1.6,  1.6, 0.8]}  color="#6A59F0" progress={progress} />
      {/* Bottom-left — Knowledge Graph */}
      <Quadrant position={[-0.68, -0.68, 0]} targetOffset={[-1.6, -1.6, 0.8]} color="#4438C0" progress={progress} />
      {/* Bottom-right — Learning Engine */}
      <Quadrant position={[0.68, -0.68, 0]}  targetOffset={[1.6, -1.6, 0.8]}  color="#3D2FC7" progress={progress} />
    </group>
  );
}

export default function SplitCube({ progress }: { progress: React.MutableRefObject<number> }) {
  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 45 }}
      style={{ width: '100%', height: '100%' }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <ambientLight intensity={0.5} />
      <directionalLight position={[-4, 5, 4]} intensity={2} color="#9B7EFF" />
      <directionalLight position={[4, -3, -2]} intensity={0.8} color="#4460FF" />
      <pointLight position={[0, -3, 0]} intensity={1} color="#5B4AE8" distance={10} />
      <SplitCubeScene progress={progress} />
    </Canvas>
  );
}
