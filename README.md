# GCP Demos, Notes and Tricks

A repository of demos and code snippets to highlight the capabilities of Google Cloud Platform (GCP). This repository serves as a learning resource and reference for common GCP implementation patterns.

## Table of Contents

| Directory | Description |
|-----------|-------------|
| [`bigquery`](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/bigquery) | Code snippets and demos for BigQuery |
| [`compute`](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/compute) | Code snippets and demos for Compute Engine |
| [`gke`](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/gke) | Code snippets and demos for Google Kubernetes Engine |
| [`modules`](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/modules) | Shared Terraform modules for GCP demos |
| [`run`](https://github.com/gallaglo/gcp-demos-notes-and-tricks/tree/main/run) | Code snippets and demos for Cloud Run |

## Prerequisites

- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
- [Terraform](https://developer.hashicorp.com/terraform/downloads) (for infrastructure code)
- A Google Cloud Project with billing enabled
- Appropriate IAM permissions for the services you want to use

## Setup

1. Clone the repository:

```bash
git clone https://github.com/gallaglo/gcp-demos-notes-and-tricks.git
cd gcp-demos-notes-and-tricks
```

2. Configure your Google Cloud project:

```bash
gcloud auth login
gcloud config set project YOUR_PROJECT_ID
```

3. Navigate to the specific demo directory you want to try and follow the README instructions in that directory.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Best Practices

Each demo in this repository follows these best practices:

- Infrastructure as Code (IaC) using Terraform
- Principle of least privilege for IAM permissions
- Clear documentation and setup instructions
- Clean up instructions to avoid unnecessary charges

## Related Resources

- [Google Cloud Documentation](https://cloud.google.com/docs)
- [Google Cloud Architecture Center](https://cloud.google.com/architecture)
- [Terraform GCP Provider Documentation](https://registry.terraform.io/providers/hashicorp/google/latest/docs)

## License

Copyright 2024 gallaglo

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

For the full license text, see the [LICENSE](LICENSE) file.
