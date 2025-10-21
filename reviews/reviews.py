#!/usr/bin/env python3
"""
Python port of the reviews service.
Provides:
 - GET /health
 - GET /reviews/<productId>

Reads these env vars:
 - ENABLE_RATINGS (true/false)
 - STAR_COLOR
 - RATINGS_HOSTNAME, RATINGS_SERVICE_PORT
 - SERVICES_DOMAIN

It will call the ratings service when ENABLE_RATINGS is true and include rating stars in the returned JSON.
"""
import os
import requests
from flask import Flask, jsonify, request

app = Flask(__name__)

ENABLE_RATINGS = os.environ.get('ENABLE_RATINGS', 'false').lower() == 'true'
STAR_COLOR = os.environ.get('STAR_COLOR', 'black')
SERVICES_DOMAIN = '' if os.environ.get('SERVICES_DOMAIN') is None else ('.' + os.environ.get('SERVICES_DOMAIN'))
RATINGS_HOSTNAME = os.environ.get('RATINGS_HOSTNAME', 'ratings')
RATINGS_PORT = os.environ.get('RATINGS_SERVICE_PORT', '9080')
RATINGS_URL = f"http://{RATINGS_HOSTNAME}{SERVICES_DOMAIN}:{RATINGS_PORT}/ratings"

HEADERS_TO_PROPAGATE = [
    'x-request-id','x-ot-span-context','x-datadog-trace-id','x-datadog-parent-id','x-datadog-sampling-priority',
    'traceparent','tracestate','x-cloud-trace-context','grpc-trace-bin','x-b3-traceid','x-b3-spanid','x-b3-parentspanid',
    'x-b3-sampled','x-b3-flags','sw8','end-user','user-agent','cookie','authorization','jwt'
]


def get_json_response(productId, starsReviewer1, starsReviewer2):
    podname = os.environ.get('HOSTNAME')
    clustername = os.environ.get('CLUSTER_NAME')
    reviews = [
        {
            'reviewer': 'Reviewer1',
            'text': "An extremely entertaining play by Shakespeare. The slapstick humour is refreshing!"
        },
        {
            'reviewer': 'Reviewer2',
            'text': "Absolutely fun and entertaining. The play lacks thematic depth when compared to other plays by Shakespeare."
        }
    ]

    if ENABLE_RATINGS:
        if starsReviewer1 != -1:
            reviews[0]['rating'] = {'stars': starsReviewer1, 'color': STAR_COLOR}
        else:
            reviews[0]['rating'] = {'error': 'Ratings service is currently unavailable'}
        if starsReviewer2 != -1:
            reviews[1]['rating'] = {'stars': starsReviewer2, 'color': STAR_COLOR}
        else:
            reviews[1]['rating'] = {'error': 'Ratings service is currently unavailable'}

    return {
        'id': str(productId),
        'podname': podname,
        'clustername': clustername,
        'reviews': reviews
    }


def get_ratings(productId):
    headers = {}
    for h in HEADERS_TO_PROPAGATE:
        val = request.headers.get(h)
        if val is not None:
            headers[h] = val
    try:
        timeout = 10 if STAR_COLOR == 'black' else 2.5
        resp = requests.get(f"{RATINGS_URL}/{productId}", headers=headers, timeout=timeout)
        if resp.status_code == 200:
            return resp.json()
        else:
            app.logger.error(f"Error: unable to contact {RATINGS_URL} got status of {resp.status_code}")
            return None
    except Exception as e:
        app.logger.error(f"Error: unable to contact {RATINGS_URL} got exception {e}")
        return None


@app.route('/health')
def health():
    return jsonify({'status': 'Reviews is healthy'})


@app.route('/reviews/<int:productId>')
def reviews(productId):
    starsReviewer1 = -1
    starsReviewer2 = -1
    if ENABLE_RATINGS:
        ratings_response = get_ratings(productId)
        if ratings_response and 'ratings' in ratings_response:
            ratings = ratings_response['ratings']
            if 'Reviewer1' in ratings:
                starsReviewer1 = ratings['Reviewer1']
            if 'Reviewer2' in ratings:
                starsReviewer2 = ratings['Reviewer2']
    return jsonify(get_json_response(productId, starsReviewer1, starsReviewer2))


if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print(f"usage: {sys.argv[0]} port")
        sys.exit(-1)
    port = int(sys.argv[1])
    app.run(host='0.0.0.0', port=port)
