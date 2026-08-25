from mcp.server.fastmcp import FastMCP

from . import docker, infrastructure
from .ssh import run_ssh

mcp = FastMCP("VPS Operations")

docker.register(mcp, run_ssh)
infrastructure.register(mcp, run_ssh)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
