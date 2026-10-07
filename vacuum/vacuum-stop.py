#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Stop the vacuum where it stands (Roborock cloud). Self-contained: ensurepip + pip install python-roborock ~20s, then login.
#: when=Use when the user tells the vacuum to stop or pause.
#: network=required
#: stdin=none
#: secret=ROBOROCK_EMAIL:d=Roborock cloud account email (a shared-device account keeps the blast radius small)
#: secret=ROBOROCK_PASSWORD:d=Roborock cloud account password
import asyncio
import inspect
import os
import subprocess
import sys


def fail(msg):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def read_secret(name):
    """Secret-file first ($NAME_FILE, fragletc delivery), bare env fallback
    (native runner). Values never touch argv, params, or stdout."""
    f = os.environ.get(name + "_FILE")
    if f:
        try:
            with open(f, encoding="utf-8") as fh:
                return fh.read().strip()
        except OSError as e:
            fail(f"cannot read secret file for {name}: {e}")
    return os.environ.get(name, "").strip()


sys.path.insert(0, "/tmp/pylibs")
try:
    import roborock  # noqa: F401
except ImportError:
    r = subprocess.run([sys.executable, "-m", "ensurepip", "--default-pip"],
                       capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        fail(f"ensurepip failed: {r.stderr[-200:]}")
    r = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--quiet",
         "--target=/tmp/pylibs", "python-roborock"],
        capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        fail(f"pip install python-roborock failed: {r.stderr[-300:]}")
    import roborock  # noqa: F401


async def main():
    from roborock import RoborockCommand
    from roborock.web_api import RoborockApiClient
    from roborock.devices.device_manager import UserParams, create_device_manager
    email = read_secret("ROBOROCK_EMAIL")
    password = read_secret("ROBOROCK_PASSWORD")
    if not email or not password:
        fail("ROBOROCK_EMAIL / ROBOROCK_PASSWORD not provisioned")
    api = RoborockApiClient(username=email)
    try:
        user_data = await api.pass_login(password)
    except Exception as e:
        fail(f"Roborock cloud login failed: {e}")
    manager = await create_device_manager(UserParams(username=email, user_data=user_data))
    devices = await manager.get_devices()
    vacs = [d for d in devices if getattr(d, "v1_properties", None)]
    if not vacs:
        fail(f"no vacuums on account {email} ({len(devices)} devices total)")
    vac = vacs[0]
    res = vac.v1_properties.command.send(RoborockCommand.APP_STOP)
    if inspect.isawaitable(res):
        await res
    print(f"{vac.name}: stopped")


asyncio.run(main())
