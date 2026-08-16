"""Uygulama loglama kurulumu.

Python'un logging modulunde iki kavrami ayirmak onemli:

  * **Logger hiyerarsisi:** Logger adlari nokta ile hiyerarsi kurar.
    `app.agent.graph` -> `app.agent` -> `app` -> root (kok). Bir logger'a
    yazilan kayit, `propagate=True` oldugu surece yukari dogru tum atalara
    tasinir ve ORADAKI handler'lar tarafindan basilir.
  * **Logger seviyesi vs handler seviyesi:** Kaydin uretilip uretilmeyecegine
    KAYDIN YAZILDIGI logger'in seviyesi karar verir. Ust logger'in seviyesi
    (ornegin root'un WARNING olmasi) alt logger'dan gelen kaydi ELEMEZ.

Bu ikisini birlestirerek su dengeyi kuruyoruz:

  * root seviyesi WARNING  -> httpx, urllib3, langchain gibi ucuncu parti
    kutuphaneler sadece uyari/hata basar (terminal cop olmaz).
  * `app` logger'i LOG_LEVEL -> bizim kodumuzun tum INFO/DEBUG loglari gecer,
    root'un handler'i tarafindan ekrana basilir.

Boylece `LOG_LEVEL=DEBUG` yapinca yalnizca KENDI loglarimiz ayrintilanir.
"""

from __future__ import annotations

import logging
import sys

from app.core.config import get_settings

# Tum uygulama modulleri `app.` ile basladigi icin (app.agent.graph,
# app.agent.service, ...) tek bir ata logger hepsini kapsar.
APP_LOGGER_NAME = "app"

_FORMAT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%H:%M:%S"


def setup_logging(level: str | None = None) -> None:
    """Kok logger'a bir handler baglar ve `app` logger'inin seviyesini ayarlar.

    `basicConfig` root'ta zaten handler varsa hicbir sey yapmaz; bu yuzden
    fonksiyonu birden fazla kez cagirmak guvenlidir (uvicorn --reload).
    """
    settings = get_settings()
    resolved = (level or settings.log_level).upper()

    logging.basicConfig(
        level=logging.WARNING,  # ucuncu parti kutuphaneler icin taban seviye
        format=_FORMAT,
        datefmt=_DATEFMT,
        stream=sys.stdout,
    )
    logging.getLogger(APP_LOGGER_NAME).setLevel(resolved)
