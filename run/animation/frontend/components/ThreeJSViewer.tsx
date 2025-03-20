'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader, GLTF } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { Button } from "@/components/ui/button";
import { Maximize2, RotateCcw, PlayIcon, PauseIcon } from "lucide-react";

interface ThreeJSViewerProps {
  signedUrl: string | null;
  initialIsPlaying?: boolean;
  onPlayingChange?: (playing: boolean) => void;
}

export default function ThreeJSViewer({ 
  signedUrl, 
  initialIsPlaying = true,
  onPlayingChange
}: ThreeJSViewerProps) {
  // Manage playing state internally
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(initialIsPlaying);
  const [isMounted, setIsMounted] = useState(false);
  
  // Set isMounted to true after component mounts
  useEffect(() => {
    setIsMounted(true);
    return () => setIsMounted(false);
  }, []);
  
  // Sync state changes with parent component if callback provided
  const handlePlayingChange = useCallback((playing: boolean) => {
    setIsAnimationPlaying(playing);
    if (onPlayingChange) {
      onPlayingChange(playing);
    }
  }, [onPlayingChange]);
  
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

  // Define fitModelToView before using it in useEffect
  const fitModelToView = useCallback(() => {
    if (!isMounted || !modelRef.current || !cameraRef.current || !controlsRef.current) return;

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
  }, [isMounted]);

  const resetCamera = useCallback(() => {
    if (!isMounted || !cameraRef.current || !controlsRef.current) return;
    
    cameraRef.current.position.set(0, 2, 10);
    cameraRef.current.lookAt(0, 0, 0);
    controlsRef.current.target.set(0, 0, 0);
    controlsRef.current.update();
  }, [isMounted]);

  // Initialize ThreeJS
  useEffect(() => {
    if (!isMounted || !containerRef.current) return;

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
  }, [isMounted]);
  
  // Animation loop in separate useEffect to handle isAnimationPlaying dependency
  useEffect(() => {
    if (!isMounted || !cameraRef.current || !sceneRef.current || !rendererRef.current || !controlsRef.current) return;
    
    const animate = () => {
      animationFrameIdRef.current = requestAnimationFrame(animate);
  
      if (mixerRef.current && isAnimationPlaying) {
        const delta = clockRef.current!.getDelta();
        mixerRef.current.update(delta);
      }
  
      controlsRef.current!.update();
      rendererRef.current!.render(sceneRef.current!, cameraRef.current!);
    };
    
    animate();
    
    return () => {
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
        animationFrameIdRef.current = null;
      }
    };
  }, [isAnimationPlaying, isMounted]);

  // Effect to load the model when signedUrl changes
  useEffect(() => {
    if (!isMounted || !signedUrl || !sceneRef.current) return;
    
    const loadModel = async () => {
      try {
        // Fetch the GLB file
        const response = await fetch(signedUrl);
        if (!response.ok) {
          throw new Error(`Failed to fetch model: ${response.statusText}`);
        }
        
        const arrayBuffer = await response.arrayBuffer();
        const loader = new GLTFLoader();
        
        // Load the model
        const gltf = await new Promise<GLTF>((resolve, reject) => {
          loader.parse(
            arrayBuffer,
            '',
            (gltf) => resolve(gltf),
            (error) => reject(error)
          );
        });
        
        // Remove existing model and mixer
        if (modelRef.current && sceneRef.current) {
          sceneRef.current.remove(modelRef.current);
        }
        if (mixerRef.current) {
          mixerRef.current.stopAllAction();
        }

        // Update model reference
        modelRef.current = gltf.scene;

        // Add new model to scene (with null check)
        if (sceneRef.current) {
          sceneRef.current.add(gltf.scene);
        }
        
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
          handlePlayingChange(true);
        }
        
        fitModelToView();
      } catch (error) {
        console.error('Error loading model:', error);
      }
    };
    
    loadModel();
  }, [signedUrl, handlePlayingChange, isMounted, fitModelToView]);

  const toggleAnimation = useCallback(() => {
    if (!isMounted || !animationRef.current) return;
    
    const newPlayingState = !isAnimationPlaying;
    handlePlayingChange(newPlayingState);
    
    if (isAnimationPlaying) {
      animationRef.current.paused = true;
    } else {
      animationRef.current.paused = false;
    }
  }, [isMounted, isAnimationPlaying, handlePlayingChange]);

  // Handle server-side rendering by rendering only a placeholder div initially
  if (!isMounted) {
    return <div className="w-full h-[calc(100vh-12rem)] rounded-lg bg-gray-100"></div>;
  }

  return (
    <div className="relative w-full h-full">
      <div ref={containerRef} className="w-full h-[calc(100vh-12rem)] rounded-lg" />
      
      {/* Controls overlay */}
      <div className="absolute bottom-4 left-4 right-4 flex gap-2">
        <Button 
          variant="outline" 
          onClick={resetCamera} 
          className="flex-1 bg-white bg-opacity-80 hover:bg-white"
        >
          <RotateCcw className="mr-2 h-4 w-4" />
          Reset Camera
        </Button>
        
        <Button 
          variant="outline" 
          onClick={fitModelToView}
          className="flex-1 bg-white bg-opacity-80 hover:bg-white"
        >
          <Maximize2 className="mr-2 h-4 w-4" />
          Fit to View
        </Button>
        
        {animationRef.current && (
          <Button 
            variant="outline" 
            onClick={toggleAnimation}
            className="flex-1 bg-white bg-opacity-80 hover:bg-white"
          >
            {isAnimationPlaying ? (
              <>
                <PauseIcon className="mr-2 h-4 w-4" />
                Pause
              </>
            ) : (
              <>
                <PlayIcon className="mr-2 h-4 w-4" />
                Play
              </>
            )}
          </Button>
        )}
      </div>
    </div>
  );
}