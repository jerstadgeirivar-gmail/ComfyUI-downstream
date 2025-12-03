"""
Workflow Model Downloader Custom Node
======================================

Downloads models specified in ComfyUI workflow files on demand.
Can load from file path or use the currently loaded workflow.

Author: Generated for ComfyUI
License: MIT
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from huggingface_hub import hf_hub_download

import folder_paths
from server import PromptServer

# Configure logging
logger = logging.getLogger(__name__)


class WorkflowModelDownloader:
    """
    Downloads models from a workflow file or currently loaded workflow.
    
    This node extracts model information from workflow metadata and downloads
    them using HuggingFace Hub for better error handling and resume support.
    """
    
    def __init__(self):
        self.models_path = folder_paths.models_dir
    
    @classmethod
    def INPUT_TYPES(cls):
        # Get list of workflow files from user directory
        workflow_files = cls._get_workflow_files()
        
        return {
            "required": {
                "mode": (["current_workflow", "from_file"], {
                    "default": "current_workflow"
                }),
                "download_checkpoints": ("BOOLEAN", {"default": True}),
                "download_vae": ("BOOLEAN", {"default": True}),
                "download_controlnet": ("BOOLEAN", {"default": True}),
                "download_loras": ("BOOLEAN", {"default": False}),
            },
            "optional": {
                "workflow_file": (workflow_files, {
                    "tooltip": "Select a workflow file to download models from"
                }),
                "workflow_json": ("STRING", {
                    "multiline": True,
                    "default": "",
                    "tooltip": "Paste workflow JSON here or leave empty to use current"
                }),
            },
            "hidden": {
                "prompt": "PROMPT",
                "extra_pnginfo": "EXTRA_PNGINFO",
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("status",)
    FUNCTION = "download_models"
    OUTPUT_NODE = True
    CATEGORY = "utils"
    
    @staticmethod
    def _get_workflow_files() -> List[str]:
        """Get list of available workflow JSON files"""
        workflow_files = ["(select file)"]
        
        # Check user/default/workflows directory
        user_workflows = Path(folder_paths.base_path) / "user" / "default" / "workflows"
        if user_workflows.exists():
            for workflow_file in user_workflows.glob("*.json"):
                workflow_files.append(str(workflow_file.relative_to(folder_paths.base_path)))
        
        return workflow_files
    
    def _extract_models_from_workflow(self, workflow: Dict) -> Dict[str, List[Dict]]:
        """
        Extract model information from workflow JSON.
        
        Returns dict with keys: checkpoints, vae, controlnet, loras
        Each contains list of model dicts with name, repo_id, filename, etc.
        """
        models = {
            "checkpoints": [],
            "vae": [],
            "controlnet": [],
            "loras": []
        }
        
        # Check for model manifest in extra_pnginfo (custom metadata)
        extra_info = workflow.get("extra_pnginfo", {})
        if "model_manifest" in extra_info:
            manifest = json.loads(extra_info["model_manifest"]) if isinstance(extra_info["model_manifest"], str) else extra_info["model_manifest"]
            return manifest
        
        # Fallback: Extract from nodes (if workflow has node structure)
        nodes = workflow.get("nodes", {})
        if isinstance(nodes, dict):
            for node_id, node_data in nodes.items():
                self._extract_from_node(node_data, models)
        elif isinstance(nodes, list):
            for node_data in nodes:
                self._extract_from_node(node_data, models)
        
        # Also check workflow root level
        for node_id, node_data in workflow.items():
            if isinstance(node_data, dict) and "class_type" in node_data:
                self._extract_from_node(node_data, models)
        
        return models
    
    def _extract_from_node(self, node_data: Dict, models: Dict[str, List[Dict]]):
        """Extract model info from a single node"""
        class_type = node_data.get("class_type", "")
        inputs = node_data.get("inputs", {})
        
        # CheckpointLoaderSimple, CheckpointLoader, etc.
        if "checkpoint" in class_type.lower() or "ckpt" in class_type.lower():
            ckpt_name = inputs.get("ckpt_name", "")
            if ckpt_name and not any(m.get("filename") == ckpt_name for m in models["checkpoints"]):
                models["checkpoints"].append({
                    "name": ckpt_name,
                    "filename": ckpt_name,
                    "source": "node_input"
                })
        
        # VAELoader
        if "vae" in class_type.lower() and "loader" in class_type.lower():
            vae_name = inputs.get("vae_name", "")
            if vae_name and not any(m.get("filename") == vae_name for m in models["vae"]):
                models["vae"].append({
                    "name": vae_name,
                    "filename": vae_name,
                    "source": "node_input"
                })
        
        # ControlNetLoader
        if "controlnet" in class_type.lower() and "loader" in class_type.lower():
            control_name = inputs.get("control_net_name", "")
            if control_name and not any(m.get("filename") == control_name for m in models["controlnet"]):
                models["controlnet"].append({
                    "name": control_name,
                    "filename": control_name,
                    "source": "node_input"
                })
        
        # LoraLoader
        if "lora" in class_type.lower() and "loader" in class_type.lower():
            lora_name = inputs.get("lora_name", "")
            if lora_name and not any(m.get("filename") == lora_name for m in models["loras"]):
                models["loras"].append({
                    "name": lora_name,
                    "filename": lora_name,
                    "source": "node_input"
                })
    
    def _download_model(self, model: Dict, model_type: str) -> bool:
        """Download a single model"""
        name = model.get("name", "Unknown")
        
        # Check if model has HuggingFace repo info
        if "repo_id" in model and "filename" in model:
            repo_id = model["repo_id"]
            filename = model["filename"]
            target_dir = os.path.join(self.models_path, model_type)
            target_path = os.path.join(target_dir, filename)
            
            # Check if already exists
            if os.path.exists(target_path):
                size_mb = os.path.getsize(target_path) / (1024 * 1024)
                logger.info(f"✅ {name} already exists ({size_mb:.1f} MB). Skipping.")
                return True
            
            logger.info(f"📥 Downloading {name} from {repo_id}...")
            
            try:
                Path(target_dir).mkdir(parents=True, exist_ok=True)
                
                downloaded_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=filename,
                    local_dir=target_dir,
                    local_dir_use_symlinks=False,
                    resume_download=True
                )
                
                size_mb = os.path.getsize(downloaded_path) / (1024 * 1024)
                logger.info(f"✅ Downloaded {name} successfully ({size_mb:.1f} MB)")
                return True
            
            except Exception as e:
                logger.error(f"❌ Failed to download {name}: {e}")
                return False
        
        else:
            # Model doesn't have download info, check if it exists locally
            filename = model.get("filename", name)
            target_dir = os.path.join(self.models_path, model_type)
            target_path = os.path.join(target_dir, filename)
            
            if os.path.exists(target_path):
                logger.info(f"✅ {name} already exists locally")
                return True
            else:
                logger.warning(f"⚠️  {name} not found and no download info available")
                return False
    
    def download_models(self, mode, download_checkpoints, download_vae, 
                       download_controlnet, download_loras,
                       workflow_file=None, workflow_json="", 
                       prompt=None, extra_pnginfo=None):
        """Main execution function"""
        
        logger.info("🎨 Workflow Model Downloader")
        logger.info(f"Mode: {mode}")
        
        # Load workflow JSON
        workflow = None
        
        if mode == "from_file" and workflow_file and workflow_file != "(select file)":
            # Load from file
            workflow_path = Path(folder_paths.base_path) / workflow_file
            try:
                with open(workflow_path, 'r', encoding='utf-8') as f:
                    workflow = json.load(f)
                logger.info(f"📋 Loaded workflow from: {workflow_file}")
            except Exception as e:
                error_msg = f"❌ Failed to load workflow file: {e}"
                logger.error(error_msg)
                return (error_msg,)
        
        elif workflow_json:
            # Load from JSON string
            try:
                workflow = json.loads(workflow_json)
                logger.info("📋 Loaded workflow from JSON input")
            except Exception as e:
                error_msg = f"❌ Failed to parse workflow JSON: {e}"
                logger.error(error_msg)
                return (error_msg,)
        
        elif mode == "current_workflow" and extra_pnginfo:
            # Use current workflow from extra_pnginfo
            workflow = extra_pnginfo.get("workflow", {})
            if not workflow and prompt:
                workflow = {"prompt": prompt}
            logger.info("📋 Using current workflow")
        
        else:
            error_msg = "❌ No workflow provided. Select a file, paste JSON, or use current workflow."
            logger.warning(error_msg)
            return (error_msg,)
        
        if not workflow:
            error_msg = "❌ Workflow is empty"
            logger.error(error_msg)
            return (error_msg,)
        
        # Extract models from workflow
        logger.info("🔍 Extracting model information...")
        models = self._extract_models_from_workflow(workflow)
        
        # Download models based on settings
        success_count = 0
        fail_count = 0
        skip_count = 0
        
        total_models = 0
        for model_type in ["checkpoints", "vae", "controlnet", "loras"]:
            total_models += len(models.get(model_type, []))
        
        if total_models == 0:
            msg = "ℹ️  No models found in workflow"
            logger.info(msg)
            return (msg,)
        
        logger.info(f"Found {total_models} model(s) in workflow")
        
        # Download checkpoints
        if download_checkpoints:
            checkpoints = models.get("checkpoints", [])
            if checkpoints:
                logger.info(f"\n📦 Processing {len(checkpoints)} checkpoint(s)...")
                for model in checkpoints:
                    if self._download_model(model, "checkpoints"):
                        success_count += 1
                    else:
                        fail_count += 1
        
        # Download VAE models
        if download_vae:
            vaes = models.get("vae", [])
            if vaes:
                logger.info(f"\n🎨 Processing {len(vaes)} VAE model(s)...")
                for model in vaes:
                    if self._download_model(model, "vae"):
                        success_count += 1
                    else:
                        fail_count += 1
        
        # Download ControlNet models
        if download_controlnet:
            controlnets = models.get("controlnet", [])
            if controlnets:
                logger.info(f"\n🎮 Processing {len(controlnets)} ControlNet model(s)...")
                for model in controlnets:
                    if self._download_model(model, "controlnet"):
                        success_count += 1
                    else:
                        fail_count += 1
        
        # Download LoRA models
        if download_loras:
            loras = models.get("loras", [])
            if loras:
                logger.info(f"\n✨ Processing {len(loras)} LoRA model(s)...")
                for model in loras:
                    if self._download_model(model, "loras"):
                        success_count += 1
                    else:
                        fail_count += 1
        
        # Summary
        logger.info(f"\n{'='*60}")
        logger.info(f"📊 Download Summary:")
        logger.info(f"   ✅ Success: {success_count}")
        logger.info(f"   ❌ Failed: {fail_count}")
        logger.info(f"{'='*60}")
        
        status_msg = f"✅ Downloaded {success_count} model(s)"
        if fail_count > 0:
            status_msg += f", ❌ {fail_count} failed"
        
        return (status_msg,)


# Node registration
NODE_CLASS_MAPPINGS = {
    "WorkflowModelDownloader": WorkflowModelDownloader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "WorkflowModelDownloader": "Download Workflow Models",
}
