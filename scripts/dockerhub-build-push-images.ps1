$ErrorActionPreference = "Stop"

if (-not $env:IMAGE_TAG) {
    throw "Set IMAGE_TAG to the release tag you want to build and push"
}

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

$env:IMAGE_REGISTRY = "docker.io"
$env:IMAGE_NAMESPACE = "3252a8"

& (Join-Path $scriptDir "docker-build-images.ps1")
& (Join-Path $scriptDir "docker-push-images.ps1")
