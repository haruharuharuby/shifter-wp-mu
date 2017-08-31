

run test as docker container.

```
docker build -f test/Dockerfile -t lambda-docker-remote-api-controller:test . && \
  docker run -it --rm lambda-docker-remote-api-controller:test
```

run unittest 

```
pip install -r requirements.txt -r mylibs/test/requirements.txt
pytest -v
```
