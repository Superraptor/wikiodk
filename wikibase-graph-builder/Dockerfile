FROM debian:bullseye-slim

# Not sure if necessary.
USER root

# https://github.com/HKdigital/docker-image--debian-slim/blob/main/Dockerfile
ENV APT_SOURCES_REFRESHED_AT 2023-05-22_10h50

# System dependencies, see:
# https://www.rosehosting.com/blog/how-to-install-node-js-and-npm-on-debian-11/
# https://github.com/HKdigital/docker-image--debian-slim/blob/main/Dockerfile
RUN apt-get update; \
    apt-get install --no-install-recommends --no-install-suggests -y \
        nano \
        telnet \
        iproute2 \
        iputils-ping \
        wget \
        tar \
        unzip \
        rsync \
        sudo \
        procps \
        gnupg \
        git \
        python3 \
        curl \
        ca-certificates \
        dumb-init > /dev/null

# https://github.com/HKdigital/docker-image--debian-slim/blob/main/Dockerfile
ENV IMAGE_FILES_REFRESHED_AT 2023-05-22_10h50

# Copy over ./image-files/
RUN git clone https://github.com/HKdigital/docker-image--debian-slim.git /srv/docker-image--debian-slim
RUN cp -r /srv/docker-image--debian-slim/image-files /

# https://github.com/nodesource/distributions?tab=readme-ov-file#debian-versions
RUN curl -fsSL https://deb.nodesource.com/setup_22.x -o nodesource_setup.sh

# https://github.com/nodesource/distributions?tab=readme-ov-file#debian-versions
RUN bash nodesource_setup.sh

# https://github.com/nodesource/distributions?tab=readme-ov-file#debian-versions
RUN apt-get install -y nodejs

# https://www.rosehosting.com/blog/how-to-install-node-js-and-npm-on-debian-11/
RUN apt update
RUN apt upgrade -y

# Install pnpm, see:
# https://pnpm.io/installation
RUN npm install -g pnpm

# Clone repo
RUN git clone https://github.com/AngryLoki/wikidata-graph-builder.git /srv/wikidata-graph-builder

# Switch to repo
WORKDIR /srv/wikidata-graph-builder

# Install pnpm, per: https://github.com/AngryLoki/wikidata-graph-builder
RUN pnpm install

# Change ownership
RUN chmod 755 /srv
RUN chmod 755 /srv/wikidata-graph-builder

# Switchback.
WORKDIR /srv/

# Run entrypoint.
ENTRYPOINT ["/usr/bin/dumb-init", "--"]
CMD ["/srv/docker-image--debian-slim/image-files/srv/run.sh"]