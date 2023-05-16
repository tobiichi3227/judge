FROM ubuntu:20.04
ARG TRAVIS_COMMIT
ENV TRAVIS_COMMIT $TRAVIS_COMMIT
ENV TZ=Asia/Taipei
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update && apt-get install -y \
    python3.8 \
    python3-pip \
    clang \
    gcc \
    g++ \
    llvm \
    cmake \
    libcgroup-dev \
    git \
    sudo \
    acl \
    rustc

RUN if [ "${TRAVIS_COMMIT}" ]; then \
    mkdir judge && \
    cd judge && \
    git init && \
    git remote add origin https://github.com/tobiichi3227/judge.git && \
    git fetch origin && \
    git fetch origin ${TRAVIS_COMMIT} && \
    git reset --hard FETCH_HEAD; \
    else \
    git clone https://github.com/tobiichi3227/judge.git; fi

RUN cd judge && \
    pip3 install -r requirements.txt && \
    mkdir lib && \
    cd lib && \
    cmake .. && \
    make
