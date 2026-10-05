FROM --platform=linux/amd64 lscr.io/linuxserver/webtop:debian-xfce-1d8767cb-ls207@sha256:9d12a70b87635ced4e884b937065ecd3dbe9e8b9e8c0b422e64300d945a79238
# Freeze Debian dependencies as well as the browser desktop base.
RUN rm -f /etc/apt/sources.list /etc/apt/sources.list.d/* && \
    printf 'deb [check-valid-until=no] https://snapshot.debian.org/archive/debian/20261001T000000Z/ trixie main contrib non-free non-free-firmware\n' > /etc/apt/sources.list && \
    dpkg --add-architecture i386 && apt-get update && \
    apt-get install -y --no-install-recommends wine=10.0~repack-6 wine64=10.0~repack-6 wine32:i386=10.0~repack-6 libwine:amd64=10.0~repack-6 libwine:i386=10.0~repack-6 fonts-wine=10.0~repack-6 python3 zenity cabextract mesa-utils libgl1-mesa-dri:amd64 libgl1-mesa-dri:i386 libvulkan1:amd64 libvulkan1:i386 && \
    rm -rf /var/lib/apt/lists/*
COPY scripts/ /opt/solid-edge/
COPY init/ /custom-cont-init.d/
RUN chmod +x /opt/solid-edge/*.py /custom-cont-init.d/*
ENV WINEPREFIX=/config/wine/solid-edge WINEARCH=win64 PIXELFLUX_WAYLAND=false START_DOCKER=false
RUN chmod +x /opt/solid-edge/entrypoint.sh
ENTRYPOINT ["/opt/solid-edge/entrypoint.sh"]
