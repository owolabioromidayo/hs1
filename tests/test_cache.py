import os, urllib.parse, bmemcached, json
from dotenv import load_dotenv

load_dotenv()

print("Testing cache")
mc = bmemcached.Client(os.environ.get('MEMCACHEDCLOUD_SERVERS').split(','), os.environ.get('MEMCACHEDCLOUD_USERNAME'), os.environ.get('MEMCACHEDCLOUD_PASSWORD'))
print("Connected!")
print(mc.get('foo'))
print("Get foo from cache")
mc.set_multi({"foo": "bam", "train": "drain"})
print("Set multiple values")
print(mc.get('foo'))
print("Getting new value of foo")
mc.set("foo", "baz")
print("Setting foo to another value")
print(mc.get('foo'))
print("Getting new value of foo")
print(mc.get('train'))
print("Getting value of train")
print("Done! Tests passed.")
