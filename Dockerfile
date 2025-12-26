FROM python:3.11-slim

# Install basics
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    xvfb \
    libxi6 \
    libnss3 \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
# We download the .deb manually to ensure we handle dependencies via apt-get -f install if needed, 
# but usually apt-get install ./google-chrome... works best.
RUN wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get update \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*

# Set up working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# Run command
CMD sh -c "Xvfb :99 -screen 0 1280x1024x24 & python bot_combined.py"
