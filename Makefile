.PHONY: docker-build docker-run

docker-build:
	docker build -t adobe-helper -f examples/adobe/Dockerfile .

docker-run: docker-build
	docker run --rm \
		-e ADOBE_HELPER_ENDPOINTS_FILE=/app/docs/discovery/discovered_endpoints.json \
		adobe-helper
