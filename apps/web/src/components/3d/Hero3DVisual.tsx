import { useRef } from 'react';
import { useFrame } from '@react-three/fiber';
import { Float, Sphere, MeshDistortMaterial } from '@react-three/drei';
import * as THREE from 'three';

export function Hero3DVisual() {
  const outerMeshRef = useRef<THREE.Mesh>(null);
  const innerMeshRef = useRef<THREE.Mesh>(null);
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame((_, delta) => {
    if (outerMeshRef.current) {
      outerMeshRef.current.rotation.x += delta * 0.2;
      outerMeshRef.current.rotation.y += delta * 0.3;
    }
    if (innerMeshRef.current) {
      innerMeshRef.current.rotation.y -= delta * 0.4;
      innerMeshRef.current.rotation.z += delta * 0.2;
    }
    if (ringRef.current) {
      ringRef.current.rotation.z += delta * 0.15;
    }
  });

  return (
    <Float speed={2} rotationIntensity={0.5} floatIntensity={1.5}>
      <group>
        {/* Ambient Lights */}
        <ambientLight intensity={0.6} />
        <directionalLight position={[10, 10, 5]} intensity={1.5} color="#4668fa" />
        <pointLight position={[-10, -10, -5]} intensity={1.2} color="#00f5d4" />

        {/* Outer Wireframe Icosahedron */}
        <mesh ref={outerMeshRef}>
          <icosahedronGeometry args={[2.2, 1]} />
          <meshStandardMaterial
            color="#4668fa"
            wireframe
            roughness={0.2}
            metalness={0.8}
            emissive="#1e2cb0"
            emissiveIntensity={0.4}
          />
        </mesh>

        {/* Inner Organic Distorted Core */}
        <Sphere ref={innerMeshRef} args={[1.2, 64, 64]}>
          <MeshDistortMaterial
            color="#9d4edd"
            attach="material"
            distort={0.4}
            speed={2}
            roughness={0.3}
            metalness={0.9}
          />
        </Sphere>

        {/* Orbiting Quantum Ring */}
        <mesh ref={ringRef} rotation={[Math.PI / 3, 0, 0]}>
          <torusGeometry args={[3.2, 0.04, 16, 100]} />
          <meshBasicMaterial color="#00f5d4" transparent opacity={0.7} />
        </mesh>
      </group>
    </Float>
  );
}
