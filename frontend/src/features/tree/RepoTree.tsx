'use client';

// =============================================================================
// RepoTree — scroll-driven 3D repository tree
// Ink/white palette — no blue, no purple, no teal.
// Dark background is transparent so the parent card colour shows through.
// Node colours: white (crown) → light grey (branches) → mid grey (trunk) → near-white (root)
// =============================================================================

import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';

// ── Ink palette ───────────────────────────────────────────────────────────────
const COLOR = {
  0: '#ffffff', // root — pure white
  1: '#e0e0e0', // trunk/modules — light grey
  2: '#aaaaaa', // branches/files — mid grey
  3: '#ffffff', // crown/leaves — white
} as const;
type Lv = keyof typeof COLOR;

// Larger sizes so the tree fills the panel properly
const SIZE  = { 0: 0.42, 1: 0.28, 2: 0.18, 3: 0.12 } as const;
const GLOW  = { 0: 2.0,  1: 1.2,  2: 0.8,  3: 0.6  } as const;

// ── Node definitions ──────────────────────────────────────────────────────────
const NODES = [
  { id:'root',         label:'cortex/',            level:0, pos:[0,-4,0]           as [number,number,number], parent:null,      revealAt:0.85 },
  { id:'api',          label:'api/',               level:1, pos:[-3.5,-1.5,0.5]   as [number,number,number], parent:'root',    revealAt:0.62 },
  { id:'domain',       label:'domain/',            level:1, pos:[-1.2,-0.8,1.5]   as [number,number,number], parent:'root',    revealAt:0.66 },
  { id:'infra',        label:'infra/',             level:1, pos:[1.5,-1.2,-1]     as [number,number,number], parent:'root',    revealAt:0.70 },
  { id:'shared',       label:'shared/',            level:1, pos:[3.2,-1.5,0.5]    as [number,number,number], parent:'root',    revealAt:0.74 },
  { id:'router',       label:'router.py',          level:2, pos:[-5,1,0.8]        as [number,number,number], parent:'api',     revealAt:0.32 },
  { id:'models',       label:'models.py',          level:2, pos:[-3.8,1.2,-0.5]   as [number,number,number], parent:'api',     revealAt:0.36 },
  { id:'entities',     label:'entities.py',        level:2, pos:[-1.8,1.5,2]      as [number,number,number], parent:'domain',  revealAt:0.40 },
  { id:'interfaces',   label:'interfaces.py',      level:2, pos:[-0.5,1.8,1]      as [number,number,number], parent:'domain',  revealAt:0.43 },
  { id:'repository',   label:'repository.py',      level:2, pos:[2.5,1.2,-1.5]    as [number,number,number], parent:'infra',   revealAt:0.46 },
  { id:'exceptions',   label:'exceptions.py',      level:2, pos:[4.2,1,1]         as [number,number,number], parent:'shared',  revealAt:0.50 },
  { id:'logging',      label:'logging.py',         level:2, pos:[3.5,1.5,-0.5]    as [number,number,number], parent:'shared',  revealAt:0.53 },
  { id:'create_job',   label:'create_job()',       level:3, pos:[-5.8,3.2,1]      as [number,number,number], parent:'router',  revealAt:0.05 },
  { id:'list_jobs',    label:'list_jobs()',        level:3, pos:[-4.5,3.5,0.5]    as [number,number,number], parent:'router',  revealAt:0.08 },
  { id:'job_cls',      label:'Job',               level:3, pos:[-2.2,3.8,2.5]    as [number,number,number], parent:'entities',revealAt:0.10 },
  { id:'jobstatus',    label:'JobStatus',         level:3, pos:[-1,4,2]          as [number,number,number], parent:'entities',revealAt:0.12 },
  { id:'abstractrepo', label:'AbstractRepo',      level:3, pos:[-0.2,4.2,1.2]    as [number,number,number], parent:'interfaces',revealAt:0.14 },
  { id:'postgresrepo', label:'PostgresRepo',      level:3, pos:[3,3.8,-2]        as [number,number,number], parent:'repository',revealAt:0.16 },
  { id:'memoryrepo',   label:'InMemoryRepo',      level:3, pos:[2,4,-1.5]        as [number,number,number], parent:'repository',revealAt:0.18 },
  { id:'notfound',     label:'NotFoundError',     level:3, pos:[5,3.2,1.5]       as [number,number,number], parent:'exceptions',revealAt:0.20 },
  { id:'valerror',     label:'ValidationError',   level:3, pos:[4,3.5,0.8]       as [number,number,number], parent:'exceptions',revealAt:0.22 },
  { id:'configure',    label:'configure_logging()',level:3, pos:[4.2,3.8,-0.8]   as [number,number,number], parent:'logging', revealAt:0.24 },
];

const EDGES = [
  { from:'router',     to:'create_job',   revealAt:0.34 },
  { from:'router',     to:'list_jobs',    revealAt:0.35 },
  { from:'entities',   to:'job_cls',      revealAt:0.42 },
  { from:'entities',   to:'jobstatus',    revealAt:0.42 },
  { from:'interfaces', to:'abstractrepo', revealAt:0.45 },
  { from:'repository', to:'postgresrepo', revealAt:0.48 },
  { from:'repository', to:'memoryrepo',   revealAt:0.48 },
  { from:'exceptions', to:'notfound',     revealAt:0.52 },
  { from:'exceptions', to:'valerror',     revealAt:0.52 },
  { from:'logging',    to:'configure',    revealAt:0.55 },
  { from:'api',        to:'router',       revealAt:0.64 },
  { from:'api',        to:'models',       revealAt:0.64 },
  { from:'domain',     to:'entities',     revealAt:0.68 },
  { from:'domain',     to:'interfaces',   revealAt:0.68 },
  { from:'infra',      to:'repository',   revealAt:0.72 },
  { from:'shared',     to:'exceptions',   revealAt:0.76 },
  { from:'shared',     to:'logging',      revealAt:0.76 },
  { from:'root',       to:'api',          revealAt:0.87 },
  { from:'root',       to:'domain',       revealAt:0.88 },
  { from:'root',       to:'infra',        revealAt:0.89 },
  { from:'root',       to:'shared',       revealAt:0.90 },
];

// ── Growing edge ──────────────────────────────────────────────────────────────
function GrowingEdge({ fromPos, toPos, color, baseOpacity, revealAt, progress }: {
  fromPos: [number,number,number];
  toPos: [number,number,number];
  color: string;
  baseOpacity: number;
  revealAt: number;
  progress: React.MutableRefObject<number>;
}) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([...fromPos, ...fromPos], 3));
    return g;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const material = useMemo(
    () => new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0 }),
  // eslint-disable-next-line react-hooks/exhaustive-deps
  []);

  const lineObj = useMemo(() => new THREE.Line(geometry, material), [geometry, material]);

  useFrame(() => {
    const p = progress.current;
    if (p < revealAt) { material.opacity = 0; return; }
    const draw = Math.min((p - revealAt) / 0.06, 1);
    const pos = geometry.attributes.position as THREE.BufferAttribute;
    pos.setXYZ(1,
      fromPos[0] + (toPos[0] - fromPos[0]) * draw,
      fromPos[1] + (toPos[1] - fromPos[1]) * draw,
      fromPos[2] + (toPos[2] - fromPos[2]) * draw,
    );
    pos.needsUpdate = true;
    material.opacity = baseOpacity * Math.min(draw * 4, 1);
  });

  return <primitive object={lineObj} />;
}

// ── Node sphere ───────────────────────────────────────────────────────────────
function NodeSphere({ node, progress }: {
  node: (typeof NODES)[0];
  progress: React.MutableRefObject<number>;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef  = useRef<THREE.MeshStandardMaterial>(null);
  const s       = useRef(0);
  const color   = COLOR[node.level as Lv];
  const maxSize = SIZE[node.level as Lv];
  const maxGlow = GLOW[node.level as Lv];

  useFrame((state, dt) => {
    if (!meshRef.current || !matRef.current) return;
    const p   = progress.current;
    const vis = p >= node.revealAt;
    s.current += ((vis ? 1 : 0) - s.current) * Math.min(dt * 10, 1);

    if (node.level === 0 && vis) {
      const bp    = Math.min((p - node.revealAt) / 0.05, 1);
      const burst = 1 + Math.sin(bp * Math.PI) * 0.45;
      meshRef.current.scale.setScalar(s.current * burst);
    } else {
      meshRef.current.scale.setScalar(s.current);
    }

    const breath = 1 + Math.sin(state.clock.elapsedTime * 1.6 + node.pos[0] * 0.9) * 0.2;
    matRef.current.emissiveIntensity = vis ? maxGlow * breath * s.current : 0;
  });

  return (
    <mesh ref={meshRef} position={node.pos} scale={0}>
      <sphereGeometry args={[maxSize, 20, 20]} />
      <meshStandardMaterial
        ref={matRef}
        color={color}
        emissive={color}
        emissiveIntensity={0}
        roughness={0.15}
        metalness={0.1}
      />
    </mesh>
  );
}

// ── Sap particle ──────────────────────────────────────────────────────────────
function SapParticle({ fromPos, toPos, speed, offset, progress }: {
  fromPos: [number,number,number];
  toPos: [number,number,number];
  speed: number;
  offset: number;
  progress: React.MutableRefObject<number>;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef  = useRef<THREE.MeshBasicMaterial>(null);

  useFrame((state) => {
    if (!meshRef.current || !matRef.current) return;
    const p = progress.current;
    if (p < 0.90) { matRef.current.opacity = 0; return; }
    const intensity = Math.min((p - 0.90) / 0.10, 1);
    const t = (state.clock.elapsedTime * speed + offset) % 1;
    meshRef.current.position.set(
      fromPos[0] + (toPos[0] - fromPos[0]) * t,
      fromPos[1] + (toPos[1] - fromPos[1]) * t,
      fromPos[2] + (toPos[2] - fromPos[2]) * t,
    );
    matRef.current.opacity = Math.sin(t * Math.PI) * 0.7 * intensity;
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.04, 7, 7]} />
      <meshBasicMaterial ref={matRef} color="#ffffff" transparent opacity={0} />
    </mesh>
  );
}

// ── Camera ────────────────────────────────────────────────────────────────────
function ScrollCamera({ progress }: { progress: React.MutableRefObject<number> }) {
  const { camera } = useThree();
  useFrame(() => {
    const p   = progress.current;
    const cam = camera as THREE.PerspectiveCamera;
    const targetZ = 11 + p * 4;
    const targetY = 1.5 - p * 2.5;
    cam.position.z += (targetZ - cam.position.z) * 0.06;
    cam.position.y += (targetY - cam.position.y) * 0.06;
    cam.position.x  = 0;
    cam.lookAt(0, 0, 0);
  });
  return null;
}

// ── Root halo ─────────────────────────────────────────────────────────────────
function RootHalo({ progress }: { progress: React.MutableRefObject<number> }) {
  const matRef = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(() => {
    if (!matRef.current) return;
    const p = progress.current;
    matRef.current.opacity = p >= 0.85 ? Math.min((p - 0.85) / 0.08, 1) * 0.12 : 0;
  });
  return (
    <mesh position={[0, -4, 0]}>
      <sphereGeometry args={[1.6, 24, 24]} />
      <meshBasicMaterial ref={matRef} color="#ffffff" transparent opacity={0} side={THREE.BackSide} />
    </mesh>
  );
}

// ── Scene ─────────────────────────────────────────────────────────────────────
function TreeScene({ progress }: { progress: React.MutableRefObject<number> }) {
  const groupRef = useRef<THREE.Group>(null);
  const nodeMap  = useMemo(() => new Map(NODES.map((n) => [n.id, n])), []);

  useFrame((state) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y = Math.sin(state.clock.elapsedTime * 0.18) * 0.07;
  });

  const sapPaths = useMemo(() => {
    const root = NODES.find((n) => n.id === 'root')!;
    return NODES.filter((n) => n.level === 3).map((leaf, i) => ({
      from: root.pos, to: leaf.pos,
      speed: 0.20 + i * 0.015, offset: i * 0.18,
    }));
  }, []);

  return (
    <>
      {/* Neutral white lighting — no colour tinting */}
      <ambientLight intensity={1.2} />
      <directionalLight position={[0, 8, 10]}  intensity={1.8} color="#ffffff" />
      <pointLight      position={[0, 6, 6]}    intensity={2.5} color="#ffffff" />
      <pointLight      position={[0, -6, 5]}   intensity={2.0} color="#ffffff" distance={16} />

      <ScrollCamera progress={progress} />

      <group ref={groupRef}>
        {EDGES.map((edge) => {
          const fromNode = nodeMap.get(edge.from);
          const toNode   = nodeMap.get(edge.to);
          if (!fromNode || !toNode) return null;
          const color = COLOR[toNode.level as Lv];
          return (
            <GrowingEdge
              key={`${edge.from}-${edge.to}`}
              fromPos={fromNode.pos}
              toPos={toNode.pos}
              color={color}
              baseOpacity={toNode.level === 1 ? 0.7 : 0.4}
              revealAt={edge.revealAt}
              progress={progress}
            />
          );
        })}

        {NODES.map((node) => (
          <NodeSphere key={node.id} node={node} progress={progress} />
        ))}

        {/* Labels for root + module level only — larger font */}
        {NODES.filter((n) => n.level <= 1).map((node) => (
          <Text
            key={`lbl-${node.id}`}
            position={[node.pos[0], node.pos[1] + SIZE[node.level as Lv] + 0.35, node.pos[2]]}
            fontSize={node.level === 0 ? 0.32 : 0.22}
            color={COLOR[node.level as Lv]}
            anchorX="center"
            anchorY="bottom"
            fillOpacity={0.85}
          >
            {node.label}
          </Text>
        ))}

        {sapPaths.map((sp, i) => (
          <SapParticle
            key={`sap-${i}`}
            fromPos={sp.from}
            toPos={sp.to}
            speed={sp.speed}
            offset={sp.offset}
            progress={progress}
          />
        ))}

        <RootHalo progress={progress} />
      </group>
    </>
  );
}

// ── Export ────────────────────────────────────────────────────────────────────
export default function RepoTree({ progress }: { progress: React.MutableRefObject<number> }) {
  return (
    <div style={{ width: '100%', height: '100%', borderRadius: '16px', overflow: 'hidden' }}>
      <Canvas
        camera={{ position: [0, 0, 11], fov: 55 }}
        style={{ background: 'transparent' }}
        gl={{ antialias: true, alpha: true }}
        dpr={[1, 2]}
      >
        <TreeScene progress={progress} />
      </Canvas>
    </div>
  );
}
