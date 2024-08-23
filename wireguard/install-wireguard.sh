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
    echo headers_tarball
    curl -SsL -o headers.tar.gz "${headers_tarball}"
    tar -xf headers.tar.gz

	if [[ ${L4T_VER} == "32.7.3" ]]; then
        echo "Performing L4T specific build"
        # rename linux tegra build directory
		mv "4.9.299-l4t-r32.7.3/build" "kernel_modules_headers"
        # Download missing header(s)
		mkdir -p kernel_modules_headers/arch/arm/include/asm/xen
		# Balena uses OE4T kernel per https://forums.balena.io/t/build-kernel-module-out-of-tree-for-jetson/295852/20
		curl -SsL -o kernel_modules_headers/arch/arm/include/asm/xen/hypervisor.h \
			https://raw.githubusercontent.com/OE4T/linux-tegra-4.9/oe4t-patches-l4t-r32.7/arch/arm/include/asm/xen/hypervisor.h
	fi

	echo "Getting Wireguard kernel source"
	git clone https://git.zx2c4.com/wireguard-linux-compat

	echo "Compiling kernel module"
	make -C kernel_modules_headers -j"$(nproc)" modules_prepare
	make -C kernel_modules_headers M="$(pwd)"/wireguard-linux-compat/src -j"$(nproc)"

	if [[ ${L4T_VER} == "32.7.3" ]]; then
		echo "Building IPIP modules"
		local output_dir="/build/ipip/${BALENA_MACHINE_NAME}/${OS_FOLDER}"
		mkdir -p "${output_dir}"
		cp -r /usr/src/ipip "${build_dir}/ipip"
		make -C kernel_modules_headers M="$(pwd)"/ipip/src -j"$(nproc)"
		cp ipip/src/ipip.ko "${output_dir}/"
		cp ipip/src/tunnel4.ko "${output_dir}/"
	fi

	# create output directory and copy module
	local output_dir="/build/wireguard/${BALENA_MACHINE_NAME}/${OS_FOLDER}"
	mkdir -p "${output_dir}"
	cp wireguard-linux-compat/src/wireguard.ko "${output_dir}/"

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

# Build kernel modules for all supported devices MACHINE_NAME OS_VERSION, L4T_VERSION
install_kmod "jetson-nano" "4.0.9+rev2" "32.7.3"
install_kmod "jetson-xavier-nx-devkit-emmc" "4.0.9+rev2" "32.7.3"
# raspberrypi4/5 in-tree

install_tools
