FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /srv

# CPU-only PyTorch: the default wheel bundles CUDA and is several GB larger.
RUN pip install torch==2.15.0 --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt requirements-dev.txt ./
ARG INSTALL_DEV=false
RUN pip install -r requirements.txt && if [ "$INSTALL_DEV" = "true" ]; then pip install -r requirements-dev.txt; fi

COPY app ./app
COPY tests ./tests
COPY eval ./eval

# Skeleton profiles are mounted from /shared and model weights cached in /models (see docker-compose.yml).
ENV AI_SKELETON_PROFILES_PATH=/shared/skeleton_profiles \
    HF_HOME=/models
EXPOSE 8001
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
