#!/bin/bash

set -e  # Exit on any error

REPO_OWNER="octra-labs"
REPO_NAME="wallet-gen"
INSTALL_DIR="$HOME/.octra"
TEMP_DIR="/tmp/octra-wallet-gen-install"
BUN_INSTALL_CHECKSUM="7713fe768665f07a90fd7ac5eb25c9e8838703a560ba7ad942bdcedd92dc115b"

echo "=== ⚠️  SECURITY WARNING ⚠️  ==="
echo ""
echo "this tool generates real cryptographic keys. always:"
echo "  - keep your private keys secure"
echo "  - never share your mnemonic phrase"
echo "  - don't store wallet files on cloud services"
echo "  - use on a secure, offline computer for production wallets"
echo ""
read -p "press enter to continue..." < /dev/tty
echo ""
echo "=== octra wallet generator installer ==="
echo ""

install_bun() {
    if ! command -v bun &> /dev/null; then
        curl -fsSL https://bun.sh/install -o /tmp/bun_install.sh
        if ! echo "$BUN_INSTALL_CHECKSUM  /tmp/bun_install.sh" | shasum -a 256 -c -q; then
            echo "Failed to install bun! Please install it manually from https://bun.sh"
            rm -f /tmp/bun_install.sh
            exit 1
        fi
        bash /tmp/bun_install.sh
        rm -f /tmp/bun_install.sh
        # Set PATH to include Bun's binary directory
        export PATH="$HOME/.bun/bin:$PATH"
    fi
}

get_latest_release() {
    curl -s "https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/tags" | \
    grep '"name":' | \
    head -1 | \
    sed 's/.*"name": "\(.*\)".*/\1/'
}

download_and_extract() {
    local tag=$1
    echo "downloading octra wallet generator..."
    
    rm -rf "$TEMP_DIR"
    mkdir -p "$TEMP_DIR"
    
    local tarball_url="https://api.github.com/repos/${REPO_OWNER}/${REPO_NAME}/tarball/refs/tags/${tag}"
    curl -L -o "$TEMP_DIR/release.tar.gz" "$tarball_url"

    cd "$TEMP_DIR"
    tar -xzf release.tar.gz --strip-components=1
}

echo "fetching latest release information..."
LATEST_TAG=$(get_latest_release)
if [ -z "$LATEST_TAG" ]; then
    echo "❌ error: could not fetch latest release information."
    echo "please check your internet connection and try again."
    exit 1
fi

download_and_extract "$LATEST_TAG"

cd "$TEMP_DIR"

install_bun

bun install

echo ""
echo "building standalone executable..."
bun run build

if [ ! -f "./wallet-generator" ]; then
    echo "❌ error: wallet-generator executable not found!"
    echo "build may have failed. please check the build output above."
    exit 1
fi

echo "installing to $INSTALL_DIR..."
mkdir -p "$INSTALL_DIR"
cp ./wallet-generator "$INSTALL_DIR/"

echo ""
echo "starting wallet generator server..."

cd "$INSTALL_DIR"

rm -rf "$TEMP_DIR"

if lsof -i :8888 >/dev/null 2>&1; then
    echo "❌ error: port 8888 is already in use!"
    echo "please stop any existing service using port 8888."
    exit 1
fi

./wallet-generator > /dev/null &
WALLET_PID=$!

sleep 2

BROWSER_CMD=$(command -v open 2>/dev/null || command -v xdg-open 2>/dev/null || echo "")

if [ -n "$BROWSER_CMD" ]; then
    $BROWSER_CMD http://localhost:8888 2>/dev/null || echo ""
fi

echo ""
echo "=== installation complete! ==="
echo "wallet generator is running at http://localhost:8888"
echo "to run again later, use: $INSTALL_DIR/wallet-generator"
echo "to stop the wallet generator, press Ctrl+C"
echo ""

wait $WALLET_PID
