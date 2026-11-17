import { Suspense } from 'react';
import { Canvas } from '@react-three/fiber';
import { Hero3DVisual } from './Hero3DVisual';

interface SceneCanvasProps {
  className?: string;
}

export function SceneCanvas({ className = 'h-full w-full' }: SceneCanvasProps) {
  return (
    <div className={className}>
      <Canvas
        camera={{ position: [0, 0, 6], fov: 45 }}
        gl={{ antialias: true, alpha: true, powerPreference: 'high-performance' }}
      >
        <Suspense fallback={null}>
          <Hero3DVisual />
        </Suspense>
      </Canvas>
    </div>
  );
}
