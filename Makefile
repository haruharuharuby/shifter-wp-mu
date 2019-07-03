.PHONY: preview
preview: package
	unzip -l .serverless/docker-swarm-controller.zip

.PHONY: package
package: depends
	find vendored -name *.pyc -type f -delete
	sls package

.PHONY: depends
depends:
	rm -rf ./vendored
	pip install -r requirements.txt -t ./vendored
