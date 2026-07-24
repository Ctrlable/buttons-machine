from __future__ import annotations
_A='caseta'
from homeassistant.config_entries import ConfigEntry
from.base import KeypadBackend
from.caseta import CasetaBackend
from.control4 import Control4Backend
from.lip import LipBackend
from.rfwc5 import RFWC5Backend
from.z2m import RodretBackend,Z2MBackend
from.zen35 import ZEN35Backend
_BACKENDS={_A:CasetaBackend,'control4':Control4Backend,'lip':LipBackend,'rfwc5':RFWC5Backend,'rodret':RodretBackend,'z2m':RodretBackend,'zen35':ZEN35Backend}
def get_backend(config_entry):
	A=config_entry;B=_A
	if A is not None:B=A.data.get('backend')or _A
	return _BACKENDS.get(B,CasetaBackend)()
__all__=['KeypadBackend','CasetaBackend','Control4Backend','LipBackend','RFWC5Backend','RodretBackend','Z2MBackend','ZEN35Backend','get_backend']