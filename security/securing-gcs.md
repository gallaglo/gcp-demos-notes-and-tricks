# Securing GCS Buckets with IAM Conditions and VPC Service Controls

This guide describes how to implement a multi-layered defense strategy for Google Cloud Storage buckets by combining IAM Conditions with VPC Service Controls.

## Overview

When securing Google Cloud Storage buckets, using both IAM Conditions and VPC Service Controls provides a defense-in-depth strategy that secures your data at two distinct levels:

1. **IAM Conditions** (Identity-based security): Control who can access your buckets based on attributes like time of day, device type, resource names, etc.
2. **VPC Service Controls** (Network perimeter security): Create a security perimeter that restricts access based on network boundaries.

## Security Layers Architecture

```bash
┌─────────────────────────────────────────────────────────┐
│                 VPC Service Controls                    │
│                                                         │
│   ┌─────────────────────────────────────────────────┐   │
│   │               IAM Conditions                    │   │
│   │                                                 │   │
│   │   ┌─────────────────────────────────────┐       │   │
│   │   │                                     │       │   │
│   │   │            GCS Bucket               │       │   │
│   │   │                                     │       │   │
│   │   └─────────────────────────────────────┘       │   │
│   │                                                 │   │
│   └─────────────────────────────────────────────────┘   │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

## Layer 1: IAM Conditions

IAM Conditions add attribute-based access control to traditional identity-based permissions.

### Example 1: Time-based Access

This policy grants the `storage.objectUser` role to the developers group at example.com, but only during business hours (9 AM to 5 PM) Monday to Friday.

```json
{
  "bindings": [
    {
      "role": "roles/storage.objectUser",
      "members": [
        "group:developers@example.com"
      ],
      "condition": {
        "title": "Business hours access for developer team",
        "description": "Grants access only during business hours (9 AM to 5 PM) Monday to Friday",
        "expression": "request.time.getHours('America/New_York') >= 9 && request.time.getHours('America/New_York') <= 17 && request.time.getDayOfWeek('America/New_York') >= 1 && request.time.getDayOfWeek('America/New_York') <= 5"
      }
    }
  ]
}
```

### Example 2: Resource Naming Pattern Access

This policy grants the `storage.objectUser` role to the developer team, but only for buckets with names starting with "dev-".

```json
{
  "bindings": [
    {
      "role": "roles/storage.objectUser",
      "members": [
        "group:developers@example.com"
      ],
      "condition": {
        "title": "Dev environment access only",
        "description": "Grants access only to Cloud Storage buckets with the 'dev-' prefix",
        "expression": "resource.type == 'storage.googleapis.com/Object' && resource.name.startsWith('projects/_/buckets/dev-')"
      }
    }
  ]
}
```

## Layer 2: VPC Service Controls

VPC Service Controls create a security perimeter around your GCS buckets, preventing access from outside networks even if credentials are compromised.

### Setting Up VPC Service Controls

1. **Enable the Access Context Manager API**:

   ```bash
   gcloud services enable accesscontextmanager.googleapis.com
   ```

2. **Create an Access Policy** (if you don't have one already):

   ```bash
   gcloud access-context-manager policies create --organization=ORGANIZATION_ID --title="My Access Policy"
   ```

3. **Create an Access Level for Company Devices**:
   Save the following to `access-level.yaml`:

   ```yaml
   name: accessPolicies/POLICY_ID/accessLevels/ExampleComDevices
   title: Example.com Company Devices
   basic:
     conditions:
       - ipSubnetworks:
         - "203.0.113.0/24"  # Replace with your company's IP range
         - "198.51.100.0/24" # Another company IP range
       - devicePolicy:
           requireCorpOwned: true
       - members:
         - "domain:example.com"
   ```

   Apply it with:

   ```bash
   gcloud access-context-manager levels create ExampleComDevices --policy=POLICY_ID --yaml-file=access-level.yaml
   ```

4. **Create a Service Perimeter**:

   ```bash
   gcloud access-context-manager perimeters create perimeter-example \
     --policy=POLICY_ID \
     --title="Storage Perimeter" \
     --resources=projects/PROJECT_ID \
     --restricted-services=storage.googleapis.com
   ```

5. **Create an Ingress Rule**:
   Save the following to `ingress.yaml`:

   ```yaml
   - ingressFrom:
       identityType: ANY_USER_ACCOUNT
       sources:
       - accessLevel: accessPolicies/POLICY_ID/accessLevels/ExampleComDevices
     ingressTo:
       operations:
       - serviceName: storage.googleapis.com
         methodSelectors:
         - method: "*"
       resources:
       - "*"
   ```

   Apply it with:

   ```bash
   gcloud access-context-manager perimeters update perimeter-example --policy=POLICY_ID --set-ingress-policies=ingress.yaml
   ```

### Advanced Ingress Rule Example

This example allows:

1. Specific service accounts to access from corporate data centers
2. Any user account from company devices to query BigQuery
3. A specific service account to write to Cloud Storage from an authorized VPC network

```yaml
- ingressFrom:
    identities:
    - serviceAccount:data-loader@example-project.iam.gserviceaccount.com
    sources:
    - accessLevel: accessPolicies/POLICY_ID/accessLevels/CorpDatacenters
  ingressTo:
    operations:
    - serviceName: storage.googleapis.com
      methodSelectors:
      - method: "google.storage.objects.create"
      - method: "google.storage.objects.update"
    resources:
    - "*"

- ingressFrom:
    identityType: ANY_SERVICE_ACCOUNT
    sources:
      - resource: //compute.googleapis.com/projects/network-project/global/networks/prod-vpc-network
  ingressTo:
    operations:
    - serviceName: storage.googleapis.com
      methodSelectors:
      - method: google.storage.Write
      - method: google.storage.objects.create
    resources:
    - "*"

- ingressFrom:
    identityType: ANY_USER_ACCOUNT
    sources:
    - accessLevel: accessPolicies/POLICY_ID/accessLevels/TrustedDevices
  ingressTo:
    operations:
    - serviceName: storage.googleapis.com
      methodSelectors:
      - method: google.storage.Read
    resources:
    - "*"
```

## Combined Security Benefits

When implemented together, these layers provide:

1. **Defense Against Stolen Credentials**: Even if IAM credentials are compromised, VPC Service Controls block access from outside the perimeter.

2. **Protection Against IAM Misconfiguration**: If IAM permissions are incorrectly assigned, VPC Service Controls still enforce network-level restrictions.

3. **Prevention of Data Exfiltration**: Users can't copy data to unauthorized locations outside the perimeter.

4. **Granular Time & Resource Access**: IAM conditions ensure that even authorized users can only access specific resources during approved times.

## Limitations

- Public buckets cannot exist within a VPC Service Controls perimeter
- IAM conditions cannot be applied to legacy basic roles (Owner, Editor, Viewer)
- IAM conditions cannot be used with allUsers or allAuthenticatedUsers

## References

- [IAM Conditions Overview](https://cloud.google.com/iam/docs/conditions-overview)
- [VPC Service Controls Documentation](https://cloud.google.com/vpc-service-controls/docs)
- [Context-aware Access with VPC Service Controls](https://cloud.google.com/vpc-service-controls/docs/ingress-egress-rules)
