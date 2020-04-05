FROM ubuntu:focal
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update &&  \
  apt-get install -yq eatmydata
RUN eatmydata apt-get install -yq --no-install-recommends  \
  make \
  build-essential \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev \
  libisal-dev \
  libisal2 \
  libreadline-dev \
  libsqlite3-dev \
  wget \
  curl \
  llvm \
  libncursesw5-dev \
  xz-utils \
  tk-dev \
  libxml2-dev \
  libxmlsec1-dev \
  libffi-dev \
  liblzma-dev \
  git \
  ca-certificates \
  cargo \
  gzip \
  pigz \
  bzip2 \
  pbzip2 \
  autoconf \
  automake \
  shtool \
  coreutils \
  autogen \
  libtool \
  shtool \
  nasm && \
  apt-get clean autoclean && \
