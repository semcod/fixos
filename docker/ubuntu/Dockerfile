FROM ubuntu:24.04

# Podstawowe narzędzia systemowe
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-psutil \
    python3-venv \
    systemd \
    procps \
    util-linux \
    alsa-utils \
    pulseaudio-utils \
    pipewire \
    wireplumber \
    findutils \
    git \
    lsof \
    dbus \
    udev \
    sudo \
    curl \
    wget \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Zainstaluj fixos
WORKDIR /app
COPY . /app
RUN pip3 install -e ".[dev]" --quiet --break-system-packages

# Ustaw env testowy
ENV FIXOS_TEST_MODE=1
ENV LLM_PROVIDER=gemini
ENV PYTHONPATH="/app"

CMD ["/bin/bash"]
