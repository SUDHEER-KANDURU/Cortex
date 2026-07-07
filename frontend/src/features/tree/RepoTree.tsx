'use client';

// =============================================================================
// RepoTree — Scroll-driven 3D repository tree
//
// Animation is 100% driven by a 0→1 scroll progress value written by GSAP
// ScrollTrigger (in page.tsx) into `progressRef`. Nothing triggers on mount —
// the user's scroll IS the timeline.
//
// Progress map:
//   0.00–0.08   root node grows in
//   0.08–0.30   level-1 branches extend (edges draw + nodes pop)
//   0.30–0.60   level-2 file nodes spawn
//   0.60–0.85   level-3 symbol nodes appear
//   0.00–1.00   camera pulls back continuously (z 8 → 15)
//   0.00–1.00   traveling particles flow along edges (always on)
// =============================================================================

import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';

// ── Node definitions ──────────────────────────────────────────────────────────

const NODES = [
  { id: 'root',         label: 'cortex/',             level: 0, pos: [0, 0, 0]           as [number,number,number], parent: null,   revealAt: 0.00 },
  { id: 'api',          label: 'api/',                 level: 1, pos: [-3.8, 2.2, 0.5]   as [number,number,number], parent: 'root', revealAt: 0.10 },
  { id: 'domain',       label: 'domain/',              level: 1, pos: [-1.0, 2.8, 1.8]   as [number,number,number], parent: 'root', revealAt: 0.16 },
  { id: 'infra',        label: 'infra/',               level: 1, pos: [1.8, 2.2, -1.2]   as [number,number,number], parent: 'root', revealAt: 0.22 },
  { id: 'shared',       label: 'shared/',              level: 1, pos: [3.6, 1.8, 0.8]    as [number,number,number], parent: 'root', revealAt: 0.28 },
  { id: 'router',       label: 'router.py',            level: 2, pos: [-5.4, 3.8, 0.8]   as [number,number,number], parent: 'api',    revealAt: 0.34 },
  { id: 'models',       label: 'models.py',            level: 2, pos: [-3.8, 4.2, -0.6]  as [number,number,number], parent: 'api',    revealAt: 0.38 },
  { id: 'entities',     label: 'entities.py',          level: 2, pos: [-2.0, 4.8, 2.4]   as [number,number,number], parent: 'domain', revealAt: 0.42 },
  { id: 'interfaces',   label: 'interfaces.py',        level: 2, pos: [-0.4, 4.6, 1.0]   as [number,number,number], parent: 'domain', revealAt: 0.46 },
  { id: 'repository',   label: 'repository.py',        level: 2, pos: [2.8, 4.0, -2.0]   as [number,number,number], parent: 'infra',  revealAt: 0.50 },
  { id: 'exceptions',   label: 'exceptions.py',        level: 2, pos: [4.8, 3.4, 1.2]    as [number,number,number], parent: 'shared', revealAt: 0.54 },
  { id: 'logging',      label: 'logging.py',           level: 2, pos: [4.0, 3.8, -0.4]   as [number,number,number], parent: 'shared', revealAt: 0.57 },
  { id: 'create_job',   label: 'create_job()',         level: 3, pos: [-6.4, 5.4, 1.2]   as [number,number,number], parent: 'router',     revealAt: 0.62 },
  { id: 'list_jobs',    label: 'list_jobs()',          level: 3, pos: [-5.0, 5.6, 0.4]   as [number,number,number], parent: 'router',     revealAt: 0.65 },
  { id: 'job_cls',      label: 'Job',                  level: 3, pos: [-2.6, 6.2, 3.0]   as [number,number,number], parent: 'entities',   revealAt: 0.67 },
  { id: 'jobstatus',    label: 'JobStatus',            level: 3, pos: [-1.0, 6.4, 2.6]   as [number,number,number], parent: 'entities',   revealAt: 0.69 },
  { id: 'abstractrepo', label: 'AbstractRepo',         level: 3, pos: [-0.2, 6.0, 1.4]   as [number,number,number], parent: 'interfaces', revealAt: 0.71 },
  { id: 'postgresrepo', label: 'PostgresRepo',         level: 3, pos: [3.6, 5.6, -2.6]   as [number,number,number], parent: 'repository', revealAt: 0.74 },
  { id: 'memoryrepo',   label: 'InMemoryRepo',         level: 3, pos: [2.2, 5.8, -2.4]   as [number,number,number], parent: 'repository', revealAt: 0.77 },
  { id: 'notfound',     label: 'NotFoundError',        level: 3, pos: [5.8, 5.0, 1.8]    as [number,number,number], parent: 'exceptions', revealAt: 0.80 },
  { id: 'valerror',     label: 'ValidationError',      level: 3, pos: [4.6, 5.2, 1.0]    as [number,number,number], parent: 'exceptions', revealAt: 0.82 },
  { id: 'configure',    label: 'configure_logging()',  level: 3, pos: [5.0, 5.6, -0.8]   as [number,number,number], parent: 'logging',    revealAt: 0.85 },
];

// ── Colour / size maps ────────────────────────────────────────────────────────

const COLOR = { 0: '#7C3AED', 1: '#22D3EE', 2: '#34D399', 3: '#94A3B8' } as const;
const SIZE  = { 0: 0.26, 1: 0.18, 2: 0.12, 3: 0.07 } as const;
const GLOW  = { 0: 5.0,  1: 3.0,  2: 1.6,  3: 0.6  } as const;

type Level = keyof typeof COLOR;

// ── Geometry for a single growing edge ───────────────────────────────────────

function GrowingEdge({
  from, to, color, lineWidth, baseOpacity, revealAt, progress,
}: {
  from: [number,number,number];
  to: [number,number,number];
  color: string;
  lineWidth: number;
  baseOpacity: number;
  revealAt: number;
  progress: React.MutableRefObject<number>;
}) {
  const lineRef = useRef<THREE.Line>(null);

  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    // Two identical points — tip moves in useFrame
    g.setAttribute('position', new THREE.Float32BufferAttribute([
      from[0], from[1], from[2],
      from[0], from[1], from[2],
    ], 3));
    return g;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const material = useMemo(
    () => new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0, linewidth: lineWidth }),
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  useFrame(() => {
    const p = progress.current;
    if (p < revealAt) {
      material.opacity = 0;
      return;
    }
    // How far along this edge we are: 0→1 over the next 0.08 of scroll
    const edgeP = Math.min((p - revealAt) / 0.08, 1);
    const tip: [number,number,number] = [
      from[0] + (to[0] - from[0]) * edgeP,
      from[1] + (to[1] - from[1]) * edgeP,
      from[2] + (to[2] - from[2]) * edgeP,
    ];
    const pos = geometry.attributes.position as THREE.BufferAttribute;
    pos.setXYZ(1, tip[0], tip[1], tip[2]);
    pos.needsUpdate = true;
    material.opacity = baseOpacity * Math.min(edgeP * 3, 1);
  });

  return <primitive object={new THREE.Line(geometry, material)} />;
}

// ── Traveling energy particle along an edge ───────────────────────────────────

function TravelParticle({
  from, to, color, speed, offset, progress, revealAt,
}: {
  from: [number,number,number];
  to: [number,number,number];
  color: string;
  speed: number;
  offset: number;
  progress: React.MutableRefObject<number>;
  revealAt: number;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef  = useRef<THREE.MeshBasicMaterial>(null);

  useFrame((state) => {
    if (!meshRef.current || !matRef.current) return;
    if (progress.current < revealAt) { matRef.current.opacity = 0; return; }
    const t = (state.clock.elapsedTime * speed + offset) % 1;
    meshRef.current.position.set(
      from[0] + (to[0] - from[0]) * t,
      from[1] + (to[1] - from[1]) * t,
      from[2] + (to[2] - from[2]) * t,
    );
    matRef.current.opacity = Math.sin(t * Math.PI) * 0.85;
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.038, 8, 8]} />
      <meshBasicMaterial ref={matRef} color={color} transparent opacity={0} />
    </mesh>
  );
}

// ── Single node sphere ────────────────────────────────────────────────────────

function NodeSphere({
  node,
  progress,
}: {
  node: (typeof NODES)[0];
  progress: React.MutableRefObject<number>;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef  = useRef<THREE.MeshStandardMaterial>(null);
  const scaleRef = useRef(0);
  const color = COLOR[node.level as Level];
  const targetSize = SIZE[node.level as Level];
  const glowMax = GLOW[node.level as Level];

  useFrame((state, dt) => {
    if (!meshRef.current || !matRef.current) return;
    const p = progress.current;
    const visible = p >= node.revealAt;
    // Spring toward target scale
    const targetScale = visible ? 1 : 0;
    scaleRef.current += (targetScale - scaleRef.current) * Math.min(dt * 9, 1);
    meshRef.current.scale.setScalar(scaleRef.current);
    // Breathing glow
    const breath = 1 + Math.sin(state.clock.elapsedTime * 1.5 + node.pos[0]) * 0.3;
    matRef.current.emissiveIntensity = visible ? glowMax * breath * scaleRef.current : 0;
  });

  return (
    <mesh ref={meshRef} position={node.pos} scale={0}>
      <sphereGeometry args={[targetSize, 20, 20]} />
      <meshStandardMaterial
        ref={matRef}
        color={color}
        emissive={color}
        emissiveIntensity={0}
        roughness={0.1}
        metalness={0.4}
      />
    </mesh>
  );
}

// ── Scroll-driven camera ──────────────────────────────────────────────────────

function ScrollCamera({ progress }: { progress: React.MutableRefObject<number> }) {
  const { camera } = useThree();
  useFrame(() => {
    const p = progress.current;
    // z: 8 at p=0  →  15 at p=1
    const targetZ = 8 + p * 7;
    const cam = camera as THREE.PerspectiveCamera;
    cam.position.z += (targetZ - cam.position.z) * 0.08;
    // Slightly tilt down as tree grows up
    cam.position.y = -0.5 + p * 2;
    cam.lookAt(0, 2, 0);
  });
  return null;
}

// ── Main scene ────────────────────────────────────────────────────────────────

function TreeScene({ progress }: { progress: React.MutableRefObject<number> }) {
  const groupRef = useRef<THREE.Group>(null);
  const nodeMap  = useMemo(() => new Map(NODES.map((n) => [n.id, n])), []);

  // Slow idle Y rotation (independent of scroll)
  useFrame((_, dt) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y += dt * 0.055;
  });

  return (
    <>
      <ambientLight intensity={0.12} />
      <pointLight position={[0, 6, 6]}   intensity={2.8} color="#7C3AED" />
      <pointLight position={[6, 2, -4]}  intensity={2.2} color="#22D3EE" />
      <pointLight position={[-6, 4, 4]}  intensity={1.8} color="#34D399" />
      <pointLight position={[0, -2, 0]}  intensity={1.2} color="#7C3AED" distance={12} />

      <ScrollCamera progress={progress} />

      <group ref={groupRef} position={[0, -1.5, 0]}>
        {/* Growing edges */}
        {NODES.map((node) => {
          const parent = node.parent ? nodeMap.get(node.parent) : null;
          if (!parent) return null;
          const color = COLOR[node.level as Level];
          return (
            <GrowingEdge
              key={`edge-${node.id}`}
              from={parent.pos}
              to={node.pos}
              color={color}
              lineWidth={node.level === 1 ? 1.4 : 0.8}
              baseOpacity={node.level === 3 ? 0.35 : 0.7}
              revealAt={node.revealAt - 0.01}
              progress={progress}
            />
          );
        })}

        {/* Energy particles */}
        {NODES.filter((n) => n.level <= 2).map((node, i) => {
          const parent = nodeMap.get(node.parent ?? '');
          if (!parent) return null;
          return (
            <TravelParticle
              key={`p-${node.id}`}
              from={parent.pos}
              to={node.pos}
              color={COLOR[node.level as Level]}
              speed={0.25 + i * 0.028}
              offset={i * 0.41}
              progress={progress}
              revealAt={node.revealAt + 0.04}
            />
          );
        })}

        {/* Node spheres */}
        {NODES.map((node) => (
          <NodeSphere key={node.id} node={node} progress={progress} />
        ))}

        {/* Labels — root + level-1 only */}
        {NODES.filter((n) => n.level <= 1).map((node) => {
          const color = COLOR[node.level as Level];
          const size  = SIZE[node.level as Level];
          return (
            <Text
              key={`lbl-${node.id}`}
              position={[node.pos[0], node.pos[1] + size + 0.3, node.pos[2]]}
              fontSize={node.level === 0 ? 0.24 : 0.17}
              color={color}
              anchorX="center"
              anchorY="bottom"
              fillOpacity={0.92}
            >
              {node.label}
            </Text>
          );
        })}
      </group>
    </>
  );
}

// ── Public component — receives shared progressRef from page ──────────────────

export default function RepoTree({ progress }: { progress: React.MutableRefObject<number> }) {
  return (
    <div style={{ width: '100%', height: '100%' }}>
      <Canvas
        camera={{ position: [0, -0.5, 8], fov: 52 }}
        style={{ background: 'transparent' }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <TreeScene progress={progress} />
      </Canvas>
    </div>
  );
}
