#!/usr/bin/env -S fragletc --image ofthemachine/python3@sha256:a015b4f9f0e7c1648f8fcd4164f6a296dd3c9189404f88f333a9764d08d13522
#: d=Query package registries (pypi, npm, crates, dockerhub) for latest versions, release dates, licenses, and dependencies.
#: when=Use when the user wants to check package versions, verify dependency existence, check release dates, or inspect package metadata.
#: network=required
#: stdin=none
#: param=registry:required:d=Registry ecosystem: pypi, npm, crates, dockerhub
#: param=package:required:d=Package or image name (e.g. 'requests', 'express', 'tokio', 'library/alpine')
#: param=version:default=latest:d=Specific version tag to query, or 'latest'
#: param=format:default=markdown:d=Output format: markdown or json
import json
import os
import sys

import httpx

registry = os.environ.get("REGISTRY", "").strip().lower()
package = os.environ.get("PACKAGE", "").strip()
version_req = os.environ["VERSION"].strip()
fmt = os.environ["FORMAT"].strip().lower()

if not registry or not package:
    print("Error: registry and package parameters are required", file=sys.stderr)
    sys.exit(1)

if fmt not in ("markdown", "json"):
    print(f"Error: unknown format '{fmt}' (expected markdown or json)", file=sys.stderr)
    sys.exit(1)

HEADERS = {
    "User-Agent": "ofthemachine-tools/0.1.0 (https://tools.ofthemachine.com)",
    "Accept": "application/json",
}

client = httpx.Client(headers=HEADERS, timeout=15.0, follow_redirects=True)


def fail_not_found(msg: str):
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(1)


def query_pypi():
    url = f"https://pypi.org/pypi/{package}/json"
    if version_req and version_req.lower() != "latest":
        url = f"https://pypi.org/pypi/{package}/{version_req}/json"
    resp = client.get(url)
    if resp.status_code == 404:
        fail_not_found(f"Package '{package}' not found on PyPI")
    if resp.status_code != 200:
        fail_not_found(f"PyPI API returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    info = data.get("info", {})
    ver = info.get("version", "")
    release_info = data.get("releases", {}).get(ver, [])
    upload_time = release_info[0].get("upload_time", "") if release_info else ""

    deps = info.get("requires_dist") or []
    return {
        "ecosystem": "pypi",
        "name": info.get("name", package),
        "version": ver,
        "summary": info.get("summary", ""),
        "license": info.get("license", "") or "Not specified",
        "author": info.get("author", ""),
        "homepage": info.get("home_page") or info.get("project_url") or f"https://pypi.org/project/{package}/",
        "released": upload_time,
        "dependencies": deps[:15],
        "dependencies_total": len(deps),
    }


def query_npm():
    url = f"https://registry.npmjs.org/{package}"
    resp = client.get(url)
    if resp.status_code == 404:
        fail_not_found(f"Package '{package}' not found on npm")
    if resp.status_code != 200:
        fail_not_found(f"npm registry returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    dist_tags = data.get("dist-tags", {})
    ver = dist_tags.get("latest", "")
    if version_req and version_req.lower() != "latest":
        ver = version_req

    versions = data.get("versions", {})
    ver_data = versions.get(ver)
    if not ver_data:
        fail_not_found(f"Version '{ver}' of package '{package}' not found on npm")

    time_data = data.get("time", {})
    released = time_data.get(ver, "")

    deps_dict = ver_data.get("dependencies", {})
    deps = [f"{k}@{v}" for k, v in deps_dict.items()]

    return {
        "ecosystem": "npm",
        "name": data.get("name", package),
        "version": ver,
        "summary": ver_data.get("description", ""),
        "license": ver_data.get("license", "") or "Not specified",
        "author": str(ver_data.get("author", "")),
        "homepage": ver_data.get("homepage") or f"https://www.npmjs.com/package/{package}",
        "released": released,
        "dependencies": deps[:15],
        "dependencies_total": len(deps_dict),
    }


def query_crates():
    url = f"https://crates.io/api/v1/crates/{package}"
    resp = client.get(url)
    if resp.status_code == 404:
        fail_not_found(f"Crate '{package}' not found on crates.io")
    if resp.status_code != 200:
        fail_not_found(f"crates.io returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    crate = data.get("crate", {})
    ver = crate.get("max_version", "")
    if version_req and version_req.lower() != "latest":
        ver = version_req

    versions = data.get("versions", [])
    matched_ver = next((v for v in versions if v.get("num") == ver), None)
    if matched_ver is None and versions:
        matched_ver = versions[0]
        ver = matched_ver.get("num", ver)

    license_str = matched_ver.get("license", "") if matched_ver else ""
    created_at = matched_ver.get("created_at", "") if matched_ver else crate.get("updated_at", "")

    return {
        "ecosystem": "crates",
        "name": crate.get("name", package),
        "version": ver,
        "summary": crate.get("description", ""),
        "license": license_str or "Not specified",
        "author": "",
        "homepage": crate.get("homepage") or crate.get("repository") or f"https://crates.io/crates/{package}",
        "released": created_at,
        "dependencies": [],
        "dependencies_total": 0,
    }


def query_dockerhub():
    img_name = package
    if "/" not in img_name:
        img_name = f"library/{img_name}"

    url = f"https://hub.docker.com/v2/repositories/{img_name}/tags?page_size=15"
    resp = client.get(url)
    if resp.status_code == 404:
        fail_not_found(f"Image '{package}' not found on Docker Hub")
    if resp.status_code != 200:
        fail_not_found(f"Docker Hub returned HTTP {resp.status_code}: {resp.text}")

    data = resp.json()
    results = data.get("results", [])
    if not results:
        fail_not_found(f"No tags found for Docker image '{package}'")

    target_tag = version_req if (version_req and version_req.lower() != "latest") else "latest"
    tag_obj = next((t for t in results if t.get("name") == target_tag), results[0])

    digest = tag_obj.get("digest") or ""
    if not digest and tag_obj.get("images"):
        digest = tag_obj["images"][0].get("digest", "")

    tags_preview = [t.get("name") for t in results if t.get("name")]

    return {
        "ecosystem": "dockerhub",
        "name": img_name,
        "version": tag_obj.get("name", "latest"),
        "summary": f"Docker image: {img_name}",
        "license": "See image repo",
        "author": img_name.split("/")[0],
        "homepage": f"https://hub.docker.com/r/{img_name}",
        "released": tag_obj.get("last_updated", ""),
        "digest": digest,
        "recent_tags": tags_preview[:10],
    }


REGISTRIES = {
    "pypi": query_pypi,
    "python": query_pypi,
    "npm": query_npm,
    "node": query_npm,
    "crates": query_crates,
    "cargo": query_crates,
    "rust": query_crates,
    "dockerhub": query_dockerhub,
    "docker": query_dockerhub,
}

if registry not in REGISTRIES:
    print(f"Error: unsupported registry '{registry}' (expected pypi, npm, crates, dockerhub)", file=sys.stderr)
    sys.exit(1)

result = REGISTRIES[registry]()

if fmt == "json":
    print(json.dumps(result, indent=2))
else:
    print(f"# {result['name']} ({result['ecosystem']})\n")
    print(f"- **Version**: `{result['version']}`")
    if result.get("released"):
        print(f"- **Released**: {result['released']}")
    if result.get("license"):
        print(f"- **License**: {result['license']}")
    if result.get("homepage"):
        print(f"- **Homepage**: {result['homepage']}")
    if result.get("digest"):
        print(f"- **Digest**: `{result['digest']}`")
    if result.get("summary"):
        print(f"\n> {result['summary'].strip()}\n")

    if result.get("dependencies"):
        print(f"### Dependencies ({result['dependencies_total']} total):")
        for d in result["dependencies"]:
            print(f"- `{d}`")
        if result["dependencies_total"] > len(result["dependencies"]):
            print(f"- *(+{result['dependencies_total'] - len(result['dependencies'])} more)*")
    elif result.get("recent_tags"):
        print("### Recent Tags:")
        print(", ".join(f"`{t}`" for t in result["recent_tags"]))
