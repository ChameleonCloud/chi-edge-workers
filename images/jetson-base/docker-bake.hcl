variable "REGISTRY" {
  default = "ghcr.io/chameleoncloud/chi-edge-workers"
}

variable "SHA" {
  default = "latest"
}

group "default" {
  targets = ["nano", "xavier-nx",  "orin",]
}

target "_common" {
  labels = {
    "org.opencontainers.image.source" = "https://github.com/chameleoncloud/chi-edge-workers"
  }
}

target "nano" {
  inherits   = ["_common"]
  dockerfile = "jetpack4.Dockerfile"
  target     = "base"
  tags       = ["${REGISTRY}/jetson-base:t210-r32.7", "${REGISTRY}/jetson-base:t210-r32.7-${SHA}"]
  args       = { SOC = "t210" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7,mode=max"]
  platforms  = ["linux/arm64"]
}

target "nano-full" {
  inherits   = ["nano"]
  target     = "full"
  tags       = ["${REGISTRY}/jetson-base:t210-r32.7-full", "${REGISTRY}/jetson-base:t210-r32.7-full-${SHA}"]
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7,mode=max"]
}

target "xavier-nx" {
  inherits   = ["_common"]
  dockerfile = "jetpack5.Dockerfile"
  target     = "base"
  tags       = ["${REGISTRY}/jetson-base:t194-r35.6", "${REGISTRY}/jetson-base:t194-r35.6-${SHA}"]
  args       = { SOC = "t194" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6,mode=max"]
  platforms  = ["linux/arm64"]
}

target "xavier-nx-full" {
  inherits   = ["xavier-nx"]
  target     = "full"
  tags       = ["${REGISTRY}/jetson-base:t194-r35.6-full", "${REGISTRY}/jetson-base:t194-r35.6-full-${SHA}"]
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6,mode=max"]
}

target "orin" {
  inherits   = ["_common"]
  dockerfile = "jetpack6.Dockerfile"
  target     = "base"
  tags       = ["${REGISTRY}/jetson-base:t234-r36.5", "${REGISTRY}/jetson-base:t234-r36.5-${SHA}"]
  args       = { SOC = "t234" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5,mode=max"]
  platforms  = ["linux/arm64"]
}

target "orin-full" {
  inherits   = ["orin"]
  target     = "full"
  tags       = ["${REGISTRY}/jetson-base:t234-r36.5-full", "${REGISTRY}/jetson-base:t234-r36.5-full-${SHA}"]
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5,mode=max"]
}
