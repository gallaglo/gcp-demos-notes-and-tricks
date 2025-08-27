# ADK Animation Agent Migration

This document describes the refactoring of the animation app to use Google Agent Development Kit (ADK) and the separation of concerns between the animator and agent services.

## Architecture Changes

### Before (Original Architecture)
```
┌─────────────────┐    ┌──────────────────────┐
│   Frontend      │───▶│  Agent Service       │
│   (Next.js)     │    │  - LangGraph         │
└─────────────────┘    │  - Prompt Analysis   │
                       │  - Script Generation │
                       └──────────┬───────────┘
                                  │
                                  ▼
                       ┌──────────────────────┐
                       │  Animator Service    │
                       │  - Blender Rendering │
                       │  - GCS Upload        │
                       │  - Signed URL Gen    │
                       └──────────────────────┘
```

### After (ADK Architecture)
```
┌─────────────────┐    ┌──────────────────────────────────────┐
│   Frontend      │───▶│         ADK Agent Service            │
│   (Next.js)     │    │                                      │
└─────────────────┘    │  ┌─────────────┐  ┌────────────────┐ │
                       │  │ Analysis    │  │ Script Gen     │ │
                       │  │ Agent       │  │ Agent          │ │
                       │  └─────────────┘  └────────────────┘ │
                       │                                      │
                       │  ┌─────────────┐  ┌────────────────┐ │
                       │  │ Storage     │  │ Orchestrator   │ │
                       │  │ Agent       │  │ Agent          │ │
                       │  └─────────────┘  └────────────────┘ │
                       └──────────────┬───────────────────────┘
                                      │
                                      ▼
                       ┌──────────────────────┐
                       │ Simplified Animator  │
                       │ - Blender Rendering  │
                       │ (GCS logic removed)  │
                       └──────────────────────┘
```

## Key Changes

### 1. Service Separation
- **GCS Upload Logic Moved**: Cloud storage operations moved from animator service to ADK storage agent
- **Simplified Animator**: Now only handles Blender rendering, returns file paths instead of signed URLs
- **ADK Agent Service**: Handles all orchestration, prompt analysis, and storage operations

### 2. ADK Agent Structure

#### Sub-Agents
- **Analysis Agent** (`sub_agents/analysis/`): Determines user intent (animation vs conversation)
- **Script Generation Agent** (`sub_agents/script_generation/`): Creates Blender Python scripts
- **Storage Agent** (`sub_agents/storage/`): Handles GCS uploads and signed URL generation

#### Tools
- **Blender Service Tool** (`tools/blender_service_tool.py`): Communicates with animator service
- **GCS Upload Tool** (`storage/tools/gcs_upload_tool.py`): Handles cloud storage operations
- **Conversation Tool** (`tools/conversation_tool.py`): Manages conversational interactions

### 3. Configuration
- **Centralized Config** (`config.py`): All environment variables and settings
- **ADK Dependencies** (`pyproject.toml`): Google ADK framework and related packages

## Directory Structure

```
animation/
├── agent-adk/                    # NEW: ADK-based agent service
│   ├── sub_agents/
│   │   ├── analysis/
│   │   ├── script_generation/
│   │   └── storage/              # NEW: Handles GCS uploads
│   ├── tools/
│   ├── prompts/
│   ├── config.py
│   ├── agent.py
│   └── main.py
├── animator-simplified/          # NEW: Simplified animator service
│   ├── app.py                   # GCS logic removed
│   ├── pyproject.toml
│   └── Dockerfile
├── animator/                     # ORIGINAL: Full animator service
├── agent/                       # ORIGINAL: LangGraph-based agent
└── frontend/                    # UNCHANGED: Next.js frontend
```

## Migration Benefits

### 1. Better Separation of Concerns
- **Single Responsibility**: Each agent handles one specific domain
- **Reusable Components**: Tools can be shared across different workflows
- **Clear Boundaries**: Storage, rendering, and logic clearly separated

### 2. Improved Scalability
- **Independent Scaling**: Each service can scale independently
- **ADK Integration**: Native Vertex AI deployment and scaling
- **Resource Optimization**: Only render service needs heavy compute resources

### 3. Enhanced Maintainability
- **Modular Architecture**: Easier to test and maintain individual components
- **Error Isolation**: Failures in one component don't affect others
- **Simplified Debugging**: Clear separation of responsibilities

### 4. ADK Framework Benefits
- **Native Google Cloud Integration**: Built-in authentication and service discovery
- **Robust State Management**: Persistent state across agent interactions
- **Tool-Based Architecture**: Standardized way to handle external service calls
- **Monitoring and Logging**: Native Vertex AI monitoring capabilities

## Implementation Status

### ✅ Completed
- [x] ADK directory structure created
- [x] Storage agent with GCS upload logic implemented
- [x] Analysis agent for prompt classification
- [x] Script generation agent with Blender script creation
- [x] External service tools (Blender service, conversation)
- [x] Simplified animator service (GCS logic removed)
- [x] Configuration and dependency management

### 🚧 In Progress
- [ ] Full ADK workflow integration
- [ ] LLM integration for script generation
- [ ] Error handling and retry logic
- [ ] Streaming response support

### 📋 Planned
- [ ] Vertex AI deployment configuration
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Documentation updates

## Deployment Strategy

### Phase 1: Parallel Deployment
1. Deploy ADK agent service alongside existing agent service
2. Test ADK system with subset of traffic
3. Validate all functionality works correctly

### Phase 2: Migration
1. Update frontend to use ADK agent service
2. Monitor performance and error rates
3. Gradually increase traffic to ADK service

### Phase 3: Cleanup
1. Remove original LangGraph-based agent service
2. Update documentation and deployment scripts
3. Optimize ADK service for production

## Configuration

### Environment Variables
```bash
# ADK Agent Service
GENAI_MODEL=gemini-2.0-flash-001
GCS_BUCKET_NAME=your-animations-bucket
BLENDER_SERVICE_URL=https://your-animator-service-url
MAX_ITERATIONS=3
SIGNED_URL_EXPIRATION_MINUTES=15

# Simplified Animator Service
PORT=8080
GOOGLE_CLOUD_PROJECT=your-project-id
```

### Dependencies
- **google-adk**: Core ADK framework
- **google-cloud-aiplatform**: Vertex AI integration
- **google-cloud-storage**: Cloud storage operations
- **google-genai**: GenAI client for model interactions

## Testing

### Unit Tests
```bash
# Test individual agents and tools
cd agent-adk
python -m pytest tests/

# Test simplified animator service
cd animator-simplified  
python -m pytest tests/
```

### Integration Tests
```bash
# Test full workflow
python test_adk_workflow.py

# Test service communication
python test_service_integration.py
```

## Next Steps

1. **Complete LLM Integration**: Connect script generation agent to actual LLM
2. **Implement Vertex AI Deployment**: Deploy ADK agents to Vertex AI
3. **Add Monitoring**: Implement comprehensive logging and monitoring
4. **Performance Optimization**: Optimize for production workloads
5. **Documentation**: Complete API documentation and deployment guides

This migration provides a more scalable, maintainable, and cloud-native architecture for the animation generation system while clearly separating concerns between rendering and orchestration services.