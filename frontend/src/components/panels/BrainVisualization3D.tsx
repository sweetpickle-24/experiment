import { useRef, useMemo } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, PerspectiveCamera } from '@react-three/drei';
import * as THREE from 'three';
import { useBrainStore } from '../../store/brainStore';

function NeuronParticles() {
  const { snapshot } = useBrainStore();
  const pointsRef = useRef<THREE.Points>(null);

  const { positions, colors, sizes } = useMemo(() => {
    if (!snapshot || !snapshot.neurons) {
      return { positions: new Float32Array(0), colors: new Float32Array(0), sizes: new Float32Array(0) };
    }

    const neurons = snapshot.neurons;
    const pos = new Float32Array(neurons.length * 3);
    const col = new Float32Array(neurons.length * 3);
    const siz = new Float32Array(neurons.length);

    neurons.forEach((neuron, i) => {
      pos[i * 3] = neuron.position[0] / 50000;
      pos[i * 3 + 1] = neuron.position[1] / 50000;
      pos[i * 3 + 2] = neuron.position[2] / 50000;

      const hue = (neuron.phase % (2 * Math.PI)) / (2 * Math.PI);
      const color = new THREE.Color().setHSL(hue, 0.8, 0.6);
      col[i * 3] = color.r;
      col[i * 3 + 1] = color.g;
      col[i * 3 + 2] = color.b;

      siz[i] = Math.max(0.5, neuron.amplitude * 2);
    });

    return { positions: pos, colors: col, sizes: siz };
  }, [snapshot]);

  useFrame(() => {
    if (pointsRef.current && snapshot?.neurons) {
      const colors = pointsRef.current.geometry.attributes.color;
      snapshot.neurons.forEach((neuron, i) => {
        const hue = (neuron.phase % (2 * Math.PI)) / (2 * Math.PI);
        const color = new THREE.Color().setHSL(hue, 0.8, 0.6);
        colors.setXYZ(i, color.r, color.g, color.b);
      });
      colors.needsUpdate = true;
    }
  });

  return (
    <points ref={pointsRef}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-color"
          count={colors.length / 3}
          array={colors}
          itemSize={3}
        />
        <bufferAttribute
          attach="attributes-size"
          count={sizes.length}
          array={sizes}
          itemSize={1}
        />
      </bufferGeometry>
      <pointsMaterial
        size={2}
        vertexColors
        transparent
        opacity={0.8}
        sizeAttenuation
        depthWrite={false}
      />
    </points>
  );
}

function HiveSpheres() {
  const { snapshot } = useBrainStore();

  if (!snapshot || !snapshot.hives) return null;

  return (
    <>
      {snapshot.hives.map((hive) => (
        <mesh
          key={hive.id}
          position={[
            hive.centroid[0] / 50000,
            hive.centroid[1] / 50000,
            hive.centroid[2] / 50000,
          ]}
        >
          <sphereGeometry args={[hive.size / 20000, 16, 16]} />
          <meshBasicMaterial
            color={new THREE.Color().setHSL(Math.random(), 0.6, 0.5)}
            transparent
            opacity={0.2}
            wireframe
          />
        </mesh>
      ))}
    </>
  );
}

export function BrainVisualization3D() {
  return (
    <div className="tahoe-panel p-6">
      <h2 className="text-lg font-semibold mb-4">3D Brain Visualization</h2>
      
      <div className="w-full h-96 bg-black/20 rounded-tahoe-sm overflow-hidden">
        <Canvas>
          <PerspectiveCamera makeDefault position={[5, 5, 5]} />
          <OrbitControls 
            enableDamping 
            dampingFactor={0.05}
            minDistance={2}
            maxDistance={20}
          />
          
          <ambientLight intensity={0.5} />
          <pointLight position={[10, 10, 10]} intensity={1} />
          
          <NeuronParticles />
          <HiveSpheres />
          
          <gridHelper args={[10, 10, 0x444444, 0x222222]} />
        </Canvas>
      </div>
      
      <div className="mt-4 text-xs text-tahoe-textMuted">
        Drag to rotate • Scroll to zoom • Colors represent phase angles
      </div>
    </div>
  );
}
