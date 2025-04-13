'use client';

import React, { useState } from 'react';
import { Button } from "@/components/ui/button";
import {
  Popover,
  PopoverContent,
  PopoverTrigger
} from "@/components/ui/popover";
import {
  Card,
  CardHeader,
  CardTitle,
  CardContent,
  CardDescription
} from "@/components/ui/card";
import {
  Badge
} from "@/components/ui/badge";
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent
} from "@/components/ui/accordion";
import {
  PaletteIcon, 
  SlidersHorizontal, 
  Eye, 
  RotateCcw, 
  Box, 
  Trash2,
  History,
  ArrowUpDown,
  Undo2
} from "lucide-react";
import { SceneObject, SceneState, SceneEditValue } from '@/lib/types/scene';

interface SceneControlsProps {
  sceneState?: SceneState;
  sceneHistory?: SceneState[];
  onObjectEdit?: (objectId: string, changeType: string, value: SceneEditValue) => void;
  onGeneratePrompt?: (prompt: string) => void;
  onUndo?: () => void;
}

const SceneControls: React.FC<SceneControlsProps> = ({
  sceneState,
  sceneHistory = [],
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  onObjectEdit,
  onGeneratePrompt,
  onUndo
}) => {
  const [selectedObjectId, setSelectedObjectId] = useState<string | null>(null);
  const [isHistoryOpen, setIsHistoryOpen] = useState(false);
  
  // Find the selected object
  const selectedObject = selectedObjectId ? 
    sceneState?.objects.find(obj => obj.id === selectedObjectId) :
    null;
  
  // Group objects by type for organization
  const objectsByType: Record<string, SceneObject[]> = {};
  
  sceneState?.objects.forEach(obj => {
    if (!objectsByType[obj.type]) {
      objectsByType[obj.type] = [];
    }
    objectsByType[obj.type].push(obj);
  });

  // Generate a modification prompt based on selected object
  const generateModificationPrompt = (action: string) => {
    if (!selectedObject) return;
    
    let prompt = "";
    
    switch (action) {
      case 'move-up':
        prompt = `Move the ${selectedObject.name} up by 2 units`;
        break;
      case 'move-right': 
        prompt = `Move the ${selectedObject.name} to the right by 2 units`;
        break;
      case 'rotate':
        prompt = `Rotate the ${selectedObject.name} 45 degrees clockwise`;
        break;
      case 'color-red':
        prompt = `Change the color of the ${selectedObject.name} to bright red`;
        break;
      case 'color-blue':
        prompt = `Change the color of the ${selectedObject.name} to deep blue`;
        break;
      case 'color-green':
        prompt = `Change the color of the ${selectedObject.name} to green`;
        break;
      case 'scale-up':
        prompt = `Make the ${selectedObject.name} twice as large`;
        break;
      case 'scale-down':
        prompt = `Make the ${selectedObject.name} half its current size`;
        break;
      case 'remove':
        prompt = `Remove the ${selectedObject.name} from the scene`;
        break;
      default:
        return;
    }
    
    if (onGeneratePrompt) {
      onGeneratePrompt(prompt);
    }
  };
  
  // Helper to format color as CSS
  const formatColor = (color?: [number, number, number]): string => {
    if (!color) return 'rgba(200, 200, 200, 0.8)';
    
    // Convert from 0-1 to 0-255 range
    const r = Math.floor(color[0] * 255);
    const g = Math.floor(color[1] * 255);
    const b = Math.floor(color[2] * 255);
    
    return `rgb(${r}, ${g}, ${b})`;
  };
  
  // Only render controls if we have scene data
  if (!sceneState) {
    return null;
  }
  
  return (
    <div className="w-full space-y-4">
      <Card className="bg-card shadow-md">
        <CardHeader className="pb-2">
          <div className="flex justify-between items-center">
            <CardTitle className="text-lg">Scene Controls</CardTitle>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={onUndo} title="Undo">
                <Undo2 className="h-4 w-4" />
              </Button>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => setIsHistoryOpen(!isHistoryOpen)}
                title="Scene History"
              >
                <History className="h-4 w-4" />
              </Button>
            </div>
          </div>
          <CardDescription>{sceneState.description}</CardDescription>
        </CardHeader>
        
        <CardContent>
          {/* History View */}
          {isHistoryOpen && sceneHistory.length > 0 && (
            <div className="mb-4 border rounded-lg p-2 bg-muted/30">
              <h4 className="text-sm font-medium mb-2">Scene History</h4>
              <div className="space-y-2 max-h-36 overflow-y-auto text-xs">
                {sceneHistory.map((scene, index) => (
                  <div key={scene.id} className="flex justify-between items-center p-1 hover:bg-accent/20 rounded">
                    <span>
                      {index + 1}. {scene.description.substring(0, 30)}{scene.description.length > 30 ? '...' : ''}
                    </span>
                    <Badge variant="outline" className="text-xs">
                      {new Date(scene.createdAt || '').toLocaleDateString()}
                    </Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
          
          {/* Object Categories */}
          <Accordion type="single" collapsible className="w-full">
            {Object.entries(objectsByType).map(([type, objects]) => (
              <AccordionItem key={type} value={type}>
                <AccordionTrigger className="text-sm py-2">
                  <div className="flex gap-2 items-center">
                    {type === 'sphere' && <Box className="h-4 w-4" />}
                    {type === 'cube' && <Box className="h-4 w-4" />}
                    {type === 'light' && <PaletteIcon className="h-4 w-4" />}
                    {type === 'camera' && <Eye className="h-4 w-4" />}
                    <span className="capitalize">{type}s ({objects.length})</span>
                  </div>
                </AccordionTrigger>
                <AccordionContent>
                  {objects.map(obj => (
                    <div 
                      key={obj.id}
                      className={`flex justify-between items-center p-2 rounded-md text-sm ${
                        selectedObjectId === obj.id ? 'bg-accent/20' : 'hover:bg-accent/10'
                      }`}
                      onClick={() => setSelectedObjectId(obj.id)}
                    >
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-3 h-3 rounded-full" 
                          style={{ 
                            backgroundColor: formatColor(obj.material?.color)
                          }}
                        />
                        <span>{obj.name}</span>
                      </div>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" className="h-6 w-6 p-1">
                          <Eye className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </AccordionContent>
              </AccordionItem>
            ))}
          </Accordion>
          
          {/* Selected Object Controls */}
          {selectedObject && (
            <div className="mt-4 p-3 border rounded-lg bg-muted/20">
              <div className="flex justify-between items-center mb-2">
                <h3 className="font-medium">{selectedObject.name}</h3>
                <Badge variant="outline">{selectedObject.type}</Badge>
              </div>
              
              <div className="grid grid-cols-2 gap-2 mb-3">
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="flex gap-1 items-center" 
                  onClick={() => generateModificationPrompt('move-up')}
                >
                  <ArrowUpDown className="h-3 w-3" />
                  <span>Move</span>
                </Button>
                
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="flex gap-1 items-center"
                  onClick={() => generateModificationPrompt('rotate')}
                >
                  <RotateCcw className="h-3 w-3" />
                  <span>Rotate</span>
                </Button>
                
                <Popover>
                  <PopoverTrigger asChild>
                    <Button 
                      size="sm" 
                      variant="outline" 
                      className="flex gap-1 items-center"
                    >
                      <PaletteIcon className="h-3 w-3" />
                      <span>Color</span>
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-auto p-2" align="start">
                    <div className="flex gap-1">
                      {['red', 'blue', 'green', 'yellow', 'purple'].map(color => (
                        <div 
                          key={color}
                          className="w-6 h-6 rounded-full cursor-pointer"
                          style={{ backgroundColor: color }}
                          onClick={() => generateModificationPrompt(`color-${color}`)}
                        />
                      ))}
                    </div>
                  </PopoverContent>
                </Popover>
                
                <Button 
                  size="sm" 
                  variant="outline" 
                  className="flex gap-1 items-center"
                  onClick={() => generateModificationPrompt('scale-up')}
                >
                  <SlidersHorizontal className="h-3 w-3" />
                  <span>Scale</span>
                </Button>
              </div>
              
              <Button 
                size="sm" 
                variant="destructive" 
                className="w-full flex gap-1 items-center justify-center"
                onClick={() => generateModificationPrompt('remove')}
              >
                <Trash2 className="h-3 w-3" />
                <span>Remove</span>
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default SceneControls;