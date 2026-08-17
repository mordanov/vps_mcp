from mcp.server.fastmcp import FastMCP

from . import docker, infrastructure

mcp = FastMCP("VPS Operations")

docker.register(mcp)
infrastructure.register(mcp)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
