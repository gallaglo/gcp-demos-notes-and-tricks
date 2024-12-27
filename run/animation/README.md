# Animation Generator

> **Note**: This demo is based on the [Securing Cloud Run services tutorial](https://cloud.google.com/run/docs/tutorials/secure-services) from the Google Cloud documentation.

## Architecture

* Frontend sends animation prompt to backend
* Backend validates prompt and calls LLM API
* Backend validates generated [Blender script](https://docs.blender.org/api/current/info_overview.html)
* Backend executes script in Blender
* Backend saves animation to GCS
* Backend returns GCS URL to frontend
* Frontend loads and displays animation

```mermaid
flowchart LR
    User((User))
    subgraph Frontend[Frontend Service - Cloud Run]
        WebUI[Web Interface]
        ThreeJS[Three.js Viewer]
    end

    subgraph Backend[Backend Service - Cloud Run]
        APIHandler[API Handler]
        ScriptGen[Script Generator]
        BlenderExec[Blender Executor]
    end

    subgraph External[External Services]
        VertexAI[Vertex AI LLM]
        GCS[(Cloud Storage)]
    end

    %% User interactions
    User -->|1. Enter prompt| WebUI
    WebUI -->|2. Send prompt| APIHandler
    
    %% Backend processing
    APIHandler -->|3. Request script| VertexAI
    VertexAI -->|4. Return script| ScriptGen
    ScriptGen -->|5. Validate script| BlenderExec
    BlenderExec -->|6. Generate animation| BlenderExec
    BlenderExec -->|7. Upload file| GCS
    
    %% Return flow
    GCS -->|8. Return signed URL| APIHandler
    APIHandler -->|9. Return URL| WebUI
    WebUI -->|10. Load animation| ThreeJS
    ThreeJS -->|11. Display| User

    %% Styling
    classDef cloudRun fill:#f2f2f2,stroke:#333,stroke-width:2px
    classDef external fill:#e6f3ff,stroke:#333,stroke-width:2px
    classDef user fill:#f9f,stroke:#333,stroke-width:2px

    class Frontend,Backend cloudRun
    class External external
    class User user
```
