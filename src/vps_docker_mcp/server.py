from mcp.server.fastmcp import FastMCP

from . import database, docker, github, infrastructure
from .ssh import run_ssh

mcp = FastMCP("VPS Operations")

docker.register(mcp, run_ssh)
infrastructure.register(mcp, run_ssh)
github.register(mcp, run_ssh)
database.register(mcp, run_ssh)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
