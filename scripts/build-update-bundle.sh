#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# WebMACS — Build Update Bundle
# Creates a self-contained OTA update package for customer deployment.
#
# Usage:
#   ./scripts/build-update-bundle.sh [version]
#
# Example:
#   ./scripts/build-update-bundle.sh 2.1.0
#
# Output:
#   dist/webmacs-update-2.1.0.tar.gz
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

VERSION="${1:?Usage: $0 <version>  (e.g. 2.1.0)}"
DIST_DIR="dist"
WORK_DIR=$(mktemp -d)
BUNDLE_NAME="webmacs-update-${VERSION}"

trap 'rm -rf "$WORK_DIR"' EXIT

echo "═══════════════════════════════════════════════════════"
echo " WebMACS Update Bundle Builder — v${VERSION}"
echo "═══════════════════════════════════════════════════════"

# ── 1. Build Docker images ────────────────────────────────────────────────
echo ""
echo "▶ Building Docker images..."
docker compose build --no-cache

# Tag images with version
echo "▶ Tagging images as :${VERSION}..."
docker tag webmacs-backend:latest   "webmacs-backend:${VERSION}"
docker tag webmacs-frontend:latest  "webmacs-frontend:${VERSION}"
docker tag webmacs-controller:latest "webmacs-controller:${VERSION}"

# ── 2. Export images to tar ──────────────────────────────────────────────
echo "▶ Exporting images to tar (this may take a few minutes)..."
docker save \
    "webmacs-backend:${VERSION}" \
    "webmacs-frontend:${VERSION}" \
    "webmacs-controller:${VERSION}" \
    > "${WORK_DIR}/images.tar"

IMAGE_SIZE=$(du -sh "${WORK_DIR}/images.tar" | cut -f1)
echo "  Images: ${IMAGE_SIZE}"

# ── 3. Compute SHA-256 ──────────────────────────────────────────────────
echo "▶ Computing SHA-256 checksum..."
IMAGES_SHA256=$(shasum -a 256 "${WORK_DIR}/images.tar" | cut -d' ' -f1)
echo "  SHA-256: ${IMAGES_SHA256}"

# ── 4. Create manifest ──────────────────────────────────────────────────
echo "▶ Creating manifest.json..."
cat > "${WORK_DIR}/manifest.json" <<EOF
{
    "version": "${VERSION}",
    "images_sha256": "${IMAGES_SHA256}",
    "created_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "changelog": "WebMACS v${VERSION} update bundle",
    "images": [
        "webmacs-backend:${VERSION}",
        "webmacs-frontend:${VERSION}",
        "webmacs-controller:${VERSION}"
    ]
}
EOF

# ── 5. Include production compose file ────────────────────────────────────
echo "▶ Including production compose file..."
cp docker-compose.prod.yml "${WORK_DIR}/docker-compose.prod.yml"

# ── 6. Create bundle ────────────────────────────────────────────────────
mkdir -p "${DIST_DIR}"
BUNDLE_PATH="${DIST_DIR}/${BUNDLE_NAME}.tar.gz"

echo "▶ Creating bundle: ${BUNDLE_PATH}..."
tar -czf "${BUNDLE_PATH}" -C "${WORK_DIR}" \
    manifest.json \
    images.tar \
    docker-compose.prod.yml

BUNDLE_SIZE=$(du -sh "${BUNDLE_PATH}" | cut -f1)

echo ""
echo "═══════════════════════════════════════════════════════"
echo " ✅ Bundle created successfully!"
echo ""
echo "   File:     ${BUNDLE_PATH}"
echo "   Size:     ${BUNDLE_SIZE}"
echo "   Version:  ${VERSION}"
echo "   SHA-256:  ${IMAGES_SHA256}"
echo ""
echo " To deploy:"
echo "   1. Copy ${BUNDLE_PATH} to the RevPi"
echo "   2. Upload via WebMACS UI → OTA Updates → Upload Bundle"
echo "   — or —"
echo "   3. Copy to /updates/ on the device:"
echo "      scp ${BUNDLE_PATH} pi@<revpi-ip>:/opt/webmacs/updates/"
echo "═══════════════════════════════════════════════════════"
