import os

from dotenv import load_dotenv

load_dotenv()

VPS_HOST: str = os.environ["VPS_HOST"]
VPS_PORT: int = int(os.getenv("VPS_PORT", "22"))
VPS_USER: str = os.environ["VPS_USER"]
VPS_SSH_KEY: str = os.path.expanduser(os.environ["VPS_SSH_KEY"])
VPS_KNOWN_HOSTS: str = os.getenv("VPS_KNOWN_HOSTS", "").strip()
DOCKER_COMPOSE_DIR: str = os.getenv("DOCKER_COMPOSE_DIR", "").strip()
MAX_OUTPUT_CHARS: int = int(os.getenv("MAX_OUTPUT_CHARS", "20000"))
