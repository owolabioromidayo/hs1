import os, urllib.parse, bmemcached, json
from dotenv import load_dotenv

load_dotenv()

mc = bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD'))
print(mc.get('foo'))
mc.set_multi({"foo": "bam", "train": "drain"})
print(mc.get('foo'))
mc.set("foo", "baz")
print(mc.get('foo'))
print(mc.get('train'))
