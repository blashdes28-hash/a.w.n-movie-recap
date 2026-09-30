FROM python:3.11-slim

# Install system dependencies including ffmpeg, git, curl, and Myanmar fonts
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-noto-core \
    fonts-sil-padauk \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Setup non-root user for Hugging Face Spaces (UID 1000) & security
RUN useradd -m -u 1000 user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR $HOME/app

# Install Python dependencies
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade -r requirements.txt

# Copy project files
COPY --chown=user . $HOME/app

# Ensure runtime directories exist with full read/write permissions
RUN mkdir -p uploads output data fonts && chmod -R 777 uploads output data fonts

ENV PORT=7860
EXPOSE 7860

CMD ["python", "run.py"]
