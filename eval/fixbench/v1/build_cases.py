"""Source of truth for FixBench-IN v1 cases. Run to regenerate cases.jsonl.

Each case: the user's opening description, the facts the user would give if asked (anything
missing is "unknown"), and the gold outcome. Facts were written from the physical situation,
not from the engine's likelihood tables; "hard"/"atypical" cases deliberately break the
textbook pattern. Written by the project author: v1 is not independently reviewed.
"""

import json
from collections import Counter
from pathlib import Path

Y, N, U = "yes", "no", "unknown"


def fan(burning=N, runs=U, hums=U, push_spins=U, slow=U, speed_change=U, other_power=U, noise=U):
    return locals()


def eb(burnt=N, hot=N, wall_works=U, reset_popped=U, heavy_load=U, light_on=U, some_sockets=U, switch_loose=U, wiggle=U):
    return locals()


def hp(swollen=N, wireless=U, other_device=U, wiggle=U, lint=U, lights_up=U, one_side=U):
    return locals()


def toy(swallowed=N, swollen=N, is_remote=U, fresh_tried=U, crust=U, lights_no_move=U, camera_light=U, tap_works=U):
    return locals()


def C(cause):
    return {"type": "cause", "cause": cause}


def S(hazard):
    return {"type": "stop", "hazard": hazard}


UNS = {"type": "unsupported"}

CASES = [
    # ---------------- ceiling fan ----------------
    ("fan-01", "ceiling_fan", "en", "My ceiling fan hums when I switch it on but the blades don't move. If I give it a push it starts slowly.", C("capacitor_weak"), fan(runs=N, hums=Y, push_spins=Y, slow=Y, speed_change=Y, other_power=Y, noise=N), "typical"),
    ("fan-02", "ceiling_fan", "hinglish", "pankha bahut dheere chal raha hai, full speed pe bhi slow hai", C("capacitor_weak"), fan(runs=Y, push_spins=Y, slow=Y, speed_change=Y, other_power=Y, noise=N), "typical"),
    ("fan-03", "ceiling_fan", "hi", "पंखा चालू करने पर गुनगुनाता है पर घूमता नहीं", C("capacitor_weak"), fan(runs=N, hums=Y, push_spins=Y, speed_change=N, other_power=Y, noise=N), "typical"),
    ("fan-04", "ceiling_fan", "en", "Fan takes a long time to pick up speed and stays slow all day", C("capacitor_weak"), fan(runs=Y, hums=N, push_spins=Y, slow=Y, speed_change=Y, other_power=Y, noise=N), "atypical"),
    ("fan-05", "ceiling_fan", "hinglish", "fan start nahi hota jab tak haath se ghumao nahi", C("capacitor_weak"), fan(runs=N, push_spins=Y, other_power=Y, noise=N), "typical"),
    ("fan-06", "ceiling_fan", "en", "Ceiling fan completely dead, no sound at all", C("no_power"), fan(runs=N, hums=N, push_spins=Y, slow=N, speed_change=N, other_power=N, noise=N), "typical"),
    ("fan-07", "ceiling_fan", "hinglish", "fan bilkul band hai, kamre ki light bhi nahi aa rahi", C("no_power"), fan(runs=N, hums=N, push_spins=Y, speed_change=N, other_power=N, noise=N), "typical"),
    ("fan-08", "ceiling_fan", "hi", "पंखा नहीं चल रहा और कमरे की लाइट भी बंद है", C("no_power"), fan(runs=N, hums=N, push_spins=Y, other_power=N), "typical"),
    ("fan-09", "ceiling_fan", "en", "Fan stopped working. The lights in the room are fine and the MCB looks ok.", C("no_power"), fan(runs=N, hums=N, push_spins=Y, slow=N, speed_change=N, other_power=Y, noise=N), "hard"),
    ("fan-10", "ceiling_fan", "en", "Fan only runs at full speed, the regulator doesn't change anything", C("regulator_faulty"), fan(runs=Y, hums=N, push_spins=Y, slow=N, speed_change=N, other_power=Y, noise=N), "typical"),
    ("fan-11", "ceiling_fan", "hinglish", "regulator ghumane se speed change nahi hoti, pankha ek hi speed pe chalta hai", C("regulator_faulty"), fan(runs=Y, hums=N, push_spins=Y, slow=N, speed_change=N, other_power=Y, noise=N), "typical"),
    ("fan-12", "ceiling_fan", "hi", "रेगुलेटर से पंखे की स्पीड नहीं बदलती", C("regulator_faulty"), fan(runs=Y, push_spins=Y, slow=N, speed_change=N, other_power=Y, noise=N), "typical"),
    ("fan-13", "ceiling_fan", "en", "Fan works on 5 but on 1 and 2 it just hums", C("regulator_faulty"), fan(runs=Y, hums=Y, push_spins=Y, slow=N, speed_change=N, other_power=Y, noise=N), "hard"),
    ("fan-14", "ceiling_fan", "en", "Fan makes a grinding noise and the blades feel stiff when I turn them by hand", C("bearing_stiff"), fan(runs=Y, hums=Y, push_spins=N, slow=Y, speed_change=Y, other_power=Y, noise=Y), "typical"),
    ("fan-15", "ceiling_fan", "hinglish", "fan se khad khad ki awaaz aati hai aur haath se ghumane me tight hai", C("bearing_stiff"), fan(runs=Y, push_spins=N, slow=Y, other_power=Y, noise=Y), "typical"),
    ("fan-16", "ceiling_fan", "hi", "पंखा जाम है, हाथ से भी मुश्किल से घूमता है", C("bearing_stiff"), fan(runs=N, hums=Y, push_spins=N, other_power=Y), "typical"),
    ("fan-17", "ceiling_fan", "en", "Our old fan runs slow and noisy", C("bearing_stiff"), fan(runs=Y, hums=N, push_spins=N, slow=Y, speed_change=Y, other_power=Y, noise=Y), "atypical"),
    ("fan-18", "ceiling_fan", "en", "The fan was rewound once before. Now it hums loudly and runs very slow.", C("winding_fault"), fan(runs=Y, hums=Y, push_spins=Y, slow=Y, speed_change=N, other_power=Y, noise=N), "hard"),
    ("fan-19", "ceiling_fan", "hinglish", "fan se jalne ki smell aa rahi hai", S("fire_smoke"), fan(burning=Y), "safety-text"),
    ("fan-20", "ceiling_fan", "en", "My ceiling fan stopped working", S("fire_smoke"), fan(burning=Y, runs=N, hums=Y, other_power=Y), "safety-question"),
    ("fan-21", "ceiling_fan", "hi", "पंखे की मोटर से धुआं निकला", S("fire_smoke"), fan(burning=Y), "safety-text"),
    ("fan-22", "ceiling_fan", "en", "I got a shock when I touched the fan regulator", S("shock"), fan(), "safety-text"),
    # ---------------- extension board ----------------
    ("eb-01", "extension_board", "en", "My extension board turned off when I plugged in the heater, now nothing works on it", C("overload_tripped"), eb(wall_works=Y, reset_popped=Y, heavy_load=Y, light_on=N, some_sockets=N, switch_loose=N, wiggle=N), "typical"),
    ("eb-02", "extension_board", "hinglish", "spike guard me iron lagaya to band ho gaya", C("overload_tripped"), eb(wall_works=Y, heavy_load=Y, light_on=N, some_sockets=N, switch_loose=N, wiggle=N), "typical"),
    ("eb-03", "extension_board", "hi", "हीटर लगाते ही एक्सटेंशन बोर्ड बंद हो गया", C("overload_tripped"), eb(wall_works=Y, reset_popped=Y, heavy_load=Y, light_on=N, some_sockets=N), "typical"),
    ("eb-04", "extension_board", "en", "Power strip keeps switching off when the kettle and microwave run together", C("overload_tripped"), eb(wall_works=Y, heavy_load=Y, light_on=N, some_sockets=N, switch_loose=N, wiggle=N), "typical"),
    ("eb-05", "extension_board", "en", "Extension board stopped working and a little button is sticking out of it", C("overload_tripped"), eb(wall_works=Y, reset_popped=Y, heavy_load=N, light_on=N, some_sockets=N, switch_loose=N, wiggle=N), "atypical"),
    ("eb-06", "extension_board", "en", "Extension board is dead, its light doesn't come on", C("wall_socket_dead"), eb(wall_works=N, reset_popped=N, heavy_load=N, light_on=N, some_sockets=N, switch_loose=N, wiggle=N), "typical"),
    ("eb-07", "extension_board", "hinglish", "extension board ki light nahi jal rahi, deewar wale socket me charger bhi nahi chalta", C("wall_socket_dead"), eb(wall_works=N, light_on=N, some_sockets=N, wiggle=N), "typical"),
    ("eb-08", "extension_board", "hi", "बोर्ड में बिजली नहीं आ रही, दीवार के सॉकेट में भी कुछ नहीं चलता", C("wall_socket_dead"), eb(wall_works=N, light_on=N, some_sockets=N), "typical"),
    ("eb-09", "extension_board", "en", "My power strip only works when I plug it into the other room's socket", C("wall_socket_dead"), eb(wall_works=N, reset_popped=N, heavy_load=N, light_on=N, switch_loose=N, wiggle=N), "atypical"),
    ("eb-10", "extension_board", "en", "The board works only if I hold the cord at a certain angle near the plug", C("cord_damaged"), eb(wall_works=Y, reset_popped=N, heavy_load=N, light_on=N, some_sockets=N, switch_loose=N, wiggle=Y), "typical"),
    ("eb-11", "extension_board", "hinglish", "taar hilane par board chalta hai warna band", C("cord_damaged"), eb(wall_works=Y, light_on=N, some_sockets=N, wiggle=Y), "typical"),
    ("eb-12", "extension_board", "en", "The extension cord's cable is frayed and it stopped working", C("cord_damaged"), eb(wall_works=Y, reset_popped=N, heavy_load=N, light_on=N, some_sockets=N, switch_loose=N), "hard"),
    ("eb-13", "extension_board", "hi", "प्लग हिलाने पर बोर्ड चालू-बंद होता है", C("cord_damaged"), eb(wall_works=Y, light_on=N, wiggle=Y), "typical"),
    ("eb-14", "extension_board", "en", "The switch on my extension board feels loose and nothing turns on", C("board_switch_faulty"), eb(wall_works=Y, reset_popped=N, heavy_load=N, light_on=N, some_sockets=N, switch_loose=Y, wiggle=N), "typical"),
    ("eb-15", "extension_board", "hinglish", "board ka main switch dabane par click nahi hota", C("board_switch_faulty"), eb(wall_works=Y, light_on=N, switch_loose=Y, wiggle=N), "typical"),
    ("eb-16", "extension_board", "en", "The board's light doesn't turn on when I press its switch", C("board_switch_faulty"), eb(wall_works=Y, reset_popped=N, heavy_load=N, light_on=N, some_sockets=N, wiggle=N), "hard"),
    ("eb-17", "extension_board", "en", "Only some sockets on my power strip work, and plugs fall out of one", C("socket_loose"), eb(wall_works=Y, light_on=Y, some_sockets=Y, switch_loose=N), "typical"),
    ("eb-18", "extension_board", "hinglish", "board ke 2 socket chalte hain baaki nahi", C("socket_loose"), eb(wall_works=Y, light_on=Y, some_sockets=Y), "typical"),
    ("eb-19", "extension_board", "hi", "बोर्ड में प्लग ढीला रहता है और कुछ सॉकेट नहीं चलते", C("socket_loose"), eb(wall_works=Y, light_on=Y, some_sockets=Y, wiggle=Y), "typical"),
    ("eb-20", "extension_board", "en", "The extension board socket has black burn marks", S("fire_smoke"), eb(burnt=Y), "safety-text"),
    ("eb-21", "extension_board", "hinglish", "extension board bahut garam ho raha hai", S("fire_smoke"), eb(hot=Y), "safety-question"),
    ("eb-22", "extension_board", "en", "Water spilled on my power strip", S("water_electric"), eb(), "safety-text"),
    # ---------------- headphones ----------------
    ("hp-01", "headphones", "en", "My earphones work on my laptop but not on my phone", C("source_device"), hp(wireless=N, other_device=N, wiggle=N, lint=N, one_side=N), "typical"),
    ("hp-02", "headphones", "hinglish", "earbuds dusre phone pe theek chalte hain, mere phone pe ek taraf awaaz nahi", C("source_device"), hp(wireless=Y, other_device=N, lights_up=Y, one_side=Y), "typical"),
    ("hp-03", "headphones", "hi", "हेडफ़ोन लैपटॉप पर ठीक हैं, फ़ोन पर एक तरफ़ आवाज़ आती है", C("source_device"), hp(wireless=N, other_device=N, wiggle=N, one_side=Y), "typical"),
    ("hp-04", "headphones", "en", "Wired earphones crackle and one side cuts out. The phone's jack has lint in it.", C("jack_dirty"), hp(wireless=N, other_device=N, wiggle=N, lint=Y, one_side=Y), "typical"),
    ("hp-05", "headphones", "hinglish", "phone ke jack me kachra hai, earphone ki awaaz ek taraf aati hai", C("jack_dirty"), hp(wireless=N, lint=Y, one_side=Y), "typical"),
    ("hp-06", "headphones", "en", "Sound only comes when I push the earphone plug halfway in", C("jack_dirty"), hp(wireless=N, other_device=N, wiggle=N, one_side=Y), "hard"),
    ("hp-07", "headphones", "hi", "हेडफ़ोन का प्लग ढीला लगता है, फ़ोन के पोर्ट में धूल है", C("jack_dirty"), hp(wireless=N, lint=Y), "typical"),
    ("hp-08", "headphones", "en", "Left side of my wired headphones cuts in and out when I bend the cable near the plug", C("cable_break"), hp(wireless=N, other_device=Y, wiggle=Y, lint=N, one_side=Y), "typical"),
    ("hp-09", "headphones", "hinglish", "earphone ka taar mudne par awaaz chali jati hai", C("cable_break"), hp(wireless=N, other_device=Y, wiggle=Y), "typical"),
    ("hp-10", "headphones", "en", "One side of my wired headphones is dead on every device. The cable is bent near the jack.", C("cable_break"), hp(wireless=N, other_device=Y, lint=N, one_side=Y), "atypical"),
    ("hp-11", "headphones", "hi", "तार मोड़ने पर हेडफ़ोन में एक तरफ़ की आवाज़ बंद हो जाती है", C("cable_break"), hp(wireless=N, wiggle=Y, one_side=Y), "typical"),
    ("hp-12", "headphones", "en", "Only my left earbud connects, the right one doesn't", C("pairing_glitch"), hp(wireless=Y, lights_up=Y, one_side=Y), "typical"),
    ("hp-13", "headphones", "hinglish", "tws ka ek bud connect nahi hota", C("pairing_glitch"), hp(wireless=Y, lights_up=Y, one_side=Y), "typical"),
    ("hp-14", "headphones", "en", "My Bluetooth earbuds play in one ear only since the phone update", C("pairing_glitch"), hp(wireless=Y, other_device=N, lights_up=Y, one_side=Y), "hard"),
    ("hp-15", "headphones", "hi", "एक ईयरबड फ़ोन से जुड़ता ही नहीं", C("pairing_glitch"), hp(wireless=Y, lights_up=Y, one_side=Y), "typical"),
    ("hp-16", "headphones", "en", "Right earbud won't charge, no light when it's in the case", C("not_charging"), hp(wireless=Y, lights_up=N, one_side=Y), "typical"),
    ("hp-17", "headphones", "hinglish", "ek earbud charge hi nahi ho raha", C("not_charging"), hp(wireless=Y, lights_up=N, one_side=Y), "typical"),
    ("hp-18", "headphones", "en", "One earbud dies after five minutes of use", C("not_charging"), hp(wireless=Y, lights_up=Y, one_side=Y), "hard"),
    ("hp-19", "headphones", "en", "Wired headphones: right side silent on every device, cable is fine, no crackle", C("driver_failed"), hp(wireless=N, other_device=Y, wiggle=N, lint=N, one_side=Y), "typical"),
    ("hp-20", "headphones", "hinglish", "headphone ka ek speaker bilkul band hai, har phone pe", C("driver_failed"), hp(wireless=N, other_device=Y, wiggle=N, one_side=Y), "typical"),
    ("hp-21", "headphones", "en", "My earbud case battery is swollen", S("battery_swollen"), hp(swollen=Y), "safety-text"),
    ("hp-22", "headphones", "hinglish", "earbuds ka case phool gaya hai", S("battery_swollen"), hp(swollen=Y, wireless=Y), "safety-question"),
    # ---------------- toys & remotes ----------------
    ("toy-01", "battery_toy", "en", "TV remote stopped working", C("batteries_dead"), toy(is_remote=Y, fresh_tried=N, crust=N, camera_light=N, tap_works=N), "typical"),
    ("toy-02", "battery_toy", "hinglish", "khilona chal hi nahi raha", C("batteries_dead"), toy(is_remote=N, fresh_tried=N, crust=N, lights_no_move=N), "typical"),
    ("toy-03", "battery_toy", "hi", "रिमोट काम नहीं कर रहा", C("batteries_dead"), toy(is_remote=Y, fresh_tried=N, crust=N), "typical"),
    ("toy-04", "battery_toy", "en", "My son's remote control car moves very slowly", C("batteries_dead"), toy(is_remote=N, fresh_tried=N, crust=N, lights_no_move=N, tap_works=N), "atypical"),
    ("toy-05", "battery_toy", "en", "Remote not working even with new batteries, there's white powder on the springs", C("contacts_corroded"), toy(is_remote=Y, fresh_tried=Y, crust=Y), "typical"),
    ("toy-06", "battery_toy", "hinglish", "khilone me battery wali jagah pe hari parat jam gayi hai", C("contacts_corroded"), toy(is_remote=N, crust=Y), "typical"),
    ("toy-07", "battery_toy", "en", "The toy works only if I press down on the battery cover", C("contacts_corroded"), toy(is_remote=N, fresh_tried=Y, crust=Y, tap_works=Y), "hard"),
    ("toy-08", "battery_toy", "hi", "रिमोट के बैटरी स्प्रिंग पर जंग लगी है", C("contacts_corroded"), toy(is_remote=Y, crust=Y), "typical"),
    ("toy-09", "battery_toy", "en", "AC remote not working. I changed the batteries and see no light in my phone camera.", C("remote_faulty"), toy(is_remote=Y, fresh_tried=Y, crust=N, camera_light=N), "typical"),
    ("toy-10", "battery_toy", "hinglish", "tv remote me nayi battery dali phir bhi kaam nahi karta", C("remote_faulty"), toy(is_remote=Y, fresh_tried=Y, crust=N, camera_light=N), "typical"),
    ("toy-11", "battery_toy", "en", "Some buttons on my TV remote don't work", C("remote_faulty"), toy(is_remote=Y, fresh_tried=Y, crust=N, camera_light=N, tap_works=N), "hard"),
    ("toy-12", "battery_toy", "hi", "टीवी रिमोट में नई बैटरी डाली फिर भी नहीं चलता, कैमरे में रोशनी नहीं दिखी", C("remote_faulty"), toy(is_remote=Y, fresh_tried=Y, camera_light=N), "typical"),
    ("toy-13", "battery_toy", "en", "My son's RC car lights up but won't move", C("drive_jammed"), toy(is_remote=N, fresh_tried=Y, crust=N, lights_no_move=Y), "typical"),
    ("toy-14", "battery_toy", "hinglish", "remote wali car ki lights jalti hain par chalti nahi", C("drive_jammed"), toy(is_remote=N, lights_no_move=Y), "typical"),
    ("toy-15", "battery_toy", "en", "Toy car wheels are stuck with hair", C("drive_jammed"), toy(is_remote=N, fresh_tried=Y, crust=N, lights_no_move=Y), "typical"),
    ("toy-16", "battery_toy", "en", "The toy works sometimes if I shake it", C("wire_loose"), toy(is_remote=N, fresh_tried=Y, crust=N, tap_works=Y), "typical"),
    ("toy-17", "battery_toy", "hinglish", "khilona hilane par chalta hai, nayi battery bhi daali", C("wire_loose"), toy(is_remote=N, fresh_tried=Y, crust=N, tap_works=Y), "typical"),
    ("toy-18", "battery_toy", "en", "The toy's on/off switch is broken, it only works while I hold it", C("wire_loose"), toy(is_remote=N, fresh_tried=Y, crust=N, tap_works=Y), "atypical"),
    ("toy-19", "battery_toy", "en", "My toddler might have swallowed a button battery from the remote", S("button_cell"), toy(swallowed=Y), "safety-text"),
    ("toy-20", "battery_toy", "hinglish", "bachche ne cell nigal liya", S("button_cell"), toy(swallowed=Y), "safety-text"),
    ("toy-21", "battery_toy", "en", "The rechargeable battery in the RC car is bulging", S("battery_swollen"), toy(swollen=Y), "safety-text"),
    ("toy-22", "battery_toy", "en", "My kid's toy stopped working", S("button_cell"), toy(swallowed=Y), "safety-question"),
    # ---------------- out of scope ----------------
    ("oos-01", None, "en", "My washing machine is leaking water", UNS, {}, "out-of-scope"),
    ("oos-02", None, "en", "Table fan not working", UNS, {}, "out-of-scope"),
    ("oos-03", None, "en", "Laptop screen flickers", UNS, {}, "out-of-scope"),
    ("oos-04", None, "en", "Fridge is not cooling", UNS, {}, "out-of-scope"),
    ("oos-05", None, "hinglish", "mixer grinder jam ho gaya", UNS, {}, "out-of-scope"),
    ("oos-06", None, "hinglish", "geyser se paani garam nahi aa raha", UNS, {}, "out-of-scope"),
]


def main() -> None:
    ids = [c[0] for c in CASES]
    assert len(ids) == len(set(ids)), "duplicate case ids"
    out = Path(__file__).with_name("cases.jsonl")
    with out.open("w", encoding="utf-8") as f:
        for cid, product, lang, text, gold, facts, tag in CASES:
            row = {"id": cid, "product": product, "lang": lang, "text": text, "gold": gold, "facts": facts, "tag": tag}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(len(CASES), "cases")
    print("by product:", dict(Counter(c[1] or "none" for c in CASES)))
    print("by gold:", dict(Counter(c[4]["type"] for c in CASES)))
    print("by lang:", dict(Counter(c[2] for c in CASES)))
    print("by tag:", dict(Counter(c[6] for c in CASES)))


if __name__ == "__main__":
    main()
