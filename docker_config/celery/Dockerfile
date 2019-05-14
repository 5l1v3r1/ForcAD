FROM python:3.7-alpine

RUN apk add gcc make musl-dev postgresql-dev

ADD backend/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

ADD ./docker_config/await_start.sh /await_start.sh
ADD ./docker_config/db_check.py /db_check.py
RUN chmod +x /await_start.sh

########## CUSTOMIZE ##########

ADD ./checkers/requirements.txt /checker_requirements.txt
RUN pip install -r /checker_requirements.txt

RUN apk add chromium chromium-chromedriver

########## END CUSTOMIZE ##########

ADD backend /app

ADD ./docker_config/celery/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN adduser -S celery
USER celery

CMD ["/entrypoint.sh"]