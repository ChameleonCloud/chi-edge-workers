#!/bin/bash
set -o errexit

no_kmod() {
	echo "The target host device _should_ have kernel support. Skipping kernel module build."
	echo "Writing flag file"
	echo 0>$(pwd)/kmod_built
	install_tools
	exit 0
}

install_kmod() {
	echo "building kmods with args ${1} ${2} ${3}"
	BALENA_MACHINE_NAME="${1}"
	OS_VERSION=${2}
	L4T_VER=${3:-false}

	#remove suffix for file path
	OS_FOLDER="${OS_VERSION%\.prod}"

	# Create build directories
	local build_dir="/build/${BALENA_MACHINE_NAME}/${OS_FOLDER}"

	mkdir -p "${build_dir}"
	cd "${build_dir}"

	local balena_images="https://files.balena-cloud.com/images"
	local km_source="${balena_images}/${BALENA_MACHINE_NAME}/${OS_VERSION}"/kernel_modules_headers.tar.gz

	echo "Getting kernel modules from ${km_source}"
	local headers_tarball="$(echo "${km_source}" | sed -e 's/+/%2B/')"
	curl -SsL -o headers.tar.gz "${headers_tarball}"

	if [[ ${L4T_VER} == "32.7.3" ]]; then
		install_kmod_r32
	elif [[ ${L4T_VER} == "36.4" ]]; then
		install_kmod_r36
	else
		echo "Unsupported L4T_VER: ${L4T_VER}" >&2
		exit 1
	fi
}

build_ipip() {
	# Build ipip.ko + tunnel4.ko from the OE4T branch matching the running
	# kernel, against an already-prepared kernel tree. Vermagic + symver CRCs
	# match balenaOS by construction.
	local kernel_tree="${1}"
	local oe4t_base="${2}"

	echo "Fetching ipip.c + tunnel4.c from ${oe4t_base}"
	mkdir -p ipip/src
	curl -fsSL -o ipip/src/ipip.c    "${oe4t_base}/ipip.c"
	curl -fsSL -o ipip/src/tunnel4.c "${oe4t_base}/tunnel4.c"
	printf 'obj-m += ipip.o\nobj-m += tunnel4.o\n' > ipip/src/Makefile

	echo "Compiling IPIP modules"
	make -C "${kernel_tree}" M="$(pwd)"/ipip/src -j"$(nproc)"

	local ipip_out="/build/ipip/${BALENA_MACHINE_NAME}/${OS_FOLDER}"
	mkdir -p "${ipip_out}"
	cp ipip/src/ipip.ko    "${ipip_out}/"
	cp ipip/src/tunnel4.ko "${ipip_out}/"
}

install_kmod_r32() {
	echo "Performing L4T r32.7 specific build"
	tar -xf headers.tar.gz
	mv "4.9.299-l4t-r32.7.3/build" "kernel_modules_headers"
	# Download missing header(s) from the matching OE4T branch
	# (see https://forums.balena.io/t/build-kernel-module-out-of-tree-for-jetson/295852/20)
	mkdir -p kernel_modules_headers/arch/arm/include/asm/xen
	curl -SsL -o kernel_modules_headers/arch/arm/include/asm/xen/hypervisor.h \
		https://raw.githubusercontent.com/OE4T/linux-tegra-4.9/oe4t-patches-l4t-r32.7/arch/arm/include/asm/xen/hypervisor.h

	echo "Getting Wireguard kernel source"
	git clone https://git.zx2c4.com/wireguard-linux-compat

	echo "Compiling Wireguard module"
	make -C kernel_modules_headers -j"$(nproc)" modules_prepare
	make -C kernel_modules_headers M="$(pwd)"/wireguard-linux-compat/src -j"$(nproc)"

	build_ipip kernel_modules_headers \
		"https://raw.githubusercontent.com/OE4T/linux-tegra-4.9/oe4t-patches-l4t-r32.7/net/ipv4"

	local wg_out="/build/wireguard/${BALENA_MACHINE_NAME}/${OS_FOLDER}"
	mkdir -p "${wg_out}"
	cp wireguard-linux-compat/src/wireguard.ko "${wg_out}/"
}

install_kmod_r36() {
	echo "Performing L4T r36.4 specific build"

	# Auto-detect inner kernel build tree by locating .config
	local depth
	depth=$(tar tf headers.tar.gz | grep '/\.config$' | head -1 | tr -dc / | wc -c)
	mkdir kernel_modules_headers
	tar --strip-components="$depth" -C kernel_modules_headers -xf headers.tar.gz
	test -f kernel_modules_headers/.config -a -f kernel_modules_headers/Module.symvers

	make -C kernel_modules_headers -j"$(nproc)" modules_prepare

	build_ipip kernel_modules_headers \
		"https://raw.githubusercontent.com/OE4T/linux-jammy-nvidia-tegra/oe4t-patches-l4t-r36.4-1012.12/net/ipv4"
	# wireguard is in-tree on 5.15; modprobe wireguard at runtime, no build.
}

install_tools() {
	echo "Compiling tools"

	# Create build directory
	local build_dir="/build/tools/"
	mkdir -p "${build_dir}"
	cd "${build_dir}"

	git clone https://git.zx2c4.com/wireguard-tools
	make -C $(pwd)/wireguard-tools/src -j$(nproc)
	mkdir -p $(pwd)/tools
	make -C $(pwd)/wireguard-tools/src DESTDIR=$(pwd)/tools install
}

# Build kernel modules for all supported devices: MACHINE_NAME OS_VERSION L4T_VERSION
install_kmod "jetson-nano" "4.0.9+rev2" "32.7.3"
install_kmod "jetson-xavier-nx-devkit-emmc" "6.0.13" "32.7.3"
install_kmod "jetson-orin-nano-devkit-nvme" "6.10.26+rev1" "36.4"
install_kmod "jetson-orin-nano-devkit-nvme" "6.12.2" "36.4"
install_kmod "jetson-agx-orin-devkit-64gb" "6.12.2" "36.4"
# raspberrypi4/5 in-tree

install_tools
