# GKE Multi-cluster Gateways Demo

This demo shows how to use [GKE Gateway controller](https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api) to deploy a multi-cluster application with a single global load balancer.

This directory deploys the GKE resources using Terraform. The resources include two GKE clusters, a GKE Gateway, and a global load balancer, following the setup instruction in [Enable multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/enabling-multi-cluster-gateways) and [Deploying multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/deploying-multi-cluster-gateways).

![multi-cluster-gateway](https://cloud.google.com/static/kubernetes-engine/images/multi-cluster-gateway-ex1-v2.svg)

## Deploy and confgure the GKE clusters

Detailed instructions are available at [Enable multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/enabling-multi-cluster-gateways).

* Deploy the GKE resources using Terraform:

```bash
terraform apply -var project_id=PROJECT_ID
```

* Fetch the credentials for us-west1-cluster and us-east1-cluster:

```bash
gcloud container clusters get-credentials us-west1-cluster --zone=us-west1-a --project=PROJECT_ID
gcloud container clusters get-credentials us-east1-cluster --zone=us-east1-b --project=PROJECT_ID
```

* Rename the cluster contexts so they are easier to reference later:

```bash
kubectl config rename-context gke_PROJECT_ID_us-west1-a_gke-west-1 gke-west-1
kubectl config rename-context gke_PROJECT_ID_us-east1-b_gke-east-1 gke-east-1
```

* Confirm that the GKE Gateway controller is enabled for your fleet:

```bash
gcloud container fleet ingress describe --project=PROJECT_ID
```

* Confirm that the GatewayClasses exist in your config cluster:

```bash
kubectl get gatewayclasses --context=gke-west-1
```

## Deploy the application

Detailed directions are available at [Deploying multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/deploying-multi-cluster-gateways). Kubernetes manifests are provided in the `k8s-manifests/` directory.
