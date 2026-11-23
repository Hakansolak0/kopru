#!/usr/bin/env python3
"""
RustDesk kaynak kodunu Kopru markasina ve kendi sunucuna gore duzenler.

Depo kokunde (alt modulleriyle birlikte) calistirilir:

    python marka/marka-uygula.py --ad Kopru --gorunen-ad "Köprü" \
        --depo https://github.com/KULLANICI/kopru \
        [--sunucu uzak.alanadin.com --anahtar "ABC...="]

Yaptiklari:
  * Program adi (APP_NAME), sunucu adresi ve anahtari (verilirse) koda isler.
  * Arayuzde gorunen RustDesk adini, rustdesk.com baglantilarini, "Powered by"
    yazisini ve dosya ozelliklerindeki (sirket/urun adi) bilgileri degistirir.
  * marka/ikonlar/ altindaki logolari depodaki yerlerine kopyalar.

Bulamadigi bir kalip olursa HATA verip durur; boylece RustDesk kodu degistiginde
sessizce eksik markalanmis bir program uretilmez.
"""
import argparse
import pathlib
import re
import shutil
import sys

KOK = pathlib.Path.cwd()
BETIK_DIZINI = pathlib.Path(__file__).resolve().parent

# marka/ikonlar/<dosya>  ->  depodaki hedef yol(lar)
IKONLAR = {
    "icon.ico": ["res/icon.ico", "flutter/windows/runner/resources/app_icon.ico", "flutter/assets/icon.ico"],
    "icon.png": ["res/icon.png", "res/mac-icon.png", "flutter/assets/icon.png"],
    "tray-icon.ico": ["res/tray-icon.ico"],
    "logo.svg": ["flutter/assets/icon.svg", "res/logo.svg", "res/scalable.svg"],
    "32x32.png": ["res/32x32.png"],
    "64x64.png": ["res/64x64.png"],
    "128x128.png": ["res/128x128.png"],
    "256x256.png": ["res/128x128@2x.png"],
    # Ana penceredeki baslik logosu (acik / koyu tema)
    "logo_light.png": ["flutter/assets/logo_light.png"],
    "logo_dark.png": ["flutter/assets/logo_dark.png"],
}


def degistir(yol: str, kalip: str, yeni, aciklama: str, regex: bool = False) -> None:
    """Dosyada kalibi degistirir; en az bir eslesme yoksa derlemeyi durdurur.
    regex=True iken `yeni` bir metin ya da eslesmeyi alan bir fonksiyon olabilir."""
    dosya = KOK / yol
    metin = dosya.read_text(encoding="utf-8")
    if regex:
        degistirici = yeni if callable(yeni) else (lambda _m: yeni)
        yeni_metin, adet = re.subn(kalip, degistirici, metin, flags=re.MULTILINE)
    else:
        adet = metin.count(kalip)
        yeni_metin = metin.replace(kalip, yeni)
    if adet == 0:
        sys.exit(f"HATA: {yol} icinde '{aciklama}' bulunamadi. RustDesk surumu degismis olabilir.")
    dosya.write_text(yeni_metin, encoding="utf-8")
    print(f"  [tamam] {aciklama} ({adet})")


def rc_metni(s: str) -> str:
    """Windows kaynak (.rc) dosyasi icin ASCII'ye cevirir (o, u vb.)."""
    tablo = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    return s.translate(tablo)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ad", required=True, help="Teknik ad: exe, servis, klasor adi. Ornek: Kopru")
    p.add_argument("--gorunen-ad", default="", help="Arayuzde gorunen ad, Turkce harf olabilir. Ornek: Köprü")
    p.add_argument("--depo", required=True, help="Programin kaynak kodu / indirme sayfasi, ornek: https://github.com/kullanici/kopru")
    p.add_argument("--sunucu", default="", help="ID/relay sunucusu (bos = gomulu sunucu yok)")
    p.add_argument("--anahtar", default="", help="Sunucudaki id_ed25519.pub icerigi (--sunucu ile birlikte)")
    a = p.parse_args()
    a.sunucu, a.anahtar = a.sunucu.strip(), a.anahtar.strip()
    gorunen = (a.gorunen_ad or a.ad).strip()
    depo = a.depo.rstrip("/")

    if not re.fullmatch(r"[A-Za-z0-9_-]{2,32}", a.ad):
        sys.exit("HATA: --ad sadece harf, rakam, - ve _ icermeli (2-32 karakter).")
    if '"' in gorunen or "\\" in gorunen or "'" in gorunen or "$" in gorunen:
        sys.exit("HATA: --gorunen-ad tirnak, ters bolu veya $ iceremez.")
    if not re.fullmatch(r"https://[A-Za-z0-9./_-]+", depo):
        sys.exit("HATA: --depo https:// ile baslayan bir adres olmali.")
    if bool(a.sunucu) != bool(a.anahtar):
        sys.exit("HATA: --sunucu ve --anahtar birlikte verilmeli (ya ikisi de dolu ya ikisi de bos).")
    if a.anahtar and not re.fullmatch(r"[A-Za-z0-9+/=]{40,60}", a.anahtar):
        sys.exit("HATA: --anahtar gecerli bir base64 anahtar gibi gorunmuyor.")
    if a.sunucu and not re.fullmatch(r"[A-Za-z0-9.-]+(:\d+)?", a.sunucu):
        sys.exit("HATA: --sunucu sadece alan adi veya IP (istege bagli :port) olmali.")

    config_rs = "libs/hbb_common/src/config.rs"
    if not (KOK / config_rs).exists():
        sys.exit(f"HATA: {config_rs} yok. Depo kokunde misin? Alt moduller indirildi mi?")

    print(f"Marka: {a.ad} / {gorunen} / {a.sunucu or 'gomulu sunucu yok'}")

    # --- Cekirdek: ad, sunucu, anahtar -------------------------------------
    degistir(config_rs,
             r'(pub static ref APP_NAME: RwLock<String> = RwLock::new\()"RustDesk"(\.to_owned\(\)\);)',
             f'pub static ref APP_NAME: RwLock<String> = RwLock::new("{a.ad}".to_owned());',
             "APP_NAME", regex=True)
    if a.sunucu:
        degistir(config_rs, r'pub const RENDEZVOUS_SERVERS: &\[&str\] = &\[[^\]]*\];',
                 f'pub const RENDEZVOUS_SERVERS: &[&str] = &["{a.sunucu}"];', "RENDEZVOUS_SERVERS", regex=True)
        degistir(config_rs, r'pub const RS_PUB_KEY: &str = "[^"]*";',
                 f'pub const RS_PUB_KEY: &str = "{a.anahtar}";', "RS_PUB_KEY", regex=True)

    # --- Ceviriler: "RustDesk" gecen her metinde gorunen ad kullanilsin ------
    degistir("src/lang.rs", "let app_name = crate::get_app_name();",
             f'let app_name = "{gorunen}".to_owned();', "ceviri metinlerinde gorunen ad")

    # --- Flutter arayuzu -----------------------------------------------------
    degistir("flutter/lib/common.dart",
             "if (bind.mainGetBuildinOption(key: \"hide-powered-by-me\") == 'Y') {",
             "if (true) {", "'Powered by' yazisini gizle")
    degistir("flutter/lib/common.dart",
             "launchUrl(Uri.parse('https://rustdesk.com'));",
             f"launchUrl(Uri.parse('{depo}'));", "powered-by baglantisi")
    degistir("flutter/lib/common.dart",
             "String getWindowName({WindowType? overrideType}) {\n  final name = bind.mainGetAppNameSync();",
             f'String getWindowName({{WindowType? overrideType}}) {{\n  final name = "{gorunen}";',
             "pencere basliklari")
    degistir("flutter/lib/desktop/widgets/tabbar_widget.dart",
             r'"RustDesk",(\s*style: TextStyle\(fontSize: 13\))',
             lambda m: f'"{gorunen}",' + m.group(1), "sekme cubugu basligi", regex=True)

    ayar = "flutter/lib/desktop/pages/desktop_setting_page.dart"
    degistir(ayar,
             r"\s*InkWell\(\s*onTap: \(\) \{\s*launchUrlString\('https://rustdesk\.com/privacy\.html'\);\s*\},"
             r"\s*child: Text\(\s*translate\('Privacy Statement'\),\s*style: linkStyle,\s*\)\.marginSymmetric\(vertical: 4\.0\)\),",
             "", "Hakkinda: gizlilik baglantisi kaldirildi", regex=True)
    degistir(ayar, "launchUrlString('https://rustdesk.com');",
             f"launchUrlString('{depo}');", "Hakkinda: web sitesi baglantisi")
    degistir(ayar,
             "'Copyright © ${DateTime.now().toString().substring(0, 4)} Purslane Tech Pte. Ltd.\\n$license'",
             f"'{gorunen} — AGPL-3.0 lisansli acik kaynak yazilim. Hicbir garanti verilmez.\\n"
             f"© Purslane Tech Pte. Ltd. ve katkida bulunanlar\\nKaynak kodu: {depo}\\n$license'",
             "Hakkinda: lisans metni")

    degistir("flutter/lib/desktop/pages/install_page.dart", "https://rustdesk.com/privacy.html",
             f"{depo}/blob/main/LICENCE", "kurulum ekrani: lisans baglantisi")
    degistir("flutter/lib/desktop/pages/connection_page.dart", "https://rustdesk.com/pricing",
             depo, "genel sunucu uyari baglantisi")
    degistir("flutter/lib/desktop/pages/desktop_home_page.dart", "https://rustdesk.com/download",
             f"{depo}/releases/latest", "indirme baglantisi")

    # --- Windows dosya ozellikleri (Ozellikler > Ayrintilar) ---------------
    rc_ad = rc_metni(gorunen)
    rc = "flutter/windows/runner/Runner.rc"
    degistir(rc, '"Purslane Tech Pte. Ltd."', f'"{rc_ad}"', "Runner.rc CompanyName")
    degistir(rc, '"RustDesk Remote Desktop"', f'"{rc_ad} Uzak Masaustu"', "Runner.rc FileDescription")
    degistir(rc, '"Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved."',
             f'"{rc_ad} - AGPL-3.0"', "Runner.rc LegalCopyright", )
    degistir(rc, 'VALUE "InternalName", "rustdesk"', f'VALUE "InternalName", "{a.ad.lower()}"', "Runner.rc InternalName")
    degistir(rc, '"rustdesk.exe"', f'"{a.ad}.exe"', "Runner.rc OriginalFilename")
    degistir(rc, 'VALUE "ProductName", "RustDesk"', f'VALUE "ProductName", "{rc_ad}"', "Runner.rc ProductName")
    for toml in ("Cargo.toml", "libs/portable/Cargo.toml"):
        degistir(toml, 'description = "RustDesk Remote Desktop"', f'description = "{rc_ad} Uzak Masaustu"', f"{toml} description")
        degistir(toml, 'LegalCopyright = "Copyright © 2026 Purslane Tech Pte. Ltd. All rights reserved."',
                 f'LegalCopyright = "{rc_ad} - AGPL-3.0"', f"{toml} LegalCopyright")
        degistir(toml, 'ProductName = "RustDesk"', f'ProductName = "{rc_ad}"', f"{toml} ProductName")
        degistir(toml, 'FileDescription = "RustDesk Remote Desktop"', f'FileDescription = "{rc_ad} Uzak Masaustu"', f"{toml} FileDescription")
        degistir(toml, 'OriginalFilename = "rustdesk.exe"', f'OriginalFilename = "{a.ad}.exe"', f"{toml} OriginalFilename")

    # --- Gorev Yoneticisi'nde gorunen yardimci surec adi --------------------
    for rs in ("src/privacy_mode/win_topmost_window.rs", "libs/portable/src/main.rs"):
        degistir(rs, "RuntimeBroker_rustdesk.exe", f"RuntimeBroker_{a.ad.lower()}.exe", f"{rs} yardimci surec adi")

    # --- Logolar --------------------------------------------------------------
    ikon_dizini = BETIK_DIZINI / "ikonlar"
    if ikon_dizini.is_dir():
        for ad, hedefler in IKONLAR.items():
            kaynak = ikon_dizini / ad
            if not kaynak.exists():
                continue
            for h in hedefler:
                hedef = KOK / h
                if hedef.parent.is_dir():
                    shutil.copyfile(kaynak, hedef)
                    print(f"  [ikon]  {ad} -> {h}")
                else:
                    print(f"  [atla]  {h.rsplit('/', 1)[0]} klasoru depoda yok")
    print("Bitti.")


if __name__ == "__main__":
    main()
