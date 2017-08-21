FROM python:3.6

ADD . /test
WORKDIR /test
RUN find . -type f -name "*.py[co]" -delete && \
    find . -type d -name "__pycache__" -delete

RUN pip install -r requirement.txt -r mylibs/test/requirements.txt

ENV AWS_DEFAULT_REGION "us-east-1"
CMD ["./test/run_test.sh"]
