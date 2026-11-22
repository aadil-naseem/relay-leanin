import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { PerformanceMonitor } from '@react-three/drei'
import { BufferGeometry, Float32BufferAttribute, Fog, Vector3 } from 'three'

function cssToken(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

function clamp(value) {
  return Math.max(0, Math.min(1, value))
}

export default function HeroScene({ tier, pointer, progress = 0, partners = [], onDecline }) {
  const colors = useMemo(() => ({
    deep: cssToken('--c-deep'),
    midnight: cssToken('--c-midnight'),
    navy: cssToken('--c-navy'),
    ocean: cssToken('--c-ocean'),
    sky: cssToken('--c-sky'),
    sun: cssToken('--c-sun'),
    pale: cssToken('--c-pale'),
    cream: cssToken('--c-cream'),
  }), [])
  const bays = useMemo(() => {
    const rows = tier === 'full' ? 4 : 2
    const columns = tier === 'full' ? 6 : 4
    return Array.from({ length: rows * columns }, (_, index) => {
      const row = Math.floor(index / columns)
      const column = index % columns
      return {
        key: `${row}-${column}`,
        x: (column - (columns - 1) / 2) * 3.4 + (row % 2 ? 0.65 : 0),
        z: -row * 3.5,
        lit: row === 1 && column === Math.floor(columns / 2),
        zone: row >= 1 && column < Math.ceil(columns / 2),
        sequence: (row * columns + column) % 5,
      }
    })
  }, [tier])
  const threatProgress = clamp((progress - 0.34) / 0.26)
  const relayProgress = clamp((progress - 0.6) / 0.26)
  const networkScale = 1 - relayProgress * 0.76

  return (
    <Canvas
      camera={{ position: [16, 8, 22], fov: 34, near: 0.1, far: 100 }}
      dpr={tier === 'full' ? [1, 1.5] : 1}
      gl={{ alpha: true, antialias: tier === 'full', powerPreference: 'low-power' }}
      onCreated={({ gl, scene }) => {
        gl.setClearColor(0x000000, 0)
        scene.fog = new Fog(colors.midnight, 30, 74)
      }}
      fallback={<div className="landing-webgl-fallback" />}
    >
      <PerformanceMonitor onDecline={onDecline} />
      <ambientLight intensity={1.25} />
      <hemisphereLight args={[colors.sky, colors.deep, 0.5]} />
      <directionalLight color={colors.pale} intensity={1.5} position={[-5, 12, 10]} />
      <directionalLight color={colors.sky} intensity={0.7} position={[8, 7, -10]} />
      <CameraSway pointer={pointer} progress={progress} />
      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -0.08, -2]} receiveShadow>
        <planeGeometry args={[56, 50]} />
        <meshStandardMaterial
          color={colors.navy}
          emissive={colors.navy}
          emissiveIntensity={0.08}
          roughness={1}
          metalness={0}
          transparent
          opacity={0.74}
        />
      </mesh>
      <ThreatWater progress={threatProgress} color={colors.sky} />
      <Rain tier={tier} progress={threatProgress} color={colors.pale} />
      <DependencyTrace progress={clamp((progress - 0.08) / 0.26)} color={colors.sun} />
      <gridHelper
        args={[42, 28, colors.sky, colors.cream]}
        position={[0, 0.035, 0]}
        visible={relayProgress > 0.04}
      />
      <group scale={networkScale}>
        {bays.map((bay) => {
          const down = bay.zone
            ? clamp((threatProgress - bay.sequence * 0.13) / 0.25)
            : 0
          return (
            <Bay
              key={bay.key}
              x={bay.x}
              z={bay.z}
              lit={bay.lit}
              zone={bay.zone}
              down={down}
              colors={colors}
            />
          )
        })}
        <Crane colors={colors} />
        <Containers colors={colors} />
      </group>
      <RelayNodes progress={relayProgress} partners={partners} colors={colors} />
    </Canvas>
  )
}

function CameraSway({ pointer, progress }) {
  const target = useRef(new Vector3())
  const lookTarget = useRef(new Vector3())
  const desiredLookTarget = useRef(new Vector3())
  useFrame(({ camera }, delta) => {
    const pose = cameraPose(progress)
    const sway = progress < 0.08 ? 1 : 0
    target.current.set(pose.position[0] + pointer.x * 0.65 * sway, pose.position[1] + pointer.y * 0.35 * sway, pose.position[2])
    camera.position.lerp(target.current, 1 - Math.exp(-delta * 3.0))
    desiredLookTarget.current.set(...pose.target)
    lookTarget.current.lerp(desiredLookTarget.current, 1 - Math.exp(-delta * 2.6))
    camera.lookAt(lookTarget.current)
  })
  return null
}

function cameraPose(progress) {
  const poses = [
    { at: 0, position: [16, 7, 20], target: [0, 1, 0] },
    { at: 0.08, position: [16, 7, 20], target: [0, 1, 0] },
    { at: 0.34, position: [2, 2.2, 3], target: [4, 3, 8] },
    { at: 0.6, position: [12, 9, 14], target: [0, 1, 0] },
    { at: 0.86, position: [0, 38, 6], target: [0, 0, 0] },
    { at: 1, position: [18, 10, 24], target: [0, 1, 0] },
  ]
  for (let index = 0; index < poses.length - 1; index += 1) {
    const first = poses[index]
    const second = poses[index + 1]
    if (progress <= second.at) {
      const mix = clamp((progress - first.at) / (second.at - first.at))
      return {
        position: first.position.map((value, axis) => value + (second.position[axis] - value) * mix),
        target: first.target.map((value, axis) => value + (second.target[axis] - value) * mix),
      }
    }
  }
  return poses[poses.length - 1]
}

function Bay({ x, z, lit, colors, zone, down = 0 }) {
  const lightRef = useRef()
  useFrame(({ clock }) => {
    if (lightRef.current && lit) lightRef.current.intensity = 1.1 + Math.sin(clock.elapsedTime * 1.15) * 0.14
  })
  const bodyColor = down > 0.55 ? colors.deep : lit ? colors.ocean : colors.navy
  const glow = lit ? 0.2 : zone ? 0.15 * (1 - down) : 0.11

  return (
    <group position={[x, 0, z]}>
      <mesh position={[-0.08, 0.82, 0]} castShadow receiveShadow>
        <boxGeometry args={[2.35, 1.64, 2.15]} />
        <meshStandardMaterial
          color={bodyColor}
          emissive={colors.navy}
          emissiveIntensity={glow}
          roughness={0.92}
        />
      </mesh>
      <mesh position={[-0.08, 1.69, 0]} castShadow>
        <boxGeometry args={[2.55, 0.18, 2.32]} />
        <meshStandardMaterial color={lit ? colors.sun : colors.sky} emissive={colors.ocean} emissiveIntensity={0.12} roughness={0.8} />
      </mesh>
      <mesh position={[-0.08, 1.25, 1.083]}>
        <boxGeometry args={[0.68, 0.82, 0.04]} />
        <meshStandardMaterial
          color={lit ? colors.sun : colors.midnight}
          emissive={lit ? colors.sun : colors.deep}
          emissiveIntensity={lit ? 0.45 : 0.04}
          roughness={0.55}
        />
      </mesh>
      <mesh position={[-0.72, 1.36, 1.084]}>
        <boxGeometry args={[0.4, 0.14, 0.035]} />
        <meshStandardMaterial color={lit ? colors.pale : colors.navy} emissive={lit ? colors.sun : colors.deep} emissiveIntensity={lit ? 0.5 : 0} />
      </mesh>
      {lit && <pointLight ref={lightRef} color={colors.sun} intensity={1.1} distance={7.5} position={[0, 1.65, 1.4]} />}
    </group>
  )
}

function ThreatWater({ progress, color }) {
  const visibility = progress * 0.24
  return (
    <mesh
      rotation={[-Math.PI / 2, 0, 0]}
      position={[0, -0.02 + progress * 0.5, -3.2]}
      visible={progress > 0.02}
    >
      <planeGeometry args={[13, 9]} />
      <meshBasicMaterial color={color} transparent opacity={visibility} depthWrite={false} />
    </mesh>
  )
}

function Rain({ tier, progress, color }) {
  const count = tier === 'full' ? 1_400 : 450
  const geometry = useMemo(() => {
    const positions = new Float32Array(count * 3)
    for (let index = 0; index < count; index += 1) {
      positions[index * 3] = (((index * 37) % 997) / 997 - 0.5) * 34
      positions[index * 3 + 1] = ((index * 53) % 991) / 991 * 17
      positions[index * 3 + 2] = (((index * 71) % 983) / 983 - 0.5) * 30
    }
    const buffer = new BufferGeometry()
    buffer.setAttribute('position', new Float32BufferAttribute(positions, 3))
    return buffer
  }, [count])
  useEffect(() => () => geometry.dispose(), [geometry])
  useFrame((_, delta) => {
    if (progress <= 0.01) return
    const position = geometry.getAttribute('position')
    for (let index = 0; index < count; index += 1) {
      const offset = index * 3 + 1
      position.array[offset] -= delta * (7 + (index % 9))
      if (position.array[offset] < -1) position.array[offset] = 16
    }
    position.needsUpdate = true
  })
  return (
    <points geometry={geometry} frustumCulled={false} visible={progress > 0.01}>
      <pointsMaterial color={color} size={0.045} transparent opacity={progress * 0.45} depthWrite={false} />
    </points>
  )
}

function DependencyTrace({ progress, color }) {
  const geometry = useMemo(() => {
    const buffer = new BufferGeometry()
    buffer.setFromPoints([
      new Vector3(-7, 1.2, 4),
      new Vector3(-4, 1.5, 2),
      new Vector3(-1.5, 1.7, 1),
      new Vector3(0, 2, 0),
    ])
    return buffer
  }, [])
  useEffect(() => () => geometry.dispose(), [geometry])
  useFrame(() => geometry.setDrawRange(0, Math.ceil(progress * 4)))
  return (
    <line geometry={geometry} visible={progress > 0.01}>
      <lineBasicMaterial color={color} transparent opacity={0.95} linewidth={2} />
    </line>
  )
}

function RelayNodes({ progress, partners, colors }) {
  if (progress <= 0.01) return null
  const partnerX = [-10, -3.3, 3.3, 10]
  const nodes = [
    { name: 'OWNER', x: -1.5, z: 1, status: 'OWNER' },
    ...partners.slice(0, 4).map((partner, index) => ({
      name: partner.name,
      x: partnerX[index],
      z: -10,
      status: partner.status,
    })),
  ]
  const tint = (status) => {
    if (status === 'READY') return colors.sky
    if (status === 'EXCLUDED') return colors.sun
    return colors.pale
  }
  return (
    <group>
      {nodes.slice(1).map((node) => (
        <group key={node.name} position={[node.x, 0.35 + progress * 0.4, node.z]}>
          <mesh>
            <sphereGeometry args={[0.32, 12, 8]} />
            <meshBasicMaterial color={tint(node.status)} />
          </mesh>
          <pointLight color={tint(node.status)} intensity={0.5} distance={2.5} />
        </group>
      ))}
      {nodes.slice(1).map((node) => (
        <line key={`arc-${node.name}`} visible={progress > 0.22}>
          <bufferGeometry>
            <bufferAttribute
              attach="attributes-position"
              count={3}
              array={new Float32Array([-1.5, 1.8, 1, node.x / 2, 3.2, -4, node.x, 0.8, node.z])}
              itemSize={3}
            />
          </bufferGeometry>
          <lineBasicMaterial color={tint(node.status)} transparent opacity={Math.min(0.85, progress)} />
        </line>
      ))}
    </group>
  )
}

function Crane({ colors }) {
  return (
    <group position={[-0.5, 0, 1.3]}>
      <mesh position={[-5.8, 3.5, -1]} castShadow>
        <boxGeometry args={[0.16, 7, 0.18]} />
        <meshStandardMaterial color={colors.navy} />
      </mesh>
      <mesh position={[5.8, 3.5, -1]} castShadow>
        <boxGeometry args={[0.16, 7, 0.18]} />
        <meshStandardMaterial color={colors.navy} />
      </mesh>
      <mesh position={[0, 6.95, -1]} castShadow>
        <boxGeometry args={[12, 0.2, 0.24]} />
        <meshStandardMaterial color={colors.pale} roughness={0.82} />
      </mesh>
      <mesh position={[1.5, 6.65, -0.85]}>
        <boxGeometry args={[1.1, 0.38, 0.38]} />
        <meshStandardMaterial color={colors.sun} emissive={colors.sun} emissiveIntensity={0.12} />
      </mesh>
      <mesh position={[1.5, 5.25, -0.85]}>
        <boxGeometry args={[0.035, 2.45, 0.035]} />
        <meshStandardMaterial color={colors.pale} />
      </mesh>
      <mesh position={[1.5, 4.1, -0.85]}>
        <boxGeometry args={[0.45, 0.12, 0.12]} />
        <meshStandardMaterial color={colors.sun} />
      </mesh>
    </group>
  )
}

function Containers({ colors }) {
  return (
    <group>
      {[-1, 1].map((side) => (
        <group key={side} position={[side * 8, 0, -4.2]}>
          <mesh position={[0, 0.58, 0]} castShadow>
            <boxGeometry args={[2.4, 1.16, 1.35]} />
            <meshStandardMaterial color={side < 0 ? colors.ocean : colors.navy} emissive={colors.navy} emissiveIntensity={0.12} roughness={0.9} />
          </mesh>
          <mesh position={[0, 1.78, 0]} castShadow>
            <boxGeometry args={[2.4, 1.16, 1.35]} />
            <meshStandardMaterial color={colors.midnight} emissive={colors.navy} emissiveIntensity={0.1} roughness={0.9} />
          </mesh>
          <mesh position={[0, 1.17, 0.68]}>
            <boxGeometry args={[2.3, 0.035, 0.035]} />
            <meshStandardMaterial color={colors.pale} />
          </mesh>
        </group>
      ))}
    </group>
  )
}
