'Solar Sync circadian engine — the target color-temp + brightness computation.\n\nLifted verbatim from the solar_sync component (an adaptive-lighting fork); it is\nself-contained + HA-agnostic (only homeassistant.util.color + astral). buttons_machine\nre-hosts it so the Solar Sync tab can compute per-fixture targets without a second\ncomponent. Do not add domain glue here — keep it pure math.\n'
from __future__ import annotations
_G='Unsupported sun event'
_F='linear'
_E='default'
_D='rgb_color'
_C=True
_B=False
_A=None
import bisect,colorsys,datetime,logging,math
from dataclasses import dataclass
from datetime import UTC,timedelta
from enum import Enum
from functools import cached_property,partial
from typing import TYPE_CHECKING,Any,Literal,cast
from homeassistant.util.color import color_RGB_to_xy,color_temperature_to_rgb,color_xy_to_hs
if TYPE_CHECKING:import astral.location
class SunEvent(str,Enum):'A set of sun events that happen during a day.';SUNRISE='sunrise';SUNSET='sunset';NOON='solar_noon';MIDNIGHT='solar_midnight'
_ORDER=SunEvent.SUNRISE,SunEvent.NOON,SunEvent.SUNSET,SunEvent.MIDNIGHT
_ALLOWED_ORDERS={_ORDER[A:]+_ORDER[:A]for A in range(len(_ORDER))}
utcnow=partial(datetime.datetime.now,UTC)
utcnow.__doc__='Get now in UTC time.'
_LOGGER=logging.getLogger(__name__)
@dataclass(frozen=_C)
class SunEvents:
	'Track the state of the sun and associated light settings.';name:str;astral_location:astral.location.Location;sunrise_time:datetime.time|_A;min_sunrise_time:datetime.time|_A;max_sunrise_time:datetime.time|_A;sunset_time:datetime.time|_A;min_sunset_time:datetime.time|_A;max_sunset_time:datetime.time|_A;sunrise_offset:datetime.timedelta=datetime.timedelta();sunset_offset:datetime.timedelta=datetime.timedelta();timezone:datetime.tzinfo=UTC
	def sunrise(A,dt):
		'Return the (adjusted) sunrise time for the given datetime.';B=(A.astral_location.sunrise(dt,local=_B)if A.sunrise_time is _A else A._replace_time(dt,A.sunrise_time))+A.sunrise_offset
		if A.min_sunrise_time is not _A:C=A._replace_time(dt,A.min_sunrise_time);B=max(C,B)
		if A.max_sunrise_time is not _A:D=A._replace_time(dt,A.max_sunrise_time);B=min(D,B)
		return B
	def sunset(A,dt):
		'Return the (adjusted) sunset time for the given datetime.';B=(A.astral_location.sunset(dt,local=_B)if A.sunset_time is _A else A._replace_time(dt,A.sunset_time))+A.sunset_offset
		if A.min_sunset_time is not _A:C=A._replace_time(dt,A.min_sunset_time);B=max(C,B)
		if A.max_sunset_time is not _A:D=A._replace_time(dt,A.max_sunset_time);B=min(D,B)
		return B
	def _replace_time(A,dt,time):B=datetime.datetime.combine(dt,time);C=B.replace(tzinfo=A.timezone);return C.astimezone(UTC)
	def noon_and_midnight(A,dt,sunset=_A,sunrise=_A):
		'Return the (adjusted) noon and midnight times for the given datetime.';C=sunrise;B=sunset
		if A.sunrise_time is _A and A.sunset_time is _A and A.min_sunrise_time is _A and A.max_sunrise_time is _A and A.min_sunset_time is _A and A.max_sunset_time is _A:G=A.astral_location.noon(dt,local=_B);H=A.astral_location.midnight(dt,local=_B);return G,H
		if B is _A:B=A.sunset(dt)
		if C is _A:C=A.sunrise(dt)
		F=abs(B-C)/2
		if B>C:D=C+F;E=D+timedelta(hours=12)*(1 if D.hour<12 else-1)
		else:E=B+F;D=E+timedelta(hours=12)*(1 if E.hour<12 else-1)
		return D,E
	def sun_events(A,dt):"Get the four sun event's timestamps at 'dt'.";B=A.sunrise(dt);C=A.sunset(dt);E,F=A.noon_and_midnight(dt,C,B);D=[(SunEvent.SUNRISE,B.timestamp()),(SunEvent.SUNSET,C.timestamp()),(SunEvent.NOON,E.timestamp()),(SunEvent.MIDNIGHT,F.timestamp())];A._validate_sun_event_order(D);return D
	def _validate_sun_event_order(D,events):
		'Check if the sun events are in the expected order.';A=events;A=sorted(A,key=lambda x:x[1]);B,E=zip(*A,strict=_C)
		if B not in _ALLOWED_ORDERS:C=f"{D.name}: The sun events {B} are not in the expected order. The Solar Sync integration will not work! This might happen if your sunrise/sunset offset is too large or your manually set sunrise/sunset time is past/before noon/midnight.";_LOGGER.error(C);raise ValueError(C)
	def prev_and_next_events(C,dt):'Get the previous and next sun event.';A=[B for A in[-1,0,1]for B in C.sun_events(dt+timedelta(days=A))];A=sorted(A,key=lambda x:x[1]);B=bisect.bisect([A for(B,A)in A],dt.timestamp());return A[B-1:B+1]
	def sun_position(E,dt):'Calculate the position of the sun, between [-1, 1].';F=dt.timestamp();(I,A),(B,C)=E.prev_and_next_events(dt);D,G=(A,C)if B in(SunEvent.SUNSET,SunEvent.SUNRISE)else(C,A);H=1 if B in(SunEvent.SUNSET,SunEvent.NOON)else-1;return H*(1-((F-D)/(D-G))**2)
	def closest_event(F,dt):
		'Get the closest sunset or sunrise event.';(A,C),(D,E)=F.prev_and_next_events(dt)
		if SunEvent.SUNRISE in(A,D):B=C if A==SunEvent.SUNRISE else E;return SunEvent.SUNRISE,B
		if SunEvent.SUNSET in(A,D):B=C if A==SunEvent.SUNSET else E;return SunEvent.SUNSET,B
		G='No sunrise or sunset event found.';raise ValueError(G)
@dataclass(frozen=_C)
class SunLightSettings:
	'Track the state of the sun and associated light settings.';name:str;astral_location:astral.location.Location;adapt_until_sleep:bool;max_brightness:int;max_color_temp:int;min_brightness:int;min_color_temp:int;sleep_brightness:int;sleep_rgb_or_color_temp:Literal['color_temp',_D];sleep_color_temp:int;sleep_rgb_color:tuple[int,int,int];sunrise_time:datetime.time|_A;min_sunrise_time:datetime.time|_A;max_sunrise_time:datetime.time|_A;sunset_time:datetime.time|_A;min_sunset_time:datetime.time|_A;max_sunset_time:datetime.time|_A;brightness_mode_time_dark:datetime.timedelta;brightness_mode_time_light:datetime.timedelta;brightness_mode:Literal[_E,_F,'tanh']=_E;sunrise_offset:datetime.timedelta=datetime.timedelta();sunset_offset:datetime.timedelta=datetime.timedelta();timezone:datetime.tzinfo=UTC
	@cached_property
	def sun(self):'Return the SunEvents object.';A=self;return SunEvents(name=A.name,astral_location=A.astral_location,sunrise_time=A.sunrise_time,sunrise_offset=A.sunrise_offset,min_sunrise_time=A.min_sunrise_time,max_sunrise_time=A.max_sunrise_time,sunset_time=A.sunset_time,sunset_offset=A.sunset_offset,min_sunset_time=A.min_sunset_time,max_sunset_time=A.max_sunset_time,timezone=A.timezone)
	def _brightness_pct_default(A,dt):
		'Calculate the brightness percentage using the default method.';B=A.sun.sun_position(dt)
		if B>0:return A.max_brightness
		C=A.max_brightness-A.min_brightness;return C*(1+B)+A.min_brightness
	def _brightness_pct_tanh(A,dt):
		B,C=A.sun.closest_event(dt);D=A.brightness_mode_time_dark.total_seconds();E=A.brightness_mode_time_light.total_seconds()
		if B==SunEvent.SUNRISE:F=scaled_tanh(dt.timestamp()-C,x1=-D,x2=+E,y1=.05,y2=.95,y_min=A.min_brightness,y_max=A.max_brightness)
		elif B==SunEvent.SUNSET:F=scaled_tanh(dt.timestamp()-C,x1=-E,x2=+D,y1=.95,y2=.05,y_min=A.min_brightness,y_max=A.max_brightness)
		else:G=_G;raise ValueError(G)
		return clamp(F,A.min_brightness,A.max_brightness)
	def _brightness_pct_linear(A,dt):
		B,C=A.sun.closest_event(dt);D=A.brightness_mode_time_dark.total_seconds();E=A.brightness_mode_time_light.total_seconds()
		if B==SunEvent.SUNRISE:F=lerp(dt.timestamp()-C,x1=-D,x2=+E,y1=A.min_brightness,y2=A.max_brightness)
		elif B==SunEvent.SUNSET:F=lerp(dt.timestamp()-C,x1=-E,x2=+D,y1=A.max_brightness,y2=A.min_brightness)
		else:G=_G;raise ValueError(G)
		return clamp(F,A.min_brightness,A.max_brightness)
	def brightness_pct(A,dt,is_sleep):
		'Calculate the brightness in %.'
		if is_sleep:return A.sleep_brightness
		if A.brightness_mode==_E:return A._brightness_pct_default(dt)
		if A.brightness_mode==_F:return A._brightness_pct_linear(dt)
		if A.brightness_mode=='tanh':return A._brightness_pct_tanh(dt)
	def color_temp_kelvin(A,sun_position):
		'Calculate the color temperature in Kelvin.';B=sun_position
		if B>0:C=A.max_color_temp-A.min_color_temp;D=C*B+A.min_color_temp;return 5*round(D/5)
		if B==0 or not A.adapt_until_sleep:return A.min_color_temp
		if A.adapt_until_sleep and B<0:C=abs(A.min_color_temp-A.sleep_color_temp);D=C*abs(1+B)+A.sleep_color_temp;return 5*round(D/5)
		E='Should not happen';raise ValueError(E)
	def brightness_and_color(A,dt,is_sleep):
		'Calculate the brightness and color.';E=is_sleep;B=A.sun.sun_position(dt);C:0;F=_B;H=A.brightness_pct(dt,E)
		if E:D=A.sleep_color_temp;C=A.sleep_rgb_color
		elif A.sleep_rgb_or_color_temp==_D and A.adapt_until_sleep and B<0:I=color_temperature_to_rgb(A.min_color_temp);C=lerp_color_hsv(I,A.sleep_rgb_color,B);D=A.color_temp_kelvin(B);F=_C
		else:D=A.color_temp_kelvin(B);J,K,L=color_temperature_to_rgb(D);C=round(J),round(K),round(L)
		M=math.floor(1000000/D);G=color_RGB_to_xy(*C);N=color_xy_to_hs(*G);return{'brightness_pct':H,'color_temp_kelvin':D,'color_temp_mired':M,_D:C,'xy_color':G,'hs_color':N,'sun_position':B,'force_rgb_color':F}
	def get_settings(A,is_sleep,transition):'Get all light settings.\n\n        Calculating all values takes <0.5ms.\n        ';B=utcnow()+timedelta(seconds=transition or 0);return A.brightness_and_color(B,is_sleep)
def find_a_b(x1,x2,y1,y2):"Compute the values of 'a' and 'b' for a scaled and shifted tanh function.\n\n    Given two points (x1, y1) and (x2, y2), this function calculates the coefficients 'a' and 'b'\n    for a tanh function of the form y = 0.5 * (tanh(a * (x - b)) + 1) that passes through these points.\n\n    The derivation is as follows:\n\n    1. Start with the equation of the tanh function:\n       y = 0.5 * (tanh(a * (x - b)) + 1)\n\n    2. Rearrange the equation to isolate tanh:\n       tanh(a * (x - b)) = 2*y - 1\n\n    3. Take the inverse tanh (or artanh) on both sides to solve for 'a' and 'b':\n       a * (x - b) = artanh(2*y - 1)\n\n    4. Plug in the points (x1, y1) and (x2, y2) to get two equations.\n       Using these, we can solve for 'a' and 'b' as:\n       a = (artanh(2*y2 - 1) - artanh(2*y1 - 1)) / (x2 - x1)\n       b = x1 - (artanh(2*y1 - 1) / a)\n\n    Parameters\n    ----------\n    x1\n        x-coordinate of the first point.\n    x2\n        x-coordinate of the second point.\n    y1\n        y-coordinate of the first point (should be between 0 and 1).\n    y2\n        y-coordinate of the second point (should be between 0 and 1).\n\n    Returns\n    -------\n    a\n        Coefficient 'a' for the tanh function.\n    b\n        Coefficient 'b' for the tanh function.\n\n    Notes\n    -----\n    The values of y1 and y2 should lie between 0 and 1, inclusive.\n\n    ";A=(math.atanh(2*y2-1)-math.atanh(2*y1-1))/(x2-x1);B=x1-math.atanh(2*y1-1)/A;return A,B
def scaled_tanh(x,x1,x2,y1=.05,y2=.95,y_min=.0,y_max=1e2):"Apply a scaled and shifted tanh function to a given input.\n\n    This function represents a transformation of the tanh function that scales and shifts\n    the output to lie between y_min and y_max. For values of 'x' close to 'x1' and 'x2'\n    (used to calculate 'a' and 'b'), the output of this function will be close to 'y_min'\n    and 'y_max', respectively.\n\n    The equation of the function is as follows:\n    y = y_min + (y_max - y_min) * 0.5 * (tanh(a * (x - b)) + 1)\n\n    Parameters\n    ----------\n    x\n        The input to the function.\n    x1\n        x-coordinate of the first point.\n    x2\n        x-coordinate of the second point.\n    y1\n        y-coordinate of the first point (should be between 0 and 1). Defaults to 0.05.\n    y2\n        y-coordinate of the second point (should be between 0 and 1). Defaults to 0.95.\n    y_min\n        The minimum value of the output range. Defaults to 0.\n    y_max\n        The maximum value of the output range. Defaults to 100.\n\n    Returns\n    -------\n        float: The output of the function, which lies in the range [y_min, y_max].\n\n    ";A=y_min;B,C=find_a_b(x1,x2,y1,y2);return A+(y_max-A)*.5*(math.tanh(B*(x-C))+1)
def lerp_color_hsv(rgb1,rgb2,t):'Linearly interpolate between two RGB colors in HSV color space.';t=abs(t);A=colorsys.rgb_to_hsv(*[A/255. for A in rgb1]);B=colorsys.rgb_to_hsv(*[A/255. for A in rgb2]);C=A[0]+t*(B[0]-A[0]),A[1]+t*(B[1]-A[1]),A[2]+t*(B[2]-A[2]);D=tuple(round(A*255)for A in colorsys.hsv_to_rgb(*C));return cast('tuple[int, int, int]',D)
def lerp(x,x1,x2,y1,y2):'Linearly interpolate between two values.';return y1+(x-x1)*(y2-y1)/(x2-x1)
def clamp(value,minimum,maximum):'Clamp value between minimum and maximum.';return max(minimum,min(value,maximum))