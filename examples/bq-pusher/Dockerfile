FROM registry.access.redhat.com/ubi9/ubi-minimal:latest

ENV PYTHONUNBUFFERED True

ENV APP_HOME /app
WORKDIR $APP_HOME
COPY . ./

ENV PORT 1234

# Install Python 3.11
RUN microdnf install -y --nodocs --setopt=keepcache=0 --setopt=tsflags=nodocs \
    python3.11 python3.11-pip \
    && microdnf clean all --enablerepo='*'

RUN pip3.11 install --no-cache-dir --upgrade pip wheel \
    && pip3.11 install --no-cache-dir --upgrade -r requirements.txt

# Run the web service with one worker on gunicorn
CMD exec uvicorn main:app --host 0.0.0.0 --port ${PORT} --workers 1
