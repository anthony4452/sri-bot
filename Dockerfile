# ===== Base: Playwright + Node-RED + Python + VNC + noVNC =====
FROM mcr.microsoft.com/playwright:v1.43.0-focal

ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_RED_USERDIR=/usr/src/node-red
ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"
ENV DISPLAY=:99
ENV SCREEN_WIDTH=1920
ENV SCREEN_HEIGHT=1080
ENV SCREEN_DEPTH=24

# Instalar dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-venv python3-dev build-essential curl ca-certificates \
    xvfb x11vnc fluxbox net-tools wget novnc websockify supervisor \
    && rm -rf /var/lib/apt/lists/*

# Instalar Node-RED global
RUN npm install -g --unsafe-perm node-red node-red-dashboard

# Crear carpetas de trabajo
RUN mkdir -p /usr/src/scripts /usr/src/descargas ${NODE_RED_USERDIR} \
    && chmod -R 777 /usr/src

# Configurar entorno Python
RUN python3 -m venv ${VENV_PATH} \
    && . ${VENV_PATH}/bin/activate \
    && pip install --upgrade pip \
    && pip install playwright flask pandas openpyxl \
    && playwright install chromium

# Copiar scripts
COPY ./scripts /usr/src/scripts
RUN chmod -R 777 /usr/src/scripts

# Carpeta de trabajo
WORKDIR ${NODE_RED_USERDIR}

# Exponer puertos Node-RED y noVNC
EXPOSE 1880 6080

# Copiar configuración de supervisord
COPY supervisord.conf /etc/supervisord.conf

# Iniciar todo con supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
