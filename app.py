
from datetime import datetime, timezone
import socket
import os
import concurrent.futures
import time

import psutil
from flask import Flask, jsonify

app = Flask(__name__)


def check_cpu():
    cpu_usage = psutil.cpu_percent(interval=0.2)

    warning = float(os.getenv("CPU_WARNING", "75"))
    critical = float(os.getenv("CPU_CRITICAL", "90"))

    if cpu_usage >= critical:
        status = "unhealthy"
    elif cpu_usage >= warning:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "value": cpu_usage,
        "unit": "%",
        "warning_threshold": warning,
        "critical_threshold": critical,
        "status": status
    }

def check_memory():
    memory = {}

    with open("/proc/meminfo", "r") as file:
        for line in file:
            key, value = line.split(":", 1)
            memory[key] = int(value.strip().split()[0])

    total = memory["MemTotal"]
    available = memory["MemAvailable"]
    used = total - available

    used_percent = round((used / total) * 100, 2)

    warning = float(os.getenv("MEMORY_WARNING", "80"))
    critical = float(os.getenv("MEMORY_CRITICAL", "95"))

    if used_percent >= critical:
        status = "unhealthy"
    elif used_percent >= warning:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "used_percent": used_percent,
        "total_mb": round(total / 1024, 2),
        "used_mb": round(used / 1024, 2),
        "available_mb": round(available / 1024, 2),
        "warning_threshold": warning,
        "critical_threshold": critical,
        "status": status
    }

def check_load():
    with open("/proc/loadavg", "r") as file:
        values = file.read().split()

    load_1 = float(values[0])
    load_5 = float(values[1])
    load_15 = float(values[2])

    cores = len(os.sched_getaffinity(0))
    normalized_load = round(load_1 / cores, 2)

    warning = float(os.getenv("LOAD_WARNING", "1.0"))
    critical = float(os.getenv("LOAD_CRITICAL", "2.0"))

    if normalized_load >= critical:
        status = "unhealthy"
    elif normalized_load >= warning:
        status = "degraded"
    else:
        status = "healthy"

    return {
        "load_1min": load_1,
        "load_5min": load_5,
        "load_15min": load_15,
        "cpu_cores": cores,
        "normalized_load": normalized_load,
        "warning_threshold": warning,
        "critical_threshold": critical,
        "status": status
    }

def check_disk():
    warning = float(os.getenv("DISK_WARNING", "80"))
    critical = float(os.getenv("DISK_CRITICAL", "95"))

    filesystems = []
    overall_status = "healthy"

    severity = {
        "healthy": 0,
        "degraded": 1,
        "unhealthy": 2
    }

    for partition in psutil.disk_partitions(all=True):
        # Exclude WSL-specific system mounts
        if partition.mountpoint.startswith("/usr/lib/wsl/"):
            continue
        # Ignore WSL Windows drives and virtual filesystems
        if partition.mountpoint.startswith(("/mnt/", "/Docker/")):
            continue

        if partition.fstype in (
            "proc", "sysfs", "tmpfs", "devtmpfs",
            "devpts", "cgroup", "cgroup2", "mqueue",
            "iso9660", "binfmt_misc", "hugetlbfs",
            "tracefs", "fusectl", "configfs", "debugfs",
	    "squashfs","securityfs", "pstore", "efivarfs",
            "bpf", "autofs"
        ):
            continue
        # Exclude virtual filesystems and Docker configuration mounts.
        if partition.fstype in ("proc", "sysfs", "tmpfs", "devtmpfs", "devpts", "cgroup", "cgroup2", "mqueue", "overlay2", "iso9660"):
            continue

        if partition.mountpoint in ("/etc/hostname", "/etc/hosts", "/etc/resolv.conf"):
            continue

        try:
            usage = psutil.disk_usage(partition.mountpoint)
            used_percent = usage.percent

            if used_percent >= critical:
                status = "unhealthy"
            elif used_percent >= warning:
                status = "degraded"
            else:
                status = "healthy"

            filesystems.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "filesystem": partition.fstype,
                "used_percent": used_percent,
                "total_gb": round(usage.total / (1024 ** 3), 2),
                "free_gb": round(usage.free / (1024 ** 3), 2),
                "warning_threshold": warning,
                "critical_threshold": critical,
                "status": status
            })

            if severity[status] > severity[overall_status]:
                overall_status = status

        except (OSError, PermissionError) as error:
            filesystems.append({
                "mountpoint": partition.mountpoint,
                "status": "unhealthy",
                "error": str(error)
            })
            overall_status = "unhealthy"

    if not filesystems:
        overall_status = "unhealthy"

    return {
        "filesystems": filesystems,
        "warning_threshold": warning,
        "critical_threshold": critical,
        "status": overall_status
    }

def check_uptime():
    with open("/proc/uptime", "r") as file:
        uptime_seconds = float(file.read().split()[0])

    total_seconds = int(uptime_seconds)

    days, remainder = divmod(total_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    return {
        "uptime_seconds": total_seconds,
        "uptime_human": f"{days}d {hours}h {minutes}m {seconds}s",
        "status": "healthy"
    }

def check_tcp_ports():
    listening_ports = []

    connections = psutil.net_connections(kind="tcp")

    for conn in connections:
        if conn.status != psutil.CONN_LISTEN:
            continue

        process_name = None

        if conn.pid is not None:
            try:
                process_name = psutil.Process(conn.pid).name()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                process_name = None

        listening_ports.append({
            "ip_address": conn.laddr.ip,
            "port": conn.laddr.port,
            "pid": conn.pid,
            "process_name": process_name
        })

    return {
        "count": len(listening_ports),
        "listening_ports": listening_ports,
        "status": "healthy"
    }
def check_dns():
    hostname = os.getenv("DNS_HOSTNAME", "google.com")
    timeout = float(os.getenv("DNS_TIMEOUT", "3"))

    def resolve():
        results = socket.getaddrinfo(
            hostname, None, family=socket.AF_INET
        )
        return sorted({item[4][0] for item in results})

    start = time.monotonic()
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    try:
        future = executor.submit(resolve)
        addresses = future.result(timeout=timeout)

        return {
            "hostname": hostname,
            "resolved_addresses": addresses,
            "response_time_ms": round(
                (time.monotonic() - start) * 1000, 2
            ),
            "status": "healthy" if addresses else "unhealthy"
        }

    except (concurrent.futures.TimeoutError, OSError, Exception) as error:
        return {
            "hostname": hostname,
            "resolved_addresses": [],
            "error": str(error) or type(error).__name__,
            "status": "unhealthy"
        }

    finally:
        executor.shutdown(wait=False, cancel_futures=True)

def check_outbound_tcp():
    host = os.getenv("TCP_TARGET_HOST", "google.com")
    port = int(os.getenv("TCP_TARGET_PORT", "443"))
    timeout = float(os.getenv("TCP_TIMEOUT", "3"))

    start = time.monotonic()

    try:
        with socket.create_connection((host, port), timeout=timeout) as connection:
            remote_address = connection.getpeername()[0]

        return {
            "target_host": host,
            "target_port": port,
            "remote_address": remote_address,
            "connection_time_ms": round(
                (time.monotonic() - start) * 1000, 2
            ),
            "status": "healthy"
        }

    except (OSError, TimeoutError) as error:
        return {
            "target_host": host,
            "target_port": port,
            "error": str(error),
            "status": "unhealthy"
        }

def check_network():
    interfaces = []

    for name, addresses in psutil.net_if_addrs().items():
        ip_addresses = []

        for address in addresses:
            if address.family == socket.AF_INET:
                ip_addresses.append({
                    "family": "IPv4",
                    "address": address.address,
                    "netmask": address.netmask
                })

            elif address.family == socket.AF_INET6:
                ip_addresses.append({
                    "family": "IPv6",
                    "address": address.address,
                    "netmask": address.netmask
                })

        interfaces.append({
            "name": name,
            "ip_addresses": ip_addresses
        })

    gateway = None
    gateway_interface = None

    with open("/proc/net/route", "r") as file:
        next(file)

        for line in file:
            fields = line.split()

            if fields[1] == "00000000":
                gateway_interface = fields[0]
                gateway_hex = fields[2]

                gateway = socket.inet_ntoa(
                    bytes.fromhex(gateway_hex)[::-1]
                )
                break

    return {
        "interfaces": interfaces,
        "default_gateway": gateway,
        "gateway_interface": gateway_interface,
        "status": "healthy" if gateway else "degraded"
    }

def run_check(name, check_function):
    try:
        return check_function()

    except Exception as error:
        app.logger.exception(
            "Health check '%s' failed", name
        )

        return {
            "status": "unhealthy",
            "error": str(error),
            "check": name
        }

def collect_health_checks():
    return {
        "cpu": run_check("cpu", check_cpu),
        "memory": run_check("memory", check_memory),
        "load": run_check("load", check_load),
        "disk": run_check("disk", check_disk),
        "uptime": run_check("uptime", check_uptime),
        "tcp_ports": run_check("tcp_ports", check_tcp_ports),
        "dns": run_check("dns", check_dns),
        "outbound_tcp": run_check("outbound_tcp", check_outbound_tcp),
        "network": run_check("network", check_network)
    }

@app.get("/health")
def health():
    checks = collect_health_checks()

    severity = {
        "healthy": 0,
        "degraded": 1,
        "unhealthy": 2
    }

    worst_check = max(
        checks,
        key=lambda name: severity[checks[name]["status"]]
    )

    overall_status = checks[worst_check]["status"]

    if overall_status == "healthy":
        reason = "All system and network checks are healthy"
    else:
        failed_checks = [
           name for name, result in checks.items()
           if result["status"] == overall_status
        ]
        reason = (
            f"{overall_status.capitalize()} checks: "
            + ", ".join(failed_checks)
        )

    response = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "status": overall_status,
        "reason": reason
    }

    http_code = 503 if overall_status == "unhealthy" else 200

    return jsonify(response), http_code

@app.get("/health/details")
def health_details():
    checks = collect_health_checks()
    
    severity = {
        "healthy": 0,
        "degraded": 1,
        "unhealthy": 2
    }

    overall_status = max(
        checks.values(),
        key=lambda check: severity[check["status"]]
    )["status"]

    response = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "hostname": socket.gethostname(),
        "status": overall_status,
        "checks": checks
    }

    http_code = 503 if overall_status == "unhealthy" else 200

    return jsonify(response), http_code

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
