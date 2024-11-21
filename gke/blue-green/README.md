# Blue/Green Deployment Demo on Kubernetes

This repository demonstrates how to perform blue/green deployments on Kubernetes using a simple web application that visually indicates its deployment status (Blue 🟦 or Green 🟩) along with GCP infrastructure information.

## Application Features

- Visual deployment indicators:
  - Blue deployment: 🟦 with Google Blue (#1a73e8) styling
  - Green deployment: 🟩 with Google Green (#137333) styling
- Infrastructure information display:
  - GCP Region and Zone
  - Kubernetes Cluster name
  - Node name
  - Pod name
- Version tracking:
  - Blue deployment: v1
  - Green deployment: v2
- Color-coded UI elements for clear deployment identification
- Health check endpoints for Kubernetes probes

## Prerequisites

- Access to a Kubernetes cluster
- `kubectl` configured to interact with your cluster
- Docker installed (if building images locally)
- Access to Google Container Registry (GCR) or another container registry

## Files Structure

```
.
├── app.py                     # Flask application
├── templates/
│   └── index.html            # HTML template with color-coded styling
├── Dockerfile                # Container configuration
├── requirements.txt          # Python dependencies
└── k8s-manifests/
    ├── service.yaml          # Main service configuration
    ├── deployment-blue.yaml  # Blue deployment configuration
    ├── deployment-green.yaml # Green deployment configuration
    └── test-service.yaml     # Test service for green deployment
```

## Building the Container Image

1. Build and push both versions:
```bash
# Build and push version 1 (blue)
docker build -t webapp:v1 .
docker tag webapp:v1 gcr.io/[PROJECT_ID]/webapp:v1
docker push gcr.io/[PROJECT_ID]/webapp:v1

# Build and push version 2 (green)
docker tag webapp:v1 gcr.io/[PROJECT_ID]/webapp:v2
docker push gcr.io/[PROJECT_ID]/webapp:v2
```

## Deployment Steps

### 1. Initial Deployment (Blue)

1. Deploy the blue version:
```bash
kubectl apply -f deployment-blue.yaml
```

2. Deploy the main service (pointing to blue):
```bash
kubectl apply -f service.yaml
```

3. Verify the deployment:
```bash
kubectl get pods -l deployment=blue
kubectl get service webapp-service
```

4. Access the application to verify:
- You should see a blue-themed interface with 🟦
- The header should say "Blue Deploy"
- Version should show as v1

### 2. Deploy Green Version

1. Deploy the green version:
```bash
kubectl apply -f deployment-green.yaml
```

2. Deploy the test service to verify green version:
```bash
kubectl apply -f test-service.yaml
```

3. Verify green deployment:
```bash
kubectl get pods -l deployment=green
kubectl get service webapp-test-service
```

4. Access the test service to verify:
- You should see a green-themed interface with 🟩
- The header should say "Green Deploy"
- Version should show as v2

### 3. Switch Traffic to Green

After verifying the green deployment is working correctly:

1. Update the main service to point to green:
```bash
kubectl patch service webapp-service -p '{"spec":{"selector":{"deployment":"green"}}}'
```

2. Verify traffic switch:
```bash
kubectl describe service webapp-service
```

### 4. Rollback (if needed)

To rollback to blue deployment:
```bash
kubectl patch service webapp-service -p '{"spec":{"selector":{"deployment":"blue"}}}'
```

### 5. Cleanup Old Deployment

After confirming the green deployment is stable:
```bash
kubectl delete -f deployment-blue.yaml
kubectl delete -f test-service.yaml
```

## Resource Specifications

Both blue and green deployments use identical resource configurations:
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

## Monitoring

1. Watch the pods:
```bash
kubectl get pods -l app=webapp -w
```

2. Check services:
```bash
kubectl get services
```

3. View pod details:
```bash
kubectl describe pods -l app=webapp
```

4. View logs:
```bash
# For blue deployment
kubectl logs -l deployment=blue

# For green deployment
kubectl logs -l deployment=green
```

## Visual Verification

When accessing the application, verify the following:

1. Blue Deployment (v1):
- Blue square emoji (🟦)
- Blue-colored header and deployment badge
- Version showing as v1
- "Blue Deploy" title

2. Green Deployment (v2):
- Green square emoji (🟩)
- Green-colored header and deployment badge
- Version showing as v2
- "Green Deploy" title

## Complete Cleanup

Remove all resources:
```bash
kubectl delete -f service.yaml
kubectl delete -f test-service.yaml
kubectl delete -f deployment-blue.yaml
kubectl delete -f deployment-green.yaml
```

## Best Practices

1. Always verify the visual indicators match the expected deployment
2. Use the test service to verify the new version before switching traffic
3. Keep the old deployment running for a while after switching in case rollback is needed
4. Use readiness probes to ensure pods are ready before receiving traffic
5. Monitor both deployments during and after the switch
6. Maintain sufficient cluster capacity to run both versions simultaneously

## Troubleshooting

1. Check pod status:
```bash
kubectl get pods -l app=webapp
kubectl describe pod <pod-name>
```

2. Verify service selectors:
```bash
kubectl describe service webapp-service
kubectl describe service webapp-test-service
```

3. Check endpoints:
```bash
kubectl get endpoints webapp-service
kubectl get endpoints webapp-test-service
```

4. Test services locally:
```bash
kubectl port-forward service/webapp-service 8080:80
kubectl port-forward service/webapp-test-service 8081:80
```

Then visit:
- http://localhost:8080 - Should show current production deployment
- http://localhost:8081 - Should show test deployment (green)

## Common Issues and Solutions

1. Wrong colors showing:
   - Verify environment variables are set correctly in deployments
   - Check pod logs for any startup errors
   - Verify deployment labels match service selectors

2. Service not switching:
   - Verify patch command executed successfully
   - Check service selector labels
   - Ensure pods have correct deployment labels

3. Resource issues:
   - Monitor CPU and memory usage
   - Check for pod evictions
   - Verify node capacity for running both deployments