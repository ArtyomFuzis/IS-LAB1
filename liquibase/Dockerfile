FROM liquibase/liquibase:4.33

COPY changelog.xml /liquibase/changelog.xml
COPY run-migrations.sh /run-migrations.sh

USER root
RUN chmod 755 /run-migrations.sh
USER liquibase

ENTRYPOINT ["/bin/sh", "/run-migrations.sh"]
