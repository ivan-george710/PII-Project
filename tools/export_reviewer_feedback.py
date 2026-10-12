"""Explicit offline export; optional sensitive bounded context never enabled by default."""
import argparse
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--audit-store',required=True)
    p.add_argument('--document-id',required=True)
    p.add_argument('--output-directory',default='.private_feedback')
    p.add_argument('--include-context',action='store_true')
    p.add_argument('--detector-version',default='unknown-legacy')
    p.add_argument('--source-category',choices=['reviewed_document','synthetic','demonstration','curated'],default='reviewed_document')
    args=p.parse_args()
    from app.engines.audit import AuditEngine
    from app.engines.audit.feedback_export import export_feedback
    audit=AuditEngine(storage_dir=args.audit_store).load_audit(args.document_id)
    export_feedback(audit,directory=args.output_directory,include_context=args.include_context,
                    detector_version=args.detector_version,source_category=args.source_category)
    print('Private feedback export completed; requires deliberate curation.')


if __name__=='__main__': main()
