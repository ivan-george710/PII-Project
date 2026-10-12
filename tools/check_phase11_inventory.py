"""Recheck media inventory against saved diagnostics without OCR or inference."""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from app.engines.extraction.docx import extract_docx
    from app.engines.extraction.pptx import extract_pptx
    from app.engines.extraction.models import PDFSourceMap
    from app.engines.visual_detection import VisualInspectionEngine
    from app.engines.extraction.office import source_hash
    from tools.validate_cadence_document import restore_extraction
    saved = json.loads((ROOT / 'phase11_visual_diagnostic.json').read_text(encoding='utf-8'))
    results = {}
    for kind in ('pdf', 'docx', 'pptx'):
        paths = list(ROOT.glob('Cadence_*.' + kind))
        if len(paths) != 1:
            raise ValueError('Source is not uniquely available')
        path = paths[0]
        evidence = json.loads((ROOT / '.private_phase11/real-documents' / (kind + '_internal.json')).read_text(encoding='utf-8'))
        if source_hash(path) != evidence['source_sha256']:
            raise ValueError('Source changed since diagnostic')
        if kind == 'pdf':
            extraction = restore_extraction(evidence['extraction'])
            extraction.pdf_source = PDFSourceMap(evidence['source_sha256'],
                {str(p.page_number): 150 for p in extraction.pages if p.extraction_method == 'ocr'})
        else:
            extraction = {'docx': extract_docx, 'pptx': extract_pptx}[kind](path)
        inspection = VisualInspectionEngine(SimpleNamespace(detect=lambda _: [])).inspect(extraction)
        previous = saved[kind]['visual_privacy']
        matched = len(inspection.units) == previous['inspected_visual_units'] and inspection.unsupported == previous['unsupported']
        results[kind] = {'inventory_matches': matched, 'inspected_visual_units': len(inspection.units),
                         'unsupported': inspection.unsupported, 'ocr_runs': 0, 'inference_runs': 0}
        if not matched:
            raise ValueError('Saved visual inventory requires updated diagnostics')
    (ROOT / 'phase11_inventory_check.json').write_text(json.dumps(results, indent=2))
    print(json.dumps(results))


if __name__ == '__main__':
    main()
