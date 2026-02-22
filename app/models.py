import json
from datetime import datetime
from peewee import Model, PostgresqlDatabase, CharField, IntegerField, TextField, BooleanField, DateTimeField
from playhouse.postgres_ext import JSONField
from app.config import DATABASE_URL

def parse_database_url(url):
    from urllib.parse import urlparse
    parsed = urlparse(url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 5432,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/')
    }

db_params = parse_database_url(DATABASE_URL)
db = PostgresqlDatabase(
    db_params['database'],
    host=db_params['host'],
    port=db_params['port'],
    user=db_params['user'],
    password=db_params['password']
)

class Album(Model):
    title = CharField()
    artist = CharField()
    year = IntegerField(null=True)
    year_discogs_release = IntegerField(null=True)
    physical_format = CharField(null=True)
    genres = JSONField(null=True, default=list)
    cover_image_path = CharField(null=True)
    discogs_id = CharField(null=True)
    is_wanted = BooleanField(default=False)
    notes = TextField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        table_name = 'albums'

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

class Artist(Model):
    name = CharField(unique=True)
    image_url = CharField(null=True)
    bio = TextField(null=True)
    genres = JSONField(null=True, default=list)
    lastfm_url = CharField(null=True)
    created_at = DateTimeField(default=datetime.now)
    updated_at = DateTimeField(default=datetime.now)

    class Meta:
        database = db
        table_name = 'artists'

    def save(self, *args, **kwargs):
        self.updated_at = datetime.now()
        return super().save(*args, **kwargs)

def create_tables():
    db.connect()
    db.create_tables([Album, Artist], safe=True)
    db.close()

def close_db(e):
    if not db.is_closed():
        db.close()
