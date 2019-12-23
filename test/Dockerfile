FROM python:3.7

# create cache
ADD requirements.txt /test/requirements.txt
ADD mylibs/test/requirements.txt /test/mylibs/test/requirements.txt
WORKDIR /test
RUN pip install -r requirements.txt -r mylibs/test/requirements.txt

ADD . /test
RUN find . -type f -name "*.py[co]" -delete && \
    find . -type d -name "__pycache__" -delete

ENV AWS_DEFAULT_REGION "us-east-1"
ENV AWS_XRAY_SDK_ENABLED "false"
CMD ["./test/run_test.sh"]
