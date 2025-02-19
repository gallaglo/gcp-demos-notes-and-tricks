'use client';

import { useState, useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader, GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Separator } from "@/components/ui/separator";
import { Maximize2, RotateCcw, PlayIcon, PauseIcon, Sparkles, Loader2 } from "lucide-react";
import { retryWithBackoff } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const EXAMPLE_PROMPTS = [
  "planets orbiting sun in solar system",
  "tumbling cube",
  "bouncing ball"
];

export default function Home() {
  const [prompt, setPrompt] = useState('');
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(true);
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelRef = useRef<THREE.Group | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clockRef = useRef<THREE.Clock | null>(null);
  const animationRef = useRef<THREE.AnimationAction | null>(null);
  const animationFrameIdRef = useRef<number | null>(null);

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
      camera.position.set(0, 2, 10);
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

      // Clock for animation
      const clock = new THREE.Clock();
      clockRef.current = clock;

      // Animation loop
      const animate = () => {
        animationFrameIdRef.current = requestAnimationFrame(animate);

        if (mixerRef.current && isAnimationPlaying) {
          const delta = clockRef.current!.getDelta();
          mixerRef.current.update(delta);
        }

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
        if (animationFrameIdRef.current) {
          cancelAnimationFrame(animationFrameIdRef.current);
        }
      };
    };

    return initThreeJS();
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
    cameraRef.current.position.z += cameraDistance * 1.5;
    cameraRef.current.lookAt(center);
    controlsRef.current.target.copy(center);
    controlsRef.current.update();
  };

  const toggleAnimation = () => {
    if (animationRef.current) {
      setIsAnimationPlaying(!isAnimationPlaying);
      if (isAnimationPlaying) {
        animationRef.current.paused = true;
      } else {
        animationRef.current.paused = false;
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setIsLoading(true);
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
  
      // Add a promise wrapper around the GLTF loader
      const loadModel = () => new Promise((resolve, reject) => {
        loader.parse(
          arrayBuffer,
          '',
          (gltf: GLTF) => resolve(gltf),
          (error) => reject(error)
        );
      });
  
      // Use retryWithBackoff for model loading
      const gltf = await retryWithBackoff(
        () => loadModel() as Promise<GLTF>,
        {
          maxAttempts: 3,
          initialDelay: 1000,
          maxDelay: 5000,
        },
        (context) => {
          setStatus(`Retrying animation load... (Attempt ${context.attempt}/${context.maxAttempts})`);
        }
      );
  
      if (!sceneRef.current) return;
  
      // Remove existing model and mixer
      if (modelRef.current) {
        sceneRef.current.remove(modelRef.current);
      }
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
      }
  
      modelRef.current = gltf.scene;
      sceneRef.current.add(gltf.scene);
  
      // Center and scale the model
      const box = new THREE.Box3().setFromObject(gltf.scene);
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
  
      const maxDim = Math.max(size.x, size.y, size.z);
      const scale = 1 / maxDim;
      gltf.scene.scale.setScalar(scale);
  
      gltf.scene.position.sub(center.multiplyScalar(scale));
  
      // Setup animation mixer
      const mixer = new THREE.AnimationMixer(gltf.scene);
      mixerRef.current = mixer;
  
      // Play first animation if available
      if (gltf.animations.length > 0) {
        const action = mixer.clipAction(gltf.animations[0]);
        action.play();
        animationRef.current = action;
        setIsAnimationPlaying(true);
      }
  
      fitModelToView();
      setStatus('Animation loaded successfully!');
    } catch (error) {
      console.error('Error:', error);
      if (error instanceof Error) {
        setError(`Error: ${error.message}`);
      } else {
        setError('An unknown error occurred');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <div className="container flex flex-col gap-4 p-4 lg:p-8">
        <div className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Animation Generator</h1>
        </div>
        <Separator />
      </div>
      
      <div className="container grid flex-1 gap-6 md:grid-cols-[380px_1fr] lg:p-8">
        {/* Left Panel - Controls */}
        <div className="flex flex-col gap-4">
          <div className="flex flex-col gap-4">
            <Card>
              <CardContent className="pt-6">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="flex flex-col gap-2">
                    <div className="flex justify-between items-center">
                      <label className="text-sm text-muted-foreground">
                        Enter prompt or select an example
                      </label>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="outline" size="sm">
                            <Sparkles className="mr-2 h-4 w-4" />
                            Examples
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          {EXAMPLE_PROMPTS.map((examplePrompt) => (
                            <DropdownMenuItem
                              key={examplePrompt}
                              onClick={() => setPrompt(examplePrompt)}
                            >
                              {examplePrompt}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                    <Textarea
                      value={prompt}
                      onChange={(e) => setPrompt(e.target.value)}
                      placeholder="Describe your animation..."
                      className="min-h-[150px]"
                    />
                  </div>
                  <Button type="submit" className="w-full" disabled={isLoading}>
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Generating...
                      </>
                    ) : (
                      'Generate Animation'
                    )}
                  </Button>
                </form>
              </CardContent>
            </Card>

            {status && (
              <Alert>
                <AlertDescription>{status}</AlertDescription>
              </Alert>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Card>
              <CardContent className="pt-6 space-y-4">
                <div className="space-y-4">
                  <div className="flex gap-2">
                    <Button 
                      variant="outline" 
                      onClick={resetCamera} 
                      className="flex-1"
                    >
                      <RotateCcw className="mr-2 h-4 w-4" />
                      Reset Camera
                    </Button>
                    <Button 
                      variant="outline" 
                      onClick={fitModelToView}
                      className="flex-1"
                    >
                      <Maximize2 className="mr-2 h-4 w-4" />
                      Fit to View
                    </Button>
                  </div>
                  
                  {animationRef.current && (
                    <Button 
                      variant="outline" 
                      onClick={toggleAnimation}
                      className="w-full"
                    >
                      {isAnimationPlaying ? (
                        <>
                          <PauseIcon className="mr-2 h-4 w-4" />
                          Pause Animation
                        </>
                      ) : (
                        <>
                          <PlayIcon className="mr-2 h-4 w-4" />
                          Play Animation
                        </>
                      )}
                    </Button>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* Right Panel - Preview */}
        <div className="flex flex-col gap-4">
          <Card className="flex-1">
            <CardContent className="p-0">
              <div ref={containerRef} className="w-full h-[calc(100vh-12rem)] rounded-lg" />
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}