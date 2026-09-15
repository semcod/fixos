FROM debian:12-slim

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
    pipewire \
    wireplumber \
    findutils \
    git \
    lsof \
    dbus \
    udev \
    sudo \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Zainstaluj fixos
WORKDIR /app
COPY . /app
RUN pip3 install -e ".[dev]" --quiet --break-system-packages

# Ustaw env testowy
ENV FIXOS_TEST_MODE=1
ENV LLM_PROVIDER=gemini

CMD ["/bin/bash"]
