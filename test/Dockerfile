FROM python:3.6

# create cache
ADD requirement.txt /test/requirement.txt
ADD mylibs/test/requirements.txt /test/mylibs/test/requirements.txt
WORKDIR /test
RUN pip install -r requirement.txt -r mylibs/test/requirements.txt

ADD . /test
RUN find . -type f -name "*.py[co]" -delete && \
    find . -type d -name "__pycache__" -delete

ENV AWS_DEFAULT_REGION "us-east-1"
CMD ["./test/run_test.sh"]
