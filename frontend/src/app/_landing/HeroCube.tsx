'use client';

// =============================================================================
// CortexCube — The Living Identity of Cortex
// A cube that breathes, floats and reasons. Pinned across the entire
// cinematic scroll experience — it is never a static hero prop, it IS the story.
// =============================================================================

import { useRef, useEffect, useMemo, memo } from 'react';
import { Canvas, useFrame, useThree } from '@react-three/fiber';
import { RoundedBox, PerspectiveCamera, Environment, ContactShadows, Line } from '@react-three/drei';
import * as THREE from 'three';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';
import { SCENES, SCROLL_TRIGGER_CONFIG } from './sceneTimings';

gsap.registerPlugin(ScrollTrigger);

// ─── Constants ────────────────────────────────────────────────────────────────

const PIECE_SIZE = 1.55;
const BEVEL = 0.06;
const GAP = 0.015;

// 4 engineering "clusters" — each holds 2 stacked octants and represents one
// stage of the Cortex pipeline once separated.
const CLUSTER_META = [
  { label: 'Repository Scanner', color: '#9AA5B1', dir: [-1, 1] },
  { label: 'AST Parser', color: '#00D4FF', dir: [1, 1] },
  { label: 'Knowledge Graph', color: '#6B57E8', dir: [-1, -1] },
  { label: 'Learning Engine', color: '#34D399', dir: [1, -1] },
] as const;

type Piece = {
  pivot: React.RefObject<THREE.Group>;
  mesh: React.RefObject<THREE.Mesh>;
  material: React.RefObject<THREE.MeshStandardMaterial>;
  cluster: number;
};

// ─── Sub-Components ───────────────────────────────────────────────────────────

function Piece({ position, piece, baseColor }: { position: [number, number, number]; piece: Piece; baseColor: string }) {
  return (
    <group ref={piece.pivot}>
      <mesh ref={piece.mesh} position={position}>
        <RoundedBox args={[PIECE_SIZE, PIECE_SIZE, PIECE_SIZE]} radius={BEVEL} smoothness={4}>
          <meshStandardMaterial
            ref={piece.material}
            color="#0D0D0F"
            roughness={0.4}
            metalness={0.3}
            emissive={baseColor}
            emissiveIntensity={0.06}
          />
        </RoundedBox>
      </mesh>
    </group>
  );
}

function ReasoningCore({ coreRef }: { coreRef: React.RefObject<THREE.Mesh> }) {
  useFrame((state) => {
    if (!coreRef.current) return;
    coreRef.current.rotation.y += 0.006;
    coreRef.current.rotation.z += 0.003;
    const material = coreRef.current.material as THREE.MeshStandardMaterial;
    const pulse = 1 + Math.sin(state.clock.elapsedTime * 1.6) * 0.08;
    coreRef.current.scale.setScalar(pulse);
    if (material) {
      material.emissiveIntensity = 6 + Math.sin(state.clock.elapsedTime * 2.4) * 2;
    }
  });

  return (
    <mesh ref={coreRef}>
      <icosahedronGeometry args={[0.55, 2]} />
      <meshStandardMaterial color="#00D4FF" emissive="#00D4FF" emissiveIntensity={6} transparent opacity={0.92} />
    </mesh>
  );
}

/** Animated energy connections that appear between the 4 clusters during the "Reasoning" scene. */
function ReasoningLines({
  groupRef,
  clusterAnchors,
  initialScale,
}: {
  groupRef: React.RefObject<THREE.Group>;
  clusterAnchors: [number, number, number][];
  initialScale: number;
}) {
  const particleRefs = useRef<THREE.Mesh[]>([]);
  const pairs = useMemo(() => [
    [0, 1], [1, 3], [3, 2], [2, 0], [0, 3], [1, 2],
  ], []);

  useFrame((state) => {
    particleRefs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const [a, b] = pairs[i % pairs.length];
      const start = new THREE.Vector3(...clusterAnchors[a]);
      const end = new THREE.Vector3(...clusterAnchors[b]);
      const t = (state.clock.elapsedTime * 0.4 + i * 0.15) % 1;
      mesh.position.lerpVectors(start, end, t);
      const material = mesh.material as THREE.MeshBasicMaterial;
      if (material) material.opacity = Math.sin(t * Math.PI);
    });
  });

  return (
    <group ref={groupRef} scale={initialScale}>
      {pairs.map(([a, b], i) => (
        <Line
          key={i}
          points={[clusterAnchors[a], clusterAnchors[b]]}
          color="#00D4FF"
          transparent
          opacity={0.12}
          lineWidth={1}
        />
      ))}
      {pairs.map((_, i) => (
        <mesh key={`particle-${i}`} ref={(el) => { if (el) particleRefs.current[i] = el; }}>
          <sphereGeometry args={[0.045, 8, 8]} />
          <meshBasicMaterial color="#00D4FF" transparent opacity={0.9} />
        </mesh>
      ))}
    </group>
  );
}

// ─── Controller ──────────────────────────────────────────────────────────────

function SceneController({
  containerRef,
  groupRef,
  coreRef,
  pieces,
  linesGroupRef,
  mouse,
}: {
  containerRef: React.RefObject<HTMLDivElement>;
  groupRef: React.RefObject<THREE.Group>;
  coreRef: React.RefObject<THREE.Mesh>;
  pieces: Piece[];
  linesGroupRef: React.RefObject<THREE.Group>;
  mouse: React.MutableRefObject<{ x: number; y: number }>;
}) {
  const { camera, scene, gl } = useThree();
  const parallaxTarget = useRef({ x: 0, y: 0 });
  const reducedMotion = useRef(false);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    reducedMotion.current = prefersReducedMotion;
    if (prefersReducedMotion) return;

    // ── BUG FIX: R3F hasn't committed groupRef when useEffect fires.
    // Poll with rAF until the Three.js object is mounted, then build the timeline.
    let rafId = 0;
    let killed = false;
    // Store the timeline so we can kill only this component's ScrollTrigger on cleanup
    let ownTl: gsap.core.Timeline | null = null;

    function waitAndBuild() {
      if (killed) return;
      if (!groupRef.current) {
        rafId = requestAnimationFrame(waitAndBuild);
        return;
      }
      buildTimeline();
    }

    function buildTimeline() {
      if (killed || !groupRef.current) return;

      const tl = gsap.timeline({
        scrollTrigger: {
          trigger: container,
          ...SCROLL_TRIGGER_CONFIG,
          pin: true,
          pinSpacing: true,
        },
      });

    // ── Scene: Ingest — camera dollies in as the repository is accepted ──────
    tl.to(camera.position, { z: 8.2, duration: 1.2, ease: 'power2.inOut' }, SCENES.ingest);
    if (coreRef.current) {
      tl.to(coreRef.current.scale, { x: 1.4, y: 1.4, z: 1.4, duration: 0.6, ease: 'power2.out' }, SCENES.ingest + 0.4)
        .to(coreRef.current.scale, { x: 1, y: 1, z: 1, duration: 0.8, ease: 'power2.inOut' }, SCENES.ingest + 1);
    }

    // ── Scene: Thinking — tiny vibration, no travel ─────────────────────────
    tl.to(groupRef.current.position, {
      x: '+=0.03', duration: 0.08, repeat: 9, yoyo: true, ease: 'none',
    }, SCENES.thinking);

    // ── Scene: Separate — 4 clusters move outward with mechanical precision ─
    pieces.forEach((piece) => {
      if (!piece.pivot.current || !piece.mesh.current) return;
      const [dx, dy] = CLUSTER_META[piece.cluster].dir;
      tl.to(piece.mesh.current.position, {
        x: `+=${dx * 2.6}`,
        y: `+=${dy * 2.6}`,
        z: '+=0.4',
        duration: 2,
        ease: 'power3.inOut',
      }, SCENES.separate);
    });
    tl.to(camera.position, { z: 11, duration: 2, ease: 'power2.inOut' }, SCENES.separate);
    tl.to(groupRef.current.rotation, { y: '+=0.35', duration: 2, ease: 'power2.inOut' }, SCENES.separate);

    // ── Scene: Pipeline — clusters light up individually (color washes in) ──
    pieces.forEach((piece, i) => {
      if (!piece.material.current) return;
      tl.to(piece.material.current, {
        emissiveIntensity: 0.9,
        duration: 0.6,
        ease: 'power2.out',
      }, SCENES.pipeline + i * 0.25);
    });

    // ── Scene: Reasoning — connection lines grow in from nothing ────────────
    if (linesGroupRef.current) {
      tl.fromTo(
        linesGroupRef.current.scale,
        { x: 0, y: 0, z: 0 },
        { x: 1, y: 1, z: 1, duration: 1.5, ease: 'power2.out' },
        SCENES.reasoning
      );
    }

    // ── Scene: Artifacts — cube recenters left so overlays have room ────────
    tl.to(groupRef.current.position, { x: -1.6, duration: 1.5, ease: 'power2.inOut' }, SCENES.artifacts);
    tl.to(camera.position, { z: 13, duration: 1.5, ease: 'power2.inOut' }, SCENES.artifacts);

    // ── Scene: Self-Analysis — cube recedes and dims behind the dashboard ───
    tl.to(groupRef.current.position, { x: 0, z: -1.5, duration: 1.5, ease: 'power2.inOut' }, SCENES.selfAnalysis);
    tl.to(groupRef.current.scale, { x: 0.75, y: 0.75, z: 0.75, duration: 1.5, ease: 'power2.inOut' }, SCENES.selfAnalysis);

    // ── Scene: Reassemble — magnetic snap back to origin ────────────────────
    pieces.forEach((piece) => {
      if (!piece.mesh.current || !piece.material.current) return;
      tl.to(piece.mesh.current.position, { x: 0, y: 0, z: 0, duration: 1.6, ease: 'power3.inOut' }, SCENES.reassemble);
      tl.to(piece.material.current, { emissiveIntensity: 0.1, duration: 1.2, ease: 'power2.out' }, SCENES.reassemble + 0.4);
    });
    if (linesGroupRef.current) {
      tl.to(linesGroupRef.current.scale, { x: 0, y: 0, z: 0, duration: 0.8, ease: 'power2.in' }, SCENES.reassemble);
    }
    tl.to(groupRef.current.position, { x: 0, y: 0, z: 0, duration: 1.6, ease: 'power3.inOut' }, SCENES.reassemble);
    tl.to(groupRef.current.scale, { x: 1, y: 1, z: 1, duration: 1.6, ease: 'power3.inOut' }, SCENES.reassemble);
    tl.to(camera.position, { z: 10, duration: 1.6, ease: 'power2.inOut' }, SCENES.reassemble);

    // ── Finale — settle for the CTA, cube keeps its idle breathing ──────────
    tl.to(camera.position, { z: 9.5, duration: 1, ease: 'power2.out' }, SCENES.finale);

    // Store reference so cleanup can kill only this timeline's ScrollTrigger
    ownTl = tl;
    } // end buildTimeline

    rafId = requestAnimationFrame(waitAndBuild);

    return () => {
      killed = true;
      cancelAnimationFrame(rafId);
      // Kill only this component's own timeline (and its embedded ScrollTrigger).
      // Using getAll() would incorrectly kill ScrollTrigger instances created by
      // useScrollStory and useDepthOfField in page.tsx.
      if (ownTl) {
        ownTl.kill();
        ownTl = null;
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [camera, containerRef, groupRef, coreRef, pieces, linesGroupRef]);

  // GPU cleanup — dispose all geometries and materials, then release the renderer (Req 11.6, 11.7)
  useEffect(() => {
    return () => {
      scene.traverse((obj) => {
        if (obj instanceof THREE.Mesh) {
          obj.geometry.dispose();
          if (Array.isArray(obj.material)) {
            obj.material.forEach((m) => m.dispose());
          } else {
            obj.material.dispose();
          }
        }
      });
      gl.dispose();
    };
  }, [scene, gl]);

  // Perpetual idle motion — breathing, floating, mouse parallax. Runs always,
  // independent of scroll, so the cube never feels inert between scenes.
  useFrame((state, delta) => {
    if (!groupRef.current) return;
    const t = state.clock.elapsedTime;

    // Mouse parallax (lerped for smoothness) — runs regardless of reduced-motion
    // so the user's interaction always has some feedback.
    parallaxTarget.current.x += (mouse.current.x - parallaxTarget.current.x) * 0.04;
    parallaxTarget.current.y += (mouse.current.y - parallaxTarget.current.y) * 0.04;

    const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (!prefersReducedMotion) {
      // Idle rotation drift — ≤ 0.5°/s (Req 11.1)
      groupRef.current.rotation.y += delta * 0.008;

      // Floating Y — vertical breathing (Req 11.2)
      const floatY = Math.sin(t * 0.6) * 0.12;
      groupRef.current.rotation.x = parallaxTarget.current.y * 0.15;
      groupRef.current.position.y = floatY + parallaxTarget.current.y * 0.05;

      // Polar coordinate camera orbit — ≤ 0.3°/s around Y axis (Req 17.1)
      // Camera breathing — ±0.08 units at 0.4 rad/s (Req 17.2)
      // FOV micro-zoom — ±0.5° based on mouse Y (Req 17.3)
      camera.position.x = Math.sin(t * 0.008) * 0.5;
      camera.position.y = Math.sin(t * 0.4) * 0.08;
      (camera as THREE.PerspectiveCamera).fov = 32 + mouse.current.y * 0.5;
      (camera as THREE.PerspectiveCamera).updateProjectionMatrix();
      camera.lookAt(0, 0, 0);
    }
  });

  return (
    <>
      <PerspectiveCamera makeDefault position={[0, 0, 10]} fov={32} />
      <fog attach="fog" args={['#0A0A0B', 9, 24]} />
    </>
  );
}

// ─── Main export ──────────────────────────────────────────────────────────────

function CortexCube() {
  const containerRef = useRef<HTMLDivElement>(null);
  const groupRef = useRef<THREE.Group>(null);
  const coreRef = useRef<THREE.Mesh>(null);
  const linesGroupRef = useRef<THREE.Group>(null);
  const mouse = useRef({ x: 0, y: 0 });

  const pieces = useMemo<Piece[]>(
    () =>
      Array.from({ length: 8 }, (_, i) => ({
        pivot: { current: null } as React.RefObject<THREE.Group>,
        mesh: { current: null } as React.RefObject<THREE.Mesh>,
        material: { current: null } as React.RefObject<THREE.MeshStandardMaterial>,
        cluster: i % 4,
      })),
    []
  );

  const clusterAnchors = useMemo<[number, number, number][]>(
    () =>
      CLUSTER_META.map(({ dir: [dx, dy] }) => [dx * 2.6, dy * 2.6, 0.4] as [number, number, number]),
    []
  );

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      mouse.current.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.current.y = (e.clientY / window.innerHeight) * 2 - 1;
    };
    window.addEventListener('mousemove', handleMouseMove);
    return () => window.removeEventListener('mousemove', handleMouseMove);
  }, []);

  return (
    <div ref={containerRef} className="relative w-full h-screen bg-onyx">
      {/* Volumetric glow behind the cube, shifted right to match the new asymmetric hero layout */}
      <div className="absolute inset-0 z-0 opacity-40 pointer-events-none bg-[radial-gradient(circle_at_68%_45%,_var(--carnallite-violet)_0%,_transparent_55%)]" />
      <div
        className="absolute inset-0 z-0 opacity-[0.07] pointer-events-none"
        style={{
          backgroundImage:
            'linear-gradient(var(--onyx) 1px, transparent 1px), linear-gradient(90deg, var(--onyx) 1px, transparent 1px)',
          backgroundSize: '44px 44px',
        }}
      />

      <Canvas dpr={[1, 2]} className="z-10" shadows>
        <SceneController
          containerRef={containerRef}
          groupRef={groupRef}
          coreRef={coreRef}
          pieces={pieces}
          linesGroupRef={linesGroupRef}
          mouse={mouse}
        />

        <ambientLight intensity={0.12} />
        <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} intensity={2.2} color="#6B57E8" castShadow />
        <pointLight position={[-10, -10, -10]} intensity={1} color="#00D4FF" />
        <pointLight position={[0, 5, 5]} intensity={0.5} color="#ffffff" />

        {/* Shifted right ~1.8 units so the cube dominates the right half of the hero */}
        <group ref={groupRef} position={[1.8, 0, 0]} scale={1.4}>
          {pieces.map((piece, i) => {
            const x = (i % 2 === 0 ? -1 : 1) * (PIECE_SIZE / 2 + GAP);
            const y = (Math.floor(i / 2) % 2 === 0 ? 1 : -1) * (PIECE_SIZE / 2 + GAP);
            const z = (i < 4 ? 1 : -1) * (PIECE_SIZE / 2 + GAP);
            return (
              <Piece
                key={i}
                position={[x, y, z]}
                piece={piece}
                baseColor={CLUSTER_META[piece.cluster].color}
              />
            );
          })}
          <ReasoningCore coreRef={coreRef} />
          <ReasoningLines groupRef={linesGroupRef} clusterAnchors={clusterAnchors} initialScale={0} />
        </group>

        <ContactShadows position={[1.8, -4.2, 0]} opacity={0.35} scale={22} blur={2.2} far={4.5} />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}

export default memo(CortexCube);
