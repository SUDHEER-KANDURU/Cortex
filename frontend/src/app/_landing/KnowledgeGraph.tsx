'use client';

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Sphere, Stars } from '@react-three/drei';
import * as THREE from 'three';

// Reduced node count from 150 → 60 for performance.
// The graph still reads as dense visually but GPU load is ~60% lower.
const NODE_COUNT = 60;

function Node({ position, color, size = 0.05 }: { position: [number, number, number]; color: string; size?: number }) {
  const meshRef = useRef<THREE.Mesh>(null);

  useFrame((state) => {
    if (meshRef.current) {
      meshRef.current.position.y += Math.sin(state.clock.elapsedTime + position[0]) * 0.001;
    }
  });

  return (
    <Sphere ref={meshRef} args={[size, 8, 8]} position={position}>
      <meshStandardMaterial color={color} emissive={color} emissiveIntensity={2} />
    </Sphere>
  );
}

function Connections({ nodes }: { nodes: [number, number, number][] }) {
  const lineGeometry = useMemo(() => {
    const geometry = new THREE.BufferGeometry();
    const points: number[] = [];

    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const dist = new THREE.Vector3(...nodes[i]).distanceTo(new THREE.Vector3(...nodes[j]));
        if (dist < 1.5) {
          points.push(...nodes[i], ...nodes[j]);
        }
      }
    }

    geometry.setAttribute('position', new THREE.Float32BufferAttribute(points, 3));
    return geometry;
  }, [nodes]);

  return (
    <lineSegments geometry={lineGeometry}>
      <lineBasicMaterial color="#00D4FF" transparent opacity={0.1} />
    </lineSegments>
  );
}

function GraphScene() {
  const nodes = useMemo<[number, number, number][]>(
    () =>
      Array.from({ length: NODE_COUNT }, () => [
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 10,
        (Math.random() - 0.5) * 10,
      ] as [number, number, number]),
    [],
  );

  const groupRef = useRef<THREE.Group>(null);

  useFrame((state) => {
    if (groupRef.current) {
      groupRef.current.rotation.y = state.clock.elapsedTime * 0.05;
      groupRef.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.1) * 0.1;
    }
  });

  return (
    <group ref={groupRef}>
      {/* Reduced star count from 5000 → 1000 — still looks great, much cheaper */}
      <Stars radius={100} depth={50} count={1000} factor={4} saturation={0} fade speed={1} />
      {nodes.map((pos, i) => (
        <Node
          key={i}
          position={pos}
          color={i % 5 === 0 ? '#6B57E8' : '#00D4FF'}
          size={i % 10 === 0 ? 0.08 : 0.03}
        />
      ))}
      <Connections nodes={nodes} />

      <ambientLight intensity={0.5} />
      <pointLight position={[10, 10, 10]} intensity={1} color="#6B57E8" />
    </group>
  );
}

export default function KnowledgeGraph() {
  return (
    <div className="w-full h-full min-h-[600px] bg-onyx/20 rounded-3xl overflow-hidden border border-white/5 relative group">
      <div className="absolute inset-0 z-0 opacity-20 pointer-events-none bg-[radial-gradient(circle_at_center,_var(--electric-blue)_0%,_transparent_70%)]" />
      {/* dpr capped at 1.5 — full 2x on retina is unnecessary for a decorative scene */}
      <Canvas
        camera={{ position: [0, 0, 8], fov: 45 }}
        dpr={[1, 1.5]}
        onCreated={({ gl }) => {
          // Allow the browser to restore the WebGL context after GPU eviction
          gl.domElement.addEventListener('webglcontextlost', (e) => {
            e.preventDefault();
          }, false);
        }}
      >
        <GraphScene />
      </Canvas>
      <div className="absolute bottom-8 left-8 z-10 p-6 backdrop-blur-md border border-white/5 rounded-xl max-w-xs">
        <h4 className="font-mono text-electric-blue text-[10px] uppercase tracking-widest mb-2 font-bold">
          Neural Topology
        </h4>
        <p className="text-white/60 text-xs leading-relaxed font-light">
          Cortex maps code symbols into a multi-dimensional graph, enabling structural reasoning that
          understands the &quot;why&quot; behind every line.
        </p>
      </div>
    </div>
  );
}
