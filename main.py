from __future__ import annotations

from documind.agent import DocumentProcessingPipeline
from documind.models import DocumentInput


def main() -> None:
    document = DocumentInput(
        doc_id="invoice-1024",
        document_type="invoice",
        file_url="https://example.com/invoice-1024.pdf",
        text="Invoice No.: INV-2024-0105\nDate: 2024-03-15\nVendor: Acme Corp\nTotal Amount: $1,245.67",
    )

    pipeline = DocumentProcessingPipeline()
    output = pipeline.process(document)

    print("Document extraction result:")
    for field, result in output["extracted_fields"].items():
        print(f"- {field}: {result['value']} (confidence {result['confidence']})")

    if output["review_queue"]:
        print("\nReview queue:")
        for item in output["review_queue"]:
            print(f"- {item['field_name']}: confidence {item['actual_confidence']} below threshold {item['required_threshold']}")


if __name__ == "__main__":
    main()
