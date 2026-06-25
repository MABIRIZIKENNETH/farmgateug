import json
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

class I18nMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.supported_languages = ['en', 'lg']
        self.default_language = 'en'
        self.translations = {}
        for lang in self.supported_languages:
            path = os.path.join('locales', f'{lang}.json')
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    self.translations[lang] = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                print(f"Warning: Could not load translations for '{lang}' from {path}. Using empty dict.")
                self.translations[lang] = {}

    async def dispatch(self, request: Request, call_next):
        lang = request.cookies.get('lang')
        if not lang:
            accept = request.headers.get('accept-language', '')
            for part in accept.split(','):
                tag = part.split(';')[0].strip()
                if tag in self.supported_languages:
                    lang = tag
                    break
        if not lang:
            lang = self.default_language

        request.state.lang = lang
        request.state.translations = self.translations.get(lang, {})
        request.state.default_lang = self.default_language

        response = await call_next(request)
        return response

def get_translations(request: Request):
    return request.state.translations

def get_lang(request: Request):
    return request.state.lang
