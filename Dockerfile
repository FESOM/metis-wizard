FROM python:3.12-slim

RUN apt update && apt upgrade -y && apt install -y git

WORKDIR /usr/src/app

COPY . .

RUN pip install .

ENTRYPOINT ["metis-wizard"]
CMD [ "--help" ]
