# Guarded Rollout Demo: `safeguard_test`

This demo creates simulated traffic so you can watch a LaunchDarkly **guarded rollout** detect a regression and roll itself back.

## How it works

`safeguard_test.py` runs in a loop, about 50 times per second. On each pass it:

1. Creates a new user context with a random key, like `abcde_48213`.
2. Evaluates the boolean flag `safeguard_test` for that user.
3. Sends a custom event called `test-event` to simulate an error. The chance depends on the variation the user got:

| Variation served | Chance of `test-event` | Role in the rollout |
|---|---|---|
| `false` | 2% (`ERROR_RATE_FALSE`) | Control (the current, safe behavior) |
| `true`  | 40% (`ERROR_RATE_TRUE`) | Treatment (the "new" behavior being rolled out) |

> The gap is deliberately huge, so `true` errors **20x** as often as `false`. With small gaps (for example 4% vs 2%) and one-minute stages, the rollout doesn't get enough treatment users to prove a regression, so it rolls forward instead of back. A 40% vs 2% gap is clear within the first stage.

The guarded rollout sends a growing share of users to `true` and compares its `test-event` rate against `false`. When it sees the higher error rate on `true`, it flags a regression and, if you turn on automatic rollback, sends everyone back to `false`.

---

## Part 1: LaunchDarkly setup

Do everything below in **the same project and environment** whose SDK key you'll put in `.env`. A sandbox or test environment is best. See the note on context volume at the end.

> Guarded rollouts need a plan that includes them. If you can't find the **Guarded rollout** option in step 3, check your account's entitlements.

### 1. Create the metric: `test-event`

1. Go to **Metrics**, then **Create metric**.
2. Configure it:
   - **Event kind:** Custom
   - **Event key:** `test-event`. This must match the code exactly.
   - **Metric definition:** set the three dropdowns so the sentence reads:

     > **Occurrence (Percent)** of **user** units that sent the event where **lower is better**

     - **Occurrence (Percent):** measures the percentage of users who hit the error at least once. Don't pick Sum or Average, because those need a numeric value and the script calls `track()` without one.
     - **user:** matches the context kind the script uses.
     - **lower is better:** the dropdown defaults to "higher is better", so **change it**. Otherwise the rollout reads more errors as an improvement and never rolls back.
   - **Name:** something like `Safeguard test errors`
3. Save the metric.

### 2. Create the flag: `safeguard_test`

1. Go to **Flags**, then **Create flag**.
2. Configure it:
   - **Name:** `safeguard_test`
   - **Key:** `safeguard_test`. This must match the code exactly.
   - **Type:** Boolean. Keep the defaults, so the variations are `true` and `false`.
3. Save the flag.
4. On the flag's **Targeting** tab for your environment:
   - Turn targeting **On**.
   - Make sure the **default rule** serves **`false`** to start. `false` is the baseline the rollout compares against.
   - Save.

### 3. Set up the guarded rollout on the default rule

1. On the flag's **Targeting** tab, edit the **Default rule**.
2. Choose **Guarded rollout** as the serve option. You can also start it from the flag's rollout menu, depending on your UI version.
3. Configure it:
   - **Variation to roll out:** `true`
   - **Control / current variation:** `false`
   - **Randomize by:** `user`
   - **Metrics to monitor:** add `test-event` (the metric from step 1)
   - **Regression threshold:** keep the default, or lower it to detect faster
   - **On regression:** turn on **automatic rollback**. This is what makes the demo roll back on its own. "Notify only" just alerts you.
   - **Rollout stages / duration:** for a demo, pick the **shortest duration** available so you don't wait hours.
4. Review and save or start the rollout. **Start the script (Part 2) right away** so the first stage has traffic.

### 4. Get the SDK key

1. Go to **Project settings**, then **Environments**, and pick the environment you used above.
2. Copy the **SDK key**. It's the server-side key and starts with `sdk-`. Don't use the client-side ID or the mobile key.

---

## Part 2: Local setup

### Prerequisites
- Python 3.9 or newer
- Network access to LaunchDarkly (`*.launchdarkly.com`)

### Install

From this folder:

```bash
python3 -m venv .venv
```

```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
```

### Configure

Copy the example env file:

```bash
cp .env.example .env
```

Open `.env` and replace the placeholder with the SDK key from Part 1, step 4:

```
LAUNCHDARKLY_SDK_KEY=sdk-your-real-key-here
```

Don't commit `.env`. It holds a secret.

### Run

```bash
python3 safeguard_test.py
```

The output should look like this:

```
flag_value: False
chance: 42
flag_value: True
chance: 98
Error thrown for user Context(...)
...
```

Leave it running for the whole rollout. Press **Ctrl+C** to stop.

---

## Part 3: Watch the rollback

1. Open the flag in LaunchDarkly and go to its guarded rollout / monitoring view.
2. In the first few minutes you should see:
   - Evaluations arriving for both `true` and `false`. Check the flag's **Insights** or evaluation graph.
   - `test-event` events arriving. Check **Metrics**, then `test-event`, or the Live events debugger.
3. After the rollout collects enough samples, it should show a **regression** on `test-event` for `true`.
4. With automatic rollback on, LaunchDarkly **rolls the default rule back to `false`**. You'll see this in the flag's history, and the script output will switch to `flag_value: False` for everyone.

How long it takes depends on the rollout duration and threshold you picked. With the default 40% vs 2% rates, expect a regression to be detected and rolled back within the first stage or two, even with one-minute stages.

---

## Troubleshooting

| Symptom | Likely cause |
|---|---|
| Every line prints `flag_value: False`, even after the rollout starts | SDK key from a different environment, flag key typo, or targeting is off. (A bad key makes the script exit at startup.) |
| Flag evaluates fine but the metric shows no events | Event key mismatch (must be `test-event`), or the metric was created in a different project. |
| Rollout rolls forward instead of back | Error rates too close together for your stage lengths (see **Tuning the demo**), metric set to "Higher is better" (it must be **Lower is better**), metric not attached to the rollout, or not enough time or traffic yet. |
| Regression detected but no rollback | Rollout was set to notify only. Turn on automatic rollback. |
| `ModuleNotFoundError: ldclient` or `dotenv` | The virtualenv isn't activated, or `pip install -r requirements.txt` wasn't run. |

## Notes

- **Context volume:** each loop iteration creates a new user, which works out to about 50 per second or 180k per hour. That counts toward your context/MAU usage, so run this in a sandbox and stop it when you're done. To slow it down, increase `time.sleep(.02)`.
- **Tuning the demo:** change `ERROR_RATE_TRUE` and `ERROR_RATE_FALSE` at the top of the script. The closer they are, the more traffic and time the rollout needs to detect a regression. If the gap is too small for your stage lengths, the rollout rolls forward instead.
- **Stopping:** press Ctrl+C. The script flushes queued events before it exits.
- **Startup check:** if the SDK can't connect (for example, because the key is wrong), the script prints an error and exits instead of silently serving `False`.
