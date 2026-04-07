"""Gunicorn configuration for UnityLens."""

import multiprocessing
import os

# Server socket
bind = os.environ.get("UNITYLENS_BIND", "0.0.0.0:8000")

# Worker processes
workers = int(os.environ.get("UNITYLENS_WORKERS", min(multiprocessing.cpu_count() * 2 + 1, 8)))
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = int(os.environ.get("UNITYLENS_TIMEOUT", 120))
graceful_timeout = int(os.environ.get("UNITYLENS_GRACEFUL_TIMEOUT", 30))
keepalive = int(os.environ.get("UNITYLENS_KEEPALIVE", 5))

# Logging
accesslog = os.environ.get("UNITYLENS_ACCESS_LOG", "-")
errorlog = os.environ.get("UNITYLENS_ERROR_LOG", "-")
loglevel = os.environ.get("UNITYLENS_LOG_LEVEL", "info")

# Process naming
proc_name = "unitylens"

# Preload app for faster worker spawns (shares memory via copy-on-write)
preload_app = True
