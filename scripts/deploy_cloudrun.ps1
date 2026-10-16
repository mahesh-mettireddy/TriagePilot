# ==============================================================================
# scripts/deploy_cloudrun.ps1
# Deploy TriagePilot to Google Cloud Run
# ==============================================================================

param(
    [string]$ProjectId = $env:GCP_PROJECT_ID,
    [string]$Region = "us-central1",
    [string]$ServiceName = "triagepilot",
    [int]$Concurrency = 40,
    [string]$ServiceAccount = $env:CLOUD_RUN_SERVICE_ACCOUNT
)

$ErrorActionPreference = "Stop"

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "  TriagePilot -- Google Cloud Run Automated Deployment" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# 1. Verify gcloud CLI
if (-not (Get-Command gcloud -ErrorAction SilentlyContinue)) {
    Write-Error "Google Cloud SDK (gcloud) is not installed or not in PATH. Please install gcloud CLI."
    exit 1
}

# 2. Resolve Project ID
if (-not $ProjectId) {
    $ProjectId = (gcloud config get-value project 2>$null).Trim()
}

if (-not $ProjectId -or $ProjectId -eq "(unset)") {
    Write-Host "No active GCP project found. Please provide -ProjectId or run 'gcloud config set project <PROJECT_ID>'." -ForegroundColor Red
    exit 1
}

Write-Host "Target GCP Project: $ProjectId" -ForegroundColor Green
Write-Host "Target Region:      $Region" -ForegroundColor Green
Write-Host "Service Name:       $ServiceName" -ForegroundColor Green

$ImageTag = "$Region-docker.pkg.dev/$ProjectId/triagepilot/${ServiceName}:latest"
$ExecutionMode = if ($env:TRIAGEPILOT_EXECUTION_MODE) { $env:TRIAGEPILOT_EXECUTION_MODE } else { "live" }
$PersistenceMode = if ($env:TRIAGEPILOT_PERSISTENCE) { $env:TRIAGEPILOT_PERSISTENCE } else { "firestore" }

# 3. Build & Push Image via Cloud Build
Write-Host ""
Write-Host "Submitting container build to Google Cloud Build ($ImageTag)..." -ForegroundColor Yellow
gcloud builds submit --tag $ImageTag .

# 4. Deploy Container to Cloud Run
Write-Host ""
Write-Host "Deploying container image to Cloud Run..." -ForegroundColor Yellow
$DeployArgs = @(
    "deploy", $ServiceName,
    "--image", $ImageTag,
    "--platform", "managed",
    "--region", $Region,
    "--allow-unauthenticated",
    "--port", "8080",
    "--memory", "2Gi",
    "--cpu", "2",
    "--concurrency", "$Concurrency",
    "--min-instances", "1",
    "--max-instances", "1",
    "--session-affinity",
    "--no-cpu-throttling",
    "--timeout", "300",
    "--set-env-vars", "TRIAGEPILOT_EXECUTION_MODE=$ExecutionMode,TRIAGEPILOT_PERSISTENCE=$PersistenceMode,TRIAGEPILOT_JSON_LOGS=true,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_PROJECT=$ProjectId,FIRESTORE_PROJECT=$ProjectId,GOOGLE_CLOUD_LOCATION=$Region"
)
if ($ServiceAccount) { $DeployArgs += @("--service-account", $ServiceAccount) }
gcloud run @DeployArgs

# 5. Retrieve Deployed URL
$ServiceUrl = (gcloud run services describe $ServiceName --platform managed --region $Region --format "value(status.url)").Trim()
$Revision = (gcloud run services describe $ServiceName --platform managed --region $Region --format "value(status.latestReadyRevisionName)").Trim()
$ImageDigest = (gcloud run revisions describe $Revision --platform managed --region $Region --format "value(status.imageDigest)").Trim()
Invoke-WebRequest -UseBasicParsing -Uri "$ServiceUrl/readyz" | Out-Null

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "  Deployment Successful!" -ForegroundColor Green
Write-Host "  Live Cloud Run Cockpit URL: $ServiceUrl" -ForegroundColor Cyan
Write-Host "  Ready revision:              $Revision" -ForegroundColor Cyan
Write-Host "  Image digest:                $ImageDigest" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Green
