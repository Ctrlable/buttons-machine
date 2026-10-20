from __future__ import annotations
_AT='unknown_module'
_AS='ENTITIES (id — name — area):'
_AR='considered'
_AQ='anything you could not satisfy, or empty'
_AP='program_ref'
_AO='_solar'
_AN='_schedules'
_AM='_sequels'
_AL='enabled'
_AK='entity_settings'
_AJ='ai_failed'
_AI='instructions'
_AH='task_name'
_AG='generate_data'
_AF='global'
_AE='model'
_AD='action_target'
_AC='linked'
_AB='records'
_AA='programs'
_A9='friendly_name'
_A8='max_brightness'
_A7='min_brightness'
_A6='max_color_temp'
_A5='min_color_temp'
_A4='sun_event'
_A3='offset_min'
_A2='days'
_A1='time'
_A0='time_type'
_z='events'
_y='loop'
_x='advance_after_s'
_w='steps'
_v='solar'
_u='schedule'
_t='sequel'
_s='shared'
_r='rejected'
_q='instruction'
_p='structure'
_o=', '
_n='_shared_programs'
_m='none'
_l='cover_cycle'
_k='dim_cycle'
_j='entity_toggle'
_i='module'
_h='hint'
_g='keys'
_f='what'
_e='ai_task'
_d='brightness'
_c='targets'
_b='scene'
_a='single_action'
_Z='proposals'
_Y='agent'
_X='unmatched'
_W='summary'
_V='keypad'
_U='entity_id'
_T='text'
_S='selector'
_R='description'
_Q='buttons'
_P='engraving'
_O='label'
_N='type'
_M='kind'
_L='lights'
_K=True
_J='action_type'
_I='area'
_H='title'
_G='brightness_pct'
_F='entry_id'
_E='entity_ids'
_D='button'
_C='id'
_B=None
_A='name'
import json,logging,re
from typing import Any
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar,device_registry as dr,entity_registry as er
from.const import DOMAIN,ACTION_TYPES
_LOGGER=logging.getLogger(__name__)
_AI_ACTION_TYPES=[_j,_a,_k,_l,_m]
_AI_DOMAINS='light','switch','fan','cover','input_boolean',_b
_MAX_ENTITIES=220
def _entity_catalogue(hass,limit=_MAX_ENTITIES,areas=(),words=''):
	C=hass;J=er.async_get(C);K=dr.async_get(C);L=ar.async_get(C);D=[];F=set()
	for A in J.entities.values():
		if A.disabled_by or A.hidden_by:continue
		if A.domain not in _AI_DOMAINS:continue
		E=A.area_id
		if not E and A.device_id:G=K.async_get(A.device_id);E=G.area_id if G else _B
		H=''
		if E:I=L.async_get_area(E);H=I.name if I else''
		B=C.states.get(A.entity_id);M=A.name or(B.attributes.get(_A9)if B else'')or A.original_name or A.entity_id;D.append({_C:A.entity_id,_A:M,_I:H});F.add(A.entity_id)
	for B in C.states.async_all(_AI_DOMAINS):
		if B.entity_id not in F:D.append({_C:B.entity_id,_A:B.attributes.get(_A9)or B.entity_id,_I:''})
	N={A.strip().lower()for A in areas if A and A.strip()};O=(words or'').lower()
	def P(e):A=(e[_I]or'').lower();B=0 if A and A in N else 1 if A and A in O else 2 if e[_C].startswith('light.')else 3;return B,A,e[_A].lower()
	D.sort(key=P);return D[:limit]
def _real_engraving(name,number):
	A=(name or'').strip()
	if not A or re.fullmatch(f"button\\s*{number}",A,re.I):return''
	return A
_FENCE=re.compile('^\\s*```(?:json)?\\s*|\\s*```\\s*$',re.I)
_TRAILING_COMMA=re.compile(',\\s*([}\\]])')
def _loads_lenient(text):
	A=_FENCE.sub('',text.strip())
	try:return json.loads(A)
	except ValueError:0
	C=[A for A in(A.find('{'),A.find('['))if A>=0]
	if not C:raise ValueError('no JSON in reply')
	B=min(C);D=A.rfind('}'if A[B]=='{'else']')
	if D<=B:raise ValueError('unterminated JSON')
	return json.loads(_TRAILING_COMMA.sub('\\1',A[B:D+1]))
def _rows(raw):
	C=raw;G=C if isinstance(C,list)else[C]if C not in(_B,'')else[];D=[];E=[]
	for B in G:
		A=B
		if isinstance(B,str):
			if not B.strip():continue
			try:A=_loads_lenient(B)
			except ValueError:E.append(f"not valid JSON: {B[:90]}");continue
		if isinstance(A,dict):
			F=A.get(_AA)or A.get(_AB)
			if isinstance(F,list):A=F
		if isinstance(A,list):D.extend(A)
		else:D.append(A)
	return D,E
_KEY_ALIASES={'button_number':_D,'number':_D,'btn':_D,'action':_J,_N:_J,'entities':_E,_U:_E,_c:_E,'target':_E,_L:_E,_d:_G,'level':_G,_A:_O,_P:_O,_V:_F,'keypad_id':_F}
_ACTION_ALIASES={'toggle':_j,'on_off':_j,'onoff':_j,_b:_a,'set':_a,'set_level':_a,'dim':_k,'dimming':_k,'hold_to_dim':_k,'shade':_l,'shades':_l,'cover':_l,'nothing':_m}
def _int_in(value):
	A=value
	if isinstance(A,bool):return
	if isinstance(A,(int,float)):return int(A)
	B=re.search('-?\\d+',str(A or''));return int(B.group())if B else _B
def _normalise(obj):
	A={}
	for(E,F)in obj.items():
		B=str(E).strip().lower();C=_KEY_ALIASES.get(B,B)
		if C in A and B!=C:continue
		A[C]=F
	if isinstance(A.get(_J),str):D=A[_J].strip().lower().replace('-','_').replace(' ','_');A[_J]=_ACTION_ALIASES.get(D,D)
	return A
def _keypads(hass):
	from.import _impl as D;G=(hass.data.get(DOMAIN,{})or{}).get(_n,{})or{};H=[]
	for B in hass.config_entries.async_entries(DOMAIN):
		if B.data.get('_controller'):continue
		C={**B.data,**B.options};I=D._entry_buttons(B);J=C.get('button_names')or{};M=C.get('button_numbers')or sorted((int(A)for A in I if str(A).isdigit()),key=int);N={C.get('raise_button'),C.get('lower_button')}-{_B};K=[]
		for A in M:
			if not str(A).isdigit()or int(A)in N:continue
			A=int(A);E=I.get(str(A))or{};F=E.get(_AP);L=D._resolve_button_program(E,G);K.append({_D:A,_P:_real_engraving(E.get(_O)or J.get(str(A))or J.get(A)or'',A),_J:L.get(_J)or _m,_c:len(D._normalize_targets(L.get(_AD))),_AC:(G.get(F)or{}).get(_A)or F if F else _B})
		H.append({_F:B.entry_id,_H:B.title,_I:C.get('area_name')or'',_AE:C.get('model_number')or'',_Q:K})
	return H
def _prompt(instruction,cat,keypads,scope):
	G=instruction;F=cat;D=scope;A=['You program lighting keypads. Return one compact JSON object per button you are programming.','','RULES:','- Use entity_ids EXACTLY as listed. Never invent one, never guess a spelling.','- Only program buttons that exist on the keypad you are told about.','- Leave a button out entirely if the request does not concern it.',f"- action_type must be one of: {_o.join(_AI_ACTION_TYPES)}",'- entity_toggle: press turns the group on, press again turns it off.','- single_action: press applies specific levels (use brightness_pct).','- dim_cycle: hold to dim. cover_cycle: for shades.','- brightness_pct is 0-100, or null to leave it at whatever the light does by default.','',"READ THE ENGRAVINGS. They are the installer's own statement of what each","button is for, and the keypad's area says which room it serves. A button",'engraved "Kitchen" on a keypad in the Hall should drive the Kitchen lights;','one engraved "Off" or "All Off" should turn that area off; "Dim" or an','up/down pair suggests dim_cycle. Prefer entities whose AREA matches the',"engraving, then the keypad's own area. A button with no engraving and no",'instruction about it should be LEFT ALONE.','','KEYS: button (int), action_type (string), entity_ids (list of exact ids),','      brightness_pct (int or null), label (short engraving-style name)','FORMAT: each item is ONE JSON object as a plain string, for example','  {"button": 1, "action_type": "entity_toggle", "entity_ids": ["light.kitchen"], "brightness_pct": null, "label": "Kitchen"}','  No code fences, no prose, no arrays inside a string.','']
	if D.get(_M)==_D:A.append(f'SCOPE: only button {D.get(_D)} on keypad "{D.get(_H)}". Return exactly one object.')
	elif D.get(_M)==_V:A.append(f'SCOPE: only the keypad "{D.get(_H)}". Return one object per button you change.')
	else:A.append('SCOPE: any keypad. Include an entry_id on every object so each program lands on the right keypad.');A.append('KEYS also include: entry_id (string, exactly as listed)')
	A.append('');A.append('KEYPADS:')
	for B in keypads:
		H=f" in {B[_I]}"if B.get(_I)else'';I=f" [{B[_AE]}]"if B.get(_AE)else'';A.append(f"  {B[_H]}{H}{I}  (entry_id {B[_F]})")
		for C in B[_Q]:J=f' engraved "{C[_P]}"'if C[_P]else' (no engraving)';K=f', linked to Shared Program "{C[_AC]}" (change only if asked)'if C.get(_AC)else'';A.append(f"    button {C[_D]}{J} — currently {C[_J]} ({C[_c]} target(s)){K}")
	A.append('');L=f"; only the {len(F)} most relevant are listed"if len(F)>=_MAX_ENTITIES else'';A.append(f"ENTITIES (id — name — area), most relevant first{L}:")
	for E in F:A.append(f"  {E[_C]} — {E[_A]}"+(f" — {E[_I]}"if E[_I]else''))
	A.append('')
	if G.strip():A.append(f'REQUEST: "{G}"')
	else:A.append('REQUEST: no instruction was given. Propose a sensible programme for this keypad from its engravings, its area and the entities available. Leave unengraved buttons alone.')
	return'\n'.join(A)
def _validate(hass,rows,scope,keypads,cat):
	M=keypads;D=scope;N={A[_C]for A in cat};O={A[_F]:A for A in M};P=[];B=[];S={A[_H].strip().lower():A for A in M};T,B=_rows(rows)
	for J in T:
		if not isinstance(J,dict):B.append(f"not an object: {str(J)[:90]}");continue
		E=_normalise(J)
		if D.get(_M)in(_V,_D):F=D.get(_F)
		else:K=str(E.get(_F)or'').strip();Q=O.get(K)or S.get(K.lower());F=Q[_F]if Q else K
		C=O.get(F)
		if C is _B:B.append(f"unknown keypad {F!r}");continue
		A=_int_in(E.get(_D))
		if A is _B and D.get(_M)==_D:A=D.get(_D)
		if A is _B:B.append(f"{C[_H]}: button {E.get(_D)!r} is not a number");continue
		if A not in{A[_D]for A in C[_Q]}:B.append(f"{C[_H]}: has no button {A}");continue
		if D.get(_M)==_D and(F!=D.get(_F)or A!=D.get(_D)):B.append(f"{C[_H]} button {A}: outside the requested scope");continue
		if D.get(_M)==_V and F!=D.get(_F):B.append(f"{C[_H]}: outside the requested keypad");continue
		G=str(E.get(_J)or'').strip()
		if G not in _AI_ACTION_TYPES or G not in ACTION_TYPES:B.append(f"{C[_H]} button {A}: unsupported action {G!r}");continue
		H=E.get(_E)or[]
		if isinstance(H,str):H=[H]
		L=[A for A in H if A in N];R=[A for A in H if A not in N]
		if R:B.append(f"{C[_H]} button {A}: unknown entities {_o.join(R[:4])}")
		if G!=_m and not L:B.append(f"{C[_H]} button {A}: no usable entities, skipped");continue
		I=_int_in(E.get(_G))
		if I is not _B:I=max(0,min(100,I))
		P.append({_F:F,_V:C[_H],_D:A,_J:G,_E:L,_G:I,_O:str(E.get(_O)or'')[:40],'current':next((B for B in C[_Q]if B[_D]==A),_B),'names':{A:next((B[_A]for B in cat if B[_C]==A),A)for A in L}})
	return P,B
@websocket_api.websocket_command({vol.Required(_N):f"{DOMAIN}/ai_agents"})
@websocket_api.async_response
async def ws_ai_agents(hass,connection,msg):A=[{_U:A.entity_id,_A:A.attributes.get(_A9)or A.entity_id}for A in hass.states.async_all(_e)];connection.send_result(msg[_C],{'agents':A,'preferred':_preferred_agent(hass)})
def _preferred_agent(hass):
	try:A=hass.data.get(_e);A=getattr(A,'preferences',A);return getattr(A,'gen_data_entity_id',_B)
	except Exception:return
def _friendly_error(exc):
	B=str(exc)or exc.__class__.__name__;A=B.lower()
	if'json'in A or'parse'in A or _p in A:return f"The assistant replied in a format Buttons Machine couldn't read. Try again, or pick a different assistant. ({B[:160]})"
	if'timeout'in A or'timed out'in A:return'The assistant took too long to answer. Try again, or ask for less at once.'
	if'429'in A or'quota'in A or'rate'in A and'limit'in A:return"The assistant's provider is limiting requests. Wait a minute and try again."
	if'401'in A or'api key'in A or'unauthor'in A:return"The assistant's provider rejected its credentials. Check that integration."
	if'not found'in A or'unknown entity'in A:return f"That assistant is no longer available. Pick another one. ({B[:160]})"
	return B
@websocket_api.websocket_command({vol.Required(_N):f"{DOMAIN}/ai_propose",vol.Optional(_q,default=''):str,vol.Required(_Y):str,vol.Optional(_F):vol.Any(str,_B),vol.Optional(_D):vol.Any(int,_B)})
@websocket_api.async_response
async def ws_ai_propose(hass,connection,msg):
	G=connection;D=hass;A=msg;E=_keypads(D)
	if not E:G.send_error(A[_C],'no_keypads','No keypads are configured');return
	B=A.get(_F);L=A.get(_D);H=_D if B and L is not _B else _V if B else _AF;Q=next((A[_H]for A in E if A[_F]==B),'');M={_M:H,_F:B,_D:L,_H:Q};I=[A for A in E if H==_AF or A[_F]==B];N=A.get(_q)or'';R=' '.join(B[_P]for A in I for B in A[_Q]);J=_entity_catalogue(D,areas=tuple(A[_I]for A in I),words=f"{N} {R}");O=_prompt(N,J,I,M);S={_AA:{_R:'one compact JSON object per button, as a string',_S:{_T:{'multiple':_K}}},_W:{_R:'one sentence on what you did',_S:{_T:_B}},_X:{_R:_AQ,_S:{_T:_B}}};F={};K=[];C=[]
	for T in range(2):
		try:U=await D.services.async_call(_e,_AG,{_U:A[_Y],_AH:'buttons_machine_program',_AI:O,_p:S},blocking=_K,return_response=_K)
		except Exception as P:_LOGGER.warning('AI propose failed: %s',P);G.send_error(A[_C],_AJ,_friendly_error(P));return
		F=(U or{}).get('data')or{};K,C=_validate(D,F.get(_AA)or[],M,E,J)
		if K or not C or T:break
		_LOGGER.info('AI propose: unusable reply, asking once more: %s',C[:3]);O+='\n\nYOUR LAST REPLY COULD NOT BE USED: '+'; '.join(C[:3])+'\nReturn ONLY the JSON objects described under FORMAT.'
	G.send_result(A[_C],{_Z:K,_r:C,_W:F.get(_W)or'',_X:F.get(_X)or'','scope':H,_AR:len(J)})
@websocket_api.websocket_command({vol.Required(_N):f"{DOMAIN}/ai_apply",vol.Required(_Z):list})
@websocket_api.async_response
async def ws_ai_apply(hass,connection,msg):
	L=connection;G=msg;D=hass;R=_keypads(D);S=_entity_catalogue(D);H,E=_validate(D,G[_Z],{_M:_AF},R,S)
	if E and not H:L.send_error(G[_C],'invalid','; '.join(E[:4]));return
	M=0;N=set()
	for F in{A[_F]for A in H}:
		C=D.config_entries.async_get_entry(F)
		if C is _B or C.domain!=DOMAIN:E.append(f"keypad {F} disappeared");continue
		from.import _impl as I;J={A:dict(B or{})for(A,B)in I._entry_buttons(C).items()}
		for A in[A for A in H if A[_F]==F]:
			O=str(A[_D]);B=dict(J.get(O)or{});B.pop(_AP,_B);B[_J]=A[_J];B[_AD]=list(A[_E])
			if A[_O]:B[_O]=A[_O]
			if A[_G]is not _B:
				K=dict(B.get(_AK)or{})
				for P in A[_E]:Q=dict(K.get(P)or{});Q[_d]=A[_G];K[P]=Q
				B[_AK]=K
			J[O]=B;M+=1
		D.config_entries.async_update_entry(C,options={**C.options,_Q:J,I.REV_KEY:I._options_rev(C.options)+1});N.add(F)
	L.send_result(G[_C],{'written':M,'keypads':len(N),_r:E})
_ADAPTERS={}
def register_adapter(name,**A):_ADAPTERS[name]=A
def async_register(hass):A=hass;websocket_api.async_register_command(A,ws_ai_agents);websocket_api.async_register_command(A,ws_ai_propose);websocket_api.async_register_command(A,ws_ai_apply);websocket_api.async_register_command(A,ws_ai_module_propose);websocket_api.async_register_command(A,ws_ai_module_apply);websocket_api.async_register_command(A,ws_ai_ask)
_MODULE_RULES={_s:{_f:'a Shared Program -- a named lighting scene that any keypad button can point at',_g:'name (string), entity_ids (list of exact ids), brightness_pct (int or null)',_h:'One object per program. Group entities that belong together in one room or mood.'},_t:{_f:'a Sequel -- an ordered sequence of steps, each a scene held for a number of seconds',_g:'name (string), loop (bool), steps (list of objects, each with name, advance_after_s (int seconds), entity_ids (list), brightness_pct)',_h:'One object per sequence. 2-6 steps is typical; give each step a short name.'},_u:{_f:'a Schedule -- timeclock events that run a scene at a time of day or at sunrise/sunset',_g:"name (string), events (list of objects, each with name, time_type ('clock' or 'sun'), time ('HH:MM', clock only), sun_event ('sunrise' or 'sunset', sun only), offset_min (int), days (list of ints 0=Mon..6=Sun), entity_ids (list), brightness_pct)",_h:"One object per schedule. Use time_type 'sun' for anything tied to daylight."},_v:{_f:'a Solar Sync programme -- lights that follow a circadian curve, warm and dim at night, cool and bright in the middle of the day',_g:'name (string), lights (list of exact ids), min_color_temp (K, e.g. 1800), max_color_temp (K, e.g. 4000), min_brightness (pct), max_brightness (pct)',_h:'One object per programme. A light may belong to only ONE Solar programme; adding it here removes it from any other.'}}
def _module_prompt(module,instruction,cat,existing):C=instruction;B=_MODULE_RULES[module];A=[f"You are configuring {B[_f]}.",'','RULES:','- Use entity_ids EXACTLY as listed below. Never invent one.','- Return one compact JSON object per record, as a string.',f"- KEYS: {B[_g]}",f"- {B[_h]}",'- brightness_pct is 0-100, or null to leave the light at its own default.','','ALREADY CONFIGURED (do not duplicate these unless asked to change them):'];A+=[f"  {B.get(_A)or A}"for(A,B)in(existing or{}).items()]or['  (none yet)'];A+=['',_AS];A+=[f"  {A[_C]} — {A[_A]}"+(f" — {A[_I]}"if A[_I]else'')for A in cat];A+=[''];A.append(f'REQUEST: "{C}"'if C.strip()else'REQUEST: no instruction was given. Propose something sensible for this installation from the rooms and fixtures available.');return'\n'.join(A)
def _validate_module(module,rows,cat):
	X='sunrise';W='18:00';V='clock';U='sun';G=module;P={A[_C]for A in cat};H=[];C=[]
	def J(v,where):
		A=v if isinstance(v,list)else[v]if isinstance(v,str)else[];D=[A for A in A if A in P];B=[A for A in A if A not in P]
		if B:C.append(f"{where}: unknown entities {_o.join(B[:4])}")
		return D
	def M(v):A=_int_in(v)if v is not _B else _B;return _B if A is _B else max(0,min(100,A))
	Y,Z=_rows(rows);C.extend(Z)
	for A in Y:
		if not isinstance(A,dict):C.append(f"not an object: {str(A)[:80]}");continue
		A={str(A).strip().lower():B for(A,B)in A.items()}
		if _E not in A:
			for Q in('entities',_U,_c):
				if Q in A:A[_E]=A[Q];break
		if _G not in A and _d in A:A[_G]=A[_d]
		B=str(A.get(_A)or'').strip()
		if not B:C.append('a record arrived with no name');continue
		if G==_s:
			D=J(A.get(_E),B)
			if not D:C.append(f"{B}: no usable entities");continue
			H.append({_A:B,_E:D,_G:M(A.get(_G))})
		elif G==_t:
			N=[]
			for(F,I)in enumerate(A.get(_w)or[],1):
				if not isinstance(I,dict):continue
				D=J(I.get(_E),f"{B} step {F}")
				if not D:continue
				try:R=max(1,min(3600,int(I.get(_x)or 8)))
				except(TypeError,ValueError):R=8
				N.append({_A:str(I.get(_A)or f"Step {F}")[:40],_x:R,_E:D,_G:M(I.get(_G))})
			if not N:C.append(f"{B}: no usable steps");continue
			H.append({_A:B,_y:bool(A.get(_y)),_w:N})
		elif G==_u:
			O=[]
			for(F,E)in enumerate(A.get(_z)or[],1):
				if not isinstance(E,dict):continue
				D=J(E.get(_E),f"{B} event {F}")
				if not D:continue
				S=U if str(E.get(_A0))==U else V;K=str(E.get(_A1)or W)
				if S==V and not re.fullmatch('\\d{1,2}:\\d{2}',K):C.append(f"{B} event {F}: bad time {K!r}, using 18:00");K=W
				a=[A for A in E.get(_A2)or[0,1,2,3,4,5,6]if isinstance(A,int)and 0<=A<=6]or[0,1,2,3,4,5,6]
				try:T=max(-720,min(720,int(E.get(_A3)or 0)))
				except(TypeError,ValueError):T=0
				O.append({_A:str(E.get(_A)or f"Event {F}")[:40],_AL:_K,_A0:S,_A1:K,_A4:X if str(E.get(_A4))==X else'sunset',_A3:T,_A2:a,_E:D,_G:M(E.get(_G))})
			if not O:C.append(f"{B}: no usable events");continue
			H.append({_A:B,_z:O})
		elif G==_v:
			D=J(A.get(_L),B)
			if not D:C.append(f"{B}: no usable lights");continue
			def L(v,lo,hi,dflt):
				try:return max(lo,min(hi,int(v)))
				except(TypeError,ValueError):return dflt
			H.append({_A:B,_L:D,_A5:L(A.get(_A5),1000,6500,1800),_A6:L(A.get(_A6),1000,6500,4000),_A7:L(A.get(_A7),1,100,20),_A8:L(A.get(_A8),1,100,80)})
		else:C.append(f"{G}: not a writable module")
	return H,C
@websocket_api.websocket_command({vol.Required(_N):f"{DOMAIN}/ai_module_propose",vol.Required(_i):str,vol.Required(_Y):str,vol.Optional(_q,default=''):str})
@websocket_api.async_response
async def ws_ai_module_propose(hass,connection,msg):
	D=hass;C=connection;B=msg;A=B[_i]
	if A=='related':C.send_error(B[_C],'read_only','Related is a read-only surface and proposes no changes');return
	if A not in _MODULE_RULES:C.send_error(B[_C],_AT,f"No AI support for {A!r}");return
	I={_s:_n,_t:_AM,_u:_AN,_v:_AO}[A];G=(D.data.get(DOMAIN,{})or{}).get(I,{})or{};E=_entity_catalogue(D);J=_module_prompt(A,B.get(_q)or'',E,G)
	try:K=await D.services.async_call(_e,_AG,{_U:B[_Y],_AH:f"buttons_machine_{A}",_AI:J,_p:{_AB:{_R:'one compact JSON object per record, as a string',_S:{_T:{'multiple':_K}}},_W:{_R:'one sentence on what you produced',_S:{_T:_B}},_X:{_R:_AQ,_S:{_T:_B}}}},blocking=_K,return_response=_K)
	except Exception as H:_LOGGER.warning('AI %s propose failed: %s',A,H);C.send_error(B[_C],_AJ,_friendly_error(H));return
	F=(K or{}).get('data')or{};L,M=_validate_module(A,F.get(_AB)or[],E);C.send_result(B[_C],{_i:A,_Z:L,_r:M,_W:F.get(_W)or'',_X:F.get(_X)or'',_AR:len(E),'existing':len(G)})
@websocket_api.websocket_command({vol.Required(_N):f"{DOMAIN}/ai_module_apply",vol.Required(_i):str,vol.Required(_Z):list})
@websocket_api.async_response
async def ws_ai_module_apply(hass,connection,msg):
	K=connection;E=msg;B=hass;C=E[_i]
	if C not in _MODULE_RULES:K.send_error(E[_C],_AT,f"No AI support for {C!r}");return
	S=_entity_catalogue(B);F,N=_validate_module(C,E[_Z],S)
	if not F:K.send_error(E[_C],'invalid','; '.join(N[:4])or'nothing to write');return
	import uuid as H;from.import _impl as I,solar as O
	def L(ids,bri):return{A:{_d:bri}if bri is not _B else{}for A in ids}
	J=B.data.setdefault(DOMAIN,{});G=0
	if C==_s:
		D=dict(J.get(_n,{})or{})
		for A in F:D['sp_'+H.uuid4().hex[:8]]={_A:A[_A],'program':{_J:_a,_AD:A[_E],_AK:L(A[_E],A[_G])}};G+=1
		await I._save_shared_programs(B,D)
	elif C==_t:
		P=dict(J.get(_AM,{})or{})
		for A in F:P['seq_'+H.uuid4().hex[:8]]={_A:A[_A],_N:'auto',_y:A[_y],_w:[{_A:A[_A],'status_led':'on',_x:A[_x],'scene_mode':'custom',_b:L(A[_E],A[_G])}for A in A[_w]]};G+=1
		await I._save_sequels(B,P)
	elif C==_u:
		Q=dict(J.get(_AN,{})or{})
		for A in F:Q['sch_'+H.uuid4().hex[:8]]={_A:A[_A],_z:[{_A:A[_A],_AL:_K,_A0:A[_A0],_A1:A[_A1],_A4:A[_A4],_A3:A[_A3],_A2:A[_A2],'action':{_M:_b,_b:L(A[_E],A[_G])}}for A in A[_z]]};G+=1
		await I._save_schedules(B,Q);I._get_schedule_engine(B).rearm()
	elif C==_v:
		D=dict(J.get(_AO,{})or{})
		for A in F:
			T=set(A[_L])
			for(U,M)in list(D.items()):
				R=[A for A in M.get(_L)or[]if A not in T]
				if len(R)!=len(M.get(_L)or[]):D[U]={**M,_L:R}
			D['sol_'+H.uuid4().hex[:8]]={_A:A[_A],_AL:_K,'on_manual':'release',_A5:A[_A5],_A6:A[_A6],_A7:A[_A7],_A8:A[_A8],'brightness_mode':'default','sunrise_offset_min':0,'sunset_offset_min':0,'interval_s':90,'transition_s':45,'detect_non_ha_changes':_K,_L:A[_L]};G+=1
		await O._save_solar(B,D);O._get_solar_manager(B).rearm_all()
	K.send_result(E[_C],{'written':G,_r:N})
@websocket_api.websocket_command({vol.Required(_N):f"{DOMAIN}/ai_ask",vol.Required('question'):str,vol.Required(_Y):str})
@websocket_api.async_response
async def ws_ai_ask(hass,connection,msg):
	G=connection;F='answer';D=msg;C=hass;I=_entity_catalogue(C);J=_keypads(C);K=C.data.get(DOMAIN,{})or{};A=['You answer questions about a lighting installation. Be brief and concrete.','Name entities and buttons exactly as they appear. If the answer is not in','the data below, say so plainly rather than guessing.','','KEYPADS:']
	for E in J:
		L=f" in {E[_I]}"if E.get(_I)else'';A.append(f"  {E[_H]}{L}")
		for B in E[_Q]:M=f' "{B[_P]}"'if B[_P]else'';A.append(f"    button {B[_D]}{M} — {B[_J]} ({B[_c]} target(s))")
	for(N,O,P)in(('SHARED PROGRAMS',_n,_A),('SEQUELS',_AM,_A),('SCHEDULES',_AN,_A),('SOLAR PROGRAMMES',_AO,_A)):Q=K.get(O)or{};A.append(f"{N}: "+(_o.join(str(B.get(P)or A)for(A,B)in Q.items())or'(none)'))
	A+=['',_AS];A+=[f"  {A[_C]} — {A[_A]}"+(f" — {A[_I]}"if A[_I]else'')for A in I];A+=['',f'QUESTION: "{D["question"]}"']
	try:R=await C.services.async_call(_e,_AG,{_U:D[_Y],_AH:'buttons_machine_ask',_AI:'\n'.join(A),_p:{F:{_R:'the answer, a few sentences at most',_S:{_T:{'multiline':_K}}}}},blocking=_K,return_response=_K)
	except Exception as H:_LOGGER.warning('AI ask failed: %s',H);G.send_error(D[_C],_AJ,_friendly_error(H));return
	G.send_result(D[_C],{F:((R or{}).get('data')or{}).get(F)or''})