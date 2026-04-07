variable "REGISTRY" {
  default = "ghcr.io/chameleoncloud/chi-edge-workers/l4t-cuda"
}

group "default" {
  targets = ["base", "devel", "infra"]
}

target "_common" {
  context   = "."
  platforms = ["linux/arm64"]
}

target "_r32" {
  inherits   = ["_common"]
  cache-from = ["type=registry,ref=${REGISTRY}:cache-r32"]
  cache-to   = ["type=registry,ref=${REGISTRY}:cache-r32,mode=max"]
  args = {
    UBUNTU       = "18.04"
    L4T_VERSION  = "r32.7"
    CUDA         = "10-2"
    CUDA_VERSION = "10.2"
  }
}

target "_r36" {
  inherits   = ["_common"]
  cache-from = ["type=registry,ref=${REGISTRY}:cache-r36"]
  cache-to   = ["type=registry,ref=${REGISTRY}:cache-r36,mode=max"]
  args = {
    UBUNTU       = "22.04"
    L4T_VERSION  = "r36.4"
    CUDA         = "12-6"
    CUDA_VERSION = "12.6"
  }
}

// --- base ---
group "base" {
  targets = ["base-r32", "base-r36"]
}

target "base-r32" {
  inherits = ["_r32"]
  target   = "base"
  tags     = ["${REGISTRY}:r32.7-10.2"]
}

target "base-r36" {
  inherits = ["_r36"]
  target   = "base"
  tags     = ["${REGISTRY}:r36.4-12.6"]
}

// --- devel ---
group "devel" {
  targets = ["devel-r32", "devel-r36"]
}

target "devel-r32" {
  inherits = ["_r32"]
  target   = "devel"
  tags     = ["${REGISTRY}:r32.7-10.2-devel"]
}

target "devel-r36" {
  inherits = ["_r36"]
  target   = "devel"
  tags     = ["${REGISTRY}:r36.4-12.6-devel"]
}

// --- infra ---
group "infra" {
  targets = ["infra-t210", "infra-t194", "infra-t234"]
}

target "infra-t210" {
  inherits   = ["_r32"]
  target     = "infra"
  args       = { SOC = "t210" }
  tags       = ["${REGISTRY}:r32.7-10.2-t210"]
  cache-from = [
    "type=registry,ref=${REGISTRY}:cache-r32",
    "type=registry,ref=${REGISTRY}:cache-t210"
    ]
  cache-to   = ["type=registry,ref=${REGISTRY}:cache-t210,mode=max"]
}

target "infra-t194" {
  inherits   = ["_r32"]
  target     = "infra"
  args       = { SOC = "t194" }
  tags       = ["${REGISTRY}:r32.7-10.2-t194"]
  cache-from = [
    "type=registry,ref=${REGISTRY}:cache-r32",
    "type=registry,ref=${REGISTRY}:cache-t194"
    ]
  cache-to   = ["type=registry,ref=${REGISTRY}:cache-t194,mode=max"]
}

target "infra-t234" {
  inherits   = ["_r36"]
  target     = "infra"
  args       = { SOC = "t234" }
  tags       = ["${REGISTRY}:r36.4-12.6-t234"]
  cache-from = [
    "type=registry,ref=${REGISTRY}:cache-r36",
    "type=registry,ref=${REGISTRY}:cache-t234"
  ]
  cache-to   = ["type=registry,ref=${REGISTRY}:cache-t234,mode=max"]
}
