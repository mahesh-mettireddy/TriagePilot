#!/usr/bin/env bash
# ==============================================================================
# scripts/deploy_cloudrun.sh
# Deploy TriagePilot to Google Cloud Run
# ==============================================================================

set -euo pipefail

PROJECT_ID="${GCP_PROJECT_ID:-$(gcloud config get-value project 2>/dev/null || true)}"
REGION="${GCP_REGION:-us-central1}"
SERVICE_NAME="${SERVICE_NAME:-triagepilot}"

echo "=========================================================="
echo "  TriagePilot — Google Cloud Run Automated Deployment"
echo "=========================================================="

if [ -z "$PROJECT_ID" ] || [ "$PROJECT_ID" = "(unset)" ]; then
    echo "Error: No active GCP project found. Run 'gcloud config set project <PROJECT_ID>' or export GCP_PROJECT_ID." >&2
    exit 1
fi

echo "[+] Target GCP Project: $PROJECT_ID"
echo "[+] Target Region:     $REGION"
echo "[+] Service Name:      $SERVICE_NAME"

IMAGE_TAG="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:latest"

echo ""
echo "[*] Submitting container build to Google Cloud Build (${IMAGE_TAG})..."
gcloud builds submit --tag "${IMAGE_TAG}" .

echo ""
echo "[*] Deploying container image to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
    --image "${IMAGE_TAG}" \
    --platform managed \
    --region "${REGION}" \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 5 \
    --timeout 300

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format "value(status.url)")

echo ""
echo "=========================================================="
echo "  Deployment Successful!"
echo "  Live Cloud Run Cockpit URL: ${SERVICE_URL}"
echo "=========================================================="
