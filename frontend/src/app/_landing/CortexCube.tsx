'use client';

// =============================================================================
// CortexCube — Solid 3D cube rendered with React Three Fiber
// Subtle mouse parallax + slow idle rotation. No glass, no transparency clutter.
// =============================================================================

import { useRef, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { RoundedBox } from '@react-three/drei';
import * as THREE from 'three';

// ── Materials ─────────────────────────────────────────────────────────────────

const FACE_COLORS = [
  '#5B4AE8', // right  — deep violet
  '#3D2FC7', // left   — darker violet
  '#6A59F0', // top    — lighter violet
  '#2A1FA0', // bottom — darkest
  '#5048D4', // front  — mid violet
  '#4438C0', // back   — mid-dark
];

// ── Inner cube mesh ───────────────────────────────────────────────────────────

function CubeMesh({ mouseX, mouseY }: { mouseX: React.MutableRefObject<number>; mouseY: React.MutableRefObject<number> }) {
  const groupRef = useRef<THREE.Group>(null);
  const baseRotation = useRef({ x: 0.4, y: 0.6 });
  const targetRotation = useRef({ x: 0.4, y: 0.6 });

  useFrame((_, delta) => {
    if (!groupRef.current) return;

    // Slow idle drift
    baseRotation.current.y += delta * 0.18;
    baseRotation.current.x += delta * 0.06;

    // Mouse parallax — gentle tilt
    targetRotation.current.x = baseRotation.current.x + mouseY.current * 0.3;
    targetRotation.current.y = baseRotation.current.y + mouseX.current * 0.3;

    // Smooth interpolation
    groupRef.current.rotation.x += (targetRotation.current.x - groupRef.current.rotation.x) * 0.05;
    groupRef.current.rotation.y += (targetRotation.current.y - groupRef.current.rotation.y) * 0.05;
  });

  // Per-face materials
  const materials = FACE_COLORS.map(
    (color) =>
      new THREE.MeshStandardMaterial({
        color,
        roughness: 0.25,
        metalness: 0.6,
      })
  );

  return (
    <group ref={groupRef}>
      <RoundedBox args={[2.8, 2.8, 2.8]} radius={0.12} smoothness={4} material={materials} castShadow />
      {/* Subtle inner edge highlight */}
      <RoundedBox args={[2.85, 2.85, 2.85]} radius={0.14} smoothness={4}>
        <meshBasicMaterial color="#7B61FF" transparent opacity={0.04} side={THREE.BackSide} />
      </RoundedBox>
    </group>
  );
}

// ── Scene lighting ─────────────────────────────────────────────────────────────

function SceneLights() {
  return (
    <>
      <ambientLight intensity={0.4} />
      {/* Key light — top left, warm-ish violet */}
      <directionalLight position={[-4, 5, 4]} intensity={2.2} color="#9B7EFF" />
      {/* Fill light — bottom right, cooler */}
      <directionalLight position={[4, -3, -2]} intensity={0.8} color="#4460FF" />
      {/* Rim — pure white edge catch */}
      <directionalLight position={[0, 0, 6]} intensity={0.6} color="#ffffff" />
      {/* Under glow */}
      <pointLight position={[0, -3, 0]} intensity={1.2} color="#5B4AE8" distance={8} />
    </>
  );
}

// ── Canvas wrapper ─────────────────────────────────────────────────────────────

export default function CortexCube() {
  const mouseX = useRef(0);
  const mouseY = useRef(0);

  useEffect(() => {
    const handleMouse = (e: MouseEvent) => {
      mouseX.current = (e.clientX / window.innerWidth - 0.5) * 2;
      mouseY.current = -(e.clientY / window.innerHeight - 0.5) * 2;
    };
    window.addEventListener('mousemove', handleMouse, { passive: true });
    return () => window.removeEventListener('mousemove', handleMouse);
  }, []);

  return (
    <Canvas
      camera={{ position: [0, 0, 6], fov: 45 }}
      style={{ width: '100%', height: '100%' }}
      gl={{ antialias: true, alpha: true }}
      dpr={[1, 2]}
    >
      <SceneLights />
      <CubeMesh mouseX={mouseX} mouseY={mouseY} />
    </Canvas>
  );
}
