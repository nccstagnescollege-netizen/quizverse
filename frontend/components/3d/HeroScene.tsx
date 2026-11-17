'use client';

import { Suspense, useRef, useEffect, useState } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { Float, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';
import { useReducedMotion } from '@/hooks/useReducedMotion';

interface RotatingCoreProps {
  isReducedMotion: boolean;
  isMobile: boolean;
}

function RotatingCore({ isReducedMotion, isMobile }: RotatingCoreProps) {
  const outerRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((state, delta) => {
    if (isReducedMotion) return;
    if (outerRef.current) {
      outerRef.current.rotation.x += delta * 0.15;
      outerRef.current.rotation.y += delta * 0.25;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 0.1;
    }
  });

  // Scale down complexity for mobile phones to save GPU battery & avoid frame drops
  const sphereSegments = isMobile ? 24 : 48;
  const torusTubular = isMobile ? 40 : 80;

  return (
    <group scale={isMobile ? 0.85 : 1.0}>
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
      <Sphere args={[1.1, sphereSegments, sphereSegments]}>
        <MeshDistortMaterial
          color="#9d4edd"
          attach="material"
          distort={isReducedMotion ? 0 : isMobile ? 0.2 : 0.3}
          speed={isReducedMotion ? 0 : 1.5}
          roughness={0.3}
          metalness={0.8}
        />
      </Sphere>

      {/* Orbital Ring */}
      <mesh ref={ringRef} rotation={[Math.PI / 3, 0, 0]}>
        <torusGeometry args={[2.8, 0.03, 16, torusTubular]} />
        <meshBasicMaterial color="#00f5d4" transparent opacity={0.65} />
      </mesh>
    </group>
  );
}

export default function HeroScene() {
  const isReducedMotion = useReducedMotion();
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    function checkSize() {
      setIsMobile(window.innerWidth < 768);
    }
    checkSize();
    window.addEventListener('resize', checkSize);
    return () => window.removeEventListener('resize', checkSize);
  }, []);

  return (
    <div className="w-full h-full min-h-[260px] sm:min-h-[340px] flex items-center justify-center relative touch-none">
      <Canvas
        camera={{ position: [0, 0, 5.5], fov: isMobile ? 50 : 45 }}
        gl={{
          antialias: !isMobile,
          alpha: true,
          powerPreference: isMobile ? 'low-power' : 'default',
        }}
        dpr={isMobile ? [1, 1.25] : [1, 2]}
      >
        <Suspense fallback={null}>
          {isReducedMotion ? (
            <RotatingCore isReducedMotion={true} isMobile={isMobile} />
          ) : (
            <Float
              speed={isMobile ? 1.0 : 1.5}
              rotationIntensity={isMobile ? 0.15 : 0.3}
              floatIntensity={isMobile ? 0.4 : 0.8}
            >
              <RotatingCore isReducedMotion={false} isMobile={isMobile} />
            </Float>
          )}
        </Suspense>
      </Canvas>
    </div>
  );
}
