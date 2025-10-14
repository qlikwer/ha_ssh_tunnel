from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from .const import DOMAIN
from .ssh_tunnel import SSHTunnel

tunnels = {}

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    data = entry.data
    tunnel = SSHTunnel(
        host=data["host"],
        port=data["port"],
        user=data["user"],
        private_key=data["private_key"],
        local_port=data["local_port"],
        remote_host=data["remote_host"],
        remote_port=data["remote_port"],
        auto_reconnect=data.get("auto_reconnect", True),
    )
    tunnels[entry.entry_id] = tunnel
    tunnel.start()
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    tunnel = tunnels.pop(entry.entry_id, None)
    if tunnel:
        tunnel.stop()
    return True
