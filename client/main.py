"""AgentHub desktop client entry point."""

import argparse
import asyncio
import logging
import os
import sys
import threading
import webbrowser

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agenthub_client import AgentHubClient
from client_config import (
    load_capability_api_keys,
    load_capability_configs,
    load_config,
    repair_config,
    save_capability_api_key,
    save_capability_config,
    update_config,
)
from local_workbench import LocalLogBuffer
from local_workbench import LocalWorkbenchServer
from plugins.isp_broadband import ISPBroadbandPlugin


def main():
    parser = argparse.ArgumentParser(description="AgentHub Client")
    parser.add_argument("--api-key", default="", help="API key issued by AgentHub")
    parser.add_argument("--server", default="wss://www.agenthub.wang", help="AgentHub WebSocket server")
    parser.add_argument("--workbench-port", type=int, default=8765, help="Local workbench port")
    parser.add_argument("--no-workbench", action="store_true", help="Disable the local workbench")
    parser.add_argument("--no-open-workbench", action="store_true", help="Do not open the local workbench in browser")
    parser.add_argument("--debug", action="store_true", help="Enable debug logs")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )

    saved = repair_config()
    api_key = args.api_key or saved.get("api_key", "")
    server_url = args.server or saved.get("server_url", "wss://www.agenthub.wang")
    if args.api_key:
        update_config({"api_key": api_key, "server_url": server_url})

    log_buffer = LocalLogBuffer()
    logging.getLogger().addHandler(log_buffer)

    client = AgentHubClient(api_key=api_key, server_url=server_url, capability_api_keys=load_capability_api_keys())
    workbench = None
    client.register_plugin_instance("isp-smart-cs", ISPBroadbandPlugin(config={}))
    client.set_local_configs(load_capability_configs())

    try:
        from plugins.vision import VisionPlugin

        client.register_plugin_instance("ai-smart-monitor", VisionPlugin(config={}))
    except ImportError:
        logging.info("Vision plugin not available, skipping")

    try:
        if not args.no_workbench:

            def save_binding(api_key_value: str, server_url_value: str, cap_id: str = ""):
                if cap_id:
                    save_capability_api_key(cap_id, api_key_value)
                    client.set_capability_api_key(cap_id, api_key_value, server_url_value)
                update_config({"server_url": server_url_value})
                if not client.api_key:
                    update_config({"api_key": api_key_value})

            def save_local_config(cap_id: str, capability_config: dict):
                saved_config = save_capability_config(cap_id, capability_config)
                client.set_local_config(cap_id, saved_config)
                return saved_config

            workbench = LocalWorkbenchServer(
                client,
                port=args.workbench_port,
                on_bind=save_binding,
                on_save_local_config=save_local_config,
                log_buffer=log_buffer,
            )
            workbench.start()
            logging.info("Local workbench URL: %s", workbench.url)
            if not args.no_open_workbench:
                threading.Timer(0.8, lambda: webbrowser.open(workbench.url)).start()
            if not api_key:
                logging.info("API Key not bound. Open the local workbench to bind this client.")
        asyncio.run(client.run())
    except KeyboardInterrupt:
        logging.info("Shutting down...")
        client.stop()
    finally:
        if workbench:
            workbench.stop()


if __name__ == "__main__":
    main()
