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
  onError?: (error: string) => void;
  onStatusChange?: (status: string) => void;
}

export default function ThreeJSViewer({ 
  signedUrl, 
  initialIsPlaying = true,
  onPlayingChange,
  onError,
  onStatusChange
}: ThreeJSViewerProps) {
  // State management
  const [isAnimationPlaying, setIsAnimationPlaying] = useState(initialIsPlaying);
  const [isMounted, setIsMounted] = useState(false);
  
  // Refs for tracking already processed URLs to prevent duplicate loading
  const loadedUrlRef = useRef<string | null>(null);
  const isLoadingRef = useRef(false);
  
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
  
  // Update status
  const updateStatus = useCallback((status: string) => {
    console.log("Status update:", status);
    if (onStatusChange) {
      onStatusChange(status);
    }
  }, [onStatusChange]);

  // Handle errors
  const handleError = useCallback((error: string) => {
    console.error("Error in ThreeJSViewer:", error);
    if (onError) {
      onError(error);
    }
  }, [onError]);
  
  // Refs
  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const modelRef = useRef<THREE.Object3D | null>(null);
  const mixerRef = useRef<THREE.AnimationMixer | null>(null);
  const clockRef = useRef<THREE.Clock | null>(null);
  const animationRef = useRef<THREE.AnimationAction | null>(null);
  const animationFrameIdRef = useRef<number | null>(null);
  const renderCountRef = useRef(0);

  // Fit model to view
  const fitModelToView = useCallback(() => {
    if (!modelRef.current || !cameraRef.current || !controlsRef.current) return;

    try {
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
    } catch (e) {
      console.error("Error in fitModelToView:", e);
    }
  }, []);

  // Reset camera to default position
  const resetCamera = useCallback(() => {
    if (!cameraRef.current || !controlsRef.current) return;
    
    try {
      cameraRef.current.position.set(0, 2, 10);
      cameraRef.current.lookAt(0, 0, 0);
      controlsRef.current.target.set(0, 0, 0);
      controlsRef.current.update();
    } catch (e) {
      console.error("Error in resetCamera:", e);
    }
  }, []);

  // Toggle animation playback
  const toggleAnimation = useCallback(() => {
    console.log("Toggle animation called. Current state:", isAnimationPlaying);
    
    if (!animationRef.current || !clockRef.current) {
      console.warn("No animation or clock to toggle");
      return;
    }
    
    // Toggle the playing state
    const newPlayingState = !isAnimationPlaying;
    console.log("Setting new animation state:", newPlayingState);
    
    // Update UI state
    handlePlayingChange(newPlayingState);
    
    // Important: Reset the clock delta to prevent time jumps when resuming
    clockRef.current.getDelta();
    
    // Update animation action's paused state
    animationRef.current.paused = !newPlayingState;
    
    console.log("Animation paused state set to:", animationRef.current.paused);
    
  }, [isAnimationPlaying, handlePlayingChange]);

  // Animation rendering loop (completely separate from the animation state)
  useEffect(() => {
    if (!isMounted || !containerRef.current) return;
    
    console.log("Setting up render loop");
    
    // Reset the clock when play state changes to prevent jumps
    if (clockRef.current) {
      clockRef.current.getDelta(); // Reset the delta time
    }
    
    const render = () => {
      renderCountRef.current++;
      
      // Log every 60 frames to avoid console spam
      if (renderCountRef.current % 60 === 0) {
        console.log("Render frame:", renderCountRef.current, "Animation playing:", isAnimationPlaying);
      }
      
      // Only update the animation if playing
      if (mixerRef.current && isAnimationPlaying) {
        const delta = clockRef.current?.getDelta() || 0;
        mixerRef.current.update(delta);
      } else if (clockRef.current) {
        // Important: still call getDelta even when paused to "consume" the time
        // This prevents accumulation of time during pause
        clockRef.current.getDelta();
      }
      
      if (controlsRef.current) {
        controlsRef.current.update();
      }
      
      if (rendererRef.current && sceneRef.current && cameraRef.current) {
        rendererRef.current.render(sceneRef.current, cameraRef.current);
      }
      
      animationFrameIdRef.current = requestAnimationFrame(render);
    };
    
    // Start the render loop
    render();
    
    // Cleanup the render loop on unmount
    return () => {
      if (animationFrameIdRef.current) {
        cancelAnimationFrame(animationFrameIdRef.current);
        animationFrameIdRef.current = null;
      }
    };
  }, [isMounted, isAnimationPlaying]);

  // Initialize ThreeJS
  useEffect(() => {
    if (!isMounted || !containerRef.current) return;

    console.log("Initializing ThreeJS");
    const container = containerRef.current!;

    // Clock for animation - start in autoStart=false mode to better control timing
    const clock = new THREE.Clock(false);
    clockRef.current = clock;
    // Start the clock
    clock.start();
    
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

    // Handle resize
    const handleResize = () => {
      if (!container || !cameraRef.current || !rendererRef.current) return;
      cameraRef.current.aspect = container.clientWidth / container.clientHeight;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(container.clientWidth, container.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (rendererRef.current) {
        rendererRef.current.dispose();
      }
    };
  }, [isMounted]);
  
  // Function to load a model
  const loadModel = useCallback(async (url: string) => {
    if (!sceneRef.current) {
      throw new Error('Scene not initialized');
    }
    
    // Skip if already loading this URL
    if (isLoadingRef.current && loadedUrlRef.current === url) {
      console.log('Already loading this URL, skipping duplicate request');
      return;
    }
    
    // Skip if already loaded this URL
    if (loadedUrlRef.current === url) {
      console.log('URL already loaded, skipping');
      return;
    }
    
    // Set loading state
    isLoadingRef.current = true;
    loadedUrlRef.current = url;
    updateStatus('Loading animation...');
    
    try {
      // Use a proxy endpoint to avoid CORS issues
      const response = await fetch('/api/proxy-model', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      });
      
      if (!response.ok) {
        throw new Error(`Failed to fetch model: ${response.statusText}`);
      }
      
      // Get the ArrayBuffer directly from the response
      const arrayBuffer = await response.arrayBuffer();
      
      console.log(`Received ${arrayBuffer.byteLength} bytes of model data`);
      
      // Use GLTFLoader to parse the downloaded data
      const loader = new GLTFLoader();
      
      const gltf = await new Promise<GLTF>((resolve, reject) => {
        loader.parse(
          arrayBuffer,
          '',
          (gltf) => resolve(gltf),
          (error) => {
            console.error("GLTFLoader parse error:", error);
            reject(error);
          }
        );
      });
      
      // Remove existing model and mixer
      if (modelRef.current && sceneRef.current) {
        sceneRef.current.remove(modelRef.current);
        modelRef.current = null;
      }
      
      if (mixerRef.current) {
        mixerRef.current.stopAllAction();
        mixerRef.current = null;
      }
      
      if (animationRef.current) {
        animationRef.current = null;
      }

      // Update model reference and add to scene
      modelRef.current = gltf.scene;
      sceneRef.current.add(gltf.scene);
      console.log("Model added to scene");
      
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
        console.log(`Found ${gltf.animations.length} animations in model`);
        const action = mixer.clipAction(gltf.animations[0]);
        action.play();
        action.paused = !initialIsPlaying;  // Set initial state correctly
        animationRef.current = action;
        
        handlePlayingChange(initialIsPlaying);
        console.log("Animation initialized with playing state:", initialIsPlaying);
      } else {
        console.log("No animations found in model");
      }
      
      fitModelToView();
      updateStatus('Animation loaded successfully!');
    } catch (error) {
      console.error('Error loading model:', error);
      handleError(error instanceof Error ? error.message : 'Unknown error loading model');
      loadedUrlRef.current = null; // Allow retry by clearing the loaded URL
      
      // Create a simple default object on error
      if (sceneRef.current) {
        // Create a simple cube as a fallback
        const geometry = new THREE.BoxGeometry(1, 1, 1);
        const material = new THREE.MeshBasicMaterial({ 
          color: 0xff0000,
          wireframe: true 
        });
        const cube = new THREE.Mesh(geometry, material);
        
        // Remove existing model if any
        if (modelRef.current) {
          sceneRef.current.remove(modelRef.current);
        }
        
        sceneRef.current.add(cube);
        modelRef.current = cube;
        
        // Create a simple rotation animation for the cube
        const mixer = new THREE.AnimationMixer(cube);
        
        // Create a keyframe track that rotates the cube
        const times = [0, 1, 2];
        const rotationValues = [
          0, 0, 0,
          Math.PI, 0, 0,
          Math.PI * 2, 0, 0
        ];
        
        const rotationTrack = new THREE.KeyframeTrack(
          '.rotation[x]',
          times,
          rotationValues
        );
        
        const clip = new THREE.AnimationClip('CubeRotation', 2, [rotationTrack]);
        const action = mixer.clipAction(clip);
        action.play();
        action.paused = !initialIsPlaying;
        
        mixerRef.current = mixer;
        animationRef.current = action;
        
        resetCamera();
      }
    } finally {
      isLoadingRef.current = false;
    }
  }, [fitModelToView, handlePlayingChange, updateStatus, handleError, resetCamera, initialIsPlaying]);
  
  // Effect to load the model when signedUrl changes
  useEffect(() => {
    if (!isMounted || !signedUrl) return;
    
    console.log("Loading model with URL:", signedUrl);
    loadModel(signedUrl).catch(err => {
      console.error("Error in loadModel effect:", err);
    });
    
  }, [isMounted, signedUrl, loadModel]);

  // Handle server-side rendering
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