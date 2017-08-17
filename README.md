

run test as docker container.

```
docker build -f test/Dockerfile -t lambda-docker-remote-api-controller:test . && \
  docker run -it --rm lambda-docker-remote-api-controller:test
```