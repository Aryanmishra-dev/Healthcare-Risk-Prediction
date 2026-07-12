# Kubernetes Deployment Guide

## Overview
The platform includes a Helm chart located at `deployment/kubernetes/healthpredict/` for production Kubernetes deployments.

## Prerequisites
- A running Kubernetes cluster (e.g., GKE, EKS, AKS or Minikube).
- Helm 3 installed.
- Nginx Ingress Controller deployed.
- Cert-Manager deployed (if using automated TLS via Let's Encrypt).

## Components
The Helm chart provisions the following resources:
1. **Deployment**: Manages the API pods with configurable replicas (default: 3). Uses readiness and liveness probes hitting `/healthz`.
2. **Service**: Exposes the API internally within the cluster.
3. **Ingress**: Routes external traffic to the service. Configured for `api.healthpredict.com` with TLS termination.
4. **ConfigMap & Secret**: Injects environment variables dynamically into the pods.
5. **HorizontalPodAutoscaler (HPA)**: Scales pods from 2 up to 10 based on CPU utilization > 80%.
6. **PersistentVolumeClaim (PVC)**: Allocates persistent block storage for databases or artifacts if stateful components are hosted in-cluster.

## Deployment Instructions
1. Navigate to the chart directory:
   ```bash
   cd deployment/kubernetes
   ```
2. Deploy the chart to your cluster:
   ```bash
   helm install healthpredict-api ./healthpredict -f ./healthpredict/values.yaml -n production --create-namespace
   ```
