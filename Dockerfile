FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    SYSTEM_ENV_LOCATION=/the_system_environement \
    SYSTEM_ENV_NAME=local_env \
    PIP_CACHE_DIR=/pip-cache \
    XDG_CACHE_HOME=/pip-cache \
    BASE_BASHRC=/root/.bashrc \
    BASH_PROFILE=/root/.bash_profile

# Restore colored ls, prompt, and normal user-like shell for root
RUN set -eux; \
    # Create /root/.bashrc if missing
    touch ${BASE_BASHRC}; \
    # Enable colored 'ls' and 'grep' like a normal user
    echo "alias ls='ls --color=auto'" >> ${BASE_BASHRC}; \
    echo "alias ll='ls -alF'" >> ${BASE_BASHRC}; \
    echo "alias grep='grep --color=auto'" >> ${BASE_BASHRC}; \
    # Add a colored PS1 prompt similar to Ubuntu’s default
    echo 'PS1="\\[\\e[1;32m\\]\\u@\\h:\\[\\e[1;34m\\]\\w\\$\\[\\e[0m\\] "' >> ${BASE_BASHRC}; \
    # Source /etc/bash.bashrc if it exists (for distros that use it)
    echo '[ -f /etc/bash.bashrc ] && source /etc/bash.bashrc' >> ${BASE_BASHRC}; \
    # Ensure bash uses the rc file even for non-login interactive shells
    echo "export BASH_ENV=${BASE_BASHRC}" >> ${BASH_PROFILE}

# Setting pip's cache directory
RUN mkdir -p "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" \
    && chmod -R 0777 "$PIP_CACHE_DIR" "$XDG_CACHE_HOME" \
    && pip config set global.cache-dir "$PIP_CACHE_DIR" \
    && python -m pip config set global.cache-dir "$PIP_CACHE_DIR"


# Update de docker system, install tzdata, set the timezone to Europe/Paris, install mariadb dependencies and install python in the container
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    tzdata \
    bash \
    libmariadb-dev \
    python3-dev \
    build-essential \
    && ln -fs /usr/share/zoneinfo/Europe/Paris /etc/localtime \
    && dpkg-reconfigure --frontend noninteractive tzdata \
    && python -m pip install -U pip \
    && rm -rf /var/lib/apt/lists/*

# Inject environement activations into shell configuration files
RUN echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/profile \
    && echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/zprofile \
    && echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/csh.cshrc \
    && echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/csh.login \
    && echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/bash.bashrc \
    && mkdir -p /etc/zsh/ && echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/zsh/zshrc \
    && mkdir -p /etc/fish && echo ". ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate" >> /etc/fish/config.fish

# Go to the working folder
WORKDIR ${HOME}

# Copy the content of the backend into the container
COPY . ${HOME}

# Create a system environement and also run the setup code from the project
RUN mkdir -p ${SYSTEM_ENV_LOCATION} \
    && python3 -m venv ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME} \
    && . ${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate \
    && python -m pip install -U pip \
    && python -m pip install --no-cache-dir -r ./requirements.txt \
    && deactivate

# Expose the ports that need to be used
EXPOSE 1024-9000

# Cleaning cache
RUN apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Creating the entry script inside the image (no build-context file required)
RUN cat > /usr/local/bin/start.sh <<'EOF'
#!/usr/bin/env sh
set -euo pipefail

VENV_ACT="${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/activate"
VENV_PY="${SYSTEM_ENV_LOCATION}/${SYSTEM_ENV_NAME}/bin/python"
PYTHON_CMD="python"

# Use POSIX '.' to source
if [ -f "$VENV_ACT" ]; then
  . "$VENV_ACT" || true
  [ -x "$VENV_PY" ] && PYTHON_CMD="$VENV_PY"
fi

if [ -f "./__main__.py" ]; then
  exec "$PYTHON_CMD" "./__main__.py"
fi

if [ -f "./__init__.py" ]; then
  exec "$PYTHON_CMD" "./__init__.py"
fi

for f in ./*.py; do
  [ "$f" = "./__main__.py" ] && continue
  [ "$f" = "./__init__.py" ] && continue
  [ ! -f "$f" ] && continue
  exec "$PYTHON_CMD" "$f"
done

echo "No Python entrypoint found in the working directory." >&2
exit 1
EOF

# Granting executable rights
RUN chmod +x /usr/local/bin/start.sh

# setting the script to be the entrypoint
ENTRYPOINT ["/usr/local/bin/start.sh"]
