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

IMAGE_TAG="${REGION}-docker.pkg.dev/${PROJECT_ID}/triagepilot/${SERVICE_NAME}:latest"
CONCURRENCY="${CLOUD_RUN_CONCURRENCY:-40}"
EXECUTION_MODE="${TRIAGEPILOT_EXECUTION_MODE:-live}"
PERSISTENCE_MODE="${TRIAGEPILOT_PERSISTENCE:-firestore}"

echo ""
echo "[*] Submitting container build to Google Cloud Build (${IMAGE_TAG})..."
gcloud builds submit --tag "${IMAGE_TAG}" .

echo ""
echo "[*] Deploying container image to Cloud Run..."
DEPLOY_ARGS=(
    "${SERVICE_NAME}"
    --image "${IMAGE_TAG}"
    --platform managed
    --region "${REGION}"
    --allow-unauthenticated
    --port 8080
    --memory 1Gi
    --cpu 1
    --concurrency "${CONCURRENCY}"
    --min-instances 1
    --max-instances 5
    --no-cpu-throttling
    --timeout 300
    --set-env-vars "TRIAGEPILOT_EXECUTION_MODE=${EXECUTION_MODE},TRIAGEPILOT_PERSISTENCE=${PERSISTENCE_MODE},TRIAGEPILOT_JSON_LOGS=true,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=${PROJECT_ID},FIRESTORE_PROJECT=${PROJECT_ID},GOOGLE_CLOUD_LOCATION=${REGION}"
)
if [ -n "${CLOUD_RUN_SERVICE_ACCOUNT:-}" ]; then
    DEPLOY_ARGS+=(--service-account "${CLOUD_RUN_SERVICE_ACCOUNT}")
fi
gcloud run deploy "${DEPLOY_ARGS[@]}"

SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format "value(status.url)")
REVISION=$(gcloud run services describe "${SERVICE_NAME}" --platform managed --region "${REGION}" --format "value(status.latestReadyRevisionName)")
IMAGE_DIGEST=$(gcloud run revisions describe "${REVISION}" --platform managed --region "${REGION}" --format "value(status.imageDigest)")

echo "[*] Running deployment smoke checks..."
curl --fail --silent --show-error "${SERVICE_URL}/readyz" >/dev/null

echo ""
echo "=========================================================="
echo "  Deployment Successful!"
echo "  Live Cloud Run Cockpit URL: ${SERVICE_URL}"
echo "  Ready revision:              ${REVISION}"
echo "  Image digest:                ${IMAGE_DIGEST}"
echo "=========================================================="
