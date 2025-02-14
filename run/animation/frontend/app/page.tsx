'use client';

import { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader, GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Slider } from "@/components/ui/slider";
import { CameraIcon, Maximize2Icon, RotateCcw } from "lucide-react";

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [zoom, setZoom] = useState([5]); // Start with zoom level 5
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelRef = useRef<THREE.Group | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const initThreeJS = () => {
      const container = containerRef.current!;
      
      // Scene
      const scene = new THREE.Scene();
      scene.background = new THREE.Color(0xf0f0f0);
      sceneRef.current = scene;

      // Camera
      const camera = new THREE.PerspectiveCamera(
        75,
        container.clientWidth / container.clientHeight,
        0.1,
        1000
      );
      camera.position.set(0, 2, 10); // Adjusted default camera position
      cameraRef.current = camera;

      // Renderer
      const renderer = new THREE.WebGLRenderer({ antialias: true });
      renderer.setSize(container.clientWidth, container.clientHeight);
      renderer.setPixelRatio(window.devicePixelRatio);
      container.innerHTML = '';
      container.appendChild(renderer.domElement);
      rendererRef.current = renderer;

      // Controls
      const controls = new OrbitControls(camera, renderer.domElement);
      controls.enableDamping = true;
      controls.dampingFactor = 0.05;
      controls.minDistance = 1;
      controls.maxDistance = 100;
      controlsRef.current = controls;

      // Lights
      const ambientLight = new THREE.AmbientLight(0xffffff, 0.5);
      scene.add(ambientLight);
      const directionalLight = new THREE.DirectionalLight(0xffffff, 0.5);
      directionalLight.position.set(0, 1, 0);
      scene.add(directionalLight);

      // Animation loop
      const animate = () => {
        requestAnimationFrame(animate);
        controls.update();
        renderer.render(scene, camera);
      };
      animate();

      // Handle resize
      const handleResize = () => {
        if (!container) return;
        camera.aspect = container.clientWidth / container.clientHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(container.clientWidth, container.clientHeight);
      };
      window.addEventListener('resize', handleResize);

      return () => {
        window.removeEventListener('resize', handleResize);
        renderer.dispose();
      };
    };

    initThreeJS();
  }, []);

  const resetCamera = () => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(0, 2, 10);
      cameraRef.current.lookAt(0, 0, 0);
      controlsRef.current.target.set(0, 0, 0);
      controlsRef.current.update();
    }
  };

  const fitModelToView = () => {
    if (!modelRef.current || !cameraRef.current || !controlsRef.current) return;

    const box = new THREE.Box3().setFromObject(modelRef.current);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    const maxDim = Math.max(size.x, size.y, size.z);
    const fov = cameraRef.current.fov * (Math.PI / 180);
    const cameraDistance = maxDim / (2 * Math.tan(fov / 2));

    cameraRef.current.position.copy(center);
    cameraRef.current.position.z += cameraDistance * 1.5; // Add some padding
    cameraRef.current.lookAt(center);
    controlsRef.current.target.copy(center);
    controlsRef.current.update();
  };

  const handleZoomChange = (value: number[]) => {
    setZoom(value);
    if (cameraRef.current) {
      const newPosition = cameraRef.current.position.clone().normalize().multiplyScalar(value[0]);
      cameraRef.current.position.copy(newPosition);
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setStatus('Generating animation...');
    setError('');

    try {
      const response = await fetch('/api/generate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText);
      }

      setStatus('Loading animation...');

      const arrayBuffer = await response.arrayBuffer();
      const loader = new GLTFLoader();
      
      loader.parse(
        arrayBuffer,
        '',
        (gltf: GLTF) => {
          if (!sceneRef.current) return;
          
          // Remove existing model
          sceneRef.current.children.forEach(child => {
            if (child.type === 'Group') sceneRef.current?.remove(child);
          });

          modelRef.current = gltf.scene; // Store reference to the model
          sceneRef.current.add(gltf.scene);

          // Center and scale the model
          const box = new THREE.Box3().setFromObject(gltf.scene);
          const center = box.getCenter(new THREE.Vector3());
          const size = box.getSize(new THREE.Vector3());

          const maxDim = Math.max(size.x, size.y, size.z);
          const scale = 1 / maxDim; // Less aggressive scaling
          gltf.scene.scale.setScalar(scale);

          gltf.scene.position.sub(center.multiplyScalar(scale));
          
          fitModelToView(); // Auto-fit the model when loaded
          setStatus('Animation loaded successfully!');
        },
        (error) => {
          console.error('Error loading GLB:', error);
          setError(`Error loading animation: ${error.message || 'Failed to load GLB file'}`);
        }
      );
    } catch (error) {
      console.error('Error:', error);
      if (error instanceof Error) {
        setError(`Error: ${error.message}`);
      } else {
        setError('An unknown error occurred');
      }
    }
  };

  return (
    <main className="container mx-auto p-4">
      <h1 className="text-4xl font-bold mb-8">Animation Generator</h1>
      
      <Card className="mb-8">
        <CardContent className="pt-6">
          <form onSubmit={handleSubmit}>
            <Textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Describe your animation..."
              className="mb-4"
              rows={4}
            />
            <Button type="submit">Generate Animation</Button>
          </form>
        </CardContent>
      </Card>

      {status && (
        <Alert className="mb-4">
          <AlertDescription>{status}</AlertDescription>
        </Alert>
      )}

      {error && (
        <Alert variant="destructive" className="mb-4">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="mb-4 flex gap-4">
        <Button variant="outline" onClick={resetCamera} className="flex items-center gap-2">
          <RotateCcw className="h-4 w-4" />
          Reset Camera
        </Button>
        <Button variant="outline" onClick={fitModelToView} className="flex items-center gap-2">
          <Maximize2Icon className="h-4 w-4" />
          Fit to View
        </Button>
      </div>

      <div className="mb-4 flex items-center gap-4">
        <CameraIcon className="h-4 w-4" />
        <div className="flex-grow">
          <Slider
            value={zoom}
            onValueChange={handleZoomChange}
            min={1}
            max={20}
            step={0.1}
          />
        </div>
      </div>

      <div ref={containerRef} className="w-full h-[600px] bg-gray-100 rounded-lg" />
    </main>
  );
}