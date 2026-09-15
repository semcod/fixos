FROM fedora:40

# Podstawowe narzędzia systemowe
RUN dnf install -y \
    python3 \
    python3-pip \
    python3-psutil \
    systemd \
    procps-ng \
    util-linux \
    alsa-utils \
    pulseaudio-utils \
    pipewire \
    wireplumber \
    findutils \
    git \
    which \
    udev \
    dbus \
    lsof \
    sudo \
    curl \
    && dnf clean all

# Zainstaluj fixos
WORKDIR /app
COPY . /app
RUN pip3 install -e ".[dev]" --quiet

# Ustaw env testowy
ENV FIXOS_TEST_MODE=1
ENV LLM_PROVIDER=gemini

CMD ["/bin/bash"]
