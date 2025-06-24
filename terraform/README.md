# GCP Instance Provisioning: A Comparison of Approaches

This document compares three different approaches to provisioning multiple Google Cloud Platform (GCP) Compute Engine instances:

1. Imperative approach using `gcloud` CLI commands
2. API-based approach using REST calls with `curl`
3. Declarative approach using Terraform (Infrastructure as Code)

## 1. Imperative Approach: gcloud CLI

```bash
#!/bin/bash

project_id="logan-gallagher"
instance_count=5

for i in $(seq 1 $instance_count); do
  instance_name="demo-instance-$i"
  disk_name="disk-$i"
  
  gcloud compute instances create $instance_name \
    --project=$project_id \
    --zone=us-central1-f \
    --machine-type=e2-medium \
    --network-interface=network-tier=PREMIUM,stack-type=IPV4_ONLY,subnet=default \
    --metadata=enable-osconfig=TRUE \
    --maintenance-policy=MIGRATE \
    --provisioning-model=STANDARD \
    --service-account=342279517497-compute@developer.gserviceaccount.com \
    --scopes=https://www.googleapis.com/auth/devstorage.read_only,https://www.googleapis.com/auth/logging.write,https://www.googleapis.com/auth/monitoring.write,https://www.googleapis.com/auth/service.management.readonly,https://www.googleapis.com/auth/servicecontrol,https://www.googleapis.com/auth/trace.append \
    --create-disk=auto-delete=yes,boot=yes,device-name=$instance_name,image=projects/debian-cloud/global/images/debian-12-bookworm-v20250415,mode=rw,size=10,type=pd-balanced \
    --create-disk=device-name=$disk_name,mode=rw,name=$disk_name,size=100,type=pd-ssd \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring \
    --labels=goog-ops-agent-policy=v2-x86-template-1-4-0,goog-ec-src=vm_add-gcloud
done

# Create the ops agent policy config file
printf 'agentsRule:\n  packageState: installed\n  version: latest\ninstanceFilter:\n  inclusionLabels:\n  - labels:\n      goog-ops-agent-policy: v2-x86-template-1-4-0\n' > config.yaml

# Create the ops agent policy
gcloud compute instances ops-agents policies create goog-ops-agent-v2-x86-template-1-4-0-us-central1-f \
  --project=$project_id \
  --zone=us-central1-f \
  --file=config.yaml

# Create snapshot schedule policy
gcloud compute resource-policies create snapshot-schedule default-schedule-1 \
  --project=$project_id \
  --region=us-central1 \
  --max-retention-days=14 \
  --on-source-disk-delete=keep-auto-snapshots \
  --daily-schedule \
  --start-time=10:00

# Add snapshot schedule to all instances and disks
for i in $(seq 1 $instance_count); do
  instance_name="demo-instance-$i"
  disk_name="disk-$i"
  
  # Add schedule to instance boot disk
  gcloud compute disks add-resource-policies $instance_name \
    --project=$project_id \
    --zone=us-central1-f \
    --resource-policies=projects/$project_id/regions/us-central1/resourcePolicies/default-schedule-1
  
  # Add schedule to additional disk
  gcloud compute disks add-resource-policies $disk_name \
    --project=$project_id \
    --zone=us-central1-f \
    --resource-policies=projects/$project_id/regions/us-central1/resourcePolicies/default-schedule-1
done
```

## 2. API-Based Approach: curl with REST API

```bash
#!/bin/bash

# Variables
PROJECT_ID="logan-gallagher"
ZONE="us-central1-f"
REGION="us-central1"
INSTANCE_COUNT=5

# Function to get authentication token
get_auth_token() {
  # Get auth token using gcloud
  TOKEN=$(gcloud auth print-access-token)
  if [ -z "$TOKEN" ]; then
    echo "Failed to obtain authentication token. Make sure you're logged in with gcloud."
    exit 1
  fi
  echo $TOKEN
}

# Get the auth token
AUTH_TOKEN=$(get_auth_token)

# Create instances
for i in $(seq 1 $INSTANCE_COUNT); do
  INSTANCE_NAME="demo-instance-$i"
  DISK_NAME="disk-$i"
  
  echo "Creating instance: $INSTANCE_NAME"
  
  # Create the JSON payload for the instance
  cat > instance_request.json << EOF
{
  "canIpForward": false,
  "confidentialInstanceConfig": {
    "enableConfidentialCompute": false
  },
  "deletionProtection": false,
  "description": "",
  "disks": [
    {
      "autoDelete": true,
      "boot": true,
      "deviceName": "${INSTANCE_NAME}",
      "initializeParams": {
        "diskSizeGb": "10",
        "diskType": "projects/${PROJECT_ID}/zones/${ZONE}/diskTypes/pd-balanced",
        "labels": {},
        "sourceImage": "projects/debian-cloud/global/images/debian-12-bookworm-v20250415"
      },
      "mode": "READ_WRITE",
      "type": "PERSISTENT"
    },
    {
      "autoDelete": false,
      "deviceName": "${DISK_NAME}",
      "diskEncryptionKey": {},
      "initializeParams": {
        "description": "",
        "diskName": "${DISK_NAME}",
        "diskSizeGb": "100",
        "diskType": "projects/${PROJECT_ID}/zones/${ZONE}/diskTypes/pd-ssd"
      },
      "mode": "READ_WRITE",
      "type": "PERSISTENT"
    }
  ],
  "displayDevice": {
    "enableDisplay": false
  },
  "guestAccelerators": [],
  "instanceEncryptionKey": {},
  "keyRevocationActionType": "NONE",
  "labels": {
    "goog-ops-agent-policy": "v2-x86-template-1-4-0",
    "goog-ec-src": "vm_add-rest"
  },
  "machineType": "projects/${PROJECT_ID}/zones/${ZONE}/machineTypes/e2-medium",
  "metadata": {
    "items": [
      {
        "key": "enable-osconfig",
        "value": "TRUE"
      }
    ]
  },
  "name": "${INSTANCE_NAME}",
  "networkInterfaces": [
    {
      "accessConfigs": [
        {
          "name": "External NAT",
          "networkTier": "PREMIUM"
        }
      ],
      "stackType": "IPV4_ONLY",
      "subnetwork": "projects/${PROJECT_ID}/regions/${REGION}/subnetworks/default"
    }
  ],
  "params": {
    "resourceManagerTags": {}
  },
  "reservationAffinity": {
    "consumeReservationType": "ANY_RESERVATION"
  },
  "scheduling": {
    "automaticRestart": true,
    "onHostMaintenance": "MIGRATE",
    "provisioningModel": "STANDARD"
  },
  "serviceAccounts": [
    {
      "email": "342279517497-compute@developer.gserviceaccount.com",
      "scopes": [
        "https://www.googleapis.com/auth/devstorage.read_only",
        "https://www.googleapis.com/auth/logging.write",
        "https://www.googleapis.com/auth/monitoring.write",
        "https://www.googleapis.com/auth/service.management.readonly",
        "https://www.googleapis.com/auth/servicecontrol",
        "https://www.googleapis.com/auth/trace.append"
      ]
    }
  ],
  "shieldedInstanceConfig": {
    "enableIntegrityMonitoring": true,
    "enableSecureBoot": true,
    "enableVtpm": true
  },
  "tags": {
    "items": []
  },
  "zone": "projects/${PROJECT_ID}/zones/${ZONE}"
}
EOF

  # Create the instance using curl
  curl -X POST \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @instance_request.json \
    "https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${ZONE}/instances"
  
  # Sleep to avoid rate limiting
  sleep 2
done

# Create the snapshot schedule policy
echo "Creating snapshot schedule policy"
cat > snapshot_policy.json << EOF
{
  "name": "default-schedule-1",
  "region": "${REGION}",
  "snapshotSchedulePolicy": {
    "retentionPolicy": {
      "maxRetentionDays": 14,
      "onSourceDiskDelete": "KEEP_AUTO_SNAPSHOTS"
    },
    "schedule": {
      "dailySchedule": {
        "daysInCycle": 1,
        "startTime": "10:00"
      }
    },
    "snapshotProperties": {
      "guestFlush": false,
      "labels": {}
    }
  }
}
EOF

# Create the snapshot policy using curl
curl -X POST \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @snapshot_policy.json \
  "https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/regions/${REGION}/resourcePolicies"

# Wait for policy to be created
echo "Waiting for policy to be created..."
sleep 10

# Add snapshot policy to each instance and disk
for i in $(seq 1 $INSTANCE_COUNT); do
  INSTANCE_NAME="demo-instance-$i"
  DISK_NAME="disk-$i"
  
  echo "Adding snapshot policy to disk: ${INSTANCE_NAME}"
  
  # Create the JSON payload for the instance disk
  cat > add_policy_instance.json << EOF
{
  "resourcePolicies": [
    "projects/${PROJECT_ID}/regions/${REGION}/resourcePolicies/default-schedule-1"
  ]
}
EOF

  # Add policy to instance disk
  curl -X POST \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @add_policy_instance.json \
    "https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${ZONE}/disks/${INSTANCE_NAME}/addResourcePolicies"
  
  echo "Adding snapshot policy to disk: ${DISK_NAME}"
  
  # Create the JSON payload for the data disk
  cat > add_policy_disk.json << EOF
{
  "resourcePolicies": [
    "projects/${PROJECT_ID}/regions/${REGION}/resourcePolicies/default-schedule-1"
  ]
}
EOF

  # Add policy to data disk
  curl -X POST \
    -H "Authorization: Bearer ${AUTH_TOKEN}" \
    -H "Content-Type: application/json" \
    -d @add_policy_disk.json \
    "https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${ZONE}/disks/${DISK_NAME}/addResourcePolicies"
  
  # Sleep to avoid rate limiting
  sleep 2
done

echo "Cleanup temporary files"
rm -f instance_request.json snapshot_policy.json add_policy_instance.json add_policy_disk.json

echo "Script execution completed"
```

## 3. Declarative Approach: Terraform (Infrastructure as Code)

```hcl
# Variables
variable "project_id" {
  description = "The ID of the project"
  default     = "logan-gallagher"
}

variable "zone" {
  description = "The zone where resources will be created"
  default     = "us-central1-f"
}

variable "region" {
  description = "The region where resources will be created"
  default     = "us-central1"
}

variable "instance_count" {
  description = "Number of instances to create"
  default     = 5
}

# Create the additional disks
resource "google_compute_disk" "additional_disk" {
  count  = var.instance_count
  name   = "disk-${count.index + 1}"
  type   = "pd-ssd"
  zone   = var.zone
  size   = 100
  project = var.project_id
}

# Create the instances
resource "google_compute_instance" "demo_instance" {
  count               = var.instance_count
  name                = "demo-instance-${count.index + 1}"
  machine_type        = "e2-medium"
  zone                = var.zone
  project             = var.project_id
  can_ip_forward      = false
  deletion_protection = false
  enable_display      = false

  labels = {
    goog-ec-src           = "vm_add-tf"
    goog-ops-agent-policy = "v2-x86-template-1-4-0"
  }

  boot_disk {
    auto_delete = true
    device_name = "demo-instance-${count.index + 1}"
    initialize_params {
      image = "projects/debian-cloud/global/images/debian-12-bookworm-v20250415"
      size  = 10
      type  = "pd-balanced"
    }
    mode = "READ_WRITE"
  }

  attached_disk {
    source      = google_compute_disk.additional_disk[count.index].self_link
    device_name = "disk-${count.index + 1}"
    mode        = "READ_WRITE"
  }

  network_interface {
    access_config {
      network_tier = "PREMIUM"
    }
    queue_count = 0
    stack_type  = "IPV4_ONLY"
    subnetwork  = "projects/${var.project_id}/regions/${var.region}/subnetworks/default"
  }

  metadata = {
    enable-osconfig = "TRUE"
  }

  scheduling {
    automatic_restart   = true
    on_host_maintenance = "MIGRATE"
    preemptible         = false
    provisioning_model  = "STANDARD"
  }

  service_account {
    email  = "342279517497-compute@developer.gserviceaccount.com"
    scopes = [
      "https://www.googleapis.com/auth/devstorage.read_only",
      "https://www.googleapis.com/auth/logging.write",
      "https://www.googleapis.com/auth/monitoring.write",
      "https://www.googleapis.com/auth/service.management.readonly",
      "https://www.googleapis.com/auth/servicecontrol",
      "https://www.googleapis.com/auth/trace.append"
    ]
  }

  shielded_instance_config {
    enable_integrity_monitoring = true
    enable_secure_boot          = true
    enable_vtpm                 = true
  }

  reservation_affinity {
    type = "ANY_RESERVATION"
  }

  depends_on = [google_compute_disk.additional_disk]
}

# Create snapshot schedule policy
resource "google_compute_resource_policy" "snapshot_schedule" {
  name    = "default-schedule-1"
  region  = var.region
  project = var.project_id

  snapshot_schedule_policy {
    schedule {
      daily_schedule {
        days_in_cycle = 1
        start_time    = "10:00"
      }
    }
    retention_policy {
      max_retention_days    = 14
      on_source_disk_delete = "KEEP_AUTO_SNAPSHOTS"
    }
    snapshot_properties {
      guest_flush = false
      labels      = {}
    }
  }
}

# Apply snapshot policy to boot disks
resource "google_compute_disk_resource_policy_attachment" "boot_disk_policy" {
  count   = var.instance_count
  name    = google_compute_resource_policy.snapshot_schedule.name
  disk    = google_compute_instance.demo_instance[count.index].name
  zone    = var.zone
  project = var.project_id
}

# Apply snapshot policy to additional disks
resource "google_compute_disk_resource_policy_attachment" "additional_disk_policy" {
  count   = var.instance_count
  name    = google_compute_resource_policy.snapshot_schedule.name
  disk    = google_compute_disk.additional_disk[count.index].name
  zone    = var.zone
  project = var.project_id
}

# Create Ops Agent Policy
module "ops_agent_policy" {
  source        = "github.com/terraform-google-modules/terraform-google-cloud-operations/modules/ops-agent-policy"
  project       = var.project_id
  zone          = var.zone
  assignment_id = "goog-ops-agent-v2-x86-template-1-4-0-us-central1-f"
  
  agents_rule = {
    package_state = "installed"
    version       = "latest"
  }
  
  instance_filter = {
    all = false
    inclusion_labels = [{
      labels = {
        goog-ops-agent-policy = "v2-x86-template-1-4-0"
      }
    }]
  }
}
```

## Why Choose a Declarative Approach with Terraform?

### 1. Infrastructure as Code (IaC) Benefits

| Feature | gcloud | REST API | Terraform |
|---------|--------|----------|-----------|
| **State Management** | ❌ No state tracking | ❌ No state tracking | ✅ Maintains state of all resources |
| **Declarative Syntax** | ❌ Imperative (step-by-step) | ❌ Imperative (step-by-step) | ✅ Declarative (describe desired end state) |
| **Change Detection** | ❌ Manual tracking | ❌ Manual tracking | ✅ Automatic detection through plan phase |
| **Dependency Management** | ❌ Manual ordering | ❌ Manual ordering | ✅ Automatic resource dependency resolution |
| **Version Control** | ⚠️ Script can be versioned | ⚠️ Script can be versioned | ✅ Infrastructure defined as code, versioned alongside application |
| **Variables & Reuse** | ⚠️ Basic shell variables | ⚠️ Basic shell variables | ✅ Rich variable management with types, validation, modules |
| **Idempotence** | ❌ May create duplicates if run twice | ❌ May create duplicates if run twice | ✅ Safe to run multiple times |

### 2. Key Advantages of Terraform

#### State Management

Terraform keeps track of all resources it manages in a state file, enabling it to understand what exists and what needs to change. This allows Terraform to:

- Detect drift (manual changes to infrastructure)
- Apply incremental changes rather than recreating everything
- Safely delete resources when no longer needed

#### Declarative over Imperative

With Terraform, you describe **what** you want (the end state), not **how** to create it (step-by-step instructions):

- No need to write conditionals to check if resources exist
- No need to handle errors for each API call
- No need to implement complex rollback logic

#### Infrastructure Drift Detection

```bash
terraform plan
```

This command previews any changes to be made, allowing you to catch:

- Unintended modifications
- Resources added outside of Terraform
- Configuration errors before they impact production

#### Dependency Management

Terraform automatically handles resource dependencies:

- Creates resources in the correct order
- Modifies resources safely when dependencies change
- Destroys resources in reverse dependency order

#### Change Management

Terraform provides a clear execution plan before making changes:

- See exactly what will be created, modified, or destroyed
- Understand the impact of changes before applying them
- Roll back by reverting to previous configuration

#### Consistency Across Environments

With variables and modules:

- Maintain identical configurations across dev, staging, production
- Change only what differs between environments
- Reuse common patterns and best practices

#### Team Collaboration

Terraform's code-based approach enables:

- Code reviews for infrastructure changes
- Standardization of infrastructure patterns
- Knowledge sharing across the team

### 3. Practical Benefits

#### Maintenance

When a configuration parameter needs to change across all instances:

- **gcloud/REST**: Modify and test a complex loop
- **Terraform**: Change a single variable or parameter

#### Scaling

To increase from 5 instances to 10:

- **gcloud/REST**: Carefully modify the loop, handle existing instances
- **Terraform**: Change the `instance_count` variable from 5 to 10

#### Reproducibility

To recreate the environment in another project:

- **gcloud/REST**: Copy and modify scripts, manage authentication
- **Terraform**: Change the project variable, run `terraform apply`

#### Rollback

If something goes wrong:

- **gcloud/REST**: Manually identify what changed and reverse it
- **Terraform**: Revert to previous configuration and run `terraform apply`

### Conclusion

The Terraform approach offers significant advantages for managing infrastructure at scale. While all three methods can accomplish the same task, Terraform provides better maintainability, scalability, and risk management through its declarative nature and state management capabilities.

For small, one-off tasks, gcloud commands can be simple and effective. For automation and integration scenarios, REST API calls provide flexibility. But for managing long-lived, complex infrastructure—especially in team environments—Terraform's declarative Infrastructure as Code approach is the most robust solution.
