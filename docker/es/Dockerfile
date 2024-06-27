FROM openjdk:8-jdk-buster

WORKDIR /usr

# add a non root user
RUN useradd -m elasticuser

# Download extras
RUN apt update
RUN apt install -y curl

# Download elasticsearch
RUN curl -L -O https://download.elastic.co/elasticsearch/release/org/elasticsearch/distribution/tar/elasticsearch/2.3.5/elasticsearch-2.3.5.tar.gz
RUN tar -xvf elasticsearch-2.3.5.tar.gz

WORKDIR /usr/elasticsearch-2.3.5

# Add config
ADD elasticsearch.yml /usr/elasticsearch-2.3.5/config/elasticsearch.yml

# Install plugins
RUN curl -L https://github.com/ElasticHQ/elasticsearch-HQ/archive/refs/tags/v2.0.3.zip --output /tmp/elasticsearch-HQ-2.0.3.zip
RUN ./bin/plugin install "file:///tmp/elasticsearch-HQ-2.0.3.zip"
RUN curl -L https://repo1.maven.org/maven2/org/elasticsearch/plugin/mapper-attachments/2.3.5/mapper-attachments-2.3.5.zip --output /tmp/mapper-attachments-2.3.5.zip
RUN ./bin/plugin install "file:///tmp/mapper-attachments-2.3.5.zip"

RUN chown -R elasticuser: .
USER elasticuser

ENV JAVA_HOME=/usr/local/openjdk-18/bin/java
ENV discovery.type=single-node
ENV xpack.security.enabled: false
ENV xpack.ml.enabled: false

EXPOSE 9200 9300
ENTRYPOINT [ "./bin/elasticsearch" ]
