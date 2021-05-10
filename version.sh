#!/bin/bash

VERSION="$1"

if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
	echo "Invalid version number"
	exit 1
fi

setup_match="version = "
setup_ver="version = ${VERSION}"
sed -i -E "/$setup_match/s/.*/$setup_ver/" setup.cfg

header_match="    def __init__\(self, license_key, platform=\"modernmt-python\", platform_version="
header_ver="    def __init__\(self, license_key, platform=\"modernmt-python\", platform_version=\"${VERSION}\"\) -> None:"
sed -i -E "/$header_match/s/.*/$header_ver/" src/modernmt/modernmt.py
