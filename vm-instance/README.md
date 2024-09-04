# Demo Steps

## Create a VM instance in the Console with a startup script

* Provision a new VM instance in the GCE console by selecting "Create Instance". In the setup wizard navigate to "Advanced options" > "Management" and paste the contents of [startup-script](https://github.com/gallaglo/gcp-demos-notes-and-tricks/blob/main/mig/startup-script) into the "Automation" form field.
* For additional info or context see: [Passing a Linux startup script directly](https://cloud.google.com/compute/docs/instances/startup-scripts/linux).

## Create a Managed Instance Group (MIG)

* [Create a new instance template](https://cloud.google.com/compute/docs/instance-templates/create-instance-templates#create_a_new_instance_template) with a similar configuration as the single instance provisioned earlier. During setup, navigate to "Advanced options" > "Management" to paste the contents of [startup-script](https://github.com/gallaglo/gcp-demos-notes-and-tricks/blob/main/mig/startup-script) into the "Automantion" form field.
* [Create a MIG with VMs in multiple zones in a region](https://cloud.google.com/compute/docs/instance-groups/distributing-instances-with-regional-instance-groups#creating_a_regional_managed_instance_group), selecting the Instance Template created in the prior step.

## Put a HTTP load balancer in front of the MIG

* [Set up the load balancer](https://cloud.google.com/load-balancing/docs/https/setup-global-ext-https-compute#load-balancer), selecting the Managed Instance Group created in the prior step when creating the Backend Service.
