# GKE Multi-cluster Gateways Demo

This demo shows how to use [GKE Gateway controller](https://cloud.google.com/kubernetes-engine/docs/concepts/gateway-api) to deploy a multi-cluster application with a single global load balancer.

This directory deploys the GKE resources using Terraform. The resources include two GKE clusters, a GKE Gateway, and a global load balancer, following the setup instruction in [Enable multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/enabling-multi-cluster-gateways) and [Deploying multi-cluster Gateways](https://cloud.google.com/kubernetes-engine/docs/how-to/deploying-multi-cluster-gateways).

![multi-cluster-gateway](https://cloud.google.com/static/kubernetes-engine/images/multi-cluster-gateway-ex1-v2.svg)
