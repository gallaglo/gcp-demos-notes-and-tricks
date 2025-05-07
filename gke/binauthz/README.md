# Binary Authorization Demo

This demo shows how to use Binary Authorization (Binauthz) to enforce security policies on container images deployed in a GKE cluster.

## Steps

1. **Enable the required APIs**:

```bash
gcloud services enable \
  container.googleapis.com \
  binaryauthorization.googleapis.com
```

2. **Update placeholders in the policy file**:

```bash
# Set your project ID and region
PROJECT_ID=$(gcloud config get-value project)
REGION="us-central1"  # Replace with your preferred region
sed -i "s/YOUR_PROJECT_ID/$PROJECT_ID/g" binauthz-policy.yaml
sed -i "s/REGION/$REGION/g" binauthz-policy.yaml
```

3. **Create the Binary Authorization policy**:

```bash
gcloud beta binauthz policy import binauthz-policy.yaml
 ```

4. **Verify the policy**:

```bash
gcloud beta binauthz policy describe
```

5. **Create a GKE cluster with Binary Authorization enabled**:

```bash
gcloud beta container --project $PROJECT_ID clusters create-auto "demo-cluster" --region $REGION --release-channel "regular" --tier "standard" --enable-ip-access --no-enable-google-cloud-access --network "projects/${PROJECT_ID}/global/networks/default" --subnetwork "projects/${PROJECT_ID}/regions/${PROJECT_ID}/subnetworks/default" --cluster-ipv4-cidr "/17" --binauthz-evaluation-mode=POLICY_BINDINGS_AND_PROJECT_SINGLETON_POLICY_ENFORCE
```

6. **Deploy a sample application**:

Follow the instructions in the [Whereami](https://github.com/gallaglo/whereami) repo to deploy the sample application. Ensure that the image used is compliant with the Binary Authorization policy you created.

7. **Deploy a non-compliant image**:

```bash
kubectl run busybox --image=docker.io/library/busybox
```

This should fail due to the Binary Authorization policy.

## Cleanup

```bash
gcloud container clusters delete demo-cluster --region $REGION
gcloud beta binauthz policy delete
```

## Additional Resources

- [Binary Authorization Documentation](https://cloud.google.com/binary-authorization/docs)
- [GKE Documentation](https://cloud.google.com/kubernetes-engine/docs)
