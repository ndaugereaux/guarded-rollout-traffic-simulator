from dotenv import load_dotenv
import os
import ldclient
from ldclient.config import Config
from ldclient import Context
import time
import random

load_dotenv()

LAUNCHDARKLY_SDK_KEY = os.getenv("LAUNCHDARKLY_SDK_KEY")

# Error rates (percent) per variation. The big gap between them is what lets
# the guarded rollout detect a regression within the first short stage.
ERROR_RATE_TRUE = 40
ERROR_RATE_FALSE = 2

ldclient.set_config(Config(LAUNCHDARKLY_SDK_KEY))

if not ldclient.get().is_initialized():
    print("LaunchDarkly SDK failed to initialize. Check LAUNCHDARKLY_SDK_KEY in .env")
    ldclient.get().close()
    exit(1)

def get_random_user():
    return Context.builder(f"abcde_{random.randint(10000, 99999)}").build()

def check_gate(user):
    flag_value = ldclient.get().variation(
        "safeguard_test",
        user,
        False
    )
    print(f'flag_value: {flag_value}')
    return flag_value


# ERROR_RATE_TRUE% chance of error if True, ERROR_RATE_FALSE% chance of error if False
def throw_error_chance(value, user):
    chance = random.randint(1, 100)
    print(f"chance: {chance}")
    error_rate = ERROR_RATE_TRUE if value else ERROR_RATE_FALSE
    if chance <= error_rate:
        ldclient.get().track(
            "test-event",
            user
        )
        print(f"Error thrown for user {user}")

try:
    while True:
        loop_user = get_random_user()
        flag_passed = check_gate(loop_user)
        throw_error_chance(flag_passed, loop_user)

        time.sleep(.02)
except KeyboardInterrupt:
    pass
finally:
    # Flush any queued events so the last batch reaches LaunchDarkly
    ldclient.get().close()
