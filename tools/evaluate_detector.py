"""Reproducible local evaluation. REVIEW is never an automatic true positive."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
from time import perf_counter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def key(span):
    return span['start'], span['end'], span['entity_type']


def metrics(gold, confirmed, reviewed):
    gold, confirmed, reviewed = set(gold), set(confirmed), set(reviewed)
    tp, fp, fn = len(gold & confirmed), len(confirmed-gold), len(gold-confirmed)
    precision = tp/(tp+fp) if tp+fp else 0.0
    recall = tp/(tp+fn) if tp+fn else 0.0
    return dict(tp=tp, fp=fp, fn=fn, precision=precision, recall=recall,
                f1=2*precision*recall/(precision+recall) if precision+recall else 0.0,
                potential_recall=len(gold & (confirmed|reviewed))/len(gold) if gold else 0.0,
                review_true_spans=len((reviewed-confirmed)&gold), review_false_spans=len(reviewed-gold))


def review_category(d):
    if d.entity_type in {'US_BANK_NUMBER','US_DRIVER_LICENSE'}: return 'context_sensitive_identifier'
    if d.entity_type == 'PERSON': return 'ambiguous_person'
    if d.confidence < .5: return 'low_confidence'
    return d.validation_reason or 'unspecified'


def summarize(rows):
    gold, confirmed, review = set(), set(), set()
    decisions, categories, reasons = Counter(), Counter(), Counter()
    fp_categories, fn_categories = Counter(), Counter()
    duplicates = 0
    for row in rows:
        prefix = row['id']
        g = {(prefix,*key(s)) for s in row['expected']}
        c = {(prefix,*key(s)) for s in row['candidates'] if s['decision']=='CONFIRM'}
        r = {(prefix,*key(s)) for s in row['candidates'] if s['decision']=='REVIEW'}
        gold |= g; confirmed |= c; review |= r
        duplicates += len(row['candidates'])-len({key(s) for s in row['candidates']})
        fp_categories[row['category']] += len(c-g)
        fn_categories[row['category']] += len(g-c)
        for s in row['candidates']:
            decisions[s['decision']] += 1
            if s['decision']=='REVIEW':
                categories[s['review_category']] += 1
                reasons[s['reason']] += 1
    raw = sum(decisions.values())
    types = sorted({s[-1] for s in gold|confirmed|review})
    return dict(cases=len(rows), gold_spans=len(gold), raw_candidates=raw, decisions=dict(decisions),
                rates={d:decisions[d]/raw if raw else 0 for d in ['CONFIRM','REJECT','REVIEW']},
                duplicate_candidates=duplicates, **metrics(gold,confirmed,review),
                per_entity={e:metrics({s for s in gold if s[-1]==e}, {s for s in confirmed if s[-1]==e},
                                    {s for s in review if s[-1]==e}) for e in types},
                review_categories=dict(categories), review_reasons=dict(reasons),
                false_positive_categories=dict(fp_categories), false_negative_categories=dict(fn_categories))


def evaluate(engine, dataset, split='all'):
    from app.engines.extraction.models import ExtractionResult, ExtractedPage
    rows=[]
    for case in dataset['cases']:
        if split!='all' and case['split']!=split: continue
        result = engine.detect(ExtractionResult(Path('synthetic.txt'),'synthetic.txt','text',
            [ExtractedPage(1,case['text'],'text')]))
        assert result.disposition_count == result.raw_candidate_count
        candidates=[]
        for d in result.detections+result.rejected+result.review:
            candidates.append(dict(start=d.start,end=d.end,entity_type=d.entity_type,
                decision=d.final_decision,reason=d.validation_reason,confidence=d.confidence,
                recognizer=d.recognizer,review_category=review_category(d)))
        rows.append(dict(id=case['id'],category=case['category'],split=case['split'],
                         expected=case['expected'],candidates=candidates))
    return dict(overall=summarize(rows),
                splits={s:summarize([r for r in rows if r['split']==s]) for s in ['development','heldout']},
                examples=rows)


def policy_fingerprint():
    return {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((ROOT/'app/engines/pii_detection').glob('*.py'))}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',required=True)
    p.add_argument('--split',choices=['all','development','heldout'],default='all')
    args=p.parse_args()
    from app.engines.pii_detection import PIIDetectionEngine
    from app.engines.pii_detection import validation
    path=ROOT/'tests/data/detector_evaluation.json'
    dataset=json.loads(path.read_text(encoding='utf-8'))
    started=perf_counter()
    engine=PIIDetectionEngine()
    result=evaluate(engine,dataset,args.split)
    result.update(detector_policy_version=getattr(validation,'DETECTOR_POLICY_VERSION','1.0'),
                  dataset_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                  policy_fingerprint=policy_fingerprint(), elapsed_seconds=perf_counter()-started,
                  recognizers=[dict(name=r.name,entities=r.supported_entities)
                               for r in engine.analyzer.registry.recognizers],
                  default_score_threshold=engine.analyzer.default_score_threshold)
    output=Path(args.output)
    if output.exists(): raise ValueError('Refusing to overwrite evaluation evidence')
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    output.with_suffix('.md').write_text('# Detector evaluation\n\nVersion: '+result['detector_policy_version']+
        '\n\nExact-span automated metrics and separate potential recall:\n\n```json\n'+
        json.dumps({k:v for k,v in result.items() if k not in {'examples','recognizers','policy_fingerprint'}},indent=2)+'\n```\n',encoding='utf-8')
    print(json.dumps({'version':result['detector_policy_version'],'overall':result['overall'],
                      'elapsed_seconds':result['elapsed_seconds']}))


if __name__=='__main__': main()
