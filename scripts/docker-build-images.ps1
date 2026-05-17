$ErrorActionPreference = "Stop"

$imageRegistry = if ($env:IMAGE_REGISTRY) { $env:IMAGE_REGISTRY } else { "ghcr.io" }
$imageNamespace = if ($env:IMAGE_NAMESPACE) { $env:IMAGE_NAMESPACE } else { "3252a8" }
$imageTag = if ($env:IMAGE_TAG) { $env:IMAGE_TAG } else { "local" }
$imagePrefix = if ($env:IMAGE_PREFIX) { $env:IMAGE_PREFIX } else { "remnawave-minishop" }
$dockerfile = if ($env:DOCKERFILE) { $env:DOCKERFILE } else { "deploy/docker/Dockerfile" }

function Build-Image {
    param([string]$Target)
    $image = "$imageRegistry/$imageNamespace/$imagePrefix-$Target`:$imageTag"
    Write-Host "Building $image" -ForegroundColor Cyan
    docker build -f $dockerfile --target $Target -t $image .
}

Build-Image backend
Build-Image worker
Build-Image frontend
