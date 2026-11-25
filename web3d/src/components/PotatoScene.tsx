"use client";

import { Suspense, useEffect, useMemo, useRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, useTexture } from "@react-three/drei";
import * as THREE from "three";

export type VisualCategory = "Healthy" | "Fungi" | "Pest" | "Virus" | "Bacteria" | "Nematode" | "Phytopthora";

export type SceneProps = {
  category?: VisualCategory;
  intensity?: number;
  analyzing?: boolean;
};

const ACCENTS: Record<VisualCategory, string> = {
  Healthy: "#61FFB8", Fungi: "#65FFD3", Pest: "#F0BA58", Virus: "#FF855C",
  Bacteria: "#79E6DC", Nematode: "#DCC36F", Phytopthora: "#FFB279",
};
const SKINS = ["healthy", "mild", "visible", "intense"] as const;

function makeBody(detail: number, stage: number) {
  const geometry = new THREE.SphereGeometry(1, detail, Math.round(detail * 0.72));
  const pos = geometry.attributes.position as THREE.BufferAttribute;
  const deformation = stage / 3;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    const organic = 1 + 0.062 * Math.sin(3.2 * x + 4.4 * y + 1.7 * z)
      + 0.039 * Math.cos(6.3 * z - 2.5 * y)
      + 0.014 * Math.sin(12.2 * x + 8.1 * y)
      + deformation * 0.041 * Math.sin(7.3 * x - 4.5 * z);
    // Botanical, asymmetrical tuber with subtle lobes and depressed "eyes".
    const leftDent = Math.exp(-((x + 0.59) ** 2 + (y - 0.22) ** 2 + (z - 0.64) ** 2) / 0.045);
    const rightDent = Math.exp(-((x - 0.35) ** 2 + (y + 0.15) ** 2 + (z - 0.80) ** 2) / 0.022);
    const sink = 1 - 0.075 * leftDent - 0.042 * rightDent;
    pos.setXYZ(i,
      (x * 1.33 + 0.055 * y * y) * organic * sink,
      (y * 0.80 + 0.055 * x * x) * organic * sink,
      (z * 0.91 + 0.027 * x) * organic * sink,
    );
  }
  pos.needsUpdate = true;
  geometry.computeVertexNormals();
  return geometry;
}

const wireVertex = `
  varying vec2 vUv;
  varying vec3 vNormal;
  void main() {
    vUv = uv;
    vNormal = normal;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  }
`;
const wireFragment = `
  uniform vec3 uColor;
  uniform float uTime;
  uniform float uIntensity;
  varying vec2 vUv;
  varying vec3 vNormal;
  void main() {
    // A brighter scientific scan mesh only over a sector of the 3D potato.
    if (vUv.x < 0.20 || vUv.x > 0.57) discard;
    float softMask = smoothstep(0.20, 0.34, vUv.x);
    float edge = 0.2 + 0.35 * pow(1.0 - abs(vNormal.z), 1.2);
    float pulse = 0.84 + 0.16 * sin(uTime * 1.4 + vUv.y * 18.0);
    float alpha = softMask * (0.24 + 0.27 * uIntensity + edge) * pulse;
    gl_FragColor = vec4(uColor, clamp(alpha, 0.0, 0.82));
  }
`;

function PotatoBody({ category, intensity, analyzing }: Required<SceneProps>) {
  const group = useRef<THREE.Group>(null);
  const shader = useRef<THREE.ShaderMaterial>(null);
  const stage = category === "Healthy" ? 0 : intensity < 0.30 ? 0 : intensity < 0.60 ? 1 : intensity < 0.80 ? 2 : 3;
  const colorMap = useTexture(`/assets/textures/potato-${SKINS[stage]}.webp`);
  // No mutamos la textura compartida del hook: Three.js debe interpretar el albedo como sRGB.
  const diffuseMap = useMemo(() => {
    const texture = colorMap.clone();
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }, [colorMap]);
  const bumpMap = useTexture("/assets/textures/potato-bump.webp");
  const geometry = useMemo(() => makeBody(112, stage), [stage]);
  const wireGeometry = useMemo(() => makeBody(20, stage), [stage]);
  const accent = useMemo(() => new THREE.Color(ACCENTS[category]), [category]);
  const uniforms = useMemo(() => ({
    uColor: { value: accent },
    uIntensity: { value: intensity },
    uTime: { value: 0 },
  }), [accent, intensity]);

  useEffect(() => {
    return () => { diffuseMap.dispose(); geometry.dispose(); wireGeometry.dispose(); };
  }, [diffuseMap, geometry, wireGeometry]);

  useFrame(({ clock }, delta) => {
    if (group.current) {
      group.current.rotation.y += delta * (analyzing ? 0.85 : 0.12);
      group.current.rotation.z = -0.11 + Math.sin(clock.elapsedTime * 0.30) * 0.035;
      group.current.position.y = Math.sin(clock.elapsedTime * 0.95) * 0.072;
    }
    if (shader.current) shader.current.uniforms.uTime.value = clock.elapsedTime;
  });

  return (
    <group ref={group} rotation={[0.05, -0.36, -0.1]}>
      <mesh geometry={geometry} castShadow receiveShadow>
        <meshPhysicalMaterial
          map={diffuseMap}
          bumpMap={bumpMap}
          bumpScale={0.052 + stage * 0.005}
          roughness={0.86}
          metalness={0.0}
          clearcoat={0.09}
          clearcoatRoughness={0.72}
        />
      </mesh>
      <mesh geometry={wireGeometry} scale={1.014} renderOrder={5}>
        <shaderMaterial ref={shader} transparent wireframe depthWrite={false} vertexShader={wireVertex} fragmentShader={wireFragment} uniforms={uniforms} />
      </mesh>
    </group>
  );
}

function Scanner({ color, analyzing }: { color: string; analyzing: boolean }) {
  const beam = useRef<THREE.Mesh>(null);
  const halo = useRef<THREE.Mesh>(null);
  useFrame(({ clock }) => {
    if (beam.current) beam.current.position.y = Math.sin(clock.elapsedTime * (analyzing ? 2.2 : 0.75)) * 0.94;
    if (halo.current) halo.current.rotation.z += 0.0016;
  });
  return (
    <group>
      <mesh position={[0, -1.31, 0]} rotation={[-Math.PI / 2, 0, 0]}>
        <circleGeometry args={[1.76, 88]} />
        <meshBasicMaterial color={color} transparent opacity={0.055} depthWrite={false} side={THREE.DoubleSide} />
      </mesh>
      {[1.18, 1.48, 1.79].map((radius, i) => (
        <group key={radius}>
          <mesh position={[0, -1.30 - i * 0.025, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[radius, i === 1 ? 0.015 : 0.008, 8, 128]} />
            <meshBasicMaterial color={color} toneMapped={false} transparent opacity={i === 1 ? 0.94 : 0.43} />
          </mesh>
          <mesh position={[0, -1.31 - i * 0.025, 0]} rotation={[-Math.PI / 2, 0, 0]}>
            <torusGeometry args={[radius, 0.046, 8, 128]} />
            <meshBasicMaterial color={color} transparent opacity={i === 1 ? 0.10 : 0.035} blending={THREE.AdditiveBlending} depthWrite={false} />
          </mesh>
        </group>
      ))}
      <mesh ref={halo} position={[0, 0.1, 0]} rotation={[0, 0, 0]}>
        <torusGeometry args={[1.94, 0.007, 8, 140, Math.PI * 1.45]} />
        <meshBasicMaterial color={color} transparent opacity={0.57} depthWrite={false} />
      </mesh>
      <mesh ref={beam} position={[0, 0, 0]}>
        <boxGeometry args={[3.35, 0.014, 2.10]} />
        <meshBasicMaterial color={color} transparent opacity={analyzing ? 0.45 : 0.12} depthWrite={false} blending={THREE.AdditiveBlending} />
      </mesh>
    </group>
  );
}

function SceneContents({ category = "Healthy", intensity = 0.16, analyzing = false }: SceneProps) {
  return (
    <>
      <ambientLight intensity={1.10} />
      <hemisphereLight args={["#e8fff2", "#0a3029", 1.45]} />
      <directionalLight color="#fff0c6" intensity={3.7} position={[-3.6, 4.8, 5.5]} />
      <directionalLight color="#9fffe0" intensity={2.4} position={[4, -0.6, 2.2]} />
      <pointLight color={ACCENTS[category]} intensity={4.7} distance={7} position={[0, -1.5, 2.6]} />
      <spotLight color="#fff6dc" intensity={2.4} angle={0.76} penumbra={1} position={[-1, 3, 4]} />
      <Scanner color={ACCENTS[category]} analyzing={analyzing} />
      <PotatoBody category={category} intensity={intensity} analyzing={analyzing} />
      <OrbitControls enablePan={false} enableZoom minDistance={3.9} maxDistance={6.4} enableDamping dampingFactor={0.08} minPolarAngle={0.65} maxPolarAngle={2.3} />
    </>
  );
}

export default function PotatoScene(props: SceneProps) {
  return (
    <Canvas
      camera={{ position: [0, 0.22, 5.05], fov: 42 }}
      dpr={[1, 1.8]}
      gl={{ antialias: true, alpha: true, powerPreference: "high-performance" }}
      style={{ position: "absolute", inset: 0, touchAction: "pan-y" }}
      aria-label="Papa tridimensional interactiva; arrastrá para girar y usá la rueda para acercar"
    >
      <Suspense fallback={null}><SceneContents {...props} /></Suspense>
    </Canvas>
  );
}
