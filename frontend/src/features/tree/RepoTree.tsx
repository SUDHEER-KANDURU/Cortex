'use client';

// =============================================================================
// RepoTree — Crown → Trunk → Roots scroll-driven 3D tree
//
// Story: Leaves appear first (phase 1), branches grow down (phase 2),
//        trunk solidifies (phase 3), roots burst out (phase 4),
//        sap particles flow upward (phase 5).
//
// ALL animation driven by progressRef (0→1 from GSAP ScrollTrigger).
// Zero React state inside the scene — only refs + useFrame mutations.
// =============================================================================

import { useRef, useMemo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { Text } from '@react-three/drei';
import * as THREE from 'three';

// ── Design tokens ─────────────────────────────────────────────────────────────

const COLOR = {
  0: '#7C3AED', // root — deep violet
  1: '#A78BFA', // trunk/modules — light violet
  2: '#22D3EE', // branches/files — cyan
  3: '#34D399', // crown/leaves — green
} as const;
type Lv = keyof typeof COLOR;

const SIZE  = { 0: 0.30, 1: 0.20, 2: 0.13, 3: 0.08 } as const;
const GLOW  = { 0: 5.0,  1: 2.8,  2: 1.8,  3: 1.0  } as const;

// ── Node definitions — CROWN at top, ROOT at bottom ───────────────────────────

const NODES = [
  // ROOT — appears last with burst
  { id:'root',         label:'cortex/',           level:0, pos:[0,-4,0]           as [number,number,number], parent:null,           revealAt:0.85 },
  // TRUNK — module nodes
  { id:'api',          label:'api/',               level:1, pos:[-3.5,-1.5,0.5]   as [number,number,number], parent:'root',         revealAt:0.62 },
  { id:'domain',       label:'domain/',            level:1, pos:[-1.2,-0.8,1.5]   as [number,number,number], parent:'root',         revealAt:0.66 },
  { id:'infra',        label:'infra/',             level:1, pos:[1.5,-1.2,-1]     as [number,number,number], parent:'root',         revealAt:0.70 },
  { id:'shared',       label:'shared/',            level:1, pos:[3.2,-1.5,0.5]    as [number,number,number], parent:'root',         revealAt:0.74 },
  // BRANCHES — file nodes
  { id:'router',       label:'router.py',          level:2, pos:[-5,1,0.8]        as [number,number,number], parent:'api',          revealAt:0.32 },
  { id:'models',       label:'models.py',          level:2, pos:[-3.8,1.2,-0.5]   as [number,number,number], parent:'api',          revealAt:0.36 },
  { id:'entities',     label:'entities.py',        level:2, pos:[-1.8,1.5,2]      as [number,number,number], parent:'domain',       revealAt:0.40 },
  { id:'interfaces',   label:'interfaces.py',      level:2, pos:[-0.5,1.8,1]      as [number,number,number], parent:'domain',       revealAt:0.43 },
  { id:'repository',   label:'repository.py',      level:2, pos:[2.5,1.2,-1.5]    as [number,number,number], parent:'infra',        revealAt:0.46 },
  { id:'exceptions',   label:'exceptions.py',      level:2, pos:[4.2,1,1]         as [number,number,number], parent:'shared',       revealAt:0.50 },
  { id:'logging',      label:'logging.py',         level:2, pos:[3.5,1.5,-0.5]    as [number,number,number], parent:'shared',       revealAt:0.53 },
  // CROWN — leaf/symbol nodes, appear FIRST
  { id:'create_job',   label:'create_job()',       level:3, pos:[-5.8,3.2,1]      as [number,number,number], parent:'router',       revealAt:0.05 },
  { id:'list_jobs',    label:'list_jobs()',        level:3, pos:[-4.5,3.5,0.5]    as [number,number,number], parent:'router',       revealAt:0.08 },
  { id:'job_cls',      label:'Job',               level:3, pos:[-2.2,3.8,2.5]    as [number,number,number], parent:'entities',     revealAt:0.10 },
  { id:'jobstatus',    label:'JobStatus',         level:3, pos:[-1,4,2]          as [number,number,number], parent:'entities',     revealAt:0.12 },
  { id:'abstractrepo', label:'AbstractRepo',      level:3, pos:[-0.2,4.2,1.2]    as [number,number,number], parent:'interfaces',   revealAt:0.14 },
  { id:'postgresrepo', label:'PostgresRepo',      level:3, pos:[3,3.8,-2]        as [number,number,number], parent:'repository',   revealAt:0.16 },
  { id:'memoryrepo',   label:'InMemoryRepo',      level:3, pos:[2,4,-1.5]        as [number,number,number], parent:'repository',   revealAt:0.18 },
  { id:'notfound',     label:'NotFoundError',     level:3, pos:[5,3.2,1.5]       as [number,number,number], parent:'exceptions',   revealAt:0.20 },
  { id:'valerror',     label:'ValidationError',   level:3, pos:[4,3.5,0.8]       as [number,number,number], parent:'exceptions',   revealAt:0.22 },
  { id:'configure',    label:'configure_logging()',level:3,pos:[4.2,3.8,-0.8]    as [number,number,number], parent:'logging',      revealAt:0.24 },
];

// ── Edge definitions (with explicit revealAt) ─────────────────────────────────

const EDGES = [
  // Crown → Branch (leaf to file)
  { from:'router',       to:'create_job',   revealAt:0.34 },
  { from:'router',       to:'list_jobs',    revealAt:0.35 },
  { from:'entities',     to:'job_cls',      revealAt:0.42 },
  { from:'entities',     to:'jobstatus',    revealAt:0.42 },
  { from:'interfaces',   to:'abstractrepo', revealAt:0.45 },
  { from:'repository',   to:'postgresrepo', revealAt:0.48 },
  { from:'repository',   to:'memoryrepo',   revealAt:0.48 },
  { from:'exceptions',   to:'notfound',     revealAt:0.52 },
  { from:'exceptions',   to:'valerror',     revealAt:0.52 },
  { from:'logging',      to:'configure',    revealAt:0.55 },
  // Branch → Trunk (file to module)
  { from:'api',          to:'router',       revealAt:0.64 },
  { from:'api',          to:'models',       revealAt:0.64 },
  { from:'domain',       to:'entities',     revealAt:0.68 },
  { from:'domain',       to:'interfaces',   revealAt:0.68 },
  { from:'infra',        to:'repository',   revealAt:0.72 },
  { from:'shared',       to:'exceptions',   revealAt:0.76 },
  { from:'shared',       to:'logging',      revealAt:0.76 },
  // Trunk → Root (module to root)
  { from:'root',         to:'api',          revealAt:0.87 },
  { from:'root',         to:'domain',       revealAt:0.88 },
  { from:'root',         to:'infra',        revealAt:0.89 },
  { from:'root',         to:'shared',       revealAt:0.90 },
];

// ── Growing edge — draws from source toward target as progress increases ───────

function GrowingEdge({
  fromPos, toPos, color, baseOpacity, lineWidth, revealAt, progress,
}: {
  fromPos: [number,number,number];
  toPos: [number,number,number];
  color: string;
  baseOpacity: number;
  lineWidth: number;
  revealAt: number;
  progress: React.MutableRefObject<number>;
}) {
  const geometry = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.Float32BufferAttribute([
      ...fromPos, ...fromPos,
    ], 3));
    return g;
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const material = useMemo(
    () => new THREE.LineBasicMaterial({ color, transparent: true, opacity: 0, linewidth: lineWidth }),
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

// ── Node sphere with spring reveal + burst for root ───────────────────────────

function NodeSphere({
  node, progress,
}: {
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
    const target = vis ? 1 : 0;
    s.current += (target - s.current) * Math.min(dt * 10, 1);

    // Root burst: overshoots scale then settles
    if (node.level === 0 && vis) {
      const bp = Math.min((p - node.revealAt) / 0.05, 1);
      const burst = 1 + Math.sin(bp * Math.PI) * 0.55;
      meshRef.current.scale.setScalar(s.current * burst);
    } else {
      meshRef.current.scale.setScalar(s.current);
    }

    // Breathing emissive
    const breath = 1 + Math.sin(state.clock.elapsedTime * 1.6 + node.pos[0] * 0.9) * 0.3;
    matRef.current.emissiveIntensity = vis ? maxGlow * breath * s.current : 0;
  });

  return (
    <mesh ref={meshRef} position={node.pos} scale={0}>
      <sphereGeometry args={[maxSize, 20, 20]} />
      <meshStandardMaterial ref={matRef} color={color} emissive={color}
        emissiveIntensity={0} roughness={0.1} metalness={0.4} />
    </mesh>
  );
}

// ── Sap particle — flows from root upward to a leaf (phase 5) ─────────────────

function SapParticle({
  fromPos, toPos, speed, offset, colorStart, colorEnd, progress,
}: {
  fromPos: [number,number,number];
  toPos: [number,number,number];
  speed: number;
  offset: number;
  colorStart: string;
  colorEnd: string;
  progress: React.MutableRefObject<number>;
}) {
  const meshRef = useRef<THREE.Mesh>(null);
  const matRef  = useRef<THREE.MeshBasicMaterial>(null);
  const col     = useMemo(() => new THREE.Color(colorStart), [colorStart]);
  const colEnd  = useMemo(() => new THREE.Color(colorEnd), [colorEnd]);

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
    col.lerpColors(new THREE.Color(colorStart), colEnd, t);
    matRef.current.color.set(col);
    matRef.current.opacity = Math.sin(t * Math.PI) * 0.8 * intensity;
  });

  return (
    <mesh ref={meshRef}>
      <sphereGeometry args={[0.03, 7, 7]} />
      <meshBasicMaterial ref={matRef} transparent opacity={0} />
    </mesh>
  );
}

// ── Scroll-driven camera ──────────────────────────────────────────────────────

function ScrollCamera({ progress }: { progress: React.MutableRefObject<number> }) {
  const { camera } = useThree();
  useFrame((state) => {
    const p = progress.current;
    const cam = camera as THREE.PerspectiveCamera;
    // Pull back as tree grows; tilt down toward root
    cam.position.z += (8 + p * 6 - cam.position.z) * 0.05;
    cam.position.y += (2 - p * 3 - cam.position.y) * 0.05;
    // Very slow X drift for depth
    cam.position.x = Math.sin(state.clock.elapsedTime * 0.05) * 1.2;
    cam.lookAt(0, 0, 0);
  });
  return null;
}

// ── Root glow burst halo ──────────────────────────────────────────────────────

function RootHalo({ progress }: { progress: React.MutableRefObject<number> }) {
  const matRef = useRef<THREE.MeshBasicMaterial>(null);
  useFrame(() => {
    if (!matRef.current) return;
    const p = progress.current;
    matRef.current.opacity = p >= 0.85 ? Math.min((p - 0.85) / 0.08, 1) * 0.18 : 0;
  });
  return (
    <mesh position={[0, -4, 0]}>
      <sphereGeometry args={[1.4, 24, 24]} />
      <meshBasicMaterial ref={matRef} color="#7C3AED" transparent opacity={0} side={THREE.BackSide} />
    </mesh>
  );
}

// ── Main scene ────────────────────────────────────────────────────────────────

function TreeScene({ progress }: { progress: React.MutableRefObject<number> }) {
  const groupRef = useRef<THREE.Group>(null);
  const nodeMap  = useMemo(() => new Map(NODES.map((n) => [n.id, n])), []);

  // Slow idle rotation (independent of scroll — keeps tree alive between scrolls)
  useFrame((_, dt) => {
    if (!groupRef.current) return;
    groupRef.current.rotation.y += dt * 0.045;
  });

  // Sap paths: root → each leaf (for phase 5 particles)
  const sapPaths = useMemo(() => {
    const root = NODES.find((n) => n.id === 'root')!;
    return NODES.filter((n) => n.level === 3).map((leaf, i) => ({
      from: root.pos,
      to: leaf.pos,
      speed: 0.22 + i * 0.02,
      offset: i * 0.19,
    }));
  }, []);

  return (
    <>
      <ambientLight intensity={0.1} />
      <pointLight position={[0, 5, 5]}   intensity={3.0} color="#7C3AED" />
      <pointLight position={[5, 0, -3]}  intensity={2.0} color="#22D3EE" />
      <pointLight position={[-5, 3, 3]}  intensity={1.5} color="#34D399" />
      <pointLight position={[0, -5, 0]}  intensity={2.5} color="#7C3AED" distance={10} />

      <ScrollCamera progress={progress} />

      <group ref={groupRef} position={[0, 0, 0]}>
        {/* Edges */}
        {EDGES.map((edge) => {
          const fromNode = nodeMap.get(edge.from);
          const toNode   = nodeMap.get(edge.to);
          if (!fromNode || !toNode) return null;
          const color     = COLOR[toNode.level as Lv];
          const isTrunk   = toNode.level === 1;
          const isCrown   = toNode.level === 3;
          return (
            <GrowingEdge
              key={`${edge.from}-${edge.to}`}
              fromPos={fromNode.pos}
              toPos={toNode.pos}
              color={color}
              baseOpacity={isTrunk ? 0.8 : isCrown ? 0.55 : 0.7}
              lineWidth={isTrunk ? 1.6 : 0.9}
              revealAt={edge.revealAt}
              progress={progress}
            />
          );
        })}

        {/* Nodes */}
        {NODES.map((node) => (
          <NodeSphere key={node.id} node={node} progress={progress} />
        ))}

        {/* Labels — root + modules only (level 0 and 1) */}
        {NODES.filter((n) => n.level <= 1).map((node) => (
          <Text
            key={`lbl-${node.id}`}
            position={[node.pos[0], node.pos[1] + SIZE[node.level as Lv] + 0.3, node.pos[2]]}
            fontSize={node.level === 0 ? 0.26 : 0.18}
            color={COLOR[node.level as Lv]}
            anchorX="center"
            anchorY="bottom"
            fillOpacity={0.9}
          >
            {node.label}
          </Text>
        ))}

        {/* Phase-5 sap particles */}
        {sapPaths.map((sp, i) => (
          <SapParticle
            key={`sap-${i}`}
            fromPos={sp.from}
            toPos={sp.to}
            speed={sp.speed}
            offset={sp.offset}
            colorStart="#7C3AED"
            colorEnd="#34D399"
            progress={progress}
          />
        ))}

        {/* Root halo burst */}
        <RootHalo progress={progress} />
      </group>
    </>
  );
}

// ── Export ────────────────────────────────────────────────────────────────────

export default function RepoTree({ progress }: { progress: React.MutableRefObject<number> }) {
  return (
    <div style={{ width:'100%', height:'100%' }}>
      <Canvas
        camera={{ position:[0, 2, 8], fov:52 }}
        style={{ background:'transparent' }}
        gl={{ antialias:true, alpha:true }}
        dpr={[1, 2]}
      >
        <TreeScene progress={progress} />
      </Canvas>
    </div>
  );
}
