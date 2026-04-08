# CHI@Edge Jetson Base Images

This folder contains build recipes for "base" docker images to support Nvidia
Jetson devices in CHI@Edge.

These devices are brittle to support in Balena's build process, due to the large
(1-3GB) libraries required for CUDA runtime support. Instead, they are built and
versioned separately here. Besides making the build more robust, it also allows
us to provide a "-devel" image to end-users for compilation against our runtime.

# Nvidia container runtime

We bake in a significant number of assumptions in order to make the Nvidia
container runtime work "as expected" across devices and versions.

At a high level:

Balena is used to deploy the "infra" image, (e.g. l4t-cuda:r32.7-10.2-t210 for 
Jetson Nano). This image contains the l4t "platform" drivers for things like the
camera and video encode/decoders, cuda and related runtime libraries, the 
nvidia container toolkit, and the k3s agent itself.

When a kubernetes container is launched by an end-user, and the nvidia runtime 
is chosen (instead of containerd directly), a pre-start hook mounts the 
necessary devices from /dev/*, libraries, and tools into the contianer for gpu
accelerated workloads to function, *without* needing to bundle those large
dependencies into the end-user container.

This allows a user to quickly download and run a 20mb container with just a 
compiled CUDA binary, instead of running a 3gb container packaging the entire
cuda runtime.

## *Using* the Nvidia runtime

In order for the mapping to occur, two things must happen:

1. The container launch must be intercepted by the Nvidia runtime, instead of `runc`
2. The nvidia runtime must be configured to mount the necessary devices and libs

To use the nvidia runtime, we can either set `runtimeClassName: nvidia` in the
pod manifest, or set it as the default on this device so that it's always used unless overridden.

As explicitly requesting it adds an extra step to either the end-user or Zun 
(depending on the caller), we set it as the default on Jetson devices. Initially
this was done by overriding containerd's setting via config.toml.tmpl, but as of
v1.26, k3s permits setting `--default-runtime=nvidia` on the agent CLI.

The only thing that the pod manifest must specify is:
```
resources:
  limits:
    nvidia.com/gpu: "1"
```

## Under the hood

Once the nvidia runtime is triggered, with a gpu request spec, it needs to find
out what to mount into the container.

In older versions, this was done via a prestart hook `nvidia-container-cli`
in the `infra` container, which reads `drivers.csv`, `devices.csv`, and `l4t.csv`
from `/etc/nvidia-container-runtime/host-files-for-container.d/`. Each file has
a list of paths to mount. This prestart hook depends on `libnvidia-container0`, 
which is available for L4T r32, but not r36.

In order to use a consistent method for the newer Orin devices and the older 
Jetson Nano and Xavier NX, we need to use Nvidia's "Container Device Interface"
(CDI) method instead. https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/cdi-support.html

Instead of reading from the CSV files, this consumes a CDI specification, either generated dynamically, or pre-generated
and saved to `/var/run/cdi/nvidia.yaml`. We configure the nvidia device plugin with `DEVICE_LIST_STRATEGY=envvar`, which injects `NVIDIA_VISIBLE_DEVICES` into the pod manifest. Once launched, the nvidia runtime shim reads the CDI spec to know what to mount based on the value of this env var, by looking it up in the CDI spec dictionary. (Usual values are `0`, `ALL`, in the single-gpu case.) 

As the JIT generation is broken on Tegra (toolkit sets NVIDIA_VISIBLE_DEVICES=tegra, but plugin doesn't handle it. TODO make a bug report.) we pre-generate it by executing `nvidia-ctk cdi generate --mode=csv` when the infra container starts. This simply translates the same csv files as before into a CDI spec. Because we use the CDI spec in all versions, we don't need the csv-compatible prestart hook from libnvidia-container0.

We *also* had to set `DEVICE_ID_STRATEGY=index` instead of the default `uuid`, as this is what was setting `NVIDIA_VISIBLE_DEVICES=tegra`. With index set, the plugin sets `NVIDIA_VISIBLE_DEVICES=0`, and things start working.

TODO: Test mode=index without the CDI pre-generation.

Note: CDI is an OCI standard interface, which became enabled by default in k3s version 1.29, and released as stable
in version 1.31. However, in Nvidia device plugin mode `envvar`, this is handled internally, and doesn't depend on k3s support.
We have not tested `cdi-annotations` or `cdi-cri` mode, which would leverage this support.
https://github.com/nvidia/k8s-device-plugin?tab=readme-ov-file#configuration-option-details

## CUDA toolkit host-mounting

Starting with JetPack 5.0 (L4T r35.x, 2022), Nvidia removed `cuda.csv`, `cudnn.csv`,
and `tensorrt.csv` from `/etc/nvidia-container-runtime/host-files-for-container.d/`.
Only `l4t.csv` (driver/platform libs) is still host-mounted. Nvidia's intended model
is that CUDA toolkit libraries (libcublas, libcufft, etc.) are installed inside user
containers, not mounted from the host.

Sources:
- https://forums.developer.nvidia.com/t/missing-cuda-csv-cudnn-csv-tensorrt-csv-in-etc-nvidia-container-runtime-host-files-for-container-d/240831
- https://forums.developer.nvidia.com/t/what-does-the-cdi-config-via-nvidia-ctk-and-why-does-it-mount-so-libs-in-the-container/268191

We intentionally diverge from this. CHI@Edge devices are deployed to
bandwidth-constrained locations with slow storage. Bundling CUDA toolkit
libraries (~600MB-1.2GB) into every user container would force each deployment
to re-download them over constrained links. Instead, we host-mount
`/usr/local/cuda-${CUDA_VERSION}` from the infra image by adding it to `l4t.csv`
before CDI spec generation. CUDA libs are downloaded once during device
provisioning, and every user container gets them via the CDI mount. This keeps
user containers small (~20MB for a compiled CUDA binary).

More Refs
* https://gitlab.com/nvidia/container-images/l4t-base
* https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-base?version=r36.2.0
* https://catalog.ngc.nvidia.com/orgs/nvidia/containers/l4t-jetpack?version=r36.4.0
