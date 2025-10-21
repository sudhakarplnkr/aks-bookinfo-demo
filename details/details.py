#!/usr/bin/env python3
"""
Converted details service from Ruby to Python (Flask).
Provides:
 - GET /health
 - GET /details/<id>

Environment variables:
 - ENABLE_EXTERNAL_BOOK_SERVICE (true/false)
 - DO_NOT_ENCRYPT (true/false) -> if true use http when calling external API
"""
from flask import Flask, request, jsonify
import os
import sys
import requests

app = Flask(__name__)

ENABLE_EXTERNAL = os.environ.get('ENABLE_EXTERNAL_BOOK_SERVICE', 'false').lower() == 'true'
DO_NOT_ENCRYPT = os.environ.get('DO_NOT_ENCRYPT', 'false').lower() == 'true'


@app.route('/health')
def health():
    return jsonify({'status': 'Details is healthy'})


def get_isbn(book, isbn_type):
    ids = [ident for ident in book.get('industryIdentifiers', []) if ident.get('type') == isbn_type]
    return ids[0]['identifier'] if ids else None


def fetch_details_from_external_service(isbn, _id, headers):
    scheme = 'http' if DO_NOT_ENCRYPT else 'https'
    url = f"{scheme}://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        resp.raise_for_status()
        json_data = resp.json()
        book = json_data.get('items', [])[0].get('volumeInfo', {})
        language = 'English' if book.get('language') == 'en' else 'unknown'
        ptype = 'paperback' if book.get('printType') == 'BOOK' else 'unknown'
        isbn10 = get_isbn(book, 'ISBN_10')
        isbn13 = get_isbn(book, 'ISBN_13')
        return {
            'id': _id,
            'author': book.get('authors', [None])[0],
            'year': book.get('publishedDate'),
            'type': ptype,
            'pages': book.get('pageCount'),
            'publisher': book.get('publisher'),
            'language': language,
            'ISBN-10': isbn10,
            'ISBN-13': isbn13,
        }
    except Exception as e:
        raise RuntimeError(f"external service error: {e}")


def get_book_details(_id, headers):
    if ENABLE_EXTERNAL:
        # Use a sample ISBN from original script
        isbn = '0486424618'
        return fetch_details_from_external_service(isbn, _id, headers)

    return {
        'id': _id,
        'author': 'William Shakespeare',
        'year': 1595,
        'type': 'paperback_1',
        'pages': 200,
        'publisher': 'PublisherA',
        'language': 'English',
        'ISBN-10': '1234567890',
        'ISBN-13': '123-1234567890'
    }


def get_forward_headers(req):
    headers = {}
    incoming_headers = [
        'x-request-id',
        'x-ot-span-context',
        'x-datadog-trace-id',
        'x-datadog-parent-id',
        'x-datadog-sampling-priority',
        'traceparent',
        'tracestate',
        'x-cloud-trace-context',
        'grpc-trace-bin',
        'x-b3-traceid',
        'x-b3-spanid',
        'x-b3-parentspanid',
        'x-b3-sampled',
        'x-b3-flags',
        'sw8',
        'end-user',
        'user-agent',
        'cookie',
        'authorization',
        'jwt'
    ]
    for h in incoming_headers:
        v = req.headers.get(h)
        if v is not None:
            headers[h] = v
    return headers


@app.route('/details', defaults={'item_id': None})
@app.route('/details/<item_id>')
def details(item_id):
    headers = get_forward_headers(request)
    try:
        if item_id is None:
            raise ValueError('please provide numeric product id')
        try:
            _id = int(item_id)
        except Exception:
            raise ValueError('please provide numeric product id')
        details = get_book_details(_id, headers)
        return jsonify(details)
    except ValueError as ve:
        return jsonify({'error': str(ve)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} port", file=sys.stderr)
        sys.exit(-1)
    port = int(sys.argv[1])
    # Use 0.0.0.0 to listen on all interfaces
    app.run(host='0.0.0.0', port=port)
