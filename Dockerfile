FROM ubuntu:focal
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get update &&  \
  apt-get install -yq eatmydata
RUN eatmydata apt-get install -yq --no-install-recommends  \
  make \
  build-essential \
  libssl-dev \
  zlib1g-dev \
  libbz2-dev