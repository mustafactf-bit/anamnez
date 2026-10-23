"""Offline synthetic benchmark; real inference requires an explicit GGUF path.

Fixture retrieval checks wiring and citation membership, not clinical accuracy.
Question/query quality requires blinded clinician scoring in addition to proxies.
"""
import argparse
import ctypes
import json
import sys
import time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ai.llm_engine import GGUFEngine
from ai.clinical_parser import extract_anamnesis
from ai.question_generator import generate_questions
from ai.evidence_synthesizer import synthesize
from literature.query_builder import build_query
from literature.pubmed_client import Article
from settings import Settings


def peak_ram_bytes():
    """Process lifetime peak working set, including native model allocations."""
    if sys.platform=='win32':
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_=[('cb',wintypes.DWORD),('faults',wintypes.DWORD)]+[(name,ctypes.c_size_t) for name in ('peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
        counters=Counters();counters.cb=ctypes.sizeof(counters)
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.GetCurrentProcess.restype=wintypes.HANDLE
        psapi=ctypes.WinDLL('psapi',use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.DWORD]
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):return None
        return counters.peak
    try:
        import resource
        peak=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        return peak if sys.platform=='darwin' else peak*1024
    except ImportError:return None


def main():
    """Emit measured JSON; never fabricate a successful model run."""
    parser=argparse.ArgumentParser()
    parser.add_argument('--model',required=True)
    parser.add_argument('--cases',default=str(Path(__file__).with_name('cases.json')))
    parser.add_argument('--output',default='benchmark-results.json')
    args=parser.parse_args()
    engine=GGUFEngine(Settings(model_path=args.model))
    cases=json.loads(Path(args.cases).read_text(encoding='utf-8'))
    results=[]
    for case in cases:
        start=time.perf_counter();tokens=0
        row={'case':case['id'],'retrieval':'offline synthetic fixture','clinical_quality':'requires clinician review'}
        try:
            structured=extract_anamnesis(engine,case['transcript']);tokens+=engine.last_usage.get('completion_tokens',0)
            row['extraction_exact_field_accuracy']=sum(structured[k]==v for k,v in case['expected'].items())/len(case['expected'])
            questions=generate_questions(engine,structured);tokens+=engine.last_usage.get('completion_tokens',0)
            row['question_schema_valid']=True;row['question_count']=len(questions)
            safe=0
            for q in questions:
                try:build_query(q['concepts']);safe+=1
                except ValueError:pass
            row['safe_query_fraction']=safe/len(questions)
            # A deliberately synthetic abstract, never published/displayed as real.
            fixture=[Article('1','SYNTHETIC BENCHMARK FIXTURE — not a publication',
                'Synthetic benchmark fixture: findings are insufficient for clinical recommendations.')]
            summary=synthesize(engine,questions[0]['question'],fixture,engine.settings.context_size)
            tokens+=engine.last_usage.get('completion_tokens',0)
            row['citation_membership_valid']=bool(summary['claims'])
            row['status']='completed'
        except Exception as error:
            row['status']='failed';row['error_type']=type(error).__name__
        finally:engine.unload()
        row.update(seconds=time.perf_counter()-start,peak_process_ram_bytes=peak_ram_bytes(),output_tokens=tokens)
        results.append(row)
    Path(args.output).write_text(json.dumps({'model':Path(args.model).name,'results':results},ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if all(x['status']=='completed' for x in results) else 1

if __name__=='__main__':raise SystemExit(main())
