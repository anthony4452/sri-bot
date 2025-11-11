FROM mcr.microsoft.com/playwright:v1.43.0-focal

ENV DEBIAN_FRONTEND=noninteractive
ENV NODE_RED_USERDIR=/usr/src/node-red
ENV VENV_PATH=/opt/venv
ENV PATH="${VENV_PATH}/bin:${PATH}"
ENV DISPLAY=:99

# Instalar dependencias
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-venv python3-dev build-essential curl ca-certificates \
    xvfb x11vnc fluxbox net-tools wget novnc websockify supervisor \
    && rm -rf /var/lib/apt/lists/*

# Instalar Node-RED
RUN npm install -g --unsafe-perm node-red node-red-dashboard

# Crear carpetas de trabajo
RUN mkdir -p /usr/src/scripts /usr/src/descargas ${NODE_RED_USERDIR} \
    && chmod -R 777 /usr/src

# Configurar Python y Playwright
RUN python3 -m venv ${VENV_PATH} \
    && . ${VENV_PATH}/bin/activate \
    && pip install --upgrade pip \
    && pip install playwright flask \
    && playwright install chromium

# Copiar scripts
COPY ./scripts /usr/src/scripts
RUN chmod -R 777 /usr/src/scripts

# Carpeta de trabajo
WORKDIR ${NODE_RED_USERDIR}

# Exponer puertos Node-RED y noVNC
EXPOSE 1880 6080

# Supervisord
COPY supervisord.conf /etc/supervisord.conf
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]
