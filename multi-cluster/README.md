# GKE Multi-cluster Gateways Demo

This demo shows how to use the [GKE Gateway controller](https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api) to deploy a multi-cluster application with a single global load balancer.

This directory deploys the GKE resources using Terraform. The resources include two GKE clusters, a GKE Gateway, and a global load balancer, following the setup instruction in [Enable multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/enabling-multi-cluster-gateways) and [Deploying multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/deploying-multi-cluster-gateways).

![multi-cluster-gateway](https://cloud.google.com/static/kubernetes-engine/images/multi-cluster-gateway-ex1-v2.svg)

## Deploy and confgure the GKE clusters

Detailed instructions are available at [Enable multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/enabling-multi-cluster-gateways).

1. Deploy the GKE resources using Terraform:

```bash
terraform apply
```

2. Fetch credentials for the us-west1-cluster and us-east1-clusters:

```bash
gcloud container clusters get-credentials us-west1-cluster \
    --zone=us-west1-b \
    --project=${DEVSHELL_PROJECT_ID}
gcloud container clusters get-credentials us-east1-cluster \
    --zone=us-east1-b \
    --project=${DEVSHELL_PROJECT_ID}
```

3.  Rename the cluster contexts so they are easier to reference later:

```bash
kubectl config rename-context gke_${DEVSHELL_PROJECT_ID}_us-west1-b_us-west1-cluster us-west1-cluster
kubectl config rename-context gke_${DEVSHELL_PROJECT_ID}_us-east1-b_us-east1-cluster us-east1-cluster 
```

4. Confirm that the GKE Gateway controller is enabled for your fleet:

```bash
gcloud container fleet ingress describe --project=${DEVSHELL_PROJECT_ID}
```

5. Confirm that the GatewayClasses exist in your config cluster:

```bash
kubectl get gatewayclasses --context=us-west1-cluster
```

## Deploy the application

Detailed directions are available at [Deploying multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/deploying-multi-cluster-gateways). Kubernetes manifests are provided in the `k8s-manifests/` directory.

1. Deploy the whereami workload to both clusters.

```bash
kubectl apply --context us-west1-cluster -f k8s-manifests/deployment.yaml
kubectl apply --context us-east1-cluster -f k8s-manifests/deployment.yaml
```

2. Apply the following manifests to create your store and store-west-1 Services and ServiceExports.

```bash
kubectl apply --context us-west1-cluster -f k8s-manifests/west-service.yaml
kubectl apply --context us-east1-cluster -f k8s-manifests/east-service.yaml
```

3. Verify that the correct ServiceExports have been created in the clusters.

```bash
kubectl get serviceexports --context us-west1-cluster --namespace demo
kubectl get serviceexports --context us-east1-cluster --namespace demo
```

4. After a few moments verify that the accompanying ServiceImports have been automatically created by the multi-cluster Services controller across all clusters in the fleet.

```bash
kubectl get serviceimports --context us-west1-cluster --namespace demo
kubectl get serviceimports --context us-east1-cluster --namespace demo
```

5. Apply the following Gateway manifest to the config cluster, us-west1-cluster.
```bash
kubectl apply --context us-west1-cluster -f k8s-manifests/gateway.yaml
```

6. Apply the following HTTPRoute manifest to the config cluster, us-west1-cluster.
```bash
kubectl apply --context us-west1-cluster -f k8s-manifests/httproute.yaml
```

7. Validate that the Gateway and HTTPRoute have been deployed successfully by inspecting the Gateway status and events.

```bash
kubectl describe gateways.gateway.networking.k8s.io external-http --context us-west1-cluster  --namespace demo
```

8. Retrieve the IP address of the Gateway to visit the whereami webpage or curl the `/api/` endpoint.

```bash
curl http://$(kubectl get gateways.gateway.networking.k8s.io external-http -o=jsonpath="{.status.addresses[0].value}" --context us-west1-cluster --namespace demo)/api/
```


## Cleanup
1. Delete GKE Gateway resources first.

```bash
kubectl delete --context us-west1-cluster -f k8s-manifests/httproute.yaml
kubectl delete --context us-west1-cluster -f k8s-manifests/gateway.yaml
```

2. Delete resources provisioned with Terraform.

```bash
terraform destroy
```

3. Disable Ingress features using gcloud because Terraform does not clean them up.

```bash
gcloud container fleet multi-cluster-services disable \
    --project=${DEVSHELL_PROJECT_ID}
gcloud container fleet ingress disable \
    --project=${DEVSHELL_PROJECT_ID}
```

4. Delete cluster contexts from `.kube/config`.

```bash
kubectl config delete-context us-west1-cluster
kubectl config delete-context us-east1-cluster
```

## TODO
* Remove hardcoded values like project IDs.
* Add support for HTTPS load balancer with [GKE Gateway](https://cloud.google.com/kubernetes-engine/docs/how-to/secure-gateway).