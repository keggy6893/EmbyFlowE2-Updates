#!/bin/bash
set -euo pipefail
task_root=${EMBYFLOW_ARM_BUILD_ROOT:-/workspace/local-artifacts/av1-arm-build}
export PATH="$task_root/toolchain/usr/bin:$task_root/tools/bin:$PATH"
export LD_LIBRARY_PATH="$task_root/toolchain/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"
task_sysroot="$task_root/toolchain/usr/arm-linux-gnueabihf"
task_prefix="$task_root/prefix"
task_cross="$task_root/toolchain/usr/bin/arm-linux-gnueabihf-"
task_flags="--sysroot=$task_sysroot -mcpu=cortex-a15 -mfpu=neon-vfpv4 -mfloat-abi=hard -O2"
mkdir -p "$task_prefix" "$task_root/build"
cat > "$task_root/hello.c" <<'EOF'
#include <stdio.h>
int main(void) { puts("ARM static toolchain OK"); return 0; }
EOF
"${task_cross}gcc" $task_flags -static "$task_root/hello.c" -o "$task_root/hello"
qemu-arm -cpu cortex-a15 "$task_root/hello"
cat > "$task_root/cross.ini" <<EOF
[binaries]
c = ['${task_cross}gcc', '--sysroot=$task_sysroot', '-mcpu=cortex-a15', '-mfpu=neon-vfpv4', '-mfloat-abi=hard']
ar = '${task_cross}ar'
strip = '${task_cross}strip'
pkg-config = '/usr/bin/pkg-config'
exe_wrapper = ['qemu-arm', '-cpu', 'cortex-a15']
[host_machine]
system = 'linux'
cpu_family = 'arm'
cpu = 'cortex-a15'
endian = 'little'
[properties]
needs_exe_wrapper = true
[built-in options]
c_link_args = ['-static']
EOF
if [ ! -f "$task_prefix/lib/libdav1d.a" ]; then
 meson setup "$task_root/build/dav1d" "$task_root/src/dav1d" --cross-file "$task_root/cross.ini" \
  --prefix "$task_prefix" --libdir lib --buildtype release --default-library static \
  -Denable_tools=false -Denable_examples=false -Denable_tests=false
 meson compile -C "$task_root/build/dav1d" -j 4
 meson install -C "$task_root/build/dav1d"
fi
if [ ! -f "$task_prefix/lib/libx264.a" ]; then
 cd "$task_root/src/x264"
 CC="${task_cross}gcc" ./configure --host=arm-linux-gnueabihf --cross-prefix="$task_cross" \
  --sysroot="$task_sysroot" --prefix="$task_prefix" --enable-static --enable-pic --disable-cli \
  --disable-opencl --bit-depth=8 --chroma-format=420 --extra-cflags="$task_flags" --extra-ldflags=-static
 make -j4
 make install
fi
export PKG_CONFIG_PATH="$task_prefix/lib/pkgconfig"
export PKG_CONFIG_LIBDIR="$task_prefix/lib/pkgconfig"
cd "$task_root/build"
mkdir -p ffmpeg
cd ffmpeg
if [ ! -f ffbuild/config.mak ] || grep -q '^LDFLAGS=.* -static ' ffbuild/config.mak; then
 "$task_root/src/ffmpeg/configure" --prefix="$task_root/output" --arch=arm --cpu=cortex-a15 \
  --target-os=linux --enable-cross-compile --cross-prefix="$task_cross" --sysroot="$task_sysroot" \
  --extra-cflags="$task_flags -I$task_prefix/include" --extra-ldflags="-static-libgcc -Wl,--sysroot=$task_root/toolchain -L$task_prefix/lib" \
  --pkg-config=/usr/bin/pkg-config --pkg-config-flags=--static \
  --disable-everything --disable-autodetect --disable-network --disable-doc --disable-debug \
  --disable-shared --enable-static --enable-small --enable-gpl --enable-pthreads \
  --disable-ffplay --disable-ffprobe --enable-ffmpeg --enable-neon --enable-vfp \
  --enable-libdav1d --enable-libx264 --enable-protocol=file,pipe \
  --enable-demuxer=matroska,mov --enable-parser=av1,aac,ac3,h264 \
  --enable-decoder=libdav1d,aac,ac3,eac3,mp3,flac,pcm_s16le \
  --enable-encoder=libx264,aac,wrapped_avframe \
  --enable-muxer=mp4,matroska,mpegts,null \
  --enable-filter=aresample,scale,format,null,anull,aformat,buffer,buffersink,abuffer,abuffersink \
  --enable-bsf=av1_frame_merge,av1_frame_split,extract_extradata,aac_adtstoasc,h264_mp4toannexb
fi
make -j4
mkdir -p "$task_root/output/bin"
cp ffmpeg "$task_root/output/bin/ffmpeg-av1-armhf"
"${task_cross}strip" "$task_root/output/bin/ffmpeg-av1-armhf"
qemu-arm -L "$task_sysroot" -cpu cortex-a15 "$task_root/output/bin/ffmpeg-av1-armhf" -hide_banner -decoders
