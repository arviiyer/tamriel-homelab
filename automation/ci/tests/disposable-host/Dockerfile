FROM docker:29.1.3-dind@sha256:173f284a4299164772a90f52b373e73e087583c0963f1334c9995f190ef6f3f5

RUN apk add --no-cache \
        bash=5.3.3-r1 \
        busybox-extras=1.37.0-r30 \
        curl=8.20.0-r0 \
        docker-registry=2.8.3-r23 \
        openssh-server=10.2_p1-r0 \
        python3=3.12.14-r0 \
        shadow=4.18.0-r0 \
        sudo=1.9.17_p2-r0 \
    && ln -s /usr/local/bin/docker /usr/bin/docker

COPY restricted_deploy.py /opt/disposable-delivery-drill/restricted_deploy.py
COPY sshd_config.example /opt/disposable-delivery-drill/sshd_config.example
COPY sudoers.example /opt/disposable-delivery-drill/sudoers.example
COPY disposable_host_drill.sh /usr/local/libexec/disposable_host_drill.sh

ENTRYPOINT ["/bin/bash", "/usr/local/libexec/disposable_host_drill.sh"]
