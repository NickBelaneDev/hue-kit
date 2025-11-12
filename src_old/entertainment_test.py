
import time
from hue_entertainment_pykit import create_bridge, Entertainment, Streaming

# 1) Bridge-Objekt bauen – trage deine echten Werte ein:
bridge = create_bridge(
    identification="YOUR-BRIDGE-ID",    # z.B. aus Discovery/REST
    rid="YOUR-ENT-CONFIG-RID",          # Entertainment-Config RID
    ip_address="192.168.1.100",
    swversion=1962097030,               # optional; aus Bridge-Info
    username="YOUR_USERNAME_APPKEY",    # PSK-IDENTITY
    hue_app_id="YOUR-APP-ID",           # frei wählbar/aus App-Flow
    clientkey="YOUR_CLIENTKEY"          # PSK (vom generateclientkey)
)

# 2) Entertainment-Service & -Konfiguration holen
ent = Entertainment(bridge)
ent_configs = ent.get_entertainment_configs()
ent_conf = next(iter(ent_configs.values()))  # nimm die erste Area

# 3) Streaming-Laufwerk starten
stream = Streaming(bridge, ent_conf, ent.get_ent_conf_repo())
stream.start_stream()
stream.set_color_space("xyb")  # x, y, brightness(0..1)

try:
    light_indices = [0]  # ggf. mehrere: [0,1,2]
    on_xy  = (0.17, 0.70)  # grün
    off_xy = on_xy         # xy bleibt, nur bri 0

    for i in range(20):
        # AN
        for li in light_indices:
            stream.set_input((on_xy[0], on_xy[1], 1.0, li))
        time.sleep(0.10)

        # AUS
        for li in light_indices:
            stream.set_input((off_xy[0], off_xy[1], 0.0, li))
        time.sleep(0.10)

finally:
    stream.stop_stream()
