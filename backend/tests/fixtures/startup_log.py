"""Native stderr regression fixture; no servers or network calls."""
import sys
import time

print("INFO: Started regression service", file=sys.stderr, flush=True)
time.sleep(2)
print("ERROR: regression service exiting", file=sys.stderr, flush=True)
sys.exit(7)
