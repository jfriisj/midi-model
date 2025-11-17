# Use newer PyTorch base image compatible with transformers 4.55+
FROM pytorch/pytorch:2.5.1-cuda12.4-cudnn9-devel

# Set working directory
WORKDIR /app

# Avoid interactive prompts during build
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install system dependencies
RUN apt-get update && apt-get install -y \
    fluidsynth \
    fluid-soundfont-gm \
    wget \
    git \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Download soundfont if not present (for audio synthesis)
RUN if [ ! -f soundfont.sf2 ]; then \
    wget -O soundfont.sf2 "https://huggingface.co/skytnt/midi-model/resolve/main/soundfont.sf2"; \
    fi

# Create necessary directories
RUN mkdir -p outputs sample lightning_logs models

# Expose port for Gradio app
EXPOSE 7860

# Set environment variables
ENV GRADIO_SERVER_NAME=0.0.0.0
ENV GRADIO_SERVER_PORT=7860

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7860 || exit 1

# Default command - run the main app
CMD ["python", "app.py", "--share"]