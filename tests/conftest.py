import os
import sys
import types

# Provide a lightweight stub for optional dependencies that are not installed in the
# test environment. The application imports ``MultiServerMCPClient`` from
# ``langchain_mcp_adapters.client`` during module import time, so we pre-populate
# ``sys.modules`` with a compatible shim to prevent ``ImportError``.
if "langchain_mcp_adapters" not in sys.modules:
    mcp_module = types.ModuleType("langchain_mcp_adapters")
    client_submodule = types.ModuleType("langchain_mcp_adapters.client")

    class _DummyMultiServerMCPClient:
        def __init__(self, *args, **kwargs):  # pragma: no cover - behaviour is irrelevant
            self.args = args
            self.kwargs = kwargs

    client_submodule.MultiServerMCPClient = _DummyMultiServerMCPClient
    mcp_module.client = client_submodule

    sys.modules["langchain_mcp_adapters"] = mcp_module
    sys.modules["langchain_mcp_adapters.client"] = client_submodule

try:
    import langchain.agents as _lc_agents  # type: ignore
except ImportError:  # pragma: no cover - dependency may be optional
    _lc_agents = types.ModuleType("langchain.agents")
    sys.modules["langchain.agents"] = _lc_agents

if not hasattr(_lc_agents, "create_agent"):

    def _dummy_create_agent(*args, **kwargs):
        class _DummyGraph:
            async def ainvoke(self_inner, *a, **kw):
                return {}

        return _DummyGraph()

    _lc_agents.create_agent = _dummy_create_agent  # type: ignore[attr-defined]

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
