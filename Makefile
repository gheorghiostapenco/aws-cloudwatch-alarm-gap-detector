LAMBDA_DIR=lambda_app
OUTPUT=lambda.zip

.PHONY: build clean upload

build:
	@echo "Building Lambda package..."
	cd $(LAMBDA_DIR) && zip -r ../$(OUTPUT) .

clean:
	rm -f $(OUTPUT)

upload:
	@if [ -z "$(BUCKET)" ] || [ -z "$(KEY)" ]; then \
		echo "Usage: make upload BUCKET=your-bucket KEY=your-key.zip"; \
		exit 1; \
	fi
	aws s3 cp $(OUTPUT) s3://$(BUCKET)/$(KEY)
