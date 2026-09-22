from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import init_db
from app import manifest

app = FastAPI(title='Artifex Protocol Core', version='1.0.0', description='Execution engine for the AI agent marketplace.')

app.add_middleware(CORSMiddleware, allow_origins=['*'\], allow_credentials=True, allow_methods=['*'\], allow_headers=['*'\])

@app.on_event('startup')
def startup_event():
    init_db()

app.include_router(manifest.router, prefix='/api/v1')

@app.get('/')
async def root():
    return {'status': 'online', 'protocol': 'Artifex Core'}
