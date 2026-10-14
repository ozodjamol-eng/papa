"""Read-only Linux host telemetry. No shell, network, arbitrary path or secrets."""
import os
import platform
import shutil
from pathlib import Path


def host_health(state_dir):
    disk = shutil.disk_usage(state_dir)
    result = {
        'scope': 'local_host_only', 'platform': platform.system(),
        'disk_free_bytes': disk.free, 'disk_total_bytes': disk.total,
        'production_genplan_verified': False, 'publisher_connected': False,
        'memory_available_bytes': None, 'memory_total_bytes': None,
        'uptime_seconds': None, 'load_average': None,
    }
    if hasattr(os, 'getloadavg'):
        result['load_average'] = list(os.getloadavg())
    if platform.system() == 'Linux':
        try:
            for line in Path('/proc/meminfo').read_text().splitlines():
                key, value = line.split(':', 1)
                if key in ('MemAvailable', 'MemTotal'):
                    target = 'memory_available_bytes' if key == 'MemAvailable' else 'memory_total_bytes'
                    result[target] = int(value.split()[0]) * 1024
            result['uptime_seconds'] = float(Path('/proc/uptime').read_text().split()[0])
        except (OSError, ValueError, IndexError):
            result['proc_telemetry'] = 'unavailable_or_partial'
    return result
