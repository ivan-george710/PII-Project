# Local demo scripts

`run-demo.py` starts employee processing and opens the cloud manager by default. `REMOTE_MANAGER_URL` can override that origin; `--local-manager` starts a separate offline manager on 8766. The root `run.py` delegates to this launcher. `create_demo_samples.py` generates fictional PDFs, scanned documents, images, faces, DOCX and PPTX in the ignored `demo/samples/` directory. The sample API creates missing defaults automatically. `setup-local.sh` prepares Python/frontend dependencies and the spaCy model. Full documents and processing stay local.
