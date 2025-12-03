# Workflow Model Downloader - Custom Node

A ComfyUI custom node that downloads models specified in workflow files on demand.

## Features

- **Multiple Input Methods**:
  - Use currently loaded workflow
  - Select from saved workflow files
  - Paste workflow JSON directly

- **Selective Downloads**:
  - Choose which model types to download (checkpoints, VAE, ControlNet, LoRAs)
  - Skip already downloaded models
  - Resume interrupted downloads

- **Smart Extraction**:
  - Extracts model info from workflow metadata
  - Parses node inputs to find model references
  - Supports custom model manifests

## Installation

This node is already included in the `custom_nodes` directory. It requires:

```bash
pip install huggingface-hub
```

## Usage

### 1. Add Node to Workflow

Right-click in ComfyUI → Add Node → utils → Download Workflow Models

### 2. Configure Settings

**Mode Options**:
- `current_workflow` - Downloads models from the currently loaded workflow
- `from_file` - Downloads models from a selected workflow file

**Download Options** (checkboxes):
- Download Checkpoints
- Download VAE
- Download ControlNet
- Download LoRAs

### 3. Select Workflow (if using `from_file` mode)

Choose a workflow file from the dropdown, or paste JSON in the `workflow_json` field.

### 4. Execute

Connect to an output node or set this as OUTPUT_NODE to trigger download.

## Workflow JSON Format

For the node to download models, your workflow needs model information in one of these formats:

### Option 1: Custom Metadata (Recommended)

Add a `model_manifest` to your workflow's `extra_pnginfo`:

```json
{
  "extra_pnginfo": {
    "model_manifest": {
      "checkpoints": [
        {
          "name": "SD 1.5",
          "repo_id": "runwayml/stable-diffusion-v1-5",
          "filename": "v1-5-pruned-emaonly.safetensors"
        }
      ],
      "vae": [
        {
          "name": "SD VAE",
          "repo_id": "stabilityai/sd-vae-ft-mse",
          "filename": "vae-ft-mse-840000-ema-pruned.safetensors"
        }
      ]
    }
  }
}
```

### Option 2: Node-based Detection

The node automatically extracts model references from loader nodes:
- `CheckpointLoaderSimple` → extracts `ckpt_name`
- `VAELoader` → extracts `vae_name`
- `ControlNetLoader` → extracts `control_net_name`
- `LoraLoader` → extracts `lora_name`

**Note**: Node-based detection only checks if files exist locally. For automatic downloads, use Option 1 with HuggingFace repo info.

## Example Workflow

```json
{
  "1": {
    "class_type": "CheckpointLoaderSimple",
    "inputs": {
      "ckpt_name": "sd_xl_base_1.0.safetensors"
    }
  },
  "extra_pnginfo": {
    "model_manifest": {
      "checkpoints": [
        {
          "name": "SDXL Base 1.0",
          "repo_id": "stabilityai/stable-diffusion-xl-base-1.0",
          "filename": "sd_xl_base_1.0.safetensors",
          "size_gb": 6.9
        }
      ]
    }
  }
}
```

## Output

The node returns a status string:
- `✅ Downloaded N model(s)` - Success
- `❌ N failed` - Some downloads failed
- `ℹ️ No models found in workflow` - No models detected

Check the console/logs for detailed progress information.

## Use Cases

### 1. Workflow Sharing
Share workflows with model manifests so users can automatically download required models.

### 2. Environment Setup
Quickly set up a new ComfyUI instance with all models from your favorite workflows.

### 3. Model Management
Verify which models are missing before running a workflow.

### 4. Batch Downloads
Download models for multiple workflows in one go.

## Integration with Azure File Share

This node works seamlessly with the Azure File Share setup:
- Models are downloaded to the mounted storage
- Downloads are persisted across container restarts
- Multiple container instances can share the same models

## Troubleshooting

**"No models found in workflow"**
- Check that your workflow has model manifest metadata
- Verify the workflow JSON is valid
- Use node-based detection by including loader nodes

**"Failed to download model"**
- Check internet connectivity
- Verify HuggingFace repo_id and filename are correct
- Check disk space on mounted storage
- Review logs for specific error messages

**"Model already exists"**
- This is normal - the node skips existing models
- No re-download needed unless file is corrupted

## Advanced Usage

### Custom Model Paths

The node uses ComfyUI's `folder_paths.models_dir` which respects your `extra_model_paths.yaml` configuration.

### Programmatic Usage

You can trigger downloads via API by including this node in your prompt:

```python
{
  "workflow_downloader": {
    "class_type": "WorkflowModelDownloader",
    "inputs": {
      "mode": "current_workflow",
      "download_checkpoints": True,
      "download_vae": True
    }
  }
}
```

## Contributing

To add support for additional model types or loaders, edit `_extract_from_node()` in the source code.

## License

MIT License - Free to use and modify
