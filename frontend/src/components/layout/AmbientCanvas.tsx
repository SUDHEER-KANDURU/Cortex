'use client';

// =============================================================================
// AmbientCanvas — Apple Music Replay-style ambient background
//
// Technique (researched from Kawarp library + iOS SwiftUI reversals):
//   Apple's actual method uses MULTIPLE independently-drifting colour sources
//   composited via domain-warped fbm fields — NOT a single Gaussian blob.
//   The Inigo Quilez double domain-warp (q = fbm(p), r = fbm(p+4q), f = fbm(p+4r))
//   creates the organic "ink in water" look. Three independent warped fields
//   each carry a different warm colour; they overlap, breathe, and shift
//   independently, creating the rich multi-colour evolution the reference shows.
// =============================================================================

import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import * as THREE from 'three';

export interface AmbientParams {
  opacity: number;
  sat: number;
  speed: number;
  warp: number;
}

const VERT = /* glsl */ `
  varying vec2 vUv;
  void main(){
    vUv = uv;
    gl_Position = vec4(position.xy, 0.0, 1.0);
  }
`;

const FRAG = /* glsl */ `
  precision highp float;
  varying vec2 vUv;
  uniform float uTime;
  uniform float uOpacity;
  uniform float uSat;
  uniform float uWarp;

  // ── Simplex noise (Ashima Arts / Stefan Gustavson) ───────────────────
  vec3 mod289(vec3 x){return x-floor(x*(1./289.))*289.;}
  vec2 mod289(vec2 x){return x-floor(x*(1./289.))*289.;}
  vec3 permute(vec3 x){return mod289(((x*34.)+1.)*x);}
  float snoise(vec2 v){
    const vec4 C=vec4(.211324865405187,.366025403784439,-.577350269189626,.024390243902439);
    vec2 i=floor(v+dot(v,C.yy)),x0=v-i+dot(i,C.xx);
    vec2 i1=(x0.x>x0.y)?vec2(1.,0.):vec2(0.,1.);
    vec4 x12=x0.xyxy+C.xxzz; x12.xy-=i1;
    i=mod289(i);
    vec3 p=permute(permute(i.y+vec3(0.,i1.y,1.))+i.x+vec3(0.,i1.x,1.));
    vec3 m=max(.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.);
    m=m*m;m=m*m;
    vec3 x=2.*fract(p*C.www)-1.,h=abs(x)-.5,ox=floor(x+.5),a0=x-ox;
    m*=1.79284291400159-.85373472095314*(a0*a0+h*h);
    vec3 g;g.x=a0.x*x0.x+h.x*x0.y;g.yz=a0.yz*x12.xz+h.yz*x12.yw;
    return 130.*dot(m,g);
  }

  // ── fBm: 5 octaves of noise ─────────────────────────────────────────
  float fbm(vec2 p){
    float v=0.,a=.5;
    for(int i=0;i<5;i++){v+=a*snoise(p);p*=2.07;a*=.5;}
    return v;
  }

  // ── Inigo Quilez double domain-warp ────────────────────────────────
  // Creates the "ink in water / smoke" look. Ref: iquilezles.org/warp
  float warpField(vec2 p, float tOff) {
    float t = uTime * 0.10 + tOff;
    vec2 q = vec2(
      fbm(p + vec2(0.0, t)),
      fbm(p + vec2(5.2, 1.3 + t * 0.9))
    );
    vec2 r = vec2(
      fbm(p + 4.0*q + vec2(1.7, 9.2) + t * 1.1),
      fbm(p + 4.0*q + vec2(8.3, 2.8) + t * 0.85)
    );
    return fbm(p + 4.0*r);
  }

  void main(){
    vec2 uv = vUv;  // uv.y=0 bottom, 1 top (verified empirically)

    // Scale: determines how "zoomed in" the noise looks.
    // Lower = larger, smoother blobs. ~1.4-1.8 matches Apple's scale.
    vec2 p = uv * 1.6;

    // ── Three independently-evolving fields ───────────────────────────
    // Each uses a different time offset → different evolution rhythm
    // Each uses a different spatial offset → different regions of the frame
    float f1 = warpField(p,                          0.0);   // primary
    float f2 = warpField(p * 0.85 + vec2(3.1, 1.4), 7.3);   // secondary
    float f3 = warpField(p * 0.70 + vec2(6.7, 3.8), 14.6);  // tertiary

    // Map from [-1..1] to [0..1]
    float v1 = f1 * 0.5 + 0.5;
    float v2 = f2 * 0.5 + 0.5;
    float v3 = f3 * 0.5 + 0.5;

    // ── Bias: dark at the top, brighter toward the bottom ────────────
    // Apple reference: top half is near-black; warmth rises from the bottom.
    // uv.y=1 is TOP, so (1-uv.y) = 1 at bottom, 0 at top.
    float rise = pow(1.0 - uv.y, 1.6);   // 1 at bottom, 0 at top
    v1 = v1 * (0.35 + 0.65 * rise);
    v2 = v2 * (0.20 + 0.80 * rise);
    v3 = v3 * (0.25 + 0.75 * rise);

    // ── Warm palette (4 colours + slow drift) ────────────────────────
    // Apple Replay uses warm ambers, embers, and deep rusts — NO cool hues.
    // Drift is on a very long period so colour changes are felt, not noticed.
    float drift1 = sin(uTime * 0.018) * 0.5 + 0.5;  // ~349s period
    float drift2 = sin(uTime * 0.023 + 2.1) * 0.5 + 0.5; // ~273s period

    // Colour sources — measured from Apple Replay reference frames
    vec3 cDeepRust  = vec3(0.38, 0.14, 0.04);  // dark ember, fills shadows
    vec3 cEmber     = mix(vec3(0.72, 0.30, 0.08), vec3(0.60, 0.22, 0.06), drift2);
    vec3 cAmber     = mix(vec3(0.85, 0.52, 0.18), vec3(0.78, 0.44, 0.14), drift1);
    vec3 cGold      = mix(vec3(0.92, 0.68, 0.28), vec3(0.86, 0.60, 0.22), drift1);

    // ── Compose: blend layers using their field values ────────────────
    // Each field drives a different colour band.
    // Layered with smoothstep to avoid harsh transitions.
    vec3 col = vec3(0.0);
    col = mix(col,   cDeepRust, smoothstep(0.0,  0.45, v3));
    col = mix(col,   cEmber,    smoothstep(0.18, 0.60, v2));
    col = mix(col,   cAmber,    smoothstep(0.28, 0.72, v1));
    col = mix(col,   cGold,     smoothstep(0.55, 0.90, max(v1, v2 * 0.8)));

    // ── Saturation control for calmer tiers ───────────────────────────
    float luma = dot(col, vec3(0.299, 0.587, 0.114));
    col = mix(vec3(luma), col, uSat);

    // ── Alpha: transparent where all fields are low ───────────────────
    // max energy across all three fields, with a gentle ramp.
    // This keeps the near-black CSS base visible wherever the atmosphere
    // hasn't "pooled" — the key to genuine dark negative space.
    float energy = max(v1, max(v2, v3));
    float a = smoothstep(0.08, 0.50, energy * uWarp) * uOpacity;

    gl_FragColor = vec4(col, a);
  }
`;

function FlowPlane({ params }: { params: AmbientParams }) {
  const matRef = useRef<THREE.ShaderMaterial>(null);
  const cur    = useRef<AmbientParams>({ ...params });

  const uniforms = useMemo(() => ({
    uTime:    { value: 0 },
    uOpacity: { value: params.opacity },
    uSat:     { value: params.sat },
    uWarp:    { value: params.warp },
  }), []);

  useFrame((_state, dt) => {
    const m = matRef.current;
    if (!m) return;
    const k = 1 - Math.pow(0.0001, dt);
    cur.current.opacity += (params.opacity - cur.current.opacity) * k;
    cur.current.sat     += (params.sat     - cur.current.sat)     * k;
    cur.current.warp    += (params.warp    - cur.current.warp)    * k;
    cur.current.speed   += (params.speed   - cur.current.speed)   * k;

    m.uniforms.uTime.value    += dt * cur.current.speed;
    m.uniforms.uOpacity.value  = cur.current.opacity;
    m.uniforms.uSat.value      = cur.current.sat;
    m.uniforms.uWarp.value     = cur.current.warp;
  });

  return (
    <mesh frustumCulled={false}>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={matRef}
        vertexShader={VERT}
        fragmentShader={FRAG}
        uniforms={uniforms}
        transparent
        depthTest={false}
        depthWrite={false}
      />
    </mesh>
  );
}

export default function AmbientCanvas({ params }: { params: AmbientParams }) {
  return (
    <Canvas
      className="cx-ambient-canvas"
      style={{ position: 'fixed', inset: 0, zIndex: 0, pointerEvents: 'none' }}
      gl={{ antialias: false, alpha: true, powerPreference: 'low-power' }}
      dpr={[1, 1.5]}
      frameloop={params.speed > 0 ? 'always' : 'demand'}
      orthographic
      camera={{ position: [0, 0, 1] }}
      onCreated={({ gl }) => {
        gl.domElement.addEventListener('webglcontextlost', e => e.preventDefault(), false);
      }}
    >
      <FlowPlane params={params} />
    </Canvas>
  );
}
