/**
 * Represents a 3D object in the scene
 */
export interface SceneObject {
  id: string;
  name: string;
  type: string;
  position: [number, number, number];
  rotation: [number, number, number];
  scale: [number, number, number];
  material?: {
    color?: [number, number, number];
    roughness?: number;
    metallic?: number;
    emission?: boolean;
    emissionStrength?: number;
  };
  // Replace Record<string, any> with a more specific type
  properties?: Record<string, string | number | boolean | null | object>;
  animation?: {
    property: string;
    keyframes: {
      frame: number;
      value: number[];
    }[];
  }[];
  visible?: boolean;
}

/**
 * Represents scene settings like frame range, FPS, etc.
 */
export interface SceneSettings {
  frameStart: number;
  frameEnd: number;
  fps: number;
  backgroundColor: [number, number, number];
  environmentLighting?: number;
}

/**
 * Represents the complete state of a scene
 */
export interface SceneState {
  id: string;
  objects: SceneObject[];
  settings: SceneSettings;
  description: string;
  createdAt: string;
  derivedFrom?: string;
  glbUrl?: string;
}

/**
 * Represents values that can be used for scene object edits
 */
export type SceneEditValue = 
  | [number, number, number]  // for position, rotation, scale
  | string                    // for names, types
  | boolean                   // for visibility
  | {                         // for material properties
      color?: [number, number, number];
      roughness?: number;
      metalness?: number; 
      emission?: boolean;
      emissionStrength?: number;
    }
  | null;

/**
 * Represents a change to an existing object
 */
export interface ObjectChange {
  position?: [number, number, number];
  rotation?: [number, number, number];
  scale?: [number, number, number];
  material?: {
    color?: [number, number, number];
    roughness?: number;
    metallic?: number;
    emission?: boolean;
    emissionStrength?: number;
  };
  // Replace Record<string, any> with the same type used for SceneObject.properties
  properties?: Record<string, string | number | boolean | null | object>;
}

/**
 * Represents edit instructions returned by MCP
 */
export interface EditInstructions {
  object_changes: Record<string, ObjectChange>;
  add_objects: SceneObject[];
  remove_object_ids: string[];
  operation_description?: string;
}

/**
 * Represents the complete thread state with scene history
 */
export interface AnimationThreadState {
  threadId: string;
  currentSceneId: string;
  sceneHistory: SceneState[];
  // Messages already include scene references via metadata
}