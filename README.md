# EVM Processor

EVM Processor is a Python-based application designed to fetch and persist blockchain block data from an RPC endpoint, specifically a Tendermint endpoint (`:26657`). This application is built for fault tolerance and ensures the continuity of block processing, even after restarts.

---

## Features

- **Fetch blocks from RPC**: Queries blocks from a Tendermint RPC endpoint (`:26657`) and retrieves block height and hash.
- **Persistence**: Stores block data locally in a CSV file (`blocks.csv`), ensuring continuity across sessions.
- **State management**: Prevents multiple processors from running concurrently by utilizing a lock file.
- **Graceful shutdown**: Handles shutdown signals to ensure the state is safely updated.
- **Dockerized deployment**: Easily build and deploy using the provided `Dockerfile`.
- **Automated CI/CD**: Docker images are built and pushed to GitHub Container Registry (GHCR) on every push to the `main` branch using GitHub Actions.
- **ArgoCD integration**: The Docker image is deployed via ArgoCD for streamlined application management.

---

## Repository Structure

```plaintext
.
├── Dockerfile               # Defines the containerized environment for the application
├── LICENSE                  # License file
├── README.md                # Documentation
├── block_processor.py       # Main application script
├── requirements.txt         # Python dependencies
├── .github/
│   └── workflows/
│       └── docker-build-push.yml  # GitHub Actions workflow for Docker build and push
```

---

## Requirements

- Python 3.9+
- Tendermint RPC endpoint (`:26657`)
- Disk storage for persistent block data

---

## Usage

### Environment Variables

The application relies on the following environment variables:

| Variable       | Description                                  | Default       |
|----------------|----------------------------------------------|---------------|
| `TM_NODE`      | Tendermint RPC endpoint URL                 | Not defined   |
| `STORAGE_PATH` | Directory to persist block data (`blocks.csv`) | `/data`       |

### Running Locally

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Run the application**:
   ```bash
   python block_processor.py
   ```

### Running with Docker

1. **Build the Docker image**:
   ```bash
   docker build -t evm-processor:latest .
   ```

2. **Run the Docker container**:
   ```bash
   docker run -e TM_NODE=http://<tendermint-url>:26657 -v /your/storage/path:/data evm-processor:latest
   ```

---

## CI/CD

The repository includes a GitHub Actions workflow to automatically build and push the Docker image to GitHub Container Registry (GHCR) on every push to the `main` branch.

### Workflow Highlights

- **Versioning**: Auto-increments the patch version based on the latest Git tag.
- **Build and push**: Docker image is built and tagged as:
  - `latest`
  - `v<version>`

---

## Deployment with ArgoCD

This application is deployed using [ArgoCD](https://argoproj.github.io/argo-cd/). It integrates with the deployment YAML in the [fhevm-zama repository](https://github.com/amunt0/fhevm-zama/blob/main/chart/templates/deployments/evm-processor-deployment.yaml).

Example deployment reference:

```yaml
image: ghcr.io/<your-repo>/block-processor:latest
```



