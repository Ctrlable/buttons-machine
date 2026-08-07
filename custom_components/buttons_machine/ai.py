from __future__ import annotations
_AL='unknown_module'
_AK='brightness'
_AJ='considered'
_AI='anything you could not satisfy, or empty'
_AH='friendly_name'
_AG='single_action'
_AF='_solar'
_AE='_schedules'
_AD='_sequels'
_AC='_shared_programs'
_AB='enabled'
_AA='entity_settings'
_A9='ai_failed'
_A8='structure'
_A7='instructions'
_A6='task_name'
_A5='generate_data'
_A4='global'
_A3='ENTITIES (id — name — area):'
_A2='action_target'
_A1='targets'
_A0='model'
_z='max_brightness'
_y='min_brightness'
_x='max_color_temp'
_w='min_color_temp'
_v='sun_event'
_u='offset_min'
_t='days'
_s='time'
_r='time_type'
_q='events'
_p='loop'
_o='advance_after_s'
_n='steps'
_m='solar'
_l='schedule'
_k='sequel'
_j='shared'
_i='rejected'
_h='instruction'
_g='ai_task'
_f='entity_id'
_e='label'
_d='keypad'
_c=', '
_b='scene'
_a='module'
_Z='hint'
_Y='keys'
_X='what'
_W='engraving'
_V='proposals'
_U='unmatched'
_T='summary'
_S='agent'
_R='text'
_Q='selector'
_P='description'
_O='type'
_N='kind'
_M='lights'
_L='action_type'
_K='buttons'
_J='area'
_I=True
_H='brightness_pct'
_G='entity_ids'
_F='title'
_E='entry_id'
_D='button'
_C=None
_B='id'
_A='name'
import json,logging,re
from typing import Any
import voluptuous as vol
from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry as ar
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from.const import DOMAIN,ACTION_TYPES
_LOGGER=logging.getLogger(__name__)
_AI_ACTION_TYPES=['entity_toggle',_AG,'dim_cycle','cover_cycle','none']
_AI_DOMAINS='light','switch','fan','cover','input_boolean',_b
_MAX_ENTITIES=220
def _entity_catalogue(hass,limit=_MAX_ENTITIES):
	B=hass;I=er.async_get(B);J=dr.async_get(B);K=ar.async_get(B);D=[]
	for A in I.entities.values():
		if A.disabled_by or A.hidden_by:continue
		if A.domain not in _AI_DOMAINS:continue
		C=A.area_id
		if not C and A.device_id:E=J.async_get(A.device_id);C=E.area_id if E else _C
		F=''
		if C:G=K.async_get_area(C);F=G.name if G else''
		H=B.states.get(A.entity_id);L=A.name or(H.attributes.get(_AH)if H else'')or A.original_name or A.entity_id;D.append({_B:A.entity_id,_A:L,_J:F})
		if len(D)>=limit:break
	return D
def _real_engraving(name,number):
	A=(name or'').strip()
	if not A or re.fullmatch(f"button\\s*{number}",A,re.I):return''
	return A
def _keypads(hass):
	D=[]
	for B in hass.config_entries.async_entries(DOMAIN):A={**B.data,**B.options};C=A.get(_K)or{};E=A.get('button_names')or{};F=A.get('button_numbers')or sorted((int(A)for A in C if str(A).isdigit()),key=int);D.append({_E:B.entry_id,_F:B.title,_J:A.get('area_name')or'',_A0:A.get('model_number')or'',_K:[{_D:int(A),_W:_real_engraving(E.get(str(A))or E.get(A)or'',A),_L:(C.get(str(A))or{}).get(_L)or'none',_A1:len((C.get(str(A))or{}).get(_A2)or[])}for A in F if str(A).isdigit()]})
	return D
def _prompt(instruction,cat,keypads,scope):
	F=instruction;C=scope;A=['You program lighting keypads. Return one compact JSON object per button you are programming.','','RULES:','- Use entity_ids EXACTLY as listed. Never invent one, never guess a spelling.','- Only program buttons that exist on the keypad you are told about.','- Leave a button out entirely if the request does not concern it.',f"- action_type must be one of: {_c.join(_AI_ACTION_TYPES)}",'- entity_toggle: press turns the group on, press again turns it off.','- single_action: press applies specific levels (use brightness_pct).','- dim_cycle: hold to dim. cover_cycle: for shades.','- brightness_pct is 0-100, or null to leave it at whatever the light does by default.','',"READ THE ENGRAVINGS. They are the installer's own statement of what each","button is for, and the keypad's area says which room it serves. A button",'engraved "Kitchen" on a keypad in the Hall should drive the Kitchen lights;','one engraved "Off" or "All Off" should turn that area off; "Dim" or an','up/down pair suggests dim_cycle. Prefer entities whose AREA matches the',"engraving, then the keypad's own area. A button with no engraving and no",'instruction about it should be LEFT ALONE.','','KEYS: button (int), action_type (string), entity_ids (list of exact ids),','      brightness_pct (int or null), label (short engraving-style name)','']
	if C.get(_N)==_D:A.append(f'SCOPE: only button {C.get(_D)} on keypad "{C.get(_F)}". Return exactly one object.')
	elif C.get(_N)==_d:A.append(f'SCOPE: only the keypad "{C.get(_F)}". Return one object per button you change.')
	else:A.append('SCOPE: any keypad. Include an entry_id on every object so each program lands on the right keypad.');A.append('KEYS also include: entry_id (string, exactly as listed)')
	A.append('');A.append('KEYPADS:')
	for B in keypads:
		G=f" in {B[_J]}"if B.get(_J)else'';H=f" [{B[_A0]}]"if B.get(_A0)else'';A.append(f"  {B[_F]}{G}{H}  (entry_id {B[_E]})")
		for D in B[_K]:I=f' engraved "{D[_W]}"'if D[_W]else' (no engraving)';A.append(f"    button {D[_D]}{I} — currently {D[_L]} ({D[_A1]} target(s))")
	A.append('');A.append(_A3)
	for E in cat:A.append(f"  {E[_B]} — {E[_A]}"+(f" — {E[_J]}"if E[_J]else''))
	A.append('')
	if F.strip():A.append(f'REQUEST: "{F}"')
	else:A.append('REQUEST: no instruction was given. Propose a sensible programme for this keypad from its engravings, its area and the entities available. Leave unengraved buttons alone.')
	return'\n'.join(A)
def _validate(hass,rows,scope,keypads,cat):
	E=scope;K={A[_B]for A in cat};O={A[_E]:A for A in keypads};L=[];A=[]
	for F in rows:
		try:D=json.loads(F)if isinstance(F,str)else F
		except Exception:A.append(f"not valid JSON: {str(F)[:90]}");continue
		if not isinstance(D,dict):A.append(f"not an object: {str(F)[:90]}");continue
		G=D.get(_E)or E.get(_E);B=O.get(G)
		if B is _C:A.append(f"unknown keypad {G!r}");continue
		try:C=int(D.get(_D))
		except(TypeError,ValueError):A.append(f"{B[_F]}: button {D.get(_D)!r} is not a number");continue
		if C not in{A[_D]for A in B[_K]}:A.append(f"{B[_F]}: has no button {C}");continue
		if E.get(_N)==_D and(G!=E.get(_E)or C!=E.get(_D)):A.append(f"{B[_F]} button {C}: outside the requested scope");continue
		if E.get(_N)==_d and G!=E.get(_E):A.append(f"{B[_F]}: outside the requested keypad");continue
		H=str(D.get(_L)or'').strip()
		if H not in _AI_ACTION_TYPES or H not in ACTION_TYPES:A.append(f"{B[_F]} button {C}: unsupported action {H!r}");continue
		I=D.get(_G)or[]
		if isinstance(I,str):I=[I]
		M=[A for A in I if A in K];N=[A for A in I if A not in K]
		if N:A.append(f"{B[_F]} button {C}: unknown entities {_c.join(N[:4])}")
		if H!='none'and not M:A.append(f"{B[_F]} button {C}: no usable entities, skipped");continue
		J=D.get(_H)
		if J is not _C:
			try:J=max(0,min(100,int(J)))
			except(TypeError,ValueError):J=_C
		L.append({_E:G,_d:B[_F],_D:C,_L:H,_G:M,_H:J,_e:str(D.get(_e)or'')[:40],'current':next((A for A in B[_K]if A[_D]==C),_C)})
	return L,A
@websocket_api.websocket_command({vol.Required(_O):f"{DOMAIN}/ai_agents"})
@websocket_api.async_response
async def ws_ai_agents(hass,connection,msg):A=[{_f:A.entity_id,_A:A.attributes.get(_AH)or A.entity_id}for A in hass.states.async_all(_g)];connection.send_result(msg[_B],{'agents':A})
@websocket_api.websocket_command({vol.Required(_O):f"{DOMAIN}/ai_propose",vol.Optional(_h,default=''):str,vol.Required(_S):str,vol.Optional(_E):vol.Any(str,_C),vol.Optional(_D):vol.Any(int,_C)})
@websocket_api.async_response
async def ws_ai_propose(hass,connection,msg):
	L='programs';E=connection;C=hass;A=msg;D=_keypads(C)
	if not D:E.send_error(A[_B],'no_keypads','No keypads are configured');return
	B=A.get(_E);I=A.get(_D);F=_D if B and I is not _C else _d if B else _A4;M=next((A[_F]for A in D if A[_E]==B),'');J={_N:F,_E:B,_D:I,_F:M};N=[A for A in D if F==_A4 or A[_E]==B];G=_entity_catalogue(C);O=_prompt(A.get(_h)or'',G,N,J)
	try:P=await C.services.async_call(_g,_A5,{_f:A[_S],_A6:'buttons_machine_program',_A7:O,_A8:{L:{_P:'one compact JSON object per button, as a string',_Q:{_R:{'multiple':_I}}},_T:{_P:'one sentence on what you did',_Q:{_R:_C}},_U:{_P:_AI,_Q:{_R:_C}}}},blocking=_I,return_response=_I)
	except Exception as K:_LOGGER.warning('AI propose failed: %s',K);E.send_error(A[_B],_A9,str(K));return
	H=(P or{}).get('data')or{};Q,R=_validate(C,H.get(L)or[],J,D,G);E.send_result(A[_B],{_V:Q,_i:R,_T:H.get(_T)or'',_U:H.get(_U)or'','scope':F,_AJ:len(G)})
@websocket_api.websocket_command({vol.Required(_O):f"{DOMAIN}/ai_apply",vol.Required(_V):list})
@websocket_api.async_response
async def ws_ai_apply(hass,connection,msg):
	L=connection;G=msg;B=hass;Q=_keypads(B);R=_entity_catalogue(B);H,F=_validate(B,G[_V],{_N:_A4},Q,R)
	if F and not H:L.send_error(G[_B],'invalid','; '.join(F[:4]));return
	M=0;I=set()
	for C in{A[_E]for A in H}:
		D=B.config_entries.async_get_entry(C)
		if D is _C or D.domain!=DOMAIN:F.append(f"keypad {C} disappeared");continue
		J=dict(D.options.get(_K)or D.data.get(_K)or{})
		for A in[A for A in H if A[_E]==C]:
			N=str(A[_D]);E=dict(J.get(N)or{});E[_L]=A[_L];E[_A2]=list(A[_G])
			if A[_e]:E[_A]=A[_e]
			if A[_H]is not _C:
				K=dict(E.get(_AA)or{})
				for O in A[_G]:P=dict(K.get(O)or{});P[_AK]=A[_H];K[O]=P
				E[_AA]=K
			J[N]=E;M+=1
		B.config_entries.async_update_entry(D,options={**D.options,_K:J});I.add(C)
	for C in I:await B.config_entries.async_reload(C)
	L.send_result(G[_B],{'written':M,'keypads':len(I),_i:F})
_ADAPTERS={}
def register_adapter(name,**A):_ADAPTERS[name]=A
def async_register(hass):A=hass;websocket_api.async_register_command(A,ws_ai_agents);websocket_api.async_register_command(A,ws_ai_propose);websocket_api.async_register_command(A,ws_ai_apply);websocket_api.async_register_command(A,ws_ai_module_propose);websocket_api.async_register_command(A,ws_ai_module_apply);websocket_api.async_register_command(A,ws_ai_ask)
_MODULE_RULES={_j:{_X:'a Shared Program -- a named lighting scene that any keypad button can point at',_Y:'name (string), entity_ids (list of exact ids), brightness_pct (int or null)',_Z:'One object per program. Group entities that belong together in one room or mood.'},_k:{_X:'a Sequel -- an ordered sequence of steps, each a scene held for a number of seconds',_Y:'name (string), loop (bool), steps (list of objects, each with name, advance_after_s (int seconds), entity_ids (list), brightness_pct)',_Z:'One object per sequence. 2-6 steps is typical; give each step a short name.'},_l:{_X:'a Schedule -- timeclock events that run a scene at a time of day or at sunrise/sunset',_Y:"name (string), events (list of objects, each with name, time_type ('clock' or 'sun'), time ('HH:MM', clock only), sun_event ('sunrise' or 'sunset', sun only), offset_min (int), days (list of ints 0=Mon..6=Sun), entity_ids (list), brightness_pct)",_Z:"One object per schedule. Use time_type 'sun' for anything tied to daylight."},_m:{_X:'a Solar Sync programme -- lights that follow a circadian curve, warm and dim at night, cool and bright in the middle of the day',_Y:'name (string), lights (list of exact ids), min_color_temp (K, e.g. 1800), max_color_temp (K, e.g. 4000), min_brightness (pct), max_brightness (pct)',_Z:'One object per programme. A light may belong to only ONE Solar programme; adding it here removes it from any other.'}}
def _module_prompt(module,instruction,cat,existing):C=instruction;B=_MODULE_RULES[module];A=[f"You are configuring {B[_X]}.",'','RULES:','- Use entity_ids EXACTLY as listed below. Never invent one.','- Return one compact JSON object per record, as a string.',f"- KEYS: {B[_Y]}",f"- {B[_Z]}",'- brightness_pct is 0-100, or null to leave the light at its own default.','','ALREADY CONFIGURED (do not duplicate these unless asked to change them):'];A+=[f"  {B.get(_A)or A}"for(A,B)in(existing or{}).items()]or['  (none yet)'];A+=['',_A3];A+=[f"  {A[_B]} — {A[_A]}"+(f" — {A[_J]}"if A[_J]else'')for A in cat];A+=[''];A.append(f'REQUEST: "{C}"'if C.strip()else'REQUEST: no instruction was given. Propose something sensible for this installation from the rooms and fixtures available.');return'\n'.join(A)
def _validate_module(module,rows,cat):
	X='sunrise';W='18:00';V='clock';U='sun';G=module;Q={A[_B]for A in cat};H=[];C=[]
	def K(v,where):
		A=v if isinstance(v,list)else[v]if isinstance(v,str)else[];D=[A for A in A if A in Q];B=[A for A in A if A not in Q]
		if B:C.append(f"{where}: unknown entities {_c.join(B[:4])}")
		return D
	def N(v):
		try:return _C if v is _C else max(0,min(100,int(v)))
		except(TypeError,ValueError):return
	for I in rows:
		try:B=json.loads(I)if isinstance(I,str)else I
		except Exception:C.append(f"not valid JSON: {str(I)[:80]}");continue
		if not isinstance(B,dict):C.append(f"not an object: {str(I)[:80]}");continue
		A=str(B.get(_A)or'').strip()
		if not A:C.append('a record arrived with no name');continue
		if G==_j:
			D=K(B.get(_G),A)
			if not D:C.append(f"{A}: no usable entities");continue
			H.append({_A:A,_G:D,_H:N(B.get(_H))})
		elif G==_k:
			O=[]
			for(F,J)in enumerate(B.get(_n)or[],1):
				if not isinstance(J,dict):continue
				D=K(J.get(_G),f"{A} step {F}")
				if not D:continue
				try:R=max(1,min(3600,int(J.get(_o)or 8)))
				except(TypeError,ValueError):R=8
				O.append({_A:str(J.get(_A)or f"Step {F}")[:40],_o:R,_G:D,_H:N(J.get(_H))})
			if not O:C.append(f"{A}: no usable steps");continue
			H.append({_A:A,_p:bool(B.get(_p)),_n:O})
		elif G==_l:
			P=[]
			for(F,E)in enumerate(B.get(_q)or[],1):
				if not isinstance(E,dict):continue
				D=K(E.get(_G),f"{A} event {F}")
				if not D:continue
				S=U if str(E.get(_r))==U else V;L=str(E.get(_s)or W)
				if S==V and not re.fullmatch('\\d{1,2}:\\d{2}',L):C.append(f"{A} event {F}: bad time {L!r}, using 18:00");L=W
				Y=[A for A in E.get(_t)or[0,1,2,3,4,5,6]if isinstance(A,int)and 0<=A<=6]or[0,1,2,3,4,5,6]
				try:T=max(-720,min(720,int(E.get(_u)or 0)))
				except(TypeError,ValueError):T=0
				P.append({_A:str(E.get(_A)or f"Event {F}")[:40],_AB:_I,_r:S,_s:L,_v:X if str(E.get(_v))==X else'sunset',_u:T,_t:Y,_G:D,_H:N(E.get(_H))})
			if not P:C.append(f"{A}: no usable events");continue
			H.append({_A:A,_q:P})
		elif G==_m:
			D=K(B.get(_M),A)
			if not D:C.append(f"{A}: no usable lights");continue
			def M(v,lo,hi,dflt):
				try:return max(lo,min(hi,int(v)))
				except(TypeError,ValueError):return dflt
			H.append({_A:A,_M:D,_w:M(B.get(_w),1000,6500,1800),_x:M(B.get(_x),1000,6500,4000),_y:M(B.get(_y),1,100,20),_z:M(B.get(_z),1,100,80)})
		else:C.append(f"{G}: not a writable module")
	return H,C
@websocket_api.websocket_command({vol.Required(_O):f"{DOMAIN}/ai_module_propose",vol.Required(_a):str,vol.Required(_S):str,vol.Optional(_h,default=''):str})
@websocket_api.async_response
async def ws_ai_module_propose(hass,connection,msg):
	I='records';D=hass;C=connection;B=msg;A=B[_a]
	if A=='related':C.send_error(B[_B],'read_only','Related is a read-only surface and proposes no changes');return
	if A not in _MODULE_RULES:C.send_error(B[_B],_AL,f"No AI support for {A!r}");return
	J={_j:_AC,_k:_AD,_l:_AE,_m:_AF}[A];G=(D.data.get(DOMAIN,{})or{}).get(J,{})or{};E=_entity_catalogue(D);K=_module_prompt(A,B.get(_h)or'',E,G)
	try:L=await D.services.async_call(_g,_A5,{_f:B[_S],_A6:f"buttons_machine_{A}",_A7:K,_A8:{I:{_P:'one compact JSON object per record, as a string',_Q:{_R:{'multiple':_I}}},_T:{_P:'one sentence on what you produced',_Q:{_R:_C}},_U:{_P:_AI,_Q:{_R:_C}}}},blocking=_I,return_response=_I)
	except Exception as H:_LOGGER.warning('AI %s propose failed: %s',A,H);C.send_error(B[_B],_A9,str(H));return
	F=(L or{}).get('data')or{};M,N=_validate_module(A,F.get(I)or[],E);C.send_result(B[_B],{_a:A,_V:M,_i:N,_T:F.get(_T)or'',_U:F.get(_U)or'',_AJ:len(E),'existing':len(G)})
@websocket_api.websocket_command({vol.Required(_O):f"{DOMAIN}/ai_module_apply",vol.Required(_a):str,vol.Required(_V):list})
@websocket_api.async_response
async def ws_ai_module_apply(hass,connection,msg):
	K=connection;E=msg;B=hass;C=E[_a]
	if C not in _MODULE_RULES:K.send_error(E[_B],_AL,f"No AI support for {C!r}");return
	S=_entity_catalogue(B);F,N=_validate_module(C,E[_V],S)
	if not F:K.send_error(E[_B],'invalid','; '.join(N[:4])or'nothing to write');return
	import uuid as H;from.import _impl as I,solar as O
	def L(ids,bri):return{A:{_AK:bri}if bri is not _C else{}for A in ids}
	J=B.data.setdefault(DOMAIN,{});G=0
	if C==_j:
		D=dict(J.get(_AC,{})or{})
		for A in F:D['sp_'+H.uuid4().hex[:8]]={_A:A[_A],'program':{_L:_AG,_A2:A[_G],_AA:L(A[_G],A[_H])}};G+=1
		await I._save_shared_programs(B,D)
	elif C==_k:
		P=dict(J.get(_AD,{})or{})
		for A in F:P['seq_'+H.uuid4().hex[:8]]={_A:A[_A],_O:'auto',_p:A[_p],_n:[{_A:A[_A],'status_led':'on',_o:A[_o],'scene_mode':'custom',_b:L(A[_G],A[_H])}for A in A[_n]]};G+=1
		await I._save_sequels(B,P)
	elif C==_l:
		Q=dict(J.get(_AE,{})or{})
		for A in F:Q['sch_'+H.uuid4().hex[:8]]={_A:A[_A],_q:[{_A:A[_A],_AB:_I,_r:A[_r],_s:A[_s],_v:A[_v],_u:A[_u],_t:A[_t],'action':{_N:_b,_b:L(A[_G],A[_H])}}for A in A[_q]]};G+=1
		await I._save_schedules(B,Q);I._get_schedule_engine(B).rearm()
	elif C==_m:
		D=dict(J.get(_AF,{})or{})
		for A in F:
			T=set(A[_M])
			for(U,M)in list(D.items()):
				R=[A for A in M.get(_M)or[]if A not in T]
				if len(R)!=len(M.get(_M)or[]):D[U]={**M,_M:R}
			D['sol_'+H.uuid4().hex[:8]]={_A:A[_A],_AB:_I,'on_manual':'release',_w:A[_w],_x:A[_x],_y:A[_y],_z:A[_z],'brightness_mode':'default','sunrise_offset_min':0,'sunset_offset_min':0,'interval_s':90,'transition_s':45,'detect_non_ha_changes':_I,_M:A[_M]};G+=1
		await O._save_solar(B,D);O._get_solar_manager(B).rearm_all()
	K.send_result(E[_B],{'written':G,_i:N})
@websocket_api.websocket_command({vol.Required(_O):f"{DOMAIN}/ai_ask",vol.Required('question'):str,vol.Required(_S):str})
@websocket_api.async_response
async def ws_ai_ask(hass,connection,msg):
	G=connection;F='answer';D=msg;C=hass;H=_entity_catalogue(C);I=_keypads(C);J=C.data.get(DOMAIN,{})or{};A=['You answer questions about a lighting installation. Be brief and concrete.','Name entities and buttons exactly as they appear. If the answer is not in','the data below, say so plainly rather than guessing.','','KEYPADS:']
	for E in I:
		K=f" in {E[_J]}"if E.get(_J)else'';A.append(f"  {E[_F]}{K}")
		for B in E[_K]:L=f' "{B[_W]}"'if B[_W]else'';A.append(f"    button {B[_D]}{L} — {B[_L]} ({B[_A1]} target(s))")
	for(M,N,O)in(('SHARED PROGRAMS',_AC,_A),('SEQUELS',_AD,_A),('SCHEDULES',_AE,_A),('SOLAR PROGRAMMES',_AF,_A)):P=J.get(N)or{};A.append(f"{M}: "+(_c.join(str(B.get(O)or A)for(A,B)in P.items())or'(none)'))
	A+=['',_A3];A+=[f"  {A[_B]} — {A[_A]}"+(f" — {A[_J]}"if A[_J]else'')for A in H];A+=['',f'QUESTION: "{D["question"]}"']
	try:Q=await C.services.async_call(_g,_A5,{_f:D[_S],_A6:'buttons_machine_ask',_A7:'\n'.join(A),_A8:{F:{_P:'the answer, a few sentences at most',_Q:{_R:{'multiline':_I}}}}},blocking=_I,return_response=_I)
	except Exception as R:G.send_error(D[_B],_A9,str(R));return
	G.send_result(D[_B],{F:((Q or{}).get('data')or{}).get(F)or''})