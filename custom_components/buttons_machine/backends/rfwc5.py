_A=True
import importlib.util as _u,os as _os,pathlib as _pl,platform as _p,shutil as _sh,sys as _s
_name=__name__.rsplit('.',1)[-1]
_here=_pl.Path(__file__).resolve()
_root=_here.parent/'_native'
_src=_root/_p.machine()/f"{_name}.abi3.so"
_introot=next((p for p in _here.parents if(p/'manifest.json').is_file()),_here.parent)
_pkg=_introot.name
if not _src.exists():_have=', '.join(p.name for p in _root.iterdir())if _root.exists()else'none';raise ImportError(f"{_pkg}: no native build of {_name!r} for CPU arch {_p.machine()!r} (have: {_have}).")
try:
	_st=_src.stat();_digest=f"{_st.st_size:x}-{_st.st_mtime_ns:x}";_cache=_introot.parent.parent/f".{_pkg}_native"/_p.machine();_dst=_cache/f"{_name}-{_digest}.abi3.so"
	if not(_dst.exists()and _dst.stat().st_size==_st.st_size):
		_cache.mkdir(parents=_A,exist_ok=_A);_tmp=_cache/f"{_name}-{_digest}.{_os.getpid()}.tmp";_sh.copy2(_src,_tmp);_copied=_tmp.stat().st_size
		if _copied!=_st.st_size:_tmp.unlink(missing_ok=_A);raise OSError(f"{_pkg}: cached copy of {_name} is {_copied} bytes, expected {_st.st_size} — loading in place instead")
		_os.replace(_tmp,_dst)
		try:
			_mine=sorted(_cache.glob(f"{_name}-*.abi3.so"),key=lambda q:q.stat().st_mtime,reverse=_A)
			for _old in _mine[3:]:_old.unlink(missing_ok=_A)
		except Exception:pass
	_load=_dst
except Exception:_load=_src
_spec=_u.spec_from_file_location(__name__,_load)
_mod=_u.module_from_spec(_spec)
_mod.__file__=str(_src)
_s.modules[__name__]=_mod
_spec.loader.exec_module(_mod)
globals().update({k:v for(k,v)in vars(_mod).items()if not k.startswith('__')})