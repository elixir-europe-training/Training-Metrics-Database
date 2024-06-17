FROM fedora:40

ARG UID=1000
ARG GID=1000
ARG UNAME=runner
ARG SRCDIR=/opt/tmd/src
ARG CONFDIR=/opt/tmd/conf
ARG DATADIR=/opt/tmd/data
ARG DBPASS="password"
ARG DBUSER="tmd"
ARG DBNAME="tmd"

RUN dnf update -y
RUN dnf install -y \
    postgresql-server \
    postgresql-contrib

RUN groupadd -g "$GID" "$UNAME" && useradd -u "$UID" -g "$GID" "$UNAME"

RUN systemctl enable postgresql

RUN mkdir -p "$SRCDIR"
RUN mkdir -p "$CONFDIR"
RUN mkdir -p "$DATADIR"

RUN chown "$UNAME":"$UNAME" -R "$SRCDIR"
RUN chown "$UNAME":"$UNAME" -R "$CONFDIR"
RUN chown "$UNAME":"$UNAME" -R "$DATADIR"

RUN dnf install -y \
    python \
    pip \
    libpq-devel \
    python-devel \
    gcc-c++

USER "$UNAME"
WORKDIR "$SRCDIR"

# Setup database
ENV PGDATA="$DATADIR" 
RUN initdb
RUN cat >"./postgres-conf.sql" <<EOL
CREATE USER $DBUSER WITH PASSWORD '$DBPASS';
CREATE DATABASE $DBNAME OWNER $DBUSER;
EOL
RUN cat >"./init-script.sh" <<EOL
postgres -k /tmp &
sleep 10s
ls -la /tmp
psql -h /tmp -d postgres -a -f ./postgres-conf.sql
EOL
RUN chmod +x ./init-script.sh
RUN ./init-script.sh

COPY utils "$SRCDIR/utils"

RUN python -m venv "$SRCDIR/.venv"
RUN bash -c "source '$SRCDIR/.venv/bin/activate'; python -m pip install -r utils/requirements.txt"
RUN bash -c "source '$SRCDIR/.venv/bin/activate'; python -m pip install setuptools"

COPY tmd "$SRCDIR/tmd"
COPY metrics "$SRCDIR/metrics"
COPY dash_app "$SRCDIR/dash_app"
COPY templates "$SRCDIR/templates"
COPY manage.py "$SRCDIR/manage.py"

ENV DJANGO_POSTGRESQL_DBNAME=$DBNAME
ENV DJANGO_POSTGRESQL_USER=$DBUSER
ENV DJANGO_POSTGRESQL_PASSWORD=$DBPASS
ENV DJANGO_POSTGRESQL_HOST=localhost
ENV DJANGO_POSTGRESQL_PORT=5432

RUN cat >"./start-script.sh" <<EOL
postgres -k /tmp &
sleep 5s
source .venv/bin/activate
./manage.py migrate --run-syncdb
./manage.py runserver 0.0.0.0:4000
EOL
RUN chmod +x ./start-script.sh

CMD ./start-script.sh