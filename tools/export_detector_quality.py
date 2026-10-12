"""Publish only aggregate synthetic evaluation metrics for the local React UI."""
import json
from pathlib import Path

def main():
    root = Path(__file__).resolve().parents[1]
    output = {'dataset': 'Synthetic labeled evaluation dataset', 'cases': None, 'policies': []}
    for name, fallback in [('baseline', '1.0'), ('hardened', '1.1')]:
        report = json.loads((root/f'detector_eval_{name}.json').read_text(encoding='utf-8'))
        overall = report['overall']
        output['cases'] = overall['cases']
        output['policies'].append({'version': report.get('detector_policy_version', fallback),
                                  'precision': overall['precision'], 'recall': overall['recall'],
                                  'f1': overall['f1'], 'review_rate': overall['rates']['REVIEW']})
    target = root/'frontend/src/lib/detector-quality.json'
    target.write_text(json.dumps(output, indent=2)+'\n', encoding='utf-8')
    print('Exported aggregate synthetic metrics. Evaluation evidence was not modified.')

if __name__ == '__main__':
    main()
