variable "REGISTRY" {
  default = "ghcr.io/chameleoncloud/chi-edge-workers"
}

variable "SHA" {
  default = ""
}

variable "CI" {
  default = ""
}

function "tags" {
  params = [name]
  result = SHA != "" ? [
    "${REGISTRY}/jetson-base:${name}",
    "${REGISTRY}/jetson-base:${name}-${SHA}",
  ] : [
    "${REGISTRY}/jetson-base:${name}",
  ]
}

group "default" {
  targets = ["nano", "xavier-nx", "orin"]
}

group "full" {
  targets = ["nano-full", "xavier-nx-full", "orin-full"]
}

target "_common" {
  platforms = ["linux/arm64"]
  labels = {
    "org.opencontainers.image.source" = "https://github.com/chameleoncloud/chi-edge-workers"
  }
}

target "nano" {
  inherits   = ["_common"]
  dockerfile = "jetpack4.Dockerfile"
  target     = "base"
  tags       = tags("t210-r32.7")
  args       = { SOC = "t210" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-jetpack4"]
  cache-to   = CI != "" ? ["type=registry,ref=${REGISTRY}/jetson-base:cache-jetpack4,mode=max"] : []
}

target "nano-full" {
  inherits   = ["nano"]
  target     = "full"
  tags       = tags("t210-r32.7-full")
}

target "xavier-nx" {
  inherits   = ["_common"]
  dockerfile = "jetpack5.Dockerfile"
  target     = "base"
  tags       = tags("t194-r35.6")
  args       = { SOC = "t194" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-jetpack5"]
  cache-to   = CI != "" ? ["type=registry,ref=${REGISTRY}/jetson-base:cache-jetpack5,mode=max"] : []
}

target "xavier-nx-full" {
  inherits   = ["xavier-nx"]
  target     = "full"
  tags       = tags("t194-r35.6-full")
}

target "orin" {
  inherits   = ["_common"]
  dockerfile = "jetpack6.Dockerfile"
  target     = "base"
  tags       = tags("t234-r36.5")
  args       = { SOC = "t234" }
  cache-from = ["type=registry,ref=${REGISTRY}/jetson-base:cache-jetpack6"]
  cache-to   = CI != "" ? ["type=registry,ref=${REGISTRY}/jetson-base:cache-jetpack6,mode=max"] : []
}

target "orin-full" {
  inherits   = ["orin"]
  target     = "full"
  tags       = tags("t234-r36.5-full")
}
