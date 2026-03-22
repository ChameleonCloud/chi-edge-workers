variable "REGISTRY" {
  default = "ghcr.io/chameleoncloud/chi-edge-workers"
}

group "default" {
  targets = ["nano", "nano-full", "xavier-nx", "xavier-nx-full", "orin", "orin-full"]
}

target "nano" {
  dockerfile = "jetpack4.Dockerfile"
  target     = "base"
  tags       = ["${REGISTRY}/jetson-base:t210-r32.7"]
  args       = { SOC = "t210" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7,mode=max"]
  platforms  = ["linux/arm64"]
}

target "nano-full" {
  inherits   = ["nano"]
  target     = "full"
  tags       = ["${REGISTRY}/jetson-base:t210-r32.7-full"]
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t210-r32.7,mode=max"]
}

target "xavier-nx" {
  dockerfile = "jetpack5.Dockerfile"
  target     = "base"
  tags       = ["${REGISTRY}/jetson-base:t194-r35.6"]
  args       = { SOC = "t194" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6,mode=max"]
  platforms  = ["linux/arm64"]
}

target "xavier-nx-full" {
  inherits   = ["xavier-nx"]
  target     = "full"
  tags       = ["${REGISTRY}/jetson-base:t194-r35.6-full"]
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t194-r35.6,mode=max"]
}

target "orin" {
  dockerfile = "jetpack6.Dockerfile"
  target     = "base"
  tags       = ["${REGISTRY}/jetson-base:t234-r36.5"]
  args       = { SOC = "t234" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5,mode=max"]
  platforms  = ["linux/arm64"]
}

target "orin-full" {
  inherits   = ["orin"]
  target     = "full"
  tags       = ["${REGISTRY}/jetson-base:t234-r36.5-full"]
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5"]
  cache-to   = ["type=registry,ref=${REGISTRY}/jetson-base:cache-t234-r36.5,mode=max"]
}
