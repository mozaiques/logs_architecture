"""Send JSON events from a file to an adequatly structured (see
`requests_table.sql`) SQL table.


This script isn't particularly foolproof. It is intented to be invoked
with the full file path as last argument and a RFC-1738 URL to the
database (which will be given to SQLAlchemy) as second to last argument,
eg:

    python to_sql.py postgresql://user:pass@host:port/dbname /path/to/events.json


Dependencies:

    * sqlalchemy
    * python-dateutil
    * 'database specific driver' (psycopg2 for postgresql for instance)

"""

import time

# Initial setup
init_start_time = time.time()

import datetime
import json
import logging
import sys

from dateutil.parser import parse
from dateutil.tz import tzlocal
import sqlalchemy as sa


class Formatter(logging.Formatter):

    def formatTime(self, record, datefmt=None):
        dt = datetime.datetime.fromtimestamp(record.created, tzlocal())
        if datefmt:
            s = dt.strftime(datefmt)
        else:
            t = dt.strftime(self.default_time_format)
            s = self.default_msec_format % (t, record.msecs)
        return s


logger = logging.getLogger('to_sql')
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(Formatter('%(asctime)s [%(name)s]: %(message)s', datefmt='%Y-%m-%d %H:%M:%S %z'))
logger.addHandler(handler)
logger.setLevel(logging.INFO)


requests_table = sa.sql.table(
    'requests',
    sa.sql.column('datetime', sa.DateTime(timezone=True)),
    sa.sql.column('app', sa.Text),
    sa.sql.column('instance', sa.Text),
    sa.sql.column('client_ip', sa.Text),
    sa.sql.column('client_id', sa.Integer),
    sa.sql.column('request_method', sa.Text),
    sa.sql.column('request_path', sa.Text),
    sa.sql.column('response_code', sa.Integer),
    sa.sql.column('response_size', sa.Integer),
    sa.sql.column('response_time', sa.Integer),
    sa.sql.column('client_ua', sa.Text),
)

init_delta_ms = str(int((time.time() - init_start_time) * 1000))


# Parse file
parse_start_time = time.time()
to_insert = []
for raw_log in open(sys.argv[-1]):

    log = json.loads(raw_log)

    log['datetime'] = parse(log.pop('time'))
    log['client_id'] = log['client_id'] if log['client_id'] != '-' else None
    log['app'], log['instance'] = log.pop('tag').split('.')

    to_insert.append(log)
parse_delta_ms = str(int((time.time() - parse_start_time) * 1000))


# Connect & insert into DB
sql_start_time = time.time()
engine_url = sys.argv[-2]
engine = sa.create_engine(engine_url)

try:
    connection = engine.connect()
except sa.exc.OperationalError:
    logger.warn('error while trying to connect to \'{}\''.format(engine_url))
    sys.exit(1)

connection.execute(requests_table.insert(), to_insert)
sql_delta_ms = str(int((time.time() - sql_start_time) * 1000))

logger.info('{} logs from {} flushed to {} (init: {}ms | parse: {}ms | sql: {}ms)'.format(
    str(len(to_insert)),
    '{}.{}'.format(log['app'], log['instance']),
    engine.url.host,
    init_delta_ms,
    parse_delta_ms,
    sql_delta_ms,
))
