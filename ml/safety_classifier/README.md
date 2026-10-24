# FT-1: safety classifier (model card)

**What it does:** reads a user's message (English, Hindi or Hinglish) and decides whether it
describes one of six hazards (`fire_smoke`, `shock`, `gas`, `water_electric`,
`battery_swollen`, `button_cell`) or none.

**Where it sits:** in the API's safety gate, after the keyword rules:

| Detected by | Behaviour |
|---|---|
| Keyword rules | Hard STOP, as before |
| FT-1 only | Fixy asks a one-tap check ("Just checking: is there smoke, sparks, a burning smell…?"). Yes leads to STOP; No continues |

The classifier is less certain than the rules, so its hits are confirmed instead of ending the session.

## Model

- **Features:** TF-IDF over character n-grams (2–5, within word boundaries, lowercase, sublinear tf). Character n-grams handle Devanagari, Hinglish spelling variants ("dhuan", "dhuwa", "dhuaan") and typos without a tokenizer.
- **Classifier:** multinomial logistic regression, `class_weight="balanced"`. C = 8, chosen by 5-fold cross-validated macro-F1.
- **Decision rule:** a hazard is flagged when 1 − P(none) ≥ **0.88**. The threshold was chosen on cross-validation for at least 98% hazard recall.
- **Runtime:** [`apps/api/src/fixwithme_api/safety_model.py`](../../apps/api/src/fixwithme_api/safety_model.py) re-implements inference in plain Python, with no scikit-learn in production.
  - Model file: 0.68 MB of JSON, 8,745 features.
  - Measured speed: about 0.2 ms per message on the development laptop.
  - Parity with scikit-learn: within 0.00004 on the exported self-test cases, checked in CI.

## Data

| Set | Size | How it was made |
|---|---|---|
| Templates | 2,760 | [`data/build_train.py`](data/build_train.py): hand-written patterns × items × EN/Hinglish/Hindi, with light noise |
| Gemma paraphrases | 1,067 | [`data/augment_gemma.py`](data/augment_gemma.py): Gemma 4 (26B A4B) through the Gemini API free tier. Prompts describe each class in general terms and never show test sentences; exact test sentences are filtered out |
| **Held-out test** | 128 (64 hazard, 64 harmless) | [`data/build_test.py`](data/build_test.py): written by hand **before** any training data, in deliberately different wording. Includes hard negatives such as "Fire TV stick remote", "smoke detector beeping", "light jal rahi hai" |

## Results

Held-out test set (128 messages):

| Detector | Trained on | Hazard recall | False alarms on harmless messages |
|---|---|---|---|
| Keyword rules (v1) | — | 67.2% (43/64) | 4.7% (3/64) |
| FT-1 alone | templates | 71.9% | 6.2% |
| FT-1 alone | templates + Gemma | 82.8% | 7.8% |
| Rules or FT-1 | templates | 82.8% | 10.9% |
| **Rules or FT-1 (deployed)** | **templates + Gemma** | **89.1% (57/64)** | **12.5% (8/64)** |

In the deployed gate, the 8 false alarms split into **3 hard STOPs from the rules** and **5 one-tap
checks from FT-1**. When FT-1 flagged a real hazard, it named the right hazard type every time.

FixBench-IN v1 opening messages (94): the rules and FT-1 together caught all 9 safety
messages. FT-1 also flagged 2 of the 85 non-safety messages, which led to a one-tap check, not a STOP.

**The Gemma paraphrases improved held-out hazard recall from 71.9% to 82.8%** for the classifier
on its own, at the cost of 1.6 points more false alarms.

## Known misses (held-out)

- *iron chalate waqt chingariyan nikli* ("sparks came out while using the iron")
- *the charger got so hot the plastic warped and smells*
- *got zapped by the switch*
- *the regulator of the cylinder is hissing*
- *the extension cord is lying in a puddle*
- *pani ki tanki overflow hoke wiring pe gira* ("the tank overflowed onto the wiring")
- *बच्चे के मुंह में बटन बैटरी थी, अब नहीं मिल रही* ("the child had a button battery in their mouth, now we can't find it")

These hazards are still covered by the product's own safety question (e.g. "Any burning smell or
smoke?"), which is always asked first. The rules' 3 false alarms ("smoke detector", "Fire TV stick",
"gas stove flame") are left as they are. Changing the rules because of held-out examples would
contaminate the test.

## Limitations

- The held-out set and the training templates have the same author, and the paraphrases come from
  one model family. The numbers are optimistic for real user messages.
- 64 hazard messages is a small test: one message is about 1.6 points.
- No transformer model was trained in this round. The comparison that matters for deployment
  (recall vs false alarms, with a model that fits the free 512 MB server) was made against the rules.
  A fine-tuned multilingual encoder (MuRIL or mDeBERTa class) is a candidate for a later round,
  if it can be served in the browser.

## Reproduce

```sh
apps/api/.venv/Scripts/python -m pip install scikit-learn
py -3.13 ml/safety_classifier/data/build_test.py
py -3.13 ml/safety_classifier/data/build_train.py
apps/api/.venv/Scripts/python ml/safety_classifier/data/augment_gemma.py   # needs a Gemini API key
apps/api/.venv/Scripts/python ml/safety_classifier/train.py --train templates,gemma --export
```
