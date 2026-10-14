"""Local-only development entrypoint. Never binds beyond loopback."""
import uvicorn
from .app import create_app,Settings

def main():
    uvicorn.run(create_app(Settings(secure_cookies=False)),host='127.0.0.1',port=8788,workers=1)
if __name__=='__main__':main()
