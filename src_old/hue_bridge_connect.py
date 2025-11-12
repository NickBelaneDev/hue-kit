import os
import requests
import urllib3

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())
HUE_BRIDGE_IP = os.getenv('HUE_BRIDGE_IP')

# Warnungen wegen verify=False ausblenden (lokales Netz, self-signed Zertifikat der Bridge)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def pair_bridge(bridge_ip: str, devicetype: str = "python_hue#mein_pc"):
    """Sendet den Pairing-Request an die Bridge. Vorher Link-Taste drücken!"""
    url = f"https://{bridge_ip}/api"
    payload = {"devicetype": devicetype}
    # Hinweis: verify=False, weil die Bridge ein selbstsigniertes Zertifikat nutzt (im LAN ok).
    r = requests.post(url, json=payload, timeout=5, verify=False)
    return r.json()

if __name__ == "__main__":
    print("Suche Hue Bridge ...")
    ip = HUE_BRIDGE_IP
    print(ip)
    input("STOP PLS\n")
    if not ip:
        print("Keine Bridge über discovery.meethue.com gefunden.")
        print("Tipp: Öffne die Hue-App → Einstellungen → Bridge → Netzwerk und nimm die IP manuell.")
    else:
        print(f"Bridge gefunden: {ip}")
        print("Drücke JETZT die Link-Taste auf der Bridge (LED blinkt) und warte 2–3 Sekunden...")
        input("Dann Enter drücken, um den Key anzufordern → ")

        resp = pair_bridge(ip)
        print("Antwort der Bridge:", resp)

        # Erwartetes success-Objekt: [{'success': {'username': 'DEIN_APP_KEY'}}]
        try:
            app_key = resp[0]["success"]["username"]
            print("\n✅ APP_KEY erhalten!")
            print("APP_KEY =", app_key)
            print("\nMerke dir den Key. Als Nächstes können wir sofort mit der v2-API Lichter auslesen.")
        except Exception:
            print("\n❌ Kein Key erhalten. Meist wurde die Link-Taste nicht rechtzeitig gedrückt.")
            print("Drück die Taste und starte das Skript einfach nochmal.")
