'use client';

import { Suspense, useRef } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { useReducedMotion } from '@/hooks/useReducedMotion';

function RotatingCore({ isReducedMotion }: { isReducedMotion: boolean }) {
  const outerRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (isReducedMotion) return;
    if (outerRef.current) {
      outerRef.current.rotation.x += delta * 0.15;
      outerRef.current.rotation.y += delta * 0.25;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 0.1;
    }
  });

  return (
    <group>
      <ambientLight intensity={0.7} />
      <directionalLight position={[8, 8, 4]} intensity={1.5} color="#4668fa" />
      <pointLight position={[-8, -8, -4]} intensity={1.2} color="#00f5d4" />

      {/* Outer Wireframe Polyhedron */}
      <mesh ref={outerRef}>
        <icosahedronGeometry args={[2.0, 1]} />
        <meshStandardMaterial
          color="#4668fa"
          wireframe
          roughness={0.2}
          metalness={0.8}
          emissive="#1e2cb0"
          emissiveIntensity={0.3}
        />
      </mesh>

      {/* Inner Glowing Core */}
      <Sphere args={[1.1, 48, 48]}>
        <MeshDistortMaterial
          color="#9d4edd"
          attach="material"
          distort={isReducedMotion ? 0 : 0.3}
          speed={isReducedMotion ? 0 : 1.5}
          roughness={0.3}
          metalness={0.8}
        />
      </Sphere>

      {/* Orbital Ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 3, 0, 0]}>
        <torusGeometry args={[2.8, 0.03, 16, 80]} />
        <meshBasicMaterial color="#00f5d4" transparent opacity={0.65} />
      </mesh>
    </group>
  );
}

export default function HeroScene() {
  const isReducedMotion = useReducedMotion();

  return (
    <div className="w-full h-full min-h-[300px] flex items-center justify-center">
      <Canvas
        camera={{ position: [0, 0, 5.5], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'low-power' }}
      >
        <Suspense fallback={null}>
          {isReducedMotion ? (
            <RotatingCore isReducedMotion={true} />
          ) : (
            <Float speed={1.5} rotationIntensity={0.3} floatIntensity={0.8}>
              <RotatingCore isReducedMotion={false} />
            </Float>
          )}
        </Suspense>
      </Canvas>
    </div>
  );
}
