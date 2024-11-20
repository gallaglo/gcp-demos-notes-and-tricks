# Canary Deployment Demo on Kubernetes

This repository demonstrates how to perform canary deployments on Kubernetes using a simple web application that displays its deployment status (Stable 🥚 or Canary 🐦) along with GCP infrastructure information.

## Prerequisites

- Access to a Kubernetes cluster
- `kubectl` configured to interact with your cluster
- Docker installed (if building images locally)
- Access to Google Container Registry (GCR) or another container registry

## Application Components

- Flask web application showing deployment status and infrastructure info
- Dockerfile for containerization
- Kubernetes manifests for canary deployment
- Service for load balancing

## Building the Container Image

1. Build the Docker image:
```bash
docker build -t webapp:v1 .
```

2. Tag and push to Google Container Registry:
```bash
# Replace [PROJECT_ID] with your GCP project ID
docker tag webapp:v1 gcr.io/[PROJECT_ID]/webapp:v1
docker push gcr.io/[PROJECT_ID]/webapp:v1

# For version 2 (canary)
docker tag webapp:v1 gcr.io/[PROJECT_ID]/webapp:v2
docker push gcr.io/[PROJECT_ID]/webapp:v2
```

## Deployment Steps

### 1. Deploy the Service

```bash
kubectl apply -f service.yaml
```

### 2. Deploy Stable Version

```bash
kubectl apply -f deployment-stable.yaml
```

Verify stable deployment:
```bash
kubectl get pods -l version=stable
```

### 3. Deploy Canary Version

```bash
kubectl apply -f deployment-canary.yaml
```

Verify both deployments:
```bash
kubectl get pods -l app=webapp --show-labels
```

## Managing Traffic Split

The traffic split is controlled by the number of replicas in each deployment.

### Initial Split (75/25)
- Stable: 3 replicas (75% of traffic)
- Canary: 1 replica (25% of traffic)

### Adjust Traffic Split

Increase canary traffic:
```bash
# 40% canary (2 replicas out of 5 total)
kubectl scale deployment webapp-canary --replicas=2

# 50% canary (3 replicas out of 6 total)
kubectl scale deployment webapp-canary --replicas=3
```

Decrease canary traffic:
```bash
# Back to 25% canary
kubectl scale deployment webapp-canary --replicas=1
```

## Monitoring the Deployment

1. Watch the pods:
```bash
kubectl get pods -l app=webapp -w
```

2. Check the service:
```bash
kubectl get service webapp-service
```

3. View pod details:
```bash
kubectl describe pods -l app=webapp
```

4. View logs:
```bash
# For stable pods
kubectl logs -l version=stable

# For canary pods
kubectl logs -l version=canary
```

## Promoting Canary to Stable

1. Update the stable deployment to use the new image:
```bash
kubectl set image deployment/webapp-stable webapp=gcr.io/[PROJECT_ID]/webapp:v2
```

2. Wait for rollout to complete:
```bash
kubectl rollout status deployment/webapp-stable
```

3. Remove canary deployment:
```bash
kubectl delete -f deployment-canary.yaml
```

## Rolling Back

If issues are detected with the canary:

1. Remove the canary deployment:
```bash
kubectl delete -f deployment-canary.yaml
```

2. Traffic will automatically route to stable pods only

## Cleanup

Remove all resources:
```bash
kubectl delete -f service.yaml
kubectl delete -f deployment-stable.yaml
kubectl delete -f deployment-canary.yaml
```

## Traffic Split Calculator

Use this table to plan your traffic split:

| Stable Replicas | Canary Replicas | Total Pods | Canary Traffic % |
|-----------------|-----------------|------------|------------------|
| 3               | 1               | 4          | 25%             |
| 3               | 2               | 5          | 40%             |
| 3               | 3               | 6          | 50%             |
| 3               | 4               | 7          | 57%             |

## Troubleshooting

1. Check pod status:
```bash
kubectl get pods -l app=webapp
kubectl describe pod <pod-name>
```

2. View application logs:
```bash
kubectl logs <pod-name>
```

3. Check service endpoints:
```bash
kubectl get endpoints webapp-service
```

4. Test service locally:
```bash
kubectl port-forward service/webapp-service 8080:80
```
Then visit http://localhost:8080 in your browser

## Notes

- The application includes readiness probes to ensure proper traffic routing
- Each deployment has environment variables to display its status (Stable 🥚 or Canary 🐦)
- The service uses the app label for selection, allowing traffic to both stable and canary pods
