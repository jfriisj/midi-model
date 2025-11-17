# Docker Setup for MIDI Model

This directory contains Docker configurations for running the MIDI Model project in containerized environments.

## Files

- `Dockerfile` - Main PyTorch-based image with full training and inference capabilities
- `Dockerfile.onnx` - Lightweight ONNX-optimized image for faster inference
- `docker-compose.yml` - Multi-service orchestration configuration

## Quick Start

### Basic Web Application

```bash
# Build and run the main application
docker-compose up midi-model-app

# Access the web interface at http://localhost:7860
```

### ONNX Optimized Version (Faster Inference)

```bash
# Run the lightweight ONNX version
docker-compose --profile onnx up midi-model-onnx

# Access at http://localhost:7861
```

### Training Mode

```bash
# Prepare training data in ./data directory
mkdir data
# Copy your MIDI files to ./data

# Run training
docker-compose --profile training up midi-model-trainer
```

## Services

### midi-model-app
- **Port**: 7860
- **GPU**: Required (NVIDIA)
- **Features**: Full PyTorch model, training, inference
- **Memory**: ~4-8GB VRAM recommended

### midi-model-onnx
- **Port**: 7861
- **GPU**: Optional
- **Features**: Optimized inference, faster startup
- **Memory**: ~2-4GB RAM

### midi-model-trainer
- **GPU**: Required
- **Features**: Model training from MIDI datasets
- **Usage**: One-time training runs

## Volume Mounts

- `./outputs` - Generated MIDI files and audio
- `./models` - Model checkpoints and weights
- `./lightning_logs` - Training logs and metrics
- `./data` - Training data (for training service)

## GPU Support

### Requirements
- NVIDIA Docker runtime
- NVIDIA drivers installed on host
- Docker Compose version 3.8+

### Setup NVIDIA Docker
```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

## Configuration

### Environment Variables

- `GRADIO_SERVER_NAME` - Server bind address (default: 0.0.0.0)
- `GRADIO_SERVER_PORT` - Server port (default: 7860)
- `CUDA_VISIBLE_DEVICES` - GPU device selection

### Custom Models

Place custom model files in `./custom_models/` directory and they'll be mounted into the container.

## Development

### Build from source
```bash
# Build the main image
docker build -t midi-model .

# Build ONNX image
docker build -f Dockerfile.onnx -t midi-model-onnx .
```

### Run with custom command
```bash
docker run -it --gpus all -p 7860:7860 \
  -v $(pwd)/outputs:/app/outputs \
  midi-model python train.py --help
```

## Troubleshooting

### GPU not detected
- Verify NVIDIA Docker runtime: `docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi`
- Check GPU availability: `nvidia-smi`

### Out of memory errors
- Reduce batch size in training
- Use ONNX version for inference
- Close other GPU applications

### Slow model loading
- Use ONNX version for faster startup
- Pre-download models to `./models` directory

### Audio synthesis issues
- FluidSynth is included in both images
- Soundfont is automatically downloaded
- Check volume mounts for output directory

## Production Deployment

For production use:

1. Use ONNX version for better performance
2. Set up reverse proxy (nginx)
3. Configure proper logging
4. Use external model storage
5. Set resource limits

Example nginx configuration:
```nginx
upstream midi-app {
    server localhost:7860;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://midi-app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```