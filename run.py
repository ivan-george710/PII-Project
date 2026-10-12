"""Start the trusted local demo. Access logs are disabled to keep review inputs private."""
import uvicorn

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8765, access_log=False,
                log_level="warning", proxy_headers=False, limit_concurrency=4)
