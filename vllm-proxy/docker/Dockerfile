FROM python:3.11
# local_gpu_verifier depens on lxml 4.9 which requires python version <=3.11

WORKDIR /tmp

# openai patch
COPY docker/ ./docker/
RUN cd docker \
    && ./install_patch.sh \
    && cd .. \
    && rm -rf docker

# poetry
RUN pip install poetry==1.8.5
COPY ./pyproject.toml ./poetry.lock* ./
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes \
    && pip install --no-cache-dir --upgrade -r requirements.txt \
    && rm -rf requirements.txt

WORKDIR /app
COPY src ./
EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
