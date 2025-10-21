# Copyright Istio Authors
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

FROM python:3.13.3-slim

WORKDIR /opt/microservices

COPY requirements.txt /opt/microservices/requirements.txt
RUN python -m pip install --no-cache-dir -r /opt/microservices/requirements.txt

COPY reviews.py /opt/microservices/

ARG service_version
ARG enable_ratings
ARG star_color
ENV SERVICE_VERSION=${service_version:-v1}
ENV ENABLE_RATINGS=${enable_ratings:-false}
ENV STAR_COLOR=${star_color:-black}

EXPOSE 9080
CMD ["python", "reviews.py", "9080"]
